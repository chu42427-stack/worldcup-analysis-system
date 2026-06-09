import pytest
from scipy.stats import poisson

from app.models.elo import elo_expected_score, elo_to_goal_delta
from app.models.market import implied_probabilities, market_edge, remove_margin
from app.models.poisson import poisson_market
from app.models.xg import build_expected_goals


def test_market_probabilities_remove_margin():
    raw = implied_probabilities(2.0, 3.5, 4.0)
    fair = remove_margin(raw)
    assert round(sum(fair.values()), 6) == 1.0
    assert fair["home"] > fair["away"]


def test_implied_probabilities_reject_invalid_odds():
    with pytest.raises(ValueError, match="odds must be finite and greater than 1"):
        implied_probabilities(1.0, 3.5, 4.0)


def test_remove_margin_rejects_negative_probability():
    with pytest.raises(ValueError, match="probabilities must be finite and non-negative"):
        remove_margin({"home": 0.5, "draw": -0.1, "away": 0.4})


def test_market_edge_rejects_invalid_probabilities():
    with pytest.raises(ValueError, match="probabilities must be finite values between 0 and 1"):
        market_edge(float("nan"), 0.4)

    with pytest.raises(ValueError, match="probabilities must be finite values between 0 and 1"):
        market_edge(0.6, 1.2)


def test_elo_helpers_are_directional():
    assert elo_expected_score(1800, 1600) > 0.5
    assert elo_to_goal_delta(1800, 1600) > 0


def test_build_expected_goals_uses_recent_and_adjustments():
    result = build_expected_goals(
        market_total=2.8,
        elo_goal_delta=0.4,
        home_recent_xg=1.8,
        away_recent_xg=1.1,
        home_injury_adjustment=-0.1,
        away_injury_adjustment=0,
        tempo_factor=1.0,
        low_event_factor=0.95,
    )
    assert result.home_xg > result.away_xg
    assert 2.0 < result.total_xg < 3.2


def test_build_expected_goals_rejects_bad_totals_and_factors():
    kwargs = {
        "market_total": 2.8,
        "elo_goal_delta": 0.4,
        "home_recent_xg": 1.8,
        "away_recent_xg": 1.1,
        "home_injury_adjustment": -0.1,
        "away_injury_adjustment": 0,
        "tempo_factor": 1.0,
        "low_event_factor": 0.95,
    }

    with pytest.raises(ValueError, match="market_total must be finite and greater than 0"):
        build_expected_goals(**{**kwargs, "market_total": -1.0})

    with pytest.raises(ValueError, match="tempo_factor must be finite and greater than 0"):
        build_expected_goals(**{**kwargs, "tempo_factor": 0})


def test_build_expected_goals_rejects_bad_recent_xg_and_injuries():
    kwargs = {
        "market_total": 2.8,
        "elo_goal_delta": 0.4,
        "home_recent_xg": 1.8,
        "away_recent_xg": 1.1,
        "home_injury_adjustment": -0.1,
        "away_injury_adjustment": 0,
        "tempo_factor": 1.0,
        "low_event_factor": 0.95,
    }

    with pytest.raises(ValueError, match="home_recent_xg must be finite and non-negative"):
        build_expected_goals(**{**kwargs, "home_recent_xg": -0.1})

    with pytest.raises(ValueError, match="away_recent_xg must be finite and non-negative"):
        build_expected_goals(**{**kwargs, "away_recent_xg": float("inf")})

    with pytest.raises(ValueError, match="home_injury_adjustment must be finite"):
        build_expected_goals(**{**kwargs, "home_injury_adjustment": float("nan")})

    with pytest.raises(ValueError, match="away_injury_adjustment must be finite"):
        build_expected_goals(**{**kwargs, "away_injury_adjustment": float("-inf")})


def test_build_expected_goals_rejects_bad_low_event_and_elo_delta():
    kwargs = {
        "market_total": 2.8,
        "elo_goal_delta": 0.4,
        "home_recent_xg": 1.8,
        "away_recent_xg": 1.1,
        "home_injury_adjustment": -0.1,
        "away_injury_adjustment": 0,
        "tempo_factor": 1.0,
        "low_event_factor": 0.95,
    }

    with pytest.raises(ValueError, match="low_event_factor must be finite and greater than 0"):
        build_expected_goals(**{**kwargs, "low_event_factor": 0})

    with pytest.raises(ValueError, match="elo_goal_delta must be finite"):
        build_expected_goals(**{**kwargs, "elo_goal_delta": float("nan")})


def test_poisson_market_probabilities_sum_to_one():
    result = poisson_market(1.7, 0.9, max_goals=8)
    total = result.home_win_prob + result.draw_prob + result.away_win_prob
    assert abs(total - 1.0) < 0.01
    assert result.home_win_prob > result.away_win_prob
    assert result.top_scores[0].probability > 0


def test_poisson_market_rejects_negative_inputs():
    with pytest.raises(ValueError, match="xG values must be finite and non-negative"):
        poisson_market(-0.1, 0.9, max_goals=8)

    with pytest.raises(ValueError, match="max_goals must be a non-negative integer"):
        poisson_market(1.7, 0.9, max_goals=-1)


def test_poisson_market_rejects_non_integer_max_goals():
    with pytest.raises(ValueError, match="max_goals must be a non-negative integer"):
        poisson_market(1.7, 0.9, max_goals=1.5)

    with pytest.raises(ValueError, match="max_goals must be a non-negative integer"):
        poisson_market(1.7, 0.9, max_goals=True)


def test_poisson_market_over_25_uses_untruncated_total_goals():
    home_xg = 1.7
    away_xg = 0.9
    result = poisson_market(home_xg, away_xg, max_goals=1)
    expected = 1 - poisson.cdf(2, home_xg + away_xg)
    assert result.over_25_prob == pytest.approx(expected)
