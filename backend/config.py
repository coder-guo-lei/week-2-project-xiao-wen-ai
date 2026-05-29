"""
整个项目的 核心配置文件 + 系统工具箱
这个文件 = 项目的控制面板 + 软件查找器 + AI 配置中心 + 文字游戏素材库
它只做 3 件事：
加载你的密钥配置（AI、语音、地图）
定义所有功能的规则（语速、图片大小、对话长度）
提供工具函数：自动找到你电脑上的微信 / QQ / 抖音 / 网易云
内置文字冒险游戏的素材
"""
import logging
import os
import re
import shutil
from pathlib import Path

from dotenv import dotenv_values, load_dotenv

# 找到项目文件夹路径
BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent
_ENV_FILE = BASE_DIR / ".env"
# 加载 .env 文件里的密钥（AI密钥、语音密钥）
load_dotenv(_ENV_FILE, encoding="utf-8-sig")
for _k, _v in dotenv_values(_ENV_FILE, encoding="utf-8-sig").items():
    if _v is not None and str(_v).strip() != "":
        os.environ[_k] = str(_v).strip()
# 开启日志（程序运行会打印记录）
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ---------- 讯飞 TTS ----------
MAX_TTS_CHARS = 8000
XFYUN_APP_ID = os.environ.get("XFYUN_APP_ID", "").strip()
XFYUN_API_KEY = os.environ.get("XFYUN_API_KEY", "").strip()
XFYUN_API_SECRET = os.environ.get("XFYUN_API_SECRET", "").strip()
XFYUN_TTS_SPEED = int(os.environ.get("XFYUN_TTS_SPEED", "50"))
XFYUN_TTS_VOLUME = int(os.environ.get("XFYUN_TTS_VOLUME", "50"))
XFYUN_TTS_DISK_CACHE = os.environ.get("XFYUN_TTS_DISK_CACHE", "0").strip().lower() in (
    "1",
    "true",
    "yes",
)
XFYUN_TTS_AUDIO_FORMAT = os.environ.get("XFYUN_TTS_AUDIO_FORMAT", "wav").strip().lower()
XFYUN_TTS_SAMPLE_RATE = int(os.environ.get("XFYUN_TTS_SAMPLE_RATE", "16000"))

XFYUN_SUPER_TTS_WS_URL = os.environ.get("XFYUN_SUPER_TTS_WS_URL", "").strip()
USE_XFYUN_SUPER_TTS = bool(XFYUN_SUPER_TTS_WS_URL)
_sr_super = int(os.environ.get("XFYUN_SUPER_TTS_SAMPLE_RATE", "24000"))
XFYUN_SUPER_TTS_SAMPLE_RATE = _sr_super if _sr_super in (8000, 16000, 24000) else 24000
XFYUN_SUPER_TEXT_UTF8_MAX = min(int(os.environ.get("XFYUN_SUPER_TEXT_UTF8_MAX", "62000")), 65500)

XFYUN_VCN_PATTERN = re.compile(r"^[a-zA-Z0-9_]{2,128}$")
XFYUN_TEXT_UTF8_MAX = 7800

TTS_CACHE_DIR = BASE_DIR / "cache" / "tts"


def xfyun_vcn_ok(vcn: str) -> bool:
    return bool(vcn and XFYUN_VCN_PATTERN.fullmatch(vcn))


if USE_XFYUN_SUPER_TTS:
    _sup_f = os.environ.get("XFYUN_DEFAULT_VCN_FEMALE", "x5_lingxiaoxuan_flow").strip()
    XFYUN_DEFAULT_VCN_FEMALE = _sup_f if xfyun_vcn_ok(_sup_f) else "x5_lingxiaoxuan_flow"
else:
    XFYUN_DEFAULT_VCN_FEMALE = "xiaoyan"

