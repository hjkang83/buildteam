"""Mock demo — 부동산 투자 자문 시스템 시연 (no real API calls).

Purpose:
- 이해관계자·팀원에게 "우리가 만들려는 결과물"을 API 없이 즉시 보여주기
- Gold Standard 기준의 회귀 테스트 레퍼런스 (페르소나 수정 후 기대값 체크)
- CI에서도 돌 수 있는 스모크 테스트 (API KEY 불필요)

주의: 여기 박힌 에이전트 응답은 **Gold Standard 기반의 이상적 출력**이며,
실제 LLM 호출 결과가 아닙니다.
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from personas import AGENT_CONFIG  # noqa: E402
from real_estate import format_for_agents, get_multi_region_data  # noqa: E402
from yield_analyzer import analyze_multi_region, format_analysis_for_agents  # noqa: E402
from scenario import format_full_scenario_for_agents  # noqa: E402
from cashflow import build_multi_cashflow, format_cashflow_for_agents  # noqa: E402
from monte_carlo import run_multi_monte_carlo, format_monte_carlo_for_agents  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
MEETINGS_DIR = REPO_ROOT / "meetings"
DEMO_TOPIC = "강남 오피스텔 투자 검토"
DEMO_REGIONS = ["강남구", "성동구", "강서구"]

BANNER = r"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   🏢  Data 기반 Multi-Agent 부동산 투자 자문 시스템
                    Mock Demo
         (API 호출 없음. Gold Standard 기반 시연용)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

MOCK_TURNS: list[dict[str, str]] = [
    {
        "user": "강남 오피스텔 수익률 3%면 낮은 거 아냐?",
        "practitioner": (
            "대표님, 숫자만 놓고 봅시다. 강남 오피스텔 표면 수익률 3%는 "
            "관리비·공실·세금 빼면 실질 수익률 1.8~2.2% 구간입니다 "
            "[출처: 한국부동산원 오피스텔 수익률 통계, 2025]. "
            "대출 60% 끼면 레버리지 수익률 4.2% 찍히지만, "
            "취득세 4.6% 떼면 첫해엔 마이너스예요 "
            "[출처: 지방세법 시행령]. "
            "같은 4.5억을 예금에 넣으면 연 3.5% 확정인데, "
            "그 비교가 먼저입니다."
        ),
        "redteam": (
            "잠깐요, 수익률 3%보다 더 중요한 게 있습니다. "
            "고금리 국면에서 오피스텔 진입은 타이밍이 안 맞습니다 "
            "— 기준금리 3.5%에 대출 이자가 수익률을 잡아먹는 구간이에요 "
            "[출처: 한국은행 기준금리, 2025.04]. "
            "거기에 강남 오피스텔 신규 공급이 2025~2026년 3,200실 예정이라 "
            "공실률 상승 압력도 있습니다 [출처: 부동산114]. "
            "하반기 금리 인하 시그널 나올 때까지 6개월 대기가 전략적으로 맞아요."
        ),
        "mentor": (
            "대표님, 한 가지 여쭤보고 싶은 게 있습니다. "
            "지금 원하시는 게 '월세 수익'인지 '시세 차익'인지, "
            "아니면 '강남이라는 타이틀'인지요? "
            "[부의 본능]에서도 말하듯, 투자에서 가장 비싼 실수는 "
            "'목적이 불분명한 상태에서 숫자에 끌려가는 것'입니다. "
            "수익률 3%가 낮은지 높은지는 대표님의 투자 목적이 "
            "정해져야 판단할 수 있습니다."
        ),
    },
    {
        "user": "월세 수익 목적이야. 대출 60% 끼고 월 150만원 정도 나오면 좋겠어.",
        "practitioner": (
            "대표님, 월세 150만원 목표로 역산해보겠습니다. "
            "강남 오피스텔 4.5억 기준, 대출 60%(2.7억) 끼면 "
            "월 이자가 약 90만원(금리 4% 기준)이고, 월세 150만원에서 "
            "이자·관리비·공실(연 1개월 가정) 빼면 순수익 월 30~40만원 수준입니다 "
            "[출처: 은행연합회 주담대 금리, 2025.04]. "
            "연 순수익 360~480만원이면 자기자본(1.8억) 대비 수익률 2~2.7%인데, "
            "이건 정기예금(3.5%)보다 낮습니다."
        ),
        "redteam": (
            "그 계산에서 빠진 게 두 가지 있습니다. 첫째, 공실이 연 1개월이 "
            "아니라 2~3개월로 가면 순수익이 0에 수렴합니다 — 강남 오피스텔 "
            "평균 공실률이 최근 6.8%로 올라가고 있어요 "
            "[출처: 한국부동산원 공실률 통계, 2025 Q1]. "
            "둘째, 금리 4%는 현재 기준인데, 변동금리라면 0.5%p만 올라도 "
            "월 이자가 11만원 추가로 꽂히면서 순수익이 마이너스에 진입합니다."
        ),
        "mentor": (
            "본질적으로 하나 짚어보시죠. '월 150만원'이라는 숫자가 "
            "대표님 삶에서 어떤 의미인가요? [부동산 투자의 정석]에서 "
            "강조하는 게 '숫자를 정하기 전에 그 숫자가 삶을 어떻게 "
            "바꾸는지 먼저 그리라'는 거거든요. "
            "월 150만원이 생활비 보조인지, 조기 은퇴 계획의 일부인지에 "
            "따라 최적 매물 유형이 완전히 달라집니다."
        ),
    },
    {
        "user": "그럼 강남 말고 성수나 마곡 쪽은 어때?",
        "practitioner": (
            "대표님, 권역별로 비교해보면 흥미로운 숫자가 나옵니다. "
            "성수 오피스텔 평균 매매가 3.2억에 월세 120만원이면 "
            "표면 수익률 4.5% [출처: 네이버 부동산 호가, 2026.04], "
            "마곡은 평균 2.8억에 월세 100만원으로 표면 4.3%입니다. "
            "강남(3%) 대비 1~1.5%p 높고, 대출 레버리지 시 "
            "실질 수익률 격차는 더 벌어집니다."
        ),
        "redteam": (
            "성수와 마곡의 수익률이 높아 보이지만, 이면을 보셔야 합니다. "
            "성수는 준공업지역 규제 변수가 있고 "
            "— 용도지역 변경 시 임대 수요 구조가 흔들릴 수 있습니다. "
            "마곡은 LG·코오롱 등 대기업 의존도가 높아서 "
            "기업 이전·구조조정 한 건이면 공실률이 급등하는 구조예요 "
            "[출처: 마곡지구 입주 기업 현황, 서울시]. "
            "강남 대비 출구 전략(매각 유동성)도 훨씬 불리합니다."
        ),
        "mentor": (
            "대표님, 지금 질문이 '강남 vs 성수 vs 마곡'으로 바뀌었는데, "
            "한 발 물러서 보면 진짜 질문은 '수익률 vs 안정성 중 "
            "뭘 우선할 것인가'입니다. "
            "[부의 추월차선]에서 강조하듯 '어디에 투자할까'보다 "
            "'어떤 기준으로 고를까'를 먼저 세우시는 게 "
            "시행착오를 줄이는 길입니다."
        ),
    },
]

MOCK_MINUTES = """# 회의록: 강남 오피스텔 투자 검토

