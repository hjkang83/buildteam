"""국토교통부 실거래가 API 클라이언트 + 샘플 데이터 fallback.

공공데이터포털(data.go.kr) 오피스텔 매매/전월세 실거래 조회 API를 호출하고,
XML 응답을 파싱하여 에이전트 컨텍스트용 텍스트 블록으로 변환한다.

API 키가 없거나 호출 실패 시, Gold Standard 기반 샘플 데이터를 반환하여
데모/테스트가 API 없이도 작동한다.
"""
from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

REGION_CODES: dict[str, str] = {
    "강남구": "11680",
    "서초구": "11650",
    "성동구": "11200",
    "강서구": "11500",
    "마포구": "11440",
    "용산구": "11170",
    "송파구": "11710",
    "영등포구": "11560",
}

TRADE_API_URL = "http://openapi.molit.go.kr/OpenAPI_ToolInstall498/service/rest/RTMSOBJSvc/getRTMSDataSvcOffiTrade"
RENT_API_URL = "http://openapi.molit.go.kr/OpenAPI_ToolInstallPack498/service/rest/RTMSOBJSvc/getRTMSDataSvcOffiRent"


@dataclass
class TradeRecord:
    district: str       # 법정동
    name: str           # 단지명
    area: float         # 전용면적 (㎡)
    floor: int          # 층
    price: int          # 거래금액 (만원)
    year: int           # 년
    month: int          # 월
    day: int            # 일

    @property
    def price_billion(self) -> str:
        if self.price >= 10000:
            b = self.price // 10000
            r = self.price % 10000
            return f"{b}억 {r:,}만원" if r else f"{b}억"
        return f"{self.price:,}만원"


@dataclass
class RentRecord:
    district: str
    name: str
    area: float
    floor: int
    deposit: int        # 보증금 (만원)
    monthly_rent: int   # 월세 (만원)
    year: int
    month: int
    day: int

    @property
    def rent_display(self) -> str:
        dep = f"{self.deposit:,}"
        return f"보증금 {dep}만원 / 월세 {self.monthly_rent:,}만원"


@dataclass
class RegionSummary:
    region: str
    deal_month: str
    trade_records: list[TradeRecord] = field(default_factory=list)
    rent_records: list[RentRecord] = field(default_factory=list)
    is_sample: bool = False

    @property
    def avg_trade_price(self) -> int:
        if not self.trade_records:
            return 0
        return sum(r.price for r in self.trade_records) // len(self.trade_records)

    @property
    def avg_monthly_rent(self) -> int:
        rents = [r for r in self.rent_records if r.monthly_rent > 0]
        if not rents:
            return 0
        return sum(r.monthly_rent for r in rents) // len(rents)

    @property
    def avg_area(self) -> float:
        all_records = self.trade_records + self.rent_records
        if not all_records:
            return 0
        return sum(r.area for r in all_records) / len(all_records)


# ------------------------------------------------------------------
# API 호출
# ------------------------------------------------------------------


def fetch_trades(region_code: str, deal_ym: str, api_key: str) -> list[TradeRecord]:
    params = {
        "serviceKey": api_key,
        "LAWD_CD": region_code,
        "DEAL_YMD": deal_ym,
    }
    url = f"{TRADE_API_URL}?{urlencode(params)}"
    with urlopen(url, timeout=10) as resp:
        xml_data = resp.read().decode("utf-8")
    return _parse_trade_xml(xml_data)


def fetch_rents(region_code: str, deal_ym: str, api_key: str) -> list[RentRecord]:
    params = {
        "serviceKey": api_key,
        "LAWD_CD": region_code,
        "DEAL_YMD": deal_ym,
    }
    url = f"{RENT_API_URL}?{urlencode(params)}"
    with urlopen(url, timeout=10) as resp:
        xml_data = resp.read().decode("utf-8")
    return _parse_rent_xml(xml_data)


def _parse_trade_xml(xml_data: str) -> list[TradeRecord]:
    root = ET.fromstring(xml_data)
    records: list[TradeRecord] = []
    for item in root.iter("item"):
        records.append(TradeRecord(
            district=_text(item, "법정동"),
            name=_text(item, "단지"),
            area=float(_text(item, "전용면적") or "0"),
            floor=int(_text(item, "층") or "0"),
            price=int(_text(item, "거래금액", "").replace(",", "").strip() or "0"),
            year=int(_text(item, "년") or "0"),
            month=int(_text(item, "월") or "0"),
            day=int(_text(item, "일") or "0"),
        ))
    return records


def _parse_rent_xml(xml_data: str) -> list[RentRecord]:
    root = ET.fromstring(xml_data)
    records: list[RentRecord] = []
    for item in root.iter("item"):
        records.append(RentRecord(
            district=_text(item, "법정동"),
            name=_text(item, "단지"),
            area=float(_text(item, "전용면적") or "0"),
            floor=int(_text(item, "층") or "0"),
            deposit=int(_text(item, "보증금", "").replace(",", "").strip() or "0"),
            monthly_rent=int(_text(item, "월세금액", "").replace(",", "").strip() or "0"),
            year=int(_text(item, "년") or "0"),
            month=int(_text(item, "월") or "0"),
            day=int(_text(item, "일") or "0"),
        ))
    return records


