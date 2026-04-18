"""Plotly 차트 생성 — 시나리오 시각화.

Streamlit의 st.plotly_chart()로 렌더링할 Figure 객체를 생성한다.
"""
from __future__ import annotations

import plotly.graph_objects as go

from scenario import SensitivityTable, StressTest
from yield_analyzer import YieldAnalysis
from cashflow import CashFlowTable
from monte_carlo import MonteCarloResult


def sensitivity_line_chart(table: SensitivityTable) -> go.Figure:
    labels = [r.label for r in table.results]
    net_yields = [r.analysis.net_yield for r in table.results]
    lev_yields = [r.analysis.leverage_yield for r in table.results]
    incomes = [r.analysis.monthly_net_income for r in table.results]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=labels, y=net_yields, name="실질 수익률(%)",
                             mode="lines+markers"))
    fig.add_trace(go.Scatter(x=labels, y=lev_yields, name="레버리지 수익률(%)",
                             mode="lines+markers"))
    fig.add_trace(go.Bar(x=labels, y=incomes, name="월순수익(만원)",
                         yaxis="y2", opacity=0.3))
    fig.update_layout(
        title=f"{table.region} — {table.variable_name} 민감도",
        yaxis=dict(title="수익률 (%)"),
        yaxis2=dict(title="월순수익 (만원)", overlaying="y", side="right"),
        height=400, template="plotly_white",
    )
    return fig


def stress_bar_chart(tests: list[StressTest]) -> go.Figure:
    regions = [t.region for t in tests]
    worst = [t.worst.analysis.monthly_net_income for t in tests]
    base = [t.base.analysis.monthly_net_income for t in tests]
    best = [t.best.analysis.monthly_net_income for t in tests]

    fig = go.Figure()
    fig.add_trace(go.Bar(name="최악", x=regions, y=worst, marker_color="#EF5350"))
    fig.add_trace(go.Bar(name="기본", x=regions, y=base, marker_color="#42A5F5"))
    fig.add_trace(go.Bar(name="최선", x=regions, y=best, marker_color="#66BB6A"))
    fig.update_layout(
        title="스트레스 테스트 — 월 순수익 비교",
        barmode="group", yaxis_title="월순수익 (만원)",
        height=400, template="plotly_white",
    )
    return fig


def region_radar(analyses: list[YieldAnalysis]) -> go.Figure:
    categories = ["표면수익률", "실질수익률", "레버리지수익률", "월순수익(정규)", "안정성(역BP)"]
    fig = go.Figure()
    for a in analyses:
        bp_inv = round(100 / a.breakeven_years, 1) if a.breakeven_years < 100 else 0
        income_norm = min(a.monthly_net_income / 10, 10)
        values = [a.gross_yield, a.net_yield, a.leverage_yield, income_norm, bp_inv]
        fig.add_trace(go.Scatterpolar(r=values, theta=categories, fill="toself", name=a.region))
    fig.update_layout(
        title="권역 비교 레이더",
        polar=dict(radialaxis=dict(visible=True)),
        height=400, template="plotly_white",
    )
    return fig


def cashflow_chart(table: CashFlowTable) -> go.Figure:
    years = [r.year for r in table.rows]
    incomes = [r.net_income for r in table.rows]
    cumulative = [r.cumulative for r in table.rows]
    values = [r.property_value for r in table.rows]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=years, y=incomes, name="연 순수익(만원)", marker_color="#42A5F5"))
    fig.add_trace(go.Scatter(x=years, y=cumulative, name="누적수익(만원)",
                             mode="lines+markers", marker_color="#FF9800"))
    fig.add_trace(go.Scatter(x=years, y=values, name="자산가치(만원)",
                             mode="lines", yaxis="y2", marker_color="#66BB6A"))
    fig.update_layout(
        title=f"{table.region} — {table.params.holding_years}년 현금흐름",
        yaxis=dict(title="수익 (만원)"),
        yaxis2=dict(title="자산가치 (만원)", overlaying="y", side="right"),
        height=400, template="plotly_white",
    )
    return fig


def monte_carlo_histogram(result: MonteCarloResult) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Histogram(x=result.irr_list, nbinsx=50, name="IRR 분포",
                               marker_color="#42A5F5", opacity=0.7))
    for p, label, color in [
        (result.p5, "P5", "red"), (result.p50, "P50", "orange"),
        (result.p95, "P95", "green"),
    ]:
        fig.add_vline(x=p, line_dash="dash", line_color=color,
                      annotation_text=f"{label}: {p:.1f}%")
    fig.update_layout(
        title=f"{result.region} — IRR 분포 ({result.n_simulations:,}회)",
        xaxis_title="IRR (%)", yaxis_title="빈도",
        height=400, template="plotly_white",
    )
    return fig
