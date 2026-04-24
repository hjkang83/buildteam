"""Streamlit 채팅 UI — 부동산 투자 자문 시스템 웹 프론트엔드.

Usage:
    streamlit run src/app.py
"""
from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

from meeting import Meeting
from personas import AGENT_CONFIG
from real_estate import REGION_CODES, PROPERTY_TYPES, format_for_agents, get_multi_region_data
from file_parser import parse_file, SUPPORTED_EXTENSIONS
from file_parser import format_for_agents as format_files_for_agents
from yield_analyzer import (
    InvestmentParams,
    analyze_multi_region,
    format_analysis_for_agents,
)
from scenario import (
    format_full_scenario_for_agents,
    rate_sensitivity, vacancy_sensitivity, price_sensitivity, stress_test,
)
from cashflow import build_multi_cashflow, format_cashflow_for_agents, CashFlowParams
from monte_carlo import run_multi_monte_carlo, format_monte_carlo_for_agents
from charts import (
    sensitivity_line_chart, stress_bar_chart, region_radar,
    cashflow_chart, monte_carlo_histogram,
)
from demo_mock import MOCK_TURNS, MOCK_MINUTES, DEMO_TOPIC, DEMO_REGIONS


st.set_page_config(
    page_title="부동산 투자 자문 시스템",
    page_icon="🏢",
    layout="wide",
)

AGENT_COLORS = {
    "practitioner": "#2196F3",
    "redteam": "#F44336",
    "mentor": "#4CAF50",
    "clerk": "#FF9800",
}


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ------------------------------------------------------------------
# Sidebar: 회의 설정
# ------------------------------------------------------------------

with st.sidebar:
    st.markdown("## 🏢 회의 설정")

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        api_key = st.text_input(
            "Anthropic API Key",
            type="password",
            help="ANTHROPIC_API_KEY 환경변수 또는 .env 파일로도 설정 가능",
        )
        if api_key:
            os.environ["ANTHROPIC_API_KEY"] = api_key

    st.divider()

    topic = st.text_input(
        "📌 회의 안건",
        placeholder="예: 강남 오피스텔 투자 검토",
    )

    property_type = st.radio(
        "🏠 매물 유형",
        options=["officetel", "apartment"],
        format_func=lambda x: "오피스텔" if x == "officetel" else "아파트",
        horizontal=True,
    )

    selected_regions = st.multiselect(
        "📈 실거래 데이터 지역",
        options=list(REGION_CODES.keys()),
        default=["강남구"],
        help="선택한 지역의 실거래 데이터를 자동 로딩합니다",
    )

    uploaded_files = st.file_uploader(
        "📎 파일 업로드",
        type=["xlsx", "xls", "pdf"],
        accept_multiple_files=True,
        help="매물 리스트(Excel), 계약서(PDF) 등",
    )

    with st.expander("🗣 토론 설정", expanded=False):
        debate_mode = st.checkbox("에이전트 간 토론 모드", value=False,
                                  help="에이전트가 서로의 의견에 반론·보충합니다")
        debate_rounds = st.slider("토론 라운드", 1, 3, 2,
                                  disabled=not debate_mode)
        auto_challenge = st.checkbox("자동 반론 주입", value=True,
                                     help="전원 합의 시 확증편향 방지 프롬프트")

    with st.expander("⚙️ 투자 분석 조건", expanded=False):
        ltv_pct = st.slider("LTV (대출비율 %)", 0, 80, 60, 5,
                             help="매매가 대비 대출 비율")
        ltv = ltv_pct / 100.0
        loan_rate = st.slider("대출금리 (연 %)", 2.0, 7.0, 4.0, 0.5)
        vacancy = st.slider("연간 공실 (개월)", 0.0, 3.0, 1.0, 0.5)
        mgmt_fee = st.number_input("월 관리비 (만원)", 0, 100, 15, 1)

    invest_params = InvestmentParams(
        ltv=ltv,
        loan_rate=loan_rate,
        vacancy_months=vacancy,
        mgmt_fee=mgmt_fee,
    )

    st.divider()

    col1, col2 = st.columns(2)
    start_btn = col1.button("🚀 회의 시작", type="primary", use_container_width=True)
    end_btn = col2.button("📝 회의 종료", use_container_width=True)

    if st.button("🗑 새 회의", use_container_width=True):
        for key in ["meeting", "messages", "finalized", "minutes", "mock_mode"]:
            st.session_state.pop(key, None)
        st.rerun()

    mock_btn = st.button("🎭 Mock 데모", use_container_width=True,
                         help="API 키 없이 Gold Standard 기반 데모를 실행합니다")

    st.divider()
    st.caption("참석자")
    for key in ["practitioner", "redteam", "mentor"]:
        cfg = AGENT_CONFIG[key]
        st.markdown(f"{cfg['emoji']} **{cfg['name']}** ({cfg['label']})")


