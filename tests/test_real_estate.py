"""Tests for real_estate module."""
from real_estate import (
    REGION_CODES,
    TradeRecord,
    RentRecord,
    RegionSummary,
    get_region_data,
    get_multi_region_data,
    format_for_agents,
)


class TestRegionCodes:
    def test_has_key_regions(self):
        for name in ["강남구", "성동구", "강서구"]:
            assert name in REGION_CODES

    def test_codes_are_5_digits(self):
        for code in REGION_CODES.values():
            assert len(code) == 5 and code.isdigit()


class TestTradeRecord:
    def test_price_billion_large(self):
        r = TradeRecord("역삼동", "T", 40.0, 5, 45000, 2026, 2, 1)
        assert r.price_billion == "4억 5,000만원"

    def test_price_billion_exact(self):
        r = TradeRecord("역삼동", "T", 40.0, 5, 50000, 2026, 2, 1)
        assert r.price_billion == "5억"

    def test_price_billion_small(self):
        r = TradeRecord("역삼동", "T", 40.0, 5, 8000, 2026, 2, 1)
        assert r.price_billion == "8,000만원"


class TestRentRecord:
    def test_rent_display(self):
        r = RentRecord("역삼동", "T", 40.0, 5, 3000, 120, 2026, 2, 1)
        assert "3,000만원" in r.rent_display
        assert "120만원" in r.rent_display


class TestGetRegionData:
    def test_known_region_returns_sample(self):
        s = get_region_data("강남구")
        assert s.is_sample
        assert s.region == "강남구"
        assert len(s.trade_records) > 0
        assert len(s.rent_records) > 0

    def test_unknown_region_returns_empty_sample(self):
        s = get_region_data("종로구")
        assert s.is_sample
        assert len(s.trade_records) == 0

    def test_avg_trade_price(self):
        s = get_region_data("강남구")
        assert s.avg_trade_price > 0

    def test_avg_monthly_rent(self):
        s = get_region_data("강남구")
        assert s.avg_monthly_rent > 0


class TestGetMultiRegion:
    def test_returns_correct_count(self):
        summaries = get_multi_region_data(["강남구", "성동구"])
        assert len(summaries) == 2

    def test_preserves_order(self):
        summaries = get_multi_region_data(["강서구", "강남구"])
        assert summaries[0].region == "강서구"
        assert summaries[1].region == "강남구"


class TestFormatForAgents:
    def test_contains_header(self, sample_summaries):
        text = format_for_agents(sample_summaries)
        assert "실거래 데이터" in text

    def test_contains_all_regions(self, sample_summaries):
        text = format_for_agents(sample_summaries)
        for s in sample_summaries:
            assert s.region in text

    def test_sample_flag(self, sample_summaries):
        text = format_for_agents(sample_summaries)
        assert "샘플 데이터" in text

    def test_empty_list_returns_empty(self):
        assert format_for_agents([]) == ""
