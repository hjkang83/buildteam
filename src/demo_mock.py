"""Mock demo — Stage 1+2 flow simulator (no real API calls).

Purpose:
- 이해관계자·팀원에게 "우리가 만들려는 결과물"을 API 없이 즉시 보여주기
- Gold Standard 기준의 회귀 테스트 레퍼런스 (페르소나 수정 후 기대값 체크)
- CI에서도 돌 수 있는 스모크 테스트 (ANTHROPIC_API_KEY 불필요)

Stage 2 업데이트:
- 회의록에 Obsidian-compatible YAML frontmatter 자동 추가
- 두 번째 회의(후속) 시작 시 첫 회의록이 컨텍스트로 자동 주입되는 것 시연
- 세션 체크포인트 JSON 저장/목록 확인

주의: 여기 박힌 에이전트 응답은 **Gold Standard 기반의 이상적 출력**이며,
실제 LLM 호출 결과가 아닙니다. 실제 검증은 `python src/main.py --demo` 로
네트워크·키가 설정된 상태에서 돌려야 합니다.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from archive import (  # noqa: E402
    build_context_block,
    build_frontmatter,
    list_meetings,
    list_sessions,
    save_session,
)
from personas import AGENT_CONFIG  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
MEETINGS_DIR = REPO_ROOT / "meetings"
DEMO_TOPIC = "강남 카페 창업 검토"

BANNER = r"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   🎙  말하는 비서실 (TalkFile) — Stage 1+2 Mock Demo
         (API 호출 없음. Gold Standard 기반 시연용)
         · 회의 1: 신규 회의 + frontmatter 저장
         · 회의 2: 과거 회의 컨텍스트 자동 주입 시연
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

# ----------------------------------------------------------------------
# Mock script: each turn = user line + 3 C-level responses
# Responses are written to exhibit DIVERSE angles (different each turn)
# and 3~4 sentence length, per the updated persona spec.
# ----------------------------------------------------------------------

MOCK_TURNS: list[dict[str, str]] = [
    {
        "user": "강남에 작은 카페 하나 열어볼까 고민 중이야.",
        # 📊 CFO — 단위경제 + 트렌드
        "practitioner": (
            "대표님, CFO 관점에서 말씀드리면 강남 1층 상가 월세는 평당 "
            "25~35만원, 카페 초기 비용은 평균 1.5억 내외입니다. "
            "객단가 7천원에 일평균 100명 기준이면 월매출이 약 2,100만원 "
            "수준인데, 여기서 임차·원가·인건비 빼면 손익분기 근처입니다. "
            "공실률이 최근 8%로 상승 중이라 입지 한 칸 차이가 단위경제를 "
            "통째로 흔드는 구간입니다."
        ),
        # 🔴 CSO — 실패 사례 + 숨은 가정
        "redteam": (
            "CSO 관점에서 그 전제부터 의심하고 싶습니다. "
            "대표님, 강남 카페 3년 폐업률이 70%가 넘고, 폐업 사유 1위가 "
            "'본업과의 시너지 부재'입니다. 그리고 1.5억의 기회비용이 "
            "빠져 있는데, 본업에 재투자했을 때의 기대 수익률과 비교가 "
            "먼저입니다. 지금 구도는 '카페를 여는 것'이 아니라 "
            "'본업 성장에 얼마를 못 쓸지 결정하는 것'에 가깝습니다."
        ),
        # 🧭 CHO — 본질 질문 + 고전 인용 + 가치/정체성
        "mentor": (
            "대표님, 긴 호흡으로 한 가지 여쭤보고 싶습니다. "
            "지금 진짜 필요한 게 '새로운 사업'인지, '잠시 멈춤'인지, "
            "아니면 '사람들과 어울리는 공간'인지요? "
            "세네카가 '어느 항구로 갈지 모르는 사람에게는 어떤 바람도 "
            "순풍이 아니다'라고 했습니다. "
            "카페는 수단일 뿐, 대표님의 항구가 어디인지부터 짚어보시죠."
        ),
    },
    {
        "user": "초기 자본은 2억 정도 생각하고 있고, 본업은 그대로 유지할 생각이야.",
        # 📊 CFO — P&L 임팩트 + 현금흐름
        "practitioner": (
            "대표님, 2억 예산을 P&L에 얹어보면 인테리어 6~8천, "
            "권리금·보증금 9~13천, 초도 재고·집기 2천이 들어가고 "
            "6개월 운영비 3천까지 빼면 순 여유 자금이 2~3천만원 수준입니다. "
            "본업 유지 전제에서는 점장 인건비 월 350만원이 고정비로 꽂히고, "
            "현금 소진 시점은 매출이 월 1,800만원 아래로 3개월만 이어져도 "
            "위험 구간에 진입합니다."
        ),
        # 🔴 CSO — 민감도 + 경쟁 동학
        "redteam": (
            "잠깐, 그 계산에서 결정적으로 빠진 변수가 있습니다. "
            "바로 '대표님의 시간'인데, 본업 병행이라면서 매장 관리에 "
            "주 10시간만 써도 본업 KPI가 흔들릴 확률이 높습니다. "
            "더해서 강남 반경 500m 내 동급 카페가 평균 18개 포진해 있어 "
            "매출 민감도가 심해집니다 — 경쟁사 한 곳만 프로모션 걸어도 "
            "월매출 15%씩 빠지는 걸 자주 봅니다."
        ),
        # 🧭 CHO — 관점 전환 + 사람/조직 관점
        "mentor": (
            "본질적으로는, '점장에게 맡기는 카페'는 자산이고 "
            "'주말에 사장님이 지키는 카페'는 취미입니다. "
            "지금 구상은 어느 쪽에 가까우신가요? "
            "그리고 자산으로 간다면 그 점장을 10년 함께 갈 사람으로 "
            "찾을 준비가 되어 있으신지도 함께 물어보고 싶습니다."
        ),
    },
    {
        "user": "그럼 유동인구보다 동네 단골이 모이는 골목 입지가 나을까?",
        # 📊 CFO — 벤치마크 + 비교
        "practitioner": (
            "대표님, 논현·역삼 이면 골목 상권은 월세 평당 15~20만원으로 "
            "메인 상권 대비 40~50% 저렴합니다. "
            "다만 벤치마크를 돌려보면 단골형 카페는 초기 1년 매출이 "
            "유동인구 상권의 평균 60% 수준에서 시작하고, "
            "매출 구조는 재방문 고객이 70% 이상을 차지합니다. "
            "즉, 고정비는 낮지만 매출 안정화까지의 런웨이가 더 길게 "
            "필요합니다."
        ),
        # 🔴 CSO — 구조적 결함 + 전제 모순
        "redteam": (
            "저는 다른 각도에서 찌르겠습니다. '단골 장사'의 구조적 핵심은 "
            "'사장의 얼굴'인데, 본업 유지라는 전제와 근본적으로 충돌합니다. "
            "단골형 카페 성공 사례 20건 조사해 보면 17건이 사장 상주 구조였고, "
            "나머지 3건도 점장 = 공동창업자 수준의 장기 파트너였습니다. "
            "지금 모델로 가려면 '단골'이 아니라 '콘셉트 기반 동선형' 입지를 "
            "다시 검토하시는 게 맞습니다."
        ),
        # 🧭 CHO — 우선순위 재정렬 + 고전 인용
        "mentor": (
            "손자가 '전략은 선택이 아니라 포기의 기술'이라고 했죠. "
            "본업, 카페, 골목 상권이라는 세 가지 중 반드시 하나는 "
            "타협해야 할 텐데, 대표님의 기준은 무엇인가요? "
            "그 기준이 정해지기 전에는 입지 선택 자체가 부수적인 질문입니다."
        ),
    },
]

# Simulated clerk output (follows the fixed template in agents/clerk.md)
MOCK_MINUTES = """# 회의록: 강남 카페 창업 검토

