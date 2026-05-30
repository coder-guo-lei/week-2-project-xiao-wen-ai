#!/usr/bin/env python
"""本地验证：意图分类 + DialogueManager。在 backend 目录执行：python scripts/test_intent_dialogue.py"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import session
from logic.dialogue_manager import STATE_MUSIC, get_dialogue_manager
from logic.intent_classifier import classify_intent, rule_classify_intent


def sep(title: str) -> None:
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def test_intent_rule_vs_llm() -> None:
    sep("1. 意图分类：规则 vs LLM")
    cases = [
        ("下一首", "music_nav", "规则高置信，应 source=rule 或 cache"),
        ("生成折线图 一月:10 二月:20", "chart", "规则高置信"),
        ("放一首稻香", "music", "口语模糊，常走 LLM（source=llm）"),
        ("听个笑话", "chat", "勿判 music"),
    ]
    for text, expect, note in cases:
        r = classify_intent(text, {})
        rr = rule_classify_intent(text, {})
        ok = r.intent == expect
        print(f"  [{('OK' if ok else '??')}] {text!r}")
        print(f"       最终: {r.intent} ({r.source}, {r.confidence:.0%}) | 规则: {rr.intent}")
        print(f"       说明: {note}")


def test_intent_cache() -> None:
    sep("2. 意图分类：缓存")
    text = "北京今天天气怎么样"
    a = classify_intent(text, {})
    b = classify_intent(text, {})
    hit = b.source == "cache"
    print(f"  第一次: {a.intent} source={a.source}")
    print(f"  第二次: {b.intent} source={b.source}")
    print(f"  缓存生效: {'是' if hit else '否（检查 INTENT_CACHE_TTL 或是否改了输入）'}")


def test_dialogue_state_machine() -> None:
    sep("3. DialogueManager：状态机")
    dm = get_dialogue_manager()
    dm.reset()
    dm.transition(intent="music", response_type="music")
    s1 = dm.state
    dm.transition(intent="chat", response_type="chat")
    s2 = dm.state
    print(f"  点歌后状态: {s1} (期望 music)")
    print(f"  闲聊追问仍保持: {s2} (期望 music，便于跟唱上下文)")
    print(f"  状态机: {'OK' if s1 == STATE_MUSIC and s2 == STATE_MUSIC else 'FAIL'}")


def test_dialogue_window() -> None:
    sep("4. DialogueManager：滑动窗口")
    dm = get_dialogue_manager()
    dm.reset()
    for i in range(6):
        dm.record_turn(f"问题{i}", f"回答{i}")
    msgs = dm.build_context_messages()
    print(f"  存储条数: {len(session.CHAT_HISTORY)} (上限见 DIALOGUE_STORE_MESSAGES)")
    print(f"  送 LLM 条数: {len(msgs)} (含摘要块则 +1，窗口见 DIALOGUE_WINDOW_MESSAGES)")
    print(f"  context_label: {dm.context_label()}")


def test_dialogue_compress() -> None:
    sep("5. DialogueManager：摘要压缩（需 DASHSCOPE/DEEPSEEK Key）")
    from config import DASHSCOPE_API_KEY, DEEPSEEK_API_KEY, DIALOGUE_COMPRESS_MIN_MESSAGES

    if not (DASHSCOPE_API_KEY or DEEPSEEK_API_KEY):
        print("  跳过：未配置 LLM Key，无法生成摘要")
        return
    dm = get_dialogue_manager()
    dm.reset()
    n = DIALOGUE_COMPRESS_MIN_MESSAGES + 2
    for i in range(n // 2 + 2):
        dm.record_turn(f"我叫测试用户{i}", f"好的，记住了{i}")
    summary = dm.summary
    stored = len(session.CHAT_HISTORY)
    print(f"  压缩后存储条数: {stored}")
    print(f"  摘要长度: {len(summary)} 字")
    print(f"  摘要预览: {summary[:120]}..." if summary else "  （暂无摘要，可能未达 DIALOGUE_COMPRESS_MIN_MESSAGES）")
    print(f"  压缩触发: {'可能已触发' if summary else '未触发，可增大对话轮数或调低 DIALOGUE_COMPRESS_MIN_MESSAGES'}")


def test_parse_command_workflow() -> None:
    sep("6. 端到端：parse_command workflow 字段")
    from logic.task_parser import parse_command

    r = parse_command("保定天气")
    wf = r.get("workflow") or []
    intent_step = next((s for s in wf if s.get("title") == "识别意图"), None)
    print(f"  type={r.get('type')}")
    print(f"  识别意图步骤: {json.dumps(intent_step, ensure_ascii=False) if intent_step else '缺失'}")
    print(f"  workflow 已实现: {'是' if intent_step else '否'}")


def main() -> None:
    test_intent_rule_vs_llm()
    test_intent_cache()
    test_dialogue_state_machine()
    test_dialogue_window()
    test_dialogue_compress()
    test_parse_command_workflow()
    sep("完成")
    print("前端测试：发指令后看「执行链路 / workflow」第一步是否为「识别意图（规则/LLM/缓存）」")
    print("闲聊多轮后看 workflow「整理上下文」是否含「窗口」「摘要」「状态=」")


if __name__ == "__main__":
    main()
