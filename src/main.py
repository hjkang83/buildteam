"""CLI entry point for the text-based meeting prototype.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python src/main.py

    # Gangnam cafe demo scenario
    python src/main.py --demo

    # Start a new meeting and auto-load relevant past meetings (Stage 2)
    python src/main.py --context

    # List stored session checkpoints
    python src/main.py --list-sessions

    # Resume a crashed meeting
    python src/main.py --resume 2026-04-13-1530-강남-카페-창업-검토
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

from archive import list_sessions  # noqa: E402
from meeting import Meeting  # noqa: E402


BANNER = r"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   🎙  말하는 비서실 (TalkFile) — Stage 2 텍스트 프로토타입
         (과거 회의 컨텍스트 + 세션 체크포인트)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  참석: 📊 실무형(CFO)  🔴 레드팀(CSO)  🧭 멘토(CHO)  📝 서기(기록)
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


async def _run_interactive(*, use_context: bool = False) -> None:
    print(BANNER)
    topic = input("이번 회의의 안건을 한 줄로 말해주세요 > ").strip()
    if not topic:
        print("안건이 없어 종료합니다.")
        return

    if use_context:
        meeting = Meeting.with_context(topic)
        if meeting.past_context:
            print("\n📚 관련 과거 회의를 자동으로 불러왔습니다:")
            print(meeting.past_context)
            print()
    else:
        meeting = Meeting(topic)

    print(f"\n📌 안건: {topic}")
    print(f"🗂  세션 ID: {meeting.session_id}")
    print("대표님, 자유롭게 말씀하세요. 3인이 동시에 응답합니다.\n")

    await _meeting_loop(meeting)
    await _finalize(meeting)


async def _run_resume(session_id: str) -> None:
    print(BANNER)
    meeting = Meeting.from_session(session_id)
    if meeting is None:
        print(f"❌ 세션을 찾을 수 없습니다: {session_id}")
        return
    print(f"\n♻️  세션 재개: {session_id}")
    print(f"📌 안건: {meeting.topic}")
    print(f"📜 저장된 턴 수: {len(meeting.transcript)}")
    print("대표님, 이어서 말씀하세요.\n")

    await _meeting_loop(meeting)
    await _finalize(meeting)


async def _meeting_loop(meeting: Meeting) -> None:
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


async def _run_demo(*, use_context: bool = False) -> None:
    print(BANNER)
    print(f"📌 데모 안건: {DEMO_TOPIC}\n")
    if use_context:
        meeting = Meeting.with_context(DEMO_TOPIC)
        if meeting.past_context:
            print("📚 관련 과거 회의를 자동으로 불러왔습니다:\n")
            print(meeting.past_context)
            print()
    else:
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


def _print_session_list() -> None:
    sessions = list_sessions()
    if not sessions:
        print("(저장된 세션이 없습니다)")
        return
    print("🗂  저장된 세션 체크포인트:")
    for sid in sessions:
        print(f"  • {sid}")
    print(f"\n재개: python src/main.py --resume <session-id>")


def main() -> None:
    parser = argparse.ArgumentParser(description="말하는 비서실 Stage 2 CLI")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="강남 카페 창업 검토 데모 시나리오를 자동 실행",
    )
    parser.add_argument(
        "--context",
        action="store_true",
        help="새 회의 시작 시 관련 과거 회의록을 자동으로 불러와 컨텍스트로 주입",
    )
    parser.add_argument(
        "--resume",
        metavar="SESSION_ID",
        help="저장된 세션 체크포인트에서 회의를 이어서 재개",
    )
    parser.add_argument(
        "--list-sessions",
        action="store_true",
        help="저장된 세션 체크포인트 목록 출력 후 종료",
    )
    args = parser.parse_args()

    if args.list_sessions:
        _print_session_list()
        return

    if not _check_api_key():
        sys.exit(1)

    if args.resume:
        asyncio.run(_run_resume(args.resume))
    elif args.demo:
        asyncio.run(_run_demo(use_context=args.context))
    else:
        asyncio.run(_run_interactive(use_context=args.context))


if __name__ == "__main__":
    main()
