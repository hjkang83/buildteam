"""CLI entry point for the text-based real estate investment advisory system.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python src/main.py

    # Gangnam officetel demo scenario
    python src/main.py --demo

    # Start a new meeting and auto-load relevant past meetings
    python src/main.py --context

    # List stored session checkpoints
    python src/main.py --list-sessions

    # Resume a crashed meeting
    python src/main.py --resume <session-id>
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
from file_parser import SUPPORTED_EXTENSIONS, parse_file  # noqa: E402
from file_parser import format_for_agents as format_files_for_agents  # noqa: E402
from meeting import Meeting  # noqa: E402
from real_estate import REGION_CODES, format_for_agents, get_multi_region_data  # noqa: E402
from yield_analyzer import analyze_multi_region, format_analysis_for_agents  # noqa: E402
from scenario import format_full_scenario_for_agents  # noqa: E402


BANNER = r"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   🏢  Data 기반 Multi-Agent 부동산 투자 자문 시스템
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  참석: 📊 CFO(재무총괄)  🔴 CSO(전략총괄)  🧭 고문(자문역)  📝 비서실장
  종료: /end  또는  quit
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

DEMO_TOPIC = "강남 오피스텔 투자 검토"
DEMO_REGIONS = ["강남구", "성동구", "강서구"]
DEMO_SCRIPT = [
    "강남 오피스텔 수익률 3%면 낮은 거 아냐?",
    "월세 수익 목적이야. 대출 60% 끼고 월 150만원 정도 나오면 좋겠어.",
    "그럼 강남 말고 성수나 마곡 쪽은 어때?",
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


def _load_files(file_paths: list[str]) -> str:
    """Parse uploaded files and return formatted text block."""
    file_texts: list[tuple[str, str]] = []
    for fp in file_paths:
        p = Path(fp)
        print(f"📎 파일 로딩: {p.name}")
        try:
            text = parse_file(fp)
            file_texts.append((p.name, text))
            print(f"   ✅ {p.name} 파싱 완료")
        except (FileNotFoundError, ValueError) as e:
            print(f"   ❌ {p.name} 실패: {e}")
    if not file_texts:
        return ""
    block = format_files_for_agents(file_texts)
    print()
    print(block)
    print()
    return block


async def _run_interactive(
    *,
    use_context: bool = False,
    regions: list[str] | None = None,
    files: list[str] | None = None,
) -> None:
    print(BANNER)
    topic = input("이번 회의의 안건을 한 줄로 말해주세요 > ").strip()
    if not topic:
        print("안건이 없어 종료합니다.")
        return

    market_data, yield_data, scenario_data = "", "", ""
    if regions:
        print(f"\n📈 실거래 데이터 로딩 중... ({', '.join(regions)})")
        summaries = get_multi_region_data(regions)
        market_data = format_for_agents(summaries)
        print(market_data)
        analyses = analyze_multi_region(summaries)
        yield_data = format_analysis_for_agents(analyses)
        if yield_data:
            print(yield_data)
        scenario_data = format_full_scenario_for_agents(summaries)
        if scenario_data:
            print(scenario_data)
        print()

    file_data = ""
    if files:
        file_data = _load_files(files)

    if use_context:
        meeting = Meeting.with_context(topic, regions=regions)
        if file_data:
            meeting.file_data = file_data
            meeting.transcript.insert(-1, {"role": "user", "text": file_data})
        if meeting.past_context:
            print("\n📚 관련 과거 회의를 자동으로 불러왔습니다:")
            print(meeting.past_context)
            print()
    elif files:
        meeting = Meeting.with_files(topic, files, regions=regions)
    elif market_data:
        meeting = Meeting(topic, market_data=market_data,
                          yield_data=yield_data, scenario_data=scenario_data)
    else:
        meeting = Meeting(topic)

    print(f"\n📌 안건: {topic}")
    print(f"🗂  세션 ID: {meeting.session_id}")
    print("대표님, 자유롭게 말씀하세요. CFO·CSO·고문이 동시에 응답합니다.\n")

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


async def _run_demo(
    *,
    use_context: bool = False,
    regions: list[str] | None = None,
) -> None:
    print(BANNER)
    regions = regions or DEMO_REGIONS
    print(f"📌 데모 안건: {DEMO_TOPIC}")
    print(f"📈 비교 권역: {', '.join(regions)}\n")

    summaries = get_multi_region_data(regions)
    market_data = format_for_agents(summaries)
    print(market_data)
    analyses = analyze_multi_region(summaries)
    yield_data = format_analysis_for_agents(analyses)
    if yield_data:
        print(yield_data)
    scenario_data = format_full_scenario_for_agents(summaries)
    if scenario_data:
        print(scenario_data)
    print()

    if use_context:
        meeting = Meeting.with_context(DEMO_TOPIC, regions=regions)
    else:
        meeting = Meeting(DEMO_TOPIC, market_data=market_data,
                          yield_data=yield_data, scenario_data=scenario_data)

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
    parser = argparse.ArgumentParser(description="부동산 투자 자문 시스템 CLI")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="강남 오피스텔 투자 검토 데모 시나리오를 자동 실행",
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
        "--region",
        nargs="+",
        metavar="REGION",
        help=f"실거래 데이터를 로딩할 지역 (예: 강남구 성동구). 지원: {', '.join(sorted(REGION_CODES))}",
    )
    parser.add_argument(
        "--file",
        nargs="+",
        metavar="FILE",
        help=f"회의에 참조할 파일 업로드 (지원: {', '.join(sorted(SUPPORTED_EXTENSIONS))})",
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

    regions = args.region
    files = args.file
    if args.resume:
        asyncio.run(_run_resume(args.resume))
    elif args.demo:
        asyncio.run(_run_demo(use_context=args.context, regions=regions))
    else:
        asyncio.run(_run_interactive(use_context=args.context, regions=regions, files=files))


if __name__ == "__main__":
    main()
