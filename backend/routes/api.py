"""
HTTP API 层（Flask Blueprint「api」）。

职责边界：
  · 只做「取请求参数 → 调 logic/services → 拼 JSON/二进制响应」，不写业务分支判断（分支在 logic.task_parser）。
  · 前端主要入口：POST /api/send-task；朗读：POST /api/tts；划词翻译、图表、图片、听写见各路由。
"""
import asyncio  # 同步 Flask 视图里调用 async 讯飞 TTS 时用 asyncio.run
import logging
import os

from flask import Blueprint, Response, jsonify, request  # Response：直接返回音频字节流

from config import (
    MAX_TTS_CHARS,
    USE_XFYUN_SUPER_TTS,
    XFYUN_API_KEY,
    XFYUN_API_SECRET,
    XFYUN_APP_ID,
    XFYUN_DEFAULT_VCN_FEMALE,
    XFYUN_TTS_DISK_CACHE,
    XFYUN_TTS_SPEED,
    XFYUN_TTS_VOLUME,
    xfyun_vcn_ok,
)
from logic.dialogue_manager import get_dialogue_manager
from logic.task_parser import (
    analyze_uploaded_image,
    build_chart_payload,
    dashscope_poll_image,
    generate_demo_chart_points,
    normalize_chat_history,
    parse_chart_file,
    parse_command,
    remember_chat_turn,
    resolve_chart_points_from_task,
    translate_selected_text,
    with_workflow,
)
from logic.user_apps import (
    add_user_app,
    pick_exe_windows_blocking,
    remove_user_app,
    user_apps_public_list,
)
import session
from services.xfyun_iat import transcribe_wav_bytes
from services.xfyun_tts import (
    async_xfyun_tts_audio,
    plain_text_for_tts,
    tts_cache_file,
    xfyun_response_is_mp3,
)

try:
    import websockets  # 讯飞 TTS / IAT 的 WebSocket 客户端依赖
except ImportError:
    websockets = None

api_bp = Blueprint("api", __name__)  # 路由前缀在各自 @route 里写全路径 /api/...
logger = logging.getLogger(__name__)


@api_bp.route("/api/translate-selection", methods=["POST"])
def translate_selection():
    """划词翻译：body JSON { text, targetLang } → { code, translation }。"""
    try:
        data = request.json or {}
        text = (data.get("text") or "").strip()
        target_lang = (data.get("targetLang") or "en").strip().lower()
        if target_lang not in {"zh", "en"}:
            target_lang = "en"
        if not text:
            return jsonify({"code": 400, "translation": "请选择要翻译的文字。"})
        if len(text) > 2000:
            text = text[:2000]
        return jsonify({"code": 200, "translation": translate_selected_text(text, target_lang)})
    except Exception as e:
        logger.error("translate_selection error: %s", e)
        return jsonify({"code": 500, "translation": f"翻译失败: {str(e)}"})


@api_bp.route("/api/image-status/<task_id>", methods=["GET"])
def image_status(task_id):
    """文生图异步任务：前端用 task_id 轮询，直到 status 成功或失败。"""
    try:
        status, url = dashscope_poll_image(task_id)
        resp = {"status": status}
        if url:
            resp["imageUrl"] = url
        return jsonify(resp)
    except Exception as e:
        logger.error("image_status error: %s", e)
        return jsonify({"status": "failed"})


@api_bp.route("/api/analyze-image", methods=["POST"])
def analyze_image_upload():
    """multipart：字段 image + question + kind → 百炼 VL 或肤质分支；返回 reply、workflow。"""
    try:
        file_storage = request.files.get("image")
        question = request.form.get("question", "")
        kind = request.form.get("kind", "")
        answer, flow, extras = analyze_uploaded_image(file_storage, question, kind)
        return jsonify({
            "code": 200,
            "reply": answer,
            "type": "chat",
            "mode": extras.get("mode", "vision"),
            "modeLabel": extras.get("modeLabel", "图片理解"),
            "workflow": flow,
        })
    except Exception as e:
        logger.error("analyze_image_upload error: %s", e)
        return jsonify({"code": 500, "reply": f"图片分析失败: {str(e)}", "type": "chat"})


