"""CLI entry point for the Stage 1 text-based meeting prototype.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python src/main.py

    # or for the Gangnam cafe demo scenario
    python src/main.py --demo
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Load .env if present (optional dependency)
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

from meeting import Meeting  # noqa: E402


BANNER = r"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   🎙  말하는 비서실 (TalkFile) — Stage 1 텍스트 프로토타입
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  참석: 📊 실무형(A)   🔴 레드팀(B)   🧭 멘토(C)   📝 서기(D)
  종료: /end  또는  quit
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

DEMO_TOPIC = "강남 카페 창업 검토"
DEMO_SCRIPT = [
    "강남에 작은 카페 하나 열어볼까 고민 중이야.",
    "초기 자본은 2억 정도 생각하고 있고, 본업은 그대로 유지할 생각이야.",
    "그럼 유동인구보다 동네 단골이 모이는 골목 입지가 나을까?",
]


def _check_api_key() -> bool:
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.")
        print("   .env 파일 또는 shell export 로 키를 설정하고 다시 실행하세요.")
        return False
    return True


def _print_turns(turns: list[dict]) -> None:
    for turn in turns:
        print(f"{turn['emoji']} {turn['name']}({turn['label']}): {turn['text']}")
        print()


async def _run_interactive() -> None:
    print(BANNER)
    topic = input("이번 회의의 안건을 한 줄로 말해주세요 > ").strip()
    if not topic:
        print("안건이 없어 종료합니다.")
        return

    meeting = Meeting(topic)
    print(f"\n📌 안건: {topic}")
    print("대표님, 자유롭게 말씀하세요. 3인이 동시에 응답합니다.\n")

    while True:
        try:
            user_text = input("🧑 대표님 > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user_text:
            continue
        if user_text.lower() in ("/end", "quit", "exit", "/종료"):
            break

        print("\n(에이전트 응답 생성 중...)\n")
        turns = await meeting.user_says(user_text)
        _print_turns(turns)

    await _finalize(meeting)


async def _run_demo() -> None:
    print(BANNER)
    print(f"📌 데모 안건: {DEMO_TOPIC}\n")
    meeting = Meeting(DEMO_TOPIC)

    for user_text in DEMO_SCRIPT:
        print(f"🧑 대표님 > {user_text}\n")
        print("(에이전트 응답 생성 중...)\n")
        turns = await meeting.user_says(user_text)
        _print_turns(turns)
        print("─" * 60)

    await _finalize(meeting)


async def _finalize(meeting: Meeting) -> None:
    print("\n📝 서기가 회의록을 정리하는 중...\n")
    try:
        minutes, path = await meeting.finalize()
    except Exception as exc:  # noqa: BLE001
        print(f"❌ 회의록 생성 실패: {exc}")
        return
    print(f"✅ 회의록 저장: {path}\n")
    print("─" * 60)
    print(minutes)
    print("─" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="말하는 비서실 Stage 1 CLI")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="강남 카페 창업 검토 데모 시나리오를 자동 실행",
    )
    args = parser.parse_args()

    if not _check_api_key():
        sys.exit(1)

    if args.demo:
        asyncio.run(_run_demo())
    else:
        asyncio.run(_run_interactive())


if __name__ == "__main__":
    main()