# ------------------------------------------------------------------
# 회의 시작
# ------------------------------------------------------------------

if start_btn:
    if not os.getenv("ANTHROPIC_API_KEY"):
        st.error("❌ Anthropic API Key를 먼저 설정해 주세요.")
        st.stop()
    if not topic:
        st.error("❌ 회의 안건을 입력해 주세요.")
        st.stop()

    market_data, yield_data, scenario_data = "", "", ""
    cashflow_data, mc_data = "", ""
    analyses_cache: list = []
    summaries_cache: list = []
    if selected_regions:
        summaries_cache = get_multi_region_data(selected_regions, property_type=property_type)
        market_data = format_for_agents(summaries_cache)
        analyses_cache = analyze_multi_region(summaries_cache, invest_params)
        yield_data = format_analysis_for_agents(analyses_cache)
        scenario_data = format_full_scenario_for_agents(summaries_cache, invest_params)
        if analyses_cache:
            cf_tables = build_multi_cashflow(analyses_cache)
            cashflow_data = format_cashflow_for_agents(cf_tables)
            mc_results = run_multi_monte_carlo(analyses_cache)
            mc_data = format_monte_carlo_for_agents(mc_results)

    file_data = ""
    if uploaded_files:
        file_texts: list[tuple[str, str]] = []
        for uf in uploaded_files:
            suffix = Path(uf.name).suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uf.getvalue())
                tmp_path = tmp.name
            try:
                text = parse_file(tmp_path)
                file_texts.append((uf.name, text))
            except Exception as e:
                st.warning(f"⚠️ {uf.name} 파싱 실패: {e}")
            finally:
                os.unlink(tmp_path)
        if file_texts:
            file_data = format_files_for_agents(file_texts)

    all_data = "\n".join(filter(None, [
        market_data, yield_data, scenario_data, cashflow_data, mc_data,
    ]))
    meeting = Meeting(
        topic,
        market_data=market_data,
        yield_data=yield_data,
        scenario_data=all_data,
        file_data=file_data,
    )
    meeting.auto_challenge = auto_challenge
    st.session_state["meeting"] = meeting
    st.session_state["messages"] = []
    st.session_state["finalized"] = False
    st.session_state["debate_mode"] = debate_mode
    st.session_state["debate_rounds"] = debate_rounds
    st.session_state["analyses"] = analyses_cache
    st.session_state["summaries"] = summaries_cache

    init_msgs: list[dict] = []
    if market_data:
        init_msgs.append({"role": "system", "content": market_data, "type": "market"})
    if yield_data:
        init_msgs.append({"role": "system", "content": yield_data, "type": "yield"})
    if scenario_data:
        init_msgs.append({"role": "system", "content": scenario_data, "type": "scenario"})
    if cashflow_data:
        init_msgs.append({"role": "system", "content": cashflow_data, "type": "cashflow"})
    if mc_data:
        init_msgs.append({"role": "system", "content": mc_data, "type": "montecarlo"})
    if file_data:
        init_msgs.append({"role": "system", "content": file_data, "type": "file"})
    st.session_state["messages"] = init_msgs
    st.rerun()