@api_bp.route("/api/tts", methods=["POST"])
def tts_xfyun():
    """
    朗读：JSON { text, voice, speed?, volume? }。
    成功时返回 audio/wav 或 audio/mpeg 二进制；失败时返回 JSON { code, reply }。
    """
    if websockets is None:
        return jsonify({"code": 503, "reply": "未安装 websockets，请在 backend 执行：pip install websockets"}), 503
    if not (XFYUN_APP_ID and XFYUN_API_KEY and XFYUN_API_SECRET):
        return jsonify({
            "code": 503,
            "reply": "未配置讯飞语音：在 backend/.env 填写 XFYUN_APP_ID、XFYUN_API_KEY、XFYUN_API_SECRET（可参考 .env.example）",
        }), 503

    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    voice_in = (data.get("voice") or "").strip()
    voice_key = voice_in.lower()
    try:
        speed = int(data.get("speed", XFYUN_TTS_SPEED))
    except (TypeError, ValueError):
        speed = XFYUN_TTS_SPEED
    try:
        volume = int(data.get("volume", XFYUN_TTS_VOLUME))
    except (TypeError, ValueError):
        volume = XFYUN_TTS_VOLUME
    speed = max(0, min(100, speed))
    volume = max(0, min(100, volume))

    # 前端 voice 传枚举或直传讯飞 vcn 字符串；非法则回默认女声
    if voice_key == "female":
        vcn = XFYUN_DEFAULT_VCN_FEMALE
    elif voice_key == "female_jiuxu":
        vcn = "x5_lingyuzhao_flow" if USE_XFYUN_SUPER_TTS else "aisjiuxu"
    elif voice_key in ("female_xiaoqi", "female_xiaoyu", "male_yunxi", "male"):
        vcn = XFYUN_DEFAULT_VCN_FEMALE
    elif xfyun_vcn_ok(voice_in):
        vcn = voice_in
    else:
        vcn = XFYUN_DEFAULT_VCN_FEMALE

    if not text:
        return jsonify({"code": 400, "reply": "缺少朗读文本 text"}), 400
    if len(text) > MAX_TTS_CHARS:
        text = text[:MAX_TTS_CHARS]

    spoken = plain_text_for_tts(text)
    if not spoken.strip():
        return jsonify({"code": 400, "reply": "清洗后无可朗读文本（可能仅为格式符号）"}), 400

    audio_fmt = "mp3" if xfyun_response_is_mp3(spoken) else "wav"
    cache_path = tts_cache_file(vcn, speed, volume, spoken, audio_fmt) if XFYUN_TTS_DISK_CACHE else None
    try:
        if cache_path and cache_path.is_file():
            blob = cache_path.read_bytes()
            if blob:
                return Response(
                    blob,
                    mimetype="audio/wav" if audio_fmt == "wav" else "audio/mpeg",
                    headers={
                        "Cache-Control": "no-store",
                        "X-TTS-Cache": "hit",
                        "X-TTS-VCN": vcn,
                        "X-TTS-Engine": "super" if USE_XFYUN_SUPER_TTS else "classic",
                    },
                )

        audio_blob, audio_mime, engine_tag = asyncio.run(async_xfyun_tts_audio(spoken, vcn, speed, volume))
        if not audio_blob:
            return jsonify({"code": 500, "reply": "合成失败：无音频数据"}), 500

        if cache_path:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_suffix = ".tmp.wav" if audio_fmt == "wav" else ".tmp.mp3"
            tmp = cache_path.with_suffix(tmp_suffix)
            tmp.write_bytes(audio_blob)
            tmp.replace(cache_path)

        resp_vcn = vcn if engine_tag != "classic-fallback" else f"{vcn}→classic"
        return Response(
            audio_blob,
            mimetype=audio_mime,
            headers={
                "Cache-Control": "no-store",
                "X-TTS-Cache": "miss" if cache_path else "off",
                "X-TTS-VCN": resp_vcn,
                "X-TTS-Engine": engine_tag,
            },
        )
    except Exception as e:
        logger.error("xfyun-tts error: %s", e)
        err_text = str(e)
        if "11200" in err_text or "licc" in err_text.lower():
            if USE_XFYUN_SUPER_TTS:
                err_text = (
                    "发音人未授权（11200）：超拟人需在控制台领取该 vcn；若已自动降级仍失败，"
                    "请检查在线合成发音人或暂时清空 XFYUN_SUPER_TTS_WS_URL 仅用经典音库。"
                )
            else:
                err_text = (
                    "发音人未授权（11200）：控制台 → 在线语音合成 → 发音人，"
                    "仅可使用已为该应用添加的 vcn。"
                )
        return jsonify({"code": 500, "reply": f"讯飞语音合成失败：{err_text}"}), 500


