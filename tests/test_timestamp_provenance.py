from app.navigation import format_timestamp, to_display_timestamp


def test_historical_ntz_is_not_relabelled_as_a_known_instant():
    assert format_timestamp("2026-10-05 17:03:39.994") == "2026-10-05 17:03 (stored time; timezone unverified)"
    assert to_display_timestamp("2026-10-05 17:03:39.994").tzinfo is None


def test_explicit_future_utc_provenance_can_be_displayed_in_halifax():
    assert format_timestamp("2026-01-15 12:00", naive_timezone="UTC") == "2026-01-15 08:00 AST (America/Halifax)"
    assert format_timestamp("2026-01-15T12:00Z") == "2026-01-15 08:00 AST (America/Halifax)"