# ------------------------------------------------------------------
# Mock 데모 모드
# ------------------------------------------------------------------

if mock_btn:
    from datetime import datetime

    summaries = get_multi_region_data(DEMO_REGIONS)
    market_data = format_for_agents(summaries)
    analyses = analyze_multi_region(summaries)
    yield_data = format_analysis_for_agents(analyses)
    scenario_data = format_full_scenario_for_agents(summaries)

    meeting = Meeting(DEMO_TOPIC, market_data=market_data,
                      yield_data=yield_data, scenario_data=scenario_data)
    st.session_state["meeting"] = meeting
    st.session_state["mock_mode"] = True
    st.session_state["finalized"] = False

    msgs: list[dict] = []
    if market_data:
        msgs.append({"role": "system", "content": market_data, "type": "market"})
    if yield_data:
        msgs.append({"role": "system", "content": yield_data, "type": "yield"})
    if scenario_data:
        msgs.append({"role": "system", "content": scenario_data, "type": "scenario"})

    for turn in MOCK_TURNS:
        msgs.append({"role": "user", "content": turn["user"]})
        for key in ("practitioner", "redteam", "mentor"):
            msgs.append({"role": "agent", "agent_key": key, "content": turn[key]})

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    minutes_text = MOCK_MINUTES.format(timestamp=timestamp)
    msgs.append({"role": "minutes", "content": minutes_text})

    st.session_state["messages"] = msgs
    st.session_state["finalized"] = True
    st.rerun()


# ------------------------------------------------------------------
# 메인 채팅 영역
# ------------------------------------------------------------------

st.markdown(
    "<h2 style='text-align:center;'>🏢 Data 기반 Multi-Agent 부동산 투자 자문 시스템</h2>",
    unsafe_allow_html=True,
)

meeting: Meeting | None = st.session_state.get("meeting")

if meeting is None:
    st.info("👈 왼쪽 사이드바에서 안건을 입력하고 **회의 시작**을 눌러주세요.")
    st.stop()

mock_label = "  |  🎭 Mock 데모" if st.session_state.get("mock_mode") else ""
st.caption(f"📌 안건: {meeting.topic}  |  🗂 세션: {meeting.session_id}{mock_label}")

messages = st.session_state.get("messages", [])

for msg in messages:
    if msg["role"] == "system":
        type_labels = {
            "market": "📈 실거래 데이터",
            "yield": "📊 수익률 분석",
            "scenario": "🔮 시나리오 시뮬레이션",
            "cashflow": "💰 10년 현금흐름",
            "montecarlo": "🎲 Monte Carlo",
            "file": "📎 업로드 파일",
        }
        msg_type = msg.get("type", "")
        label = type_labels.get(msg_type, "📋 데이터")
        with st.expander(label, expanded=msg_type in ("yield", "scenario")):
            st.text(msg["content"])
    elif msg["role"] == "user":
        with st.chat_message("user", avatar="🧑"):
            st.markdown(msg["content"])
    elif msg["role"] == "agent":
        key = msg.get("agent_key", "")
        cfg = AGENT_CONFIG.get(key, {})
        avatar = cfg.get("emoji", "🤖")
        name = cfg.get("name", "Agent")
        label = cfg.get("label", "")
        color = AGENT_COLORS.get(key, "#666")
        with st.chat_message("assistant", avatar=avatar):
            st.markdown(
                f"<span style='color:{color};font-weight:bold;'>"
                f"{name}({label})</span>",
                unsafe_allow_html=True,
            )
            st.markdown(msg["content"])
    elif msg["role"] == "minutes":
        st.divider()
        st.markdown("### 📝 회의록")
        st.markdown(msg["content"])