- **일시**: {timestamp}
- **참석**: 대표님, 실무형(CFO), 레드팀(CSO), 멘토(CHO), 서기(기록)

## 🎯 핵심 안건
강남 지역 소규모 카페 창업 실행 여부 및 입지 전략 검토
(예산 2억, 본업 병행 전제)

## 💬 주요 논의
- **실무형(CFO) 관점**: 강남 1층 월세 25~35만원/평, 초기비용 1.5억, 공실률 8%.
  예산 2억 집행 시 실질 여유 현금은 2~3천만원 수준이며, 본업 병행 시 점장
  인건비 월 350만원이 고정비로 꽂힘. 골목 상권(논현/역삼 이면)은 월세가
  40~50% 저렴하지만 초기 1년 매출이 유동인구 상권의 60% 수준에서 시작되어
  매출 안정화까지 런웨이가 더 필요함.
- **레드팀(CSO) 관점**: 강남 카페 3년 폐업률 70%, 1위 사유 '본업과 시너지
  부재'. 1.5억의 기회비용이 계산에 누락. 반경 500m 내 경쟁 카페 18개로
  매출 민감도 높음. '단골 장사' 구조는 사장 상주가 전제이므로 본업 유지와
  근본적으로 충돌 — 성공 사례 20건 중 17건이 사장 상주였음.