# ---------- DashScope / 高德 / DeepSeek 等 ----------
AMAP_KEY = os.environ.get("AMAP_KEY", "").strip()
REQUEST_TIMEOUT = 10
CHAT_TIMEOUT = int(os.environ.get("CHAT_TIMEOUT", "60"))
LOCAL_TIMEZONE = os.environ.get("LOCAL_TIMEZONE", "Asia/Shanghai").strip()
DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "").strip()
DASHSCOPE_CHAT_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
DASHSCOPE_CHAT_MODEL = os.environ.get("DASHSCOPE_CHAT_MODEL", "qwen-turbo").strip()
DASHSCOPE_IMAGE_MODEL = os.environ.get("DASHSCOPE_IMAGE_MODEL", "wanx2.1-t2i-turbo").strip()
DASHSCOPE_VL_MODEL = os.environ.get("DASHSCOPE_VL_MODEL", "qwen-vl-plus").strip()
MAX_UPLOAD_IMAGE_BYTES = int(os.environ.get("MAX_UPLOAD_IMAGE_BYTES", str(8 * 1024 * 1024)))
IMAGE_SIZE = os.environ.get("IMAGE_SIZE", "768*1024").strip()
IMAGE_TASK_TIMEOUT = int(os.environ.get("IMAGE_TASK_TIMEOUT", "120"))
DASHSCOPE_TASK_POLL_INTERVAL = float(os.environ.get("DASHSCOPE_TASK_POLL_INTERVAL", "1"))
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_CHAT_URL = os.environ.get("DEEPSEEK_CHAT_URL", "https://api.deepseek.com/v1/chat/completions").strip()
DEEPSEEK_CHAT_MODEL = os.environ.get("DEEPSEEK_CHAT_MODEL", "deepseek-chat").strip()
# 对话/翻译/世界叙事等：先试哪个厂商。deepseek = 优先 DeepSeek；默认 dashscope = 优先百炼
_PRIMARY_LLM = os.environ.get("PRIMARY_LLM", "dashscope").strip().lower()
PRIMARY_LLM_DEEPSEEK_FIRST = _PRIMARY_LLM in ("deepseek", "ds", "deep_seek")

NETEASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://music.163.com/",
}

MAX_KNOWLEDGE_SNIPPETS = 80
MAX_CHAT_HISTORY_MESSAGES = 12
MAX_CHAT_MESSAGE_CHARS = 1200

# 文字模拟世界：长叙事时用 LLM 润色（需配置百炼或 DeepSeek）
WORLD_SIM_LLM = os.environ.get("WORLD_SIM_LLM", "1").strip().lower() not in ("0", "false", "no", "off")
WORLD_SIM_LLM_MIN_LEN = int(os.environ.get("WORLD_SIM_LLM_MIN_LEN", "72"))

