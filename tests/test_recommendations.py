import math

import pytest

from app.services.recommendations import classify_recommendation, risk_level


def test_classify_strong_value_when_edge_and_quality_are_high():
    rec = classify_recommendation(edge=0.09, data_quality=0.9, risk_tags=[])
    assert rec.label == "Strong value"
    assert rec.confidence > 0.75


def test_classify_avoid_when_data_quality_is_low():
    rec = classify_recommendation(edge=0.1, data_quality=0.35, risk_tags=["injuries_missing"])
    assert rec.label == "Avoid"
    assert rec.risk_level == "high"
    assert rec.risk_tags == ("injuries_missing", "low_data_quality")


def test_returned_risk_tags_are_stable_tuple():
    tags = ["weather_missing"]
    rec = classify_recommendation(edge=0.04, data_quality=0.8, risk_tags=tags)

    tags.append("market_conflict")

    assert rec.risk_tags == ("weather_missing",)


def test_risk_level_uses_tag_count():
    assert risk_level([]) == "low"
    assert risk_level(["weather_missing", "market_conflict"]) == "medium"
    assert risk_level(["a", "b", "c"]) == "high"


def test_threshold_boundaries():
    strong = classify_recommendation(edge=0.07, data_quality=0.9, risk_tags=[])
    lean = classify_recommendation(edge=0.035, data_quality=0.9, risk_tags=[])
    no_bet = classify_recommendation(edge=0.034, data_quality=0.9, risk_tags=[])

    assert strong.label == "Strong value"
    assert lean.label == "Lean value"
    assert no_bet.label == "No bet"


def test_three_risk_tags_cause_avoid_high():
    rec = classify_recommendation(edge=0.2, data_quality=0.9, risk_tags=["a", "b", "c"])

    assert rec.label == "Avoid"
    assert rec.risk_level == "high"


@pytest.mark.parametrize("edge", [math.inf, -math.inf, math.nan, "bad"])
def test_invalid_edge_raises_value_error(edge):
    with pytest.raises(ValueError, match="edge must be finite"):
        classify_recommendation(edge=edge, data_quality=0.9, risk_tags=[])


@pytest.mark.parametrize("data_quality", [math.inf, -math.inf, math.nan, -0.01, 1.01, None])
def test_invalid_data_quality_raises_value_error(data_quality):
    with pytest.raises(ValueError, match="data_quality must be finite and between 0 and 1"):
        classify_recommendation(edge=0.1, data_quality=data_quality, risk_tags=[])


@pytest.mark.parametrize("risk_tags", ["tag", [1], ["ok", object()]])
def test_invalid_risk_tags_raise_value_error(risk_tags):
    with pytest.raises(ValueError, match="risk_tags must be a sequence of strings"):
        classify_recommendation(edge=0.1, data_quality=0.9, risk_tags=risk_tags)


def test_scoring_re_exports_classify_recommendation():
    from app.models.scoring import (
        Recommendation as ScoringRecommendation,
        classify_recommendation as scoring_classify_recommendation,
    )

    rec = scoring_classify_recommendation(edge=0.09, data_quality=0.9, risk_tags=[])

    assert isinstance(rec, ScoringRecommendation)
    assert rec.label == "Strong value"