def _text(item: ET.Element, tag: str, default: str = "") -> str:
    el = item.find(tag)
    return el.text.strip() if el is not None and el.text else default


# ------------------------------------------------------------------
# 통합 조회 (API → fallback)
# ------------------------------------------------------------------


def get_region_data(
    region_name: str,
    deal_ym: str | None = None,
    api_key: str | None = None,
) -> RegionSummary:
    """지역 실거래 데이터 조회. API 키 없으면 샘플 데이터 반환."""
    api_key = api_key or os.getenv("DATA_GO_KR_API_KEY")
    region_code = REGION_CODES.get(region_name)

    if not deal_ym:
        from datetime import datetime
        now = datetime.now()
        if now.month <= 2:
            deal_ym = f"{now.year - 1}{now.month + 10:02d}"
        else:
            deal_ym = f"{now.year}{now.month - 2:02d}"

    if api_key and region_code:
        try:
            trades = fetch_trades(region_code, deal_ym, api_key)
            rents = fetch_rents(region_code, deal_ym, api_key)
            return RegionSummary(
                region=region_name,
                deal_month=deal_ym,
                trade_records=trades,
                rent_records=rents,
                is_sample=False,
            )
        except Exception:
            pass

    return _get_sample_data(region_name, deal_ym)


def get_multi_region_data(
    regions: list[str],
    deal_ym: str | None = None,
) -> list[RegionSummary]:
    return [get_region_data(r, deal_ym) for r in regions]


# ------------------------------------------------------------------
# 에이전트 컨텍스트 포매터
# ------------------------------------------------------------------


def format_for_agents(summaries: list[RegionSummary]) -> str:
    """RegionSummary 리스트를 에이전트 주입용 텍스트 블록으로 변환."""
    if not summaries:
        return ""

    lines = ["=== 📈 부동산 실거래 데이터 ==="]
    sample_flag = any(s.is_sample for s in summaries)
    if sample_flag:
        lines.append("(⚠️ API 키 미설정 — 샘플 데이터 기반)")
    lines.append("")

    for s in summaries:
        lines.append(f"■ {s.region} (조회기간: {s.deal_month})")

        if s.trade_records:
            lines.append(f"  매매 건수: {len(s.trade_records)}건")
            avg = s.avg_trade_price
            if avg >= 10000:
                lines.append(f"  평균 매매가: {avg // 10000}억 {avg % 10000:,}만원")
            else:
                lines.append(f"  평균 매매가: {avg:,}만원")
            lines.append(f"  평균 전용면적: {s.avg_area:.1f}㎡")
            lines.append("  최근 거래:")
            for r in s.trade_records[:5]:
                lines.append(
                    f"    - {r.name} {r.area}㎡ {r.floor}층 "
                    f"→ {r.price_billion} ({r.year}.{r.month:02d}.{r.day:02d})"
                )
        else:
            lines.append("  매매 실거래: 데이터 없음")

        if s.rent_records:
            rents_with_monthly = [r for r in s.rent_records if r.monthly_rent > 0]
            lines.append(f"  전월세 건수: {len(s.rent_records)}건 (월세 {len(rents_with_monthly)}건)")
            if rents_with_monthly:
                lines.append(f"  평균 월세: {s.avg_monthly_rent:,}만원")
            lines.append("  최근 전월세:")
            for r in s.rent_records[:5]:
                lines.append(
                    f"    - {r.name} {r.area}㎡ {r.floor}층 "
                    f"→ {r.rent_display} ({r.year}.{r.month:02d}.{r.day:02d})"
                )
        else:
            lines.append("  전월세 실거래: 데이터 없음")

        lines.append("")

    lines.append("=== 실거래 데이터 끝 ===")
    return "\n".join(lines)


# ------------------------------------------------------------------
# 샘플 데이터 (API 키 없을 때 fallback — Gold Standard 기반)
# ------------------------------------------------------------------