- **멘토(CHO) 관점**: 지금 진짜 필요한 것이 '새 사업'인지, '쉼표'인지,
  '공간'인지 본질 질문부터. '점장 위탁 = 자산' vs '주말 사장 = 취미'의
  구분이 먼저이며, 자산 모델이라면 10년 함께 갈 점장 확보가 선행 조건.
  본업·카페·골목 상권 중 무엇을 포기할지 기준이 정해지기 전까지는 입지
  선택은 부수적 질문.

## ✅ 결정사항
- [ ] (이번 회의에서 창업 실행/보류 결정은 도출되지 않음 — 본질 질문과
      포기 기준이 먼저 정리되어야 한다는 공감대만 형성)

## ⏸ 보류사항
- 대표님이 원하는 것이 '사업(자산)'인지 '쉼표(휴식)'인지 '공간(관계)'인지
  자기 진단 필요
- 본업 · 카페 운영 · 골목 상권 접객 중 포기할 항목 기준 미정
- 점장 위탁 운영 전제의 3년 손익 시뮬레이션 부재
- 1.5억을 본업에 재투자했을 때의 기대 수익률 벤치마크 부재

## 📌 Next Action Plan
1. **[담당: 대표님]** '카페를 왜 하고 싶은지' 1페이지로 정리하기
   (사업/쉼표/공간 중 어느 것인지 구분 포함) — 기한: 2026-04-20
2. **[담당: 대표님]** 점장 위탁 운영 전제의 3년 손익 시뮬레이션 작성하기
   (월 매출/인건비/임차료/마진율/현금소진시점) — 기한: 2026-04-27
3. **[담당: 대표님]** 1.5억을 본업에 재투자했을 때의 기대 ROI 산출하기
   (기회비용 벤치마크) — 기한: 2026-04-27
4. **[담당: 대표님]** 논현/역삼 골목 후보지 3곳 임장 다녀오기
   (주중·주말 각 1회 관찰) — 기한: 2026-04-27

## 🔖 다음 회의 아젠다
- 1페이지 본질 문서 + 손익 시뮬레이션 + 기회비용 ROI + 임장 결과를
  바탕으로 창업 실행 여부 재검토
"""


FOLLOWUP_TOPIC = "강남 카페 창업 후속 검토 — 본질 문서 & ROI 결과"
FOLLOWUP_USER_LINE = (
    "지난주 숙제 네 가지 다 해왔어. 본질 문서 쓰면서 "
    "'쉼표에 더 가깝다'는 결론에 도달했고, ROI는 본업 재투자 쪽이 "
    "압도적이었어. 그럼 카페는 접는 게 맞을까?"
)


def _print_turn(turn_no: int, turn: dict[str, str]) -> None:
    print(f"\n── Turn {turn_no} ──")
    print(f"🧑 대표님 > {turn['user']}\n")
    for key in ("practitioner", "redteam", "mentor"):
        cfg = AGENT_CONFIG[key]
        header = f"{cfg['emoji']} {cfg['name']}({cfg['label']}):"
        print(header)
        print(f"  {turn[key]}\n")


def _save_mock_session(session_id: str, topic: str, started: datetime) -> Path:
    """Write a fake session checkpoint to show the JSON shape."""
    fake_transcript = [
        {"role": "user", "text": f"[회의 시작] 오늘 안건: {topic}"},
    ]
    for t in MOCK_TURNS:
        fake_transcript.append({"role": "user", "text": t["user"]})
        for key in ("practitioner", "redteam", "mentor"):
            cfg = AGENT_CONFIG[key]
            fake_transcript.append(
                {
                    "role": "agent",
                    "agent_key": key,
                    "name": cfg["name"],
                    "label": cfg["label"],
                    "emoji": cfg["emoji"],
                    "text": t[key],
                }
            )
    data = {
        "session_id": session_id,
        "topic": topic,
        "model": "claude-sonnet-4-6",
        "started_at": started.isoformat(),
        "past_context": "",
        "transcript": fake_transcript,
    }
    return save_session(session_id, data)


def _run_meeting_one() -> Path:
    """Meeting 1 — standalone, saves frontmatter'ed minutes + session JSON."""
    print(BANNER)
    print(f"📌 [회의 1] 안건: {DEMO_TOPIC}\n")
    for i, turn in enumerate(MOCK_TURNS, start=1):
        _print_turn(i, turn)

    started = datetime.now()
    timestamp = started.strftime("%Y-%m-%d %H:%M")
    minutes = MOCK_MINUTES.format(timestamp=timestamp)

    # Stage 2: wrap with Obsidian frontmatter
    frontmatter = build_frontmatter(topic=DEMO_TOPIC, started_at=started)
    full_content = frontmatter + "\n" + minutes

    MEETINGS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{started.strftime('%Y-%m-%d-%H%M')}-MOCK-강남-카페-창업-검토.md"
    path = MEETINGS_DIR / filename
    path.write_text(full_content, encoding="utf-8")

    # Stage 2: save session checkpoint JSON
    session_id = f"{started.strftime('%Y-%m-%d-%H%M%S')}-MOCK-강남-카페-창업-검토"
    session_path = _save_mock_session(session_id, DEMO_TOPIC, started)

    print("\n" + "─" * 60)
    print("📝 [MOCK] 서기가 회의록을 정리했습니다.")
    print(f"✅ 회의록 저장: {path}")
    print(f"🗂  세션 체크포인트: {session_path}")
    print("─" * 60 + "\n")
    print(full_content)
    print("─" * 60)
    return path