WORLD_THEMES = {
    "修仙": {
        "cores": ["灵气潮汐", "天道残缺", "万宗争鸣", "妖魔复苏", "古仙遗迹", "灵根觉醒"],
        "birthplaces": ["青岚山脚的破旧药庐", "云河镇外的竹林", "玄霜谷边缘", "落霞宗杂役院", "黑石矿洞入口", "无名古庙"],
        "resources": ["下品灵石", "凝气草", "灵泉水", "妖兽骨", "破损符箓", "赤阳果", "寒铁矿", "旧丹方"],
        "scenes": ["雾气缭绕的山涧", "传来兽吼的密林", "灵光闪动的废墟", "小镇夜市", "宗门试炼路", "被阵法封住的洞府"],
        "events": ["遇到受伤散修", "发现一处浅层灵脉", "被低阶妖兽盯上", "听见宗门招收弟子的消息", "捡到一枚残缺玉简", "遭遇突来的灵雨"],
    },
    "末日": {
        "cores": ["资源枯竭", "感染扩散", "机械失控", "极寒降临", "废土重建", "异种入侵"],
        "birthplaces": ["废弃超市仓库", "地下车站", "城市边缘避难所", "荒废学校", "裂开的高架桥下", "旧医院楼顶"],
        "resources": ["压缩饼干", "净水片", "旧电池", "急救绷带", "铁管", "防寒布", "罐头", "打火机"],
        "scenes": ["满是灰尘的街区", "警报残响的避难所", "停电的商场", "被藤蔓吞没的楼群", "浓雾里的停车场", "断裂的天桥"],
        "events": ["远处传来求救声", "发现被撬开的物资箱", "一群感染者正在游荡", "夜色提前降临", "避难所广播断断续续响起", "暴雨即将到来"],
    },
    "奇幻": {
        "cores": ["魔法复苏", "诸神沉眠", "龙族回归", "王国分裂", "地下城涌现", "星陨预言"],
        "birthplaces": ["边境酒馆", "银月森林", "风车村", "古堡废墙旁", "冒险者公会门口", "幽蓝湖畔"],
        "resources": ["银币", "治疗药水", "魔晶碎片", "旧短剑", "羊皮地图", "火绒草", "精灵面包", "铁质护符"],
        "scenes": ["铺满萤火的森林", "阴冷的古堡大厅", "喧闹的冒险者集市", "巨龙掠过的山谷", "被诅咒的墓园", "星光照耀的湖面"],
        "events": ["吟游诗人说出预言", "哥布林留下脚印", "商队请求护送", "湖面浮出古老符文", "远方出现龙影", "迷路的精灵向你求助"],
    },
}
WORLD_ACTIONS = ["探索", "采集", "修炼", "休息", "战斗", "交易", "向北", "向南", "向东", "向西", "生存", "查看状态"]

APP_LAUNCHERS = {
    "记事本": "notepad",
    "笔记本": "notepad",
    "计算器": "calc",
    "画图": "mspaint",
    "截图": "SnippingTool",
    "命令行": "cmd",
    "终端": "wt",
    "文件管理器": "explorer",
    "资源管理器": "explorer",
    "浏览器": "start msedge",
    "edge": "start msedge",
    "谷歌": "start chrome",
    "chrome": "start chrome",
    "微信": "resolve:wechat",
    "qq": "resolve:qq",
    "网易云": "resolve:netease",
    "抖音": "resolve:douyin",
    "douyin": "resolve:douyin",
    "vscode": "code",
    "代码": "code",
}


def _tencent_install_roots():
    roots = []
    for key in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA", "APPDATA"):
        v = os.environ.get(key, "").strip()
        if v:
            roots.append(Path(v))
    return roots


def _winreg_try_wechat_exe():
    """从腾讯写在注册表里的安装路径解析 WeChat.exe（国内版常见）。"""
    if os.name != "nt":
        return None
    import winreg

    subkeys = (
        (winreg.HKEY_CURRENT_USER, r"Software\Tencent\WeChat"),
        (winreg.HKEY_CURRENT_USER, r"Software\Tencent\Weixin"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Tencent\WeChat"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Tencent\Weixin"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Tencent\WeChat"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Tencent\Weixin"),
    )
    value_names = ("InstallPath", "InstallLocation", "InstPath", "Path", "InstallDir")
    raw_dirs = []
    for hkey, sub in subkeys:
        try:
            key = winreg.OpenKey(hkey, sub)
        except OSError:
            continue
        try:
            for vn in value_names:
                try:
                    val, _ = winreg.QueryValueEx(key, vn)
                except OSError:
                    continue
                if isinstance(val, str) and val.strip():
                    raw_dirs.append(val.strip().strip('"'))
        finally:
            key.Close()

    seen = set()
    for c in raw_dirs:
        if c in seen:
            continue
        seen.add(c)
        p = Path(c)
        if p.is_file() and p.suffix.lower() == ".exe":
            low = p.name.lower()
            if "wechat" in low or "weixin" in low:
                return p
            continue
        if not p.is_dir():
            continue
        for name in ("WeChat.exe", "Weixin.exe"):
            exe = p / name
            if exe.is_file():
                return exe
    return None