- **일시**: {timestamp}
- **참석**: 대표님, CFO(재무총괄), CSO(전략총괄), 고문(자문역), 비서실장(서기)

## 🎯 핵심 안건
강남 오피스텔 (표면 수익률 3%) 투자 실행 여부 및 대안 권역 비교 검토
(월세 수익 목적, 대출 60% 전제)

## 💬 주요 논의
- **CFO 의견**: 강남 오피스텔 표면 3%에서 실질 1.8~2.2%, 레버리지 시 4.2%이나
  취득세 감안 첫해 마이너스. 월세 150만원 목표 시 순수익 월 30~40만원으로
  정기예금(3.5%) 대비 불리. 성수(표면 4.5%), 마곡(4.3%)이 수익률 우위.
- **CSO 의견**: 고금리 국면에서 오피스텔 진입 타이밍 부적합. 강남 신규 공급
  3,200실로 공실률 상승 압력. 성수는 준공업지역 규제 변수, 마곡은 대기업
  의존도 리스크. 6개월 대기 후 재검토 권장.
- **고문 의견**: 투자 목적(월세/시세차익/타이틀) 명확화가 선행 조건.
  '수익률 vs 안정성' 기준 설정이 권역 선택보다 먼저. 월 150만원의 생활
  내 의미 정의 필요.