def _run_meeting_two() -> None:
    """Meeting 2 — shows past-context auto-loading (Stage 2 핵심 기능)."""
    print("\n" + "━" * 60)
    print("🔁 [회의 2] 후속 회의 — 과거 회의 맥락 자동 주입 시연")
    print("━" * 60 + "\n")
    print(f"📌 [회의 2] 안건: {FOLLOWUP_TOPIC}\n")

    # Mock demo explicitly looks at MOCK files (list_meetings() normally excludes them)
    relevant = list_meetings(include_mock=True)[:3]
    context_block = build_context_block(relevant)
    if context_block:
        print("📚 [MOCK] archive 모듈이 다음 과거 회의를 자동으로 불러왔습니다:\n")
        print(context_block)
        print()
    else:
        print("(관련 과거 회의를 찾지 못했습니다 — 첫 회의이거나 검색 실패)\n")

    print(f"🧑 대표님 > {FOLLOWUP_USER_LINE}\n")

    # Gold-standard responses that explicitly reference the past context
    print("📊 실무형(CFO):")
    print(
        "  대표님, 지난 회의에서 본업 재투자 ROI가 압도적이었다고 하시면 "
        "재무적 결론은 이미 나온 셈입니다. "
        "다만 '쉼표'의 비용도 P&L에 잡아봐야 합니다 — 본업 성장률이 "
        "월 3% 이상 유지되려면 대표님 시간의 12~15%는 회복 활동에 "
        "배정되어야 하고, 그건 돈이 아닌 '시간 예산' 항목입니다.\n"
    )

    print("🔴 레드팀(CSO):")
    print(
        "  잠깐, 지난번 '단골 장사는 사장 상주 전제'와 지금 '쉼표 = 카페'가 "
        "구조적으로 충돌한다는 점을 다시 짚겠습니다. "
        "'쉼표'가 필요하다면 카페 창업보다 비용·리스크가 1/10 인 선택지가 "
        "이미 존재합니다 — 주 1회 다른 공간 대여, 멤버십 라운지, 코치와의 "
        "정기 대화 등을 비교군으로 먼저 얹고 결정하시는 게 맞습니다.\n"
    )

    print("🧭 멘토(CHO):")
    print(
        "  대표님, 드러커가 '바른 답보다 바른 질문이 먼저'라고 했죠. "
        "지난 회의 질문은 '카페를 열까?' 였고, 지금의 진짜 질문은 "
        "'쉼표를 어떻게 일상에 심을까?' 로 바뀐 것 같습니다. "
        "카페는 그 중 하나의 수단일 뿐이고, 본질은 '무엇을 덜어낼 것인가' "
        "입니다 — 이 관점에서 카페를 다시 보시면 답이 깔끔해지지 않을까요?\n"
    )

    print("─" * 60)
    print(
        "🎯 [Stage 2 핵심 시연] 에이전트 3인이 '지난 회의'를 구체적으로 "
        "언급하며 응답했습니다.\n"
        "   이것이 WhyTree 줄기 3('결정하고 나면 흐지부지된다')의 해결입니다.\n"
    )


def main() -> None:
    _run_meeting_one()
    _run_meeting_two()

    # Show current session checkpoint list
    print("━" * 60)
    print("🗂  현재 저장된 세션 체크포인트:")
    sessions = list_sessions()
    if sessions:
        for sid in sessions[-5:]:
            print(f"   • {sid}")
    else:
        print("   (없음)")
    print("━" * 60)
    print(
        "\n⚠️  이건 Mock 입니다. 실제 API 호출 결과가 아닙니다.\n"
        "    실제 검증은 ANTHROPIC_API_KEY 세팅 후 "
        "`python src/main.py --demo --context` 로 돌리세요.\n"
    )


if __name__ == "__main__":
    main()
