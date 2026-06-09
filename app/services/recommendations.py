from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

LOW_DATA_QUALITY_THRESHOLD = 0.45
STRONG_VALUE_EDGE_THRESHOLD = 0.07
LEAN_VALUE_EDGE_THRESHOLD = 0.035
STRONG_VALUE_CONFIDENCE_THRESHOLD = 0.75
RISK_TAG_CONFIDENCE_PENALTY = 0.08
LOW_DATA_QUALITY_TAG = "low_data_quality"


@dataclass(frozen=True)
class Recommendation:
    label: str
    edge: float
    confidence: float
    risk_level: str
    risk_tags: tuple[str, ...]
    note: str


def risk_level(tags: Sequence[str]) -> str:
    if len(tags) >= 3:
        return "high"
    if len(tags) >= 1:
        return "medium"
    return "low"


def _validate_edge(edge: float) -> None:
    try:
        is_finite = math.isfinite(edge)
    except TypeError as exc:
        raise ValueError("edge must be finite") from exc
    if not is_finite:
        raise ValueError("edge must be finite")


def _validate_data_quality(data_quality: float) -> None:
    try:
        is_valid = math.isfinite(data_quality) and 0 <= data_quality <= 1
    except TypeError as exc:
        raise ValueError("data_quality must be finite and between 0 and 1") from exc
    if not is_valid:
        raise ValueError("data_quality must be finite and between 0 and 1")


def _normalize_risk_tags(risk_tags: Sequence[str]) -> tuple[str, ...]:
    if isinstance(risk_tags, str):
        raise ValueError("risk_tags must be a sequence of strings")
    try:
        normalized = tuple(risk_tags)
    except TypeError as exc:
        raise ValueError("risk_tags must be a sequence of strings") from exc
    if not all(isinstance(tag, str) for tag in normalized):
        raise ValueError("risk_tags must be a sequence of strings")
    return normalized


def classify_recommendation(
    edge: float, data_quality: float, risk_tags: Sequence[str]
) -> Recommendation:
    _validate_edge(edge)
    _validate_data_quality(data_quality)
    normalized_tags = _normalize_risk_tags(risk_tags)

    level = risk_level(normalized_tags)
    if data_quality < LOW_DATA_QUALITY_THRESHOLD:
        level = "high"
        if LOW_DATA_QUALITY_TAG not in normalized_tags:
            normalized_tags = (*normalized_tags, LOW_DATA_QUALITY_TAG)
    confidence = max(
        min(
            data_quality
            - len(normalized_tags) * RISK_TAG_CONFIDENCE_PENALTY
            + max(edge, 0),
            1.0,
        ),
        0.0,
    )
    if data_quality < LOW_DATA_QUALITY_THRESHOLD or level == "high":
        label = "Avoid"
        note = "Data quality or risk conditions are too weak for a confident position."
    elif edge >= STRONG_VALUE_EDGE_THRESHOLD and confidence >= STRONG_VALUE_CONFIDENCE_THRESHOLD:
        label = "Strong value"
        note = "Model edge is meaningful and data confidence is acceptable."
    elif edge >= LEAN_VALUE_EDGE_THRESHOLD:
        label = "Lean value"
        note = "Model edge exists, but risk or confidence limits stake conviction."
    else:
        label = "No bet"
        note = "No clear model-market edge."
    return Recommendation(label, edge, confidence, level, normalized_tags, note)