## ✅ 결정사항
- [ ] 강남 오피스텔 즉시 투자 보류
- [ ] 성수·마곡 권역으로 검토 범위 확대

## ⏸ 보류사항
- 투자 기준(수익률 우선 vs 안정성 우선) 미확정 — 고문 지적
- 금리 인하 시그널 확인 전까지 진입 타이밍 미결 — CSO 권장
- 성수 준공업지역 규제 변수 추가 조사 필요

## 📌 Next Action Plan
1. **[담당: 대표님]** 투자 기준 정리하기 (수익률 우선 vs 안정성 우선, 1줄로) — 기한: 2026-04-24
2. **[담당: 대표님]** 성수·마곡 오피스텔 급매물 각 3건 리스트업하기 — 기한: 2026-04-27
3. **[담당: 대표님]** 강남·성수·마곡 3개 권역 비교표 작성하기
   (수익률/공실률/매각유동성/리스크) — 기한: 2026-04-27
4. **[담당: 대표님]** 한국은행 금리 전망 보고서 확인하기 — 기한: 2026-04-24

## 🔖 다음 회의 아젠다
- 투자 기준 확정 후, 성수·마곡 급매물 기반 구체 매물 분석
"""


def _print_turn(turn_no: int, turn: dict[str, str]) -> None:
    print(f"\n── Turn {turn_no} ──")
    print(f"🧑 대표님 > {turn['user']}\n")
    for key in ("practitioner", "redteam", "mentor"):
        cfg = AGENT_CONFIG[key]
        header = f"{cfg['emoji']} {cfg['name']}({cfg['label']}):"
        print(header)
        print(f"  {turn[key]}\n")


def main() -> None:
    print(BANNER)
    print(f"📌 데모 안건: {DEMO_TOPIC}")
    print(f"📈 비교 권역: {', '.join(DEMO_REGIONS)}\n")

    summaries = get_multi_region_data(DEMO_REGIONS)
    market_text = format_for_agents(summaries)
    print(market_text)
    analyses = analyze_multi_region(summaries)
    yield_text = format_analysis_for_agents(analyses)
    if yield_text:
        print(yield_text)
    scenario_text = format_full_scenario_for_agents(summaries)
    if scenario_text:
        print(scenario_text)

    cf_tables = build_multi_cashflow(analyses)
    cashflow_text = format_cashflow_for_agents(cf_tables)
    print(cashflow_text)
    mc_results = run_multi_monte_carlo(analyses)
    mc_text = format_monte_carlo_for_agents(mc_results)
    print(mc_text)
    print()

    for i, turn in enumerate(MOCK_TURNS, start=1):
        _print_turn(i, turn)

    started = datetime.now()
    timestamp = started.strftime("%Y-%m-%d %H:%M")
    minutes = MOCK_MINUTES.format(timestamp=timestamp)

    MEETINGS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{started.strftime('%Y-%m-%d-%H%M')}-MOCK-강남-오피스텔-투자-검토.md"
    path = MEETINGS_DIR / filename
    path.write_text(minutes, encoding="utf-8")

    print("\n" + "─" * 60)
    print("📝 [MOCK] 비서실장이 회의록을 정리했습니다.")
    print(f"✅ 저장 경로: {path}")
    print("─" * 60 + "\n")
    print(minutes)
    print("─" * 60)
    print(
        "\n⚠️  이건 Mock 입니다. 실제 API 호출 결과가 아닙니다.\n"
        "    실제 검증은 API KEY 세팅 후 "
        "`python src/main.py --demo` 로 돌리세요.\n"
    )


if __name__ == "__main__":
    main()