# ------------------------------------------------------------------
# 차트 시각화
# ------------------------------------------------------------------

analyses_data = st.session_state.get("analyses", [])
summaries_data = st.session_state.get("summaries", [])

if analyses_data and not st.session_state.get("mock_mode"):
    with st.expander("📊 시각화 차트", expanded=False):
        chart_tabs = st.tabs(["권역 비교", "민감도", "스트레스", "현금흐름", "Monte Carlo"])
        with chart_tabs[0]:
            st.plotly_chart(region_radar(analyses_data), use_container_width=True)
        with chart_tabs[1]:
            for s in summaries_data[:2]:
                rt = rate_sensitivity(s, invest_params)
                if rt:
                    st.plotly_chart(sensitivity_line_chart(rt), use_container_width=True)
        with chart_tabs[2]:
            tests = [stress_test(s, invest_params) for s in summaries_data]
            tests = [t for t in tests if t]
            if tests:
                st.plotly_chart(stress_bar_chart(tests), use_container_width=True)
        with chart_tabs[3]:
            cf_tables = build_multi_cashflow(analyses_data)
            for t in cf_tables[:2]:
                st.plotly_chart(cashflow_chart(t), use_container_width=True)
        with chart_tabs[4]:
            mc = run_multi_monte_carlo(analyses_data)
            for r in mc:
                if r.n_simulations > 0:
                    st.plotly_chart(monte_carlo_histogram(r), use_container_width=True)

# ------------------------------------------------------------------
# 회의 종료 → 회의록 생성
# ------------------------------------------------------------------

if end_btn and meeting and not st.session_state.get("finalized"):
    user_turns = [m for m in messages if m["role"] == "user"]
    if not user_turns:
        st.warning("⚠️ 아직 대화가 없습니다. 먼저 발언해 주세요.")
    else:
        with st.spinner("📝 비서실장이 회의록을 정리하는 중..."):
            try:
                minutes_text, path = _run_async(meeting.finalize())
                st.session_state["finalized"] = True
                st.session_state["minutes"] = minutes_text
                messages.append({"role": "minutes", "content": minutes_text})
                st.session_state["messages"] = messages
                st.success(f"✅ 회의록 저장: {path}")
                st.rerun()
            except Exception as e:
                st.error(f"❌ 회의록 생성 실패: {e}")

# ------------------------------------------------------------------
# 채팅 입력
# ------------------------------------------------------------------

if not st.session_state.get("finalized"):
    if user_input := st.chat_input("대표님, 말씀하세요..."):
        messages.append({"role": "user", "content": user_input})

        with st.chat_message("user", avatar="🧑"):
            st.markdown(user_input)

        use_debate = st.session_state.get("debate_mode", False)
        n_rounds = st.session_state.get("debate_rounds", 2)

        if use_debate and n_rounds > 1:
            with st.spinner(f"에이전트 토론 중 ({n_rounds} 라운드)..."):
                all_rounds = _run_async(
                    meeting.user_says_with_debate(user_input, rounds=n_rounds)
                )
            turns = [t for rnd in all_rounds for t in rnd]
        else:
            with st.spinner("에이전트 응답 생성 중..."):
                turns = _run_async(meeting.user_says(user_input))

        for turn in turns:
            key = turn["agent_key"]
            cfg = AGENT_CONFIG[key]
            color = AGENT_COLORS.get(key, "#666")
            msg_data = {
                "role": "agent",
                "agent_key": key,
                "content": turn["text"],
            }
            messages.append(msg_data)

            with st.chat_message("assistant", avatar=cfg["emoji"]):
                st.markdown(
                    f"<span style='color:{color};font-weight:bold;'>"
                    f"{cfg['name']}({cfg['label']})</span>",
                    unsafe_allow_html=True,
                )
                st.markdown(turn["text"])

        st.session_state["messages"] = messages
