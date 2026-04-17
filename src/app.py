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
from real_estate import REGION_CODES, format_for_agents, get_multi_region_data
from file_parser import parse_file, SUPPORTED_EXTENSIONS
from file_parser import format_for_agents as format_files_for_agents


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

    selected_regions = st.multiselect(
        "📈 실거래 데이터 지역",
        options=list(REGION_CODES.keys()),
        default=["강남구"],
        help="선택한 지역의 오피스텔 실거래 데이터를 자동 로딩합니다",
    )

    uploaded_files = st.file_uploader(
        "📎 파일 업로드",
        type=["xlsx", "xls", "pdf"],
        accept_multiple_files=True,
        help="매물 리스트(Excel), 계약서(PDF) 등",
    )

    st.divider()

    col1, col2 = st.columns(2)
    start_btn = col1.button("🚀 회의 시작", type="primary", use_container_width=True)
    end_btn = col2.button("📝 회의 종료", use_container_width=True)

    if st.button("🗑 새 회의", use_container_width=True):
        for key in ["meeting", "messages", "finalized", "minutes"]:
            st.session_state.pop(key, None)
        st.rerun()

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

    market_data = ""
    if selected_regions:
        summaries = get_multi_region_data(selected_regions)
        market_data = format_for_agents(summaries)

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

    meeting = Meeting(
        topic,
        market_data=market_data,
        file_data=file_data,
    )
    st.session_state["meeting"] = meeting
    st.session_state["messages"] = []
    st.session_state["finalized"] = False

    init_msgs = []
    if market_data:
        init_msgs.append({"role": "system", "content": market_data, "type": "market"})
    if file_data:
        init_msgs.append({"role": "system", "content": file_data, "type": "file"})
    st.session_state["messages"] = init_msgs
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

st.caption(f"📌 안건: {meeting.topic}  |  🗂 세션: {meeting.session_id}")

messages = st.session_state.get("messages", [])

for msg in messages:
    if msg["role"] == "system":
        label = "📈 실거래 데이터" if msg.get("type") == "market" else "📎 업로드 파일"
        with st.expander(label, expanded=False):
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