_SAMPLE_DATA: dict[str, dict[str, Any]] = {
    "강남구": {
        "trades": [
            {"district": "역삼동", "name": "역삼 센트럴 오피스텔", "area": 42.3, "floor": 8, "price": 45000, "year": 2026, "month": 2, "day": 15},
            {"district": "역삼동", "name": "역삼 파크뷰", "area": 35.7, "floor": 5, "price": 38000, "year": 2026, "month": 2, "day": 8},
            {"district": "삼성동", "name": "삼성 오피스텔타워", "area": 48.1, "floor": 12, "price": 52000, "year": 2026, "month": 1, "day": 22},
            {"district": "논현동", "name": "논현 스퀘어", "area": 39.5, "floor": 6, "price": 41000, "year": 2026, "month": 1, "day": 10},
            {"district": "대치동", "name": "대치 센트럴", "area": 44.8, "floor": 10, "price": 47000, "year": 2026, "month": 2, "day": 3},
        ],
        "rents": [
            {"district": "역삼동", "name": "역삼 센트럴 오피스텔", "area": 42.3, "floor": 7, "deposit": 3000, "monthly_rent": 120, "year": 2026, "month": 2, "day": 18},
            {"district": "삼성동", "name": "삼성 오피스텔타워", "area": 48.1, "floor": 9, "deposit": 5000, "monthly_rent": 140, "year": 2026, "month": 2, "day": 12},
            {"district": "논현동", "name": "논현 스퀘어", "area": 39.5, "floor": 4, "deposit": 2000, "monthly_rent": 110, "year": 2026, "month": 1, "day": 25},
            {"district": "대치동", "name": "대치 센트럴", "area": 44.8, "floor": 8, "deposit": 4000, "monthly_rent": 130, "year": 2026, "month": 2, "day": 5},
            {"district": "역삼동", "name": "역삼 파크뷰", "area": 35.7, "floor": 3, "deposit": 10000, "monthly_rent": 80, "year": 2026, "month": 1, "day": 15},
        ],
    },
    "성동구": {
        "trades": [
            {"district": "성수동1가", "name": "성수 에비뉴", "area": 38.2, "floor": 7, "price": 32000, "year": 2026, "month": 2, "day": 20},
            {"district": "성수동2가", "name": "서울숲 오피스텔", "area": 41.5, "floor": 9, "price": 35000, "year": 2026, "month": 2, "day": 14},
            {"district": "성수동1가", "name": "성수 IT타워", "area": 33.8, "floor": 5, "price": 28000, "year": 2026, "month": 1, "day": 28},
            {"district": "옥수동", "name": "옥수 리버뷰", "area": 45.2, "floor": 11, "price": 38000, "year": 2026, "month": 1, "day": 18},
        ],
        "rents": [
            {"district": "성수동1가", "name": "성수 에비뉴", "area": 38.2, "floor": 6, "deposit": 2000, "monthly_rent": 120, "year": 2026, "month": 2, "day": 22},
            {"district": "성수동2가", "name": "서울숲 오피스텔", "area": 41.5, "floor": 8, "deposit": 3000, "monthly_rent": 130, "year": 2026, "month": 2, "day": 10},
            {"district": "성수동1가", "name": "성수 IT타워", "area": 33.8, "floor": 4, "deposit": 1500, "monthly_rent": 100, "year": 2026, "month": 1, "day": 30},
            {"district": "옥수동", "name": "옥수 리버뷰", "area": 45.2, "floor": 10, "deposit": 5000, "monthly_rent": 110, "year": 2026, "month": 1, "day": 20},
        ],
    },
    "강서구": {
        "trades": [
            {"district": "마곡동", "name": "마곡 엠밸리", "area": 36.4, "floor": 6, "price": 28000, "year": 2026, "month": 2, "day": 17},
            {"district": "마곡동", "name": "마곡 나루", "area": 42.0, "floor": 8, "price": 31000, "year": 2026, "month": 2, "day": 9},
            {"district": "마곡동", "name": "마곡 테크노타워", "area": 33.5, "floor": 4, "price": 25000, "year": 2026, "month": 1, "day": 23},
            {"district": "마곡동", "name": "마곡 센트럴파크", "area": 39.8, "floor": 10, "price": 30000, "year": 2026, "month": 1, "day": 12},
        ],
        "rents": [
            {"district": "마곡동", "name": "마곡 엠밸리", "area": 36.4, "floor": 5, "deposit": 1500, "monthly_rent": 100, "year": 2026, "month": 2, "day": 19},
            {"district": "마곡동", "name": "마곡 나루", "area": 42.0, "floor": 7, "deposit": 2000, "monthly_rent": 110, "year": 2026, "month": 2, "day": 11},
            {"district": "마곡동", "name": "마곡 테크노타워", "area": 33.5, "floor": 3, "deposit": 1000, "monthly_rent": 85, "year": 2026, "month": 1, "day": 25},
            {"district": "마곡동", "name": "마곡 센트럴파크", "area": 39.8, "floor": 9, "deposit": 3000, "monthly_rent": 95, "year": 2026, "month": 1, "day": 14},
        ],
    },
}


def _get_sample_data(region_name: str, deal_ym: str) -> RegionSummary:
    data = _SAMPLE_DATA.get(region_name)
    if not data:
        return RegionSummary(
            region=region_name,
            deal_month=deal_ym,
            is_sample=True,
        )

    trades = [TradeRecord(**r) for r in data["trades"]]
    rents = [RentRecord(**r) for r in data["rents"]]
    return RegionSummary(
        region=region_name,
        deal_month=deal_ym,
        trade_records=trades,
        rent_records=rents,
        is_sample=True,
    )
