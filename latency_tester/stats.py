"""Latency statistics.  Pure functions on lists of floats (milliseconds)."""

from __future__ import annotations

import math
import statistics
from typing import Iterable, Sequence

NAN = math.nan

_EMPTY = {
    "n": 0, "mean": NAN, "median": NAN, "min": NAN, "max": NAN, "stdev": NAN,
    "p5": NAN, "p95": NAN, "p99": NAN, "q1": NAN, "q3": NAN, "iqr": NAN,
    "jitter": NAN, "mad": NAN,
}


def percentile(values: Sequence[float], p: float) -> float:
    """Linear-interpolated percentile, ``p`` in [0, 100]."""
    if not values:
        return NAN
    ordered = sorted(float(v) for v in values)
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * (p / 100.0)
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return ordered[lo]
    frac = pos - lo
    return ordered[lo] * (1.0 - frac) + ordered[hi] * frac


def mad(values: Sequence[float]) -> float:
    """Median Absolute Deviation -- dispersion that ignores a few wild samples."""
    if not values:
        return NAN
    med = statistics.median(values)
    return statistics.median([abs(float(v) - med) for v in values])


def compute_stats(values: Iterable[float]) -> dict:
    vals = [float(v) for v in values]
    if not vals:
        return dict(_EMPTY)

    q1 = percentile(vals, 25)
    q3 = percentile(vals, 75)
    p5 = percentile(vals, 5)
    p95 = percentile(vals, 95)
    return {
        "n": len(vals),
        "mean": statistics.fmean(vals),
        "median": statistics.median(vals),
        "min": min(vals),
        "max": max(vals),
        "stdev": statistics.stdev(vals) if len(vals) > 1 else 0.0,
        "p5": p5,
        "p95": p95,
        "p99": percentile(vals, 99),
        "q1": q1,
        "q3": q3,
        "iqr": q3 - q1,
        "jitter": p95 - p5,
        "mad": mad(vals),
    }


def outlier_indices(values: Sequence[float], k: float = 1.5) -> list[int]:
    """Indices outside the Tukey fence ``[q1 - k*iqr, q3 + k*iqr]``.

    Purely advisory: outliers are highlighted in charts, never dropped from the
    raw data or from any statistic.
    """
    if len(values) < 4:
        return []
    q1 = percentile(values, 25)
    q3 = percentile(values, 75)
    iqr = q3 - q1
    if iqr <= 0:
        return []
    lo, hi = q1 - k * iqr, q3 + k * iqr
    return [i for i, v in enumerate(values) if v < lo or v > hi]


def delta(value: float, baseline: float) -> tuple[float, float]:
    """``(absolute, percent)`` difference of ``value`` against ``baseline``."""
    if any(math.isnan(x) for x in (value, baseline)):
        return NAN, NAN
    diff = value - baseline
    pct = (diff / baseline * 100.0) if baseline else NAN
    return diff, pct


def fmt_ms(value: float | None, digits: int = 3) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "—"
    return f"{value:.{digits}f}"


def fmt_delta(value: float, digits: int = 3) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "—"
    return f"{value:+.{digits}f}"