@api_bp.route("/api/generate-chart", methods=["POST"])
def generate_chart_upload():
    """multipart：可选 file + task 文案；解析数值列 → chartData + workflow。"""
    try:
        task = request.form.get("task", "生成柱状图")
        file_storage = request.files.get("file")
        if file_storage and file_storage.filename:
            points = parse_chart_file(file_storage)
            source = file_storage.filename
            if len(points) < 2:
                points, source = (
                    generate_demo_chart_points(task),
                    "模拟示例数据（文件中未解析出至少两组有效数据，已自动生成）",
                )
        else:
            points, source = resolve_chart_points_from_task(task)
        payload = build_chart_payload(task, points, source)
        payload = with_workflow(
            payload,
            ("接收数据", source),
            ("解析数据", "读取前两列作为名称和值"),
            ("统计摘要", "计算总数、最大值、最小值"),
            ("生成图表", "前端 SVG 可视化渲染"),
        )
        return jsonify({
            "code": 200,
            "reply": payload["msg"],
            "type": "chart",
            "chartData": payload["chartData"],
            "mode": payload.get("mode", "chart"),
            "modeLabel": payload.get("modeLabel", "数据可视化"),
            "workflow": payload.get("workflow", []),
        })
    except Exception as e:
        logger.error("generate_chart_upload error: %s", e)
        return jsonify({"code": 400, "reply": f"图表生成失败: {str(e)}", "type": "chat"})


@api_bp.route("/api/send-task", methods=["POST"])
def send_task():
    """
    主入口：JSON { task, history?, location? }。
    task 为用户自然语言；history 为前端多轮列表；location 为浏览器经纬度（可选）。
    返回字段由 parse_command 决定，此处把 res 中有值的键「白名单」拷贝到 HTTP JSON（避免泄露内部键）。
    """
    try:
        data = request.get_json(silent=True) or {}
        task = (data.get("task") or "").strip()
        dm = get_dialogue_manager()
        incoming_history = dm.sync_frontend_history(data.get("history"))
        if not task:
            return jsonify({"code": 400, "reply": "指令不能为空"})

        logger.info("Received task: %s", task)
        raw_loc = data.get("location")
        client_location = raw_loc if isinstance(raw_loc, dict) else None
        res = parse_command(task, incoming_history, client_location)

        dm.transition(intent=session.LAST_INTENT, response_type=res.get("type"))
        if res.get("type") == "goodbye":
            dm.reset()
        elif res.get("type") == "chat" and not res.get("resetUI"):
            remember_chat_turn(task, res.get("msg", ""))

        response = {
            "code": 200,
            "reply": res["msg"],
            "type": res["type"],
        }

        # 以下：parse_command 可能返回的扩展字段，按需带给前端（音乐、图、模式栏、工作流等）
        if "previewUrl" in res:
            response["previewUrl"] = res["previewUrl"]
        if "musicProvider" in res:
            response["musicProvider"] = res["musicProvider"]
        if "qishuiUrl" in res:
            response["qishuiUrl"] = res["qishuiUrl"]
        if "qishuiEmbedUrl" in res:
            response["qishuiEmbedUrl"] = res["qishuiEmbedUrl"]
        if "songName" in res:
            response["songName"] = res["songName"]
        if "musicAction" in res:
            response["musicAction"] = res["musicAction"]
        if "imageUrl" in res:
            response["imageUrl"] = res["imageUrl"]
        if "taskId" in res:
            response["taskId"] = res["taskId"]
        if "prompt" in res:
            response["prompt"] = res["prompt"]
        if "extraData" in res:
            response["extraData"] = res["extraData"]
        if "mode" in res:
            response["mode"] = res["mode"]
        if "modeLabel" in res:
            response["modeLabel"] = res["modeLabel"]
        if "worldState" in res:
            response["worldState"] = res["worldState"]
        if "quickActions" in res:
            response["quickActions"] = res["quickActions"]
        if "resetUI" in res:
            response["resetUI"] = res["resetUI"]
        if "workflow" in res:
            response["workflow"] = res["workflow"]
        if "knowledgeSources" in res:
            response["knowledgeSources"] = res["knowledgeSources"]
        if "chartData" in res:
            response["chartData"] = res["chartData"]
        if "imageUnderstandingUrl" in res:
            response["imageUnderstandingUrl"] = res["imageUnderstandingUrl"]

        return jsonify(response)
    except Exception as e:
        logger.error("Server Error: %s", e)
        return jsonify({"code": 500, "reply": f"服务器内部错误: {str(e)}"})