def resolve_tencent_wechat_exe():
    """微信（Weixin/WeChat）主程序路径；未安装或路径非常规时返回 None。"""
    hit = _winreg_try_wechat_exe()
    if hit is not None:
        return hit
    rels = (
        ("Tencent", "Weixin", "Weixin.exe"),
        ("Tencent", "Weixin", "WeChat.exe"),
        ("Tencent", "WeChat", "WeChat.exe"),
        ("Tencent", "WeChat", "Weixin.exe"),
    )
    for root in _tencent_install_roots():
        for rel in rels:
            p = root.joinpath(*rel)
            if p.is_file():
                return p
    return None


def resolve_tencent_qq_exe():
    """QQ（含 QQNT 新版）可执行文件路径。"""
    rels = (
        ("Tencent", "QQNT", "QQ.exe"),
        ("Tencent", "QQ", "Bin", "QQScLauncher.exe"),
        ("Tencent", "QQ", "Bin", "QQ.exe"),
    )
    for root in _tencent_install_roots():
        for rel in rels:
            p = root.joinpath(*rel)
            if p.is_file():
                return p
    return None


DOUYIN_EXE_PATH = os.environ.get("DOUYIN_EXE_PATH", "").strip()


def _winreg_resolve_app_paths_exe(*exe_names: str) -> Path | None:
    """从「App Paths」读可执行文件完整路径（安装器常写入，可覆盖非 ByteDance 目录如 D:\\1\\douyin）。"""
    if os.name != "nt":
        return None
    import winreg

    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        for name in exe_names:
            try:
                key = winreg.OpenKey(hive, rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{name}")
                try:
                    val, _ = winreg.QueryValueEx(key, "")
                finally:
                    key.Close()
                raw = str(val).strip().strip('"')
                raw = os.path.expandvars(raw)
                if not raw:
                    continue
                p = Path(raw)
                if p.is_file():
                    return p
            except OSError:
                continue
    return None


def _winreg_douyin_from_uninstall():
    """从卸载信息里找抖音安装目录或 DisplayIcon 中的 exe（适合自定义盘符如 D:\\1\\douyin）。"""
    if os.name != "nt":
        return None
    import winreg

    def looks_douyin(dn: str) -> bool:
        s = str(dn or "")
        return "抖音" in s or "douyin" in s.lower()

    def pick_in_dir(loc: str):
        if not loc or not isinstance(loc, str):
            return None
        root = Path(os.path.expandvars(loc.strip().strip('"')))
        if not root.is_dir():
            return None
        for name in ("Douyin.exe", "douyin.exe"):
            p = root / name
            if p.is_file():
                return p
        return None

    def pick_from_icon(icon: str):
        if not icon or not isinstance(icon, str) or ".exe" not in icon.lower():
            return None
        base = icon.split(",")[0].strip().strip('"')
        base = os.path.expandvars(base)
        p = Path(base)
        return p if p.is_file() and p.suffix.lower() == ".exe" else None

    roots = (
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
    )
    for hive, path in roots:
        try:
            parent = winreg.OpenKey(hive, path)
        except OSError:
            continue
        try:
            i = 0
            while True:
                try:
                    sk = winreg.EnumKey(parent, i)
                except OSError:
                    break
                i += 1
                try:
                    sub = winreg.OpenKey(parent, sk)
                except OSError:
                    continue
                try:
                    try:
                        dn, _ = winreg.QueryValueEx(sub, "DisplayName")
                    except OSError:
                        dn = ""
                    if not looks_douyin(str(dn)):
                        continue
                    try:
                        loc, _ = winreg.QueryValueEx(sub, "InstallLocation")
                    except OSError:
                        loc = ""
                    hit = pick_in_dir(str(loc))
                    if hit is not None:
                        return hit
                    try:
                        icon, _ = winreg.QueryValueEx(sub, "DisplayIcon")
                    except OSError:
                        icon = ""
                    hit = pick_from_icon(str(icon))
                    if hit is not None:
                        return hit
                finally:
                    sub.Close()
        finally:
            parent.Close()
    return None


def resolve_douyin_exe():
    """抖音 PC 客户端；支持 .env、PATH、注册表 App Paths / 卸载信息、ByteDance 目录；兼容 Douyin.exe / douyin.exe。"""
    try:
        return _resolve_douyin_exe_impl()
    except Exception as e:
        logging.getLogger(__name__).warning("resolve_douyin_exe failed: %s", e)
        return None


def _resolve_douyin_exe_impl():
    if DOUYIN_EXE_PATH:
        p = Path(DOUYIN_EXE_PATH)
        if p.is_file():
            return p
    if os.name != "nt":
        return None

    for exe_name in ("douyin.exe", "Douyin.exe"):
        w = shutil.which(exe_name)
        if w:
            p = Path(w)
            if p.is_file():
                return p

    hit = _winreg_resolve_app_paths_exe("douyin.exe", "Douyin.exe")
    if hit is not None:
        return hit

    hit = _winreg_douyin_from_uninstall()
    if hit is not None:
        return hit

    def _mtime_key(path: Path) -> float:
        try:
            return path.stat().st_mtime if path.is_dir() else 0.0
        except OSError:
            return 0.0

    def _pick_exe_in_dir(sub):
        for exe_name in ("Douyin.exe", "douyin.exe"):
            exe = sub / exe_name
            if exe.is_file():
                return exe
        return None

    local = os.environ.get("LOCALAPPDATA", "").strip()
    if local:
        bd = Path(local) / "ByteDance"
        if bd.is_dir():
            subs = sorted((x for x in bd.glob("Douyin*") if x.is_dir()), key=_mtime_key, reverse=True)
            for sub in subs:
                exe = _pick_exe_in_dir(sub)
                if exe is not None:
                    return exe

    for env_key in ("ProgramFiles", "ProgramFiles(x86)"):
        base = os.environ.get(env_key, "").strip()
        if not base:
            continue
        root = Path(base) / "ByteDance"
        if not root.is_dir():
            continue
        for sub in sorted((x for x in root.glob("Douyin*") if x.is_dir()), key=_mtime_key, reverse=True):
            exe = _pick_exe_in_dir(sub)
            if exe is not None:
                return exe
    return None


def resolve_netease_cloud_exe():
    """网易云音乐 cloudmusic.exe 常见安装位置（不依赖 PATH 里的 cloudmusic 命令）。"""
    if os.name != "nt":
        return None
    rels = (
        Path(os.environ.get("ProgramFiles(x86)", "")) / "NetEase" / "CloudMusic" / "cloudmusic.exe",
        Path(os.environ.get("ProgramFiles", "")) / "NetEase" / "CloudMusic" / "cloudmusic.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "cloudmusic" / "cloudmusic.exe",
    )
    for p in rels:
        if p.is_file():
            return p
    return None


MSG_LLM_NOT_CONFIGURED = (
    "对话服务未就绪：请在 backend 目录的 .env 中至少配置其一，保存后重启后端：\n"
    "· DASHSCOPE_API_KEY — 阿里云百炼（推荐：对话、文生图、图片理解、翻译）\n"
    "· DEEPSEEK_API_KEY — DeepSeek（对话、翻译、知识库；生图/看图仍需要百炼）\n"
    "若已配置仍失败，请检查密钥是否有效、网络是否可访问对应 API。"
)
MSG_TRANSLATE_NOT_CONFIGURED = (
    "翻译未就绪：请在 backend/.env 中配置 DASHSCOPE_API_KEY 或 DEEPSEEK_API_KEY 后重启后端。"
)
MSG_VISION_NEED_DASHSCOPE = (
    "图片理解需要阿里云百炼：请在 backend/.env 配置 DASHSCOPE_API_KEY。"
    "DeepSeek 不提供看图接口。"
)