@api_bp.route("/api/user-apps", methods=["GET"])
def user_apps_get():
    """列出用户自行添加的可启动应用（名称 + 绝对路径）。"""
    try:
        return jsonify({"code": 200, "apps": user_apps_public_list()})
    except Exception as e:
        logger.error("user_apps_get: %s", e)
        return jsonify({"code": 500, "apps": [], "error": str(e)}), 500


@api_bp.route("/api/user-apps", methods=["POST"])
def user_apps_post():
    """JSON { name, path }：将本机 .exe 加入白名单（path 一般由 /api/user-apps/pick 返回）。"""
    try:
        data = request.get_json(silent=True) or {}
        name = (data.get("name") or "").strip()
        path = (data.get("path") or "").strip()
        ok, msg = add_user_app(name, path)
        if ok:
            return jsonify({"code": 200, "message": msg})
        return jsonify({"code": 400, "message": msg}), 400
    except Exception as e:
        logger.error("user_apps_post: %s", e)
        return jsonify({"code": 500, "message": str(e)}), 500


@api_bp.route("/api/user-apps", methods=["DELETE"])
def user_apps_delete():
    """Query: name=显示名称，移除一条用户白名单。"""
    try:
        name = (request.args.get("name") or "").strip()
        ok, msg = remove_user_app(name)
        if ok:
            return jsonify({"code": 200, "message": msg})
        return jsonify({"code": 400, "message": msg}), 400
    except Exception as e:
        logger.error("user_apps_delete: %s", e)
        return jsonify({"code": 500, "message": str(e)}), 500


@api_bp.route("/api/user-apps/pick", methods=["POST"])
def user_apps_pick_exe():
    """
    Windows：阻塞直至用户在系统对话框中选好 .exe（子进程 tkinter）。
    成功 { code, path, suggestedName }；取消 { code:204, path:null }；非 Windows { code:501 }。
    """
    if os.name != "nt":
        return jsonify({
            "code": 501,
            "path": None,
            "suggestedName": None,
            "message": "浏览添加仅支持在本机 Windows 上运行后端时使用。",
        }), 501
    try:
        path = pick_exe_windows_blocking()
        if not path:
            return jsonify({
                "code": 204,
                "path": None,
                "suggestedName": None,
                "message": "未选择文件或无法弹出选择窗口（请确认已安装 tkinter，且未在纯 SSH 无桌面环境运行）。",
            })
        stem = os.path.splitext(os.path.basename(path))[0]
        return jsonify({"code": 200, "path": path, "suggestedName": stem or "我的应用", "message": "ok"})
    except Exception as e:
        logger.error("user_apps_pick_exe: %s", e)
        return jsonify({"code": 500, "path": None, "suggestedName": None, "message": str(e)}), 500


@api_bp.route("/api/capabilities", methods=["GET"])
def capabilities():
    """前端用于判断是否展示「讯飞听写」上传按钮等；与 TTS 共用同一套讯飞密钥。"""
    ok = bool(XFYUN_APP_ID and XFYUN_API_KEY and XFYUN_API_SECRET)
    return jsonify({"code": 200, "xfyunAsr": ok, "userExePick": os.name == "nt"})


@api_bp.route("/api/speech-to-text", methods=["POST"])
def speech_to_text():
    """multipart：字段 audio = WAV 文件 → 讯飞 IAT 转写文本。"""
    try:
        if websockets is None:
            return jsonify({"code": 500, "text": "", "error": "服务端未安装 websockets"}), 500
        if not (XFYUN_APP_ID and XFYUN_API_KEY and XFYUN_API_SECRET):
            return jsonify({"code": 503, "text": "", "error": "未配置讯飞密钥"}), 503
        f = request.files.get("audio")
        if not f:
            return jsonify({"code": 400, "text": "", "error": "缺少音频字段 audio"}), 400
        raw = f.read()
        if len(raw) > 8 * 1024 * 1024:
            return jsonify({"code": 400, "text": "", "error": "音频过大"}), 400
        if len(raw) < 44 or raw[:4] != b"RIFF":
            return jsonify({"code": 400, "text": "", "error": "请上传 WAV 格式"}), 400
        text, err = transcribe_wav_bytes(raw)
        if err:
            return jsonify({"code": 502, "text": "", "error": err}), 502
        return jsonify({"code": 200, "text": text or ""})
    except Exception as e:
        logger.error("speech_to_text: %s", e)
        return jsonify({"code": 500, "text": "", "error": str(e)}), 500
