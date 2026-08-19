import math

import pytest

from latency_tester.stats import (compute_stats, delta, fmt_delta, fmt_ms, mad,
                                  outlier_indices, percentile)


def test_percentile_matches_known_values():
    values = list(range(1, 101))          # 1..100
    assert percentile(values, 0) == 1
    assert percentile(values, 100) == 100
    assert percentile(values, 50) == pytest.approx(50.5)
    assert percentile(values, 95) == pytest.approx(95.05)


def test_percentile_interpolates():
    assert percentile([10, 20], 50) == pytest.approx(15.0)


def test_percentile_edge_cases():
    assert math.isnan(percentile([], 50))
    assert percentile([7.0], 99) == 7.0


def test_compute_stats_on_a_known_sample():
    values = [5.0, 6.0, 7.0, 8.0, 9.0]
    stats = compute_stats(values)
    assert stats["n"] == 5
    assert stats["mean"] == pytest.approx(7.0)
    assert stats["median"] == pytest.approx(7.0)
    assert stats["min"] == 5.0
    assert stats["max"] == 9.0
    assert stats["stdev"] == pytest.approx(1.5811, abs=1e-4)
    assert stats["iqr"] == pytest.approx(stats["q3"] - stats["q1"])
    assert stats["jitter"] == pytest.approx(stats["p95"] - stats["p5"])


def test_compute_stats_empty_is_all_nan_but_shaped():
    stats = compute_stats([])
    assert stats["n"] == 0
    assert all(math.isnan(v) for k, v in stats.items() if k != "n")


def test_single_sample_has_zero_stdev():
    assert compute_stats([4.2])["stdev"] == 0.0


def test_mad_ignores_a_wild_sample():
    tight = [5.0, 5.1, 4.9, 5.0, 5.2]
    with_spike = tight + [90.0]
    assert mad(with_spike) == pytest.approx(mad(tight), abs=0.15)
    # ...while the standard deviation explodes.
    assert compute_stats(with_spike)["stdev"] > 10 * compute_stats(tight)["stdev"]


def test_outliers_are_reported_not_removed():
    values = [5.0, 5.1, 5.2, 5.0, 4.9, 5.1, 40.0]
    indices = outlier_indices(values)
    assert indices == [6]
    # The statistics still see every raw sample.
    assert compute_stats(values)["n"] == len(values)
    assert compute_stats(values)["max"] == 40.0


def test_outliers_need_enough_samples_and_spread():
    assert outlier_indices([1.0, 2.0]) == []
    assert outlier_indices([5.0] * 10) == []


def test_delta_absolute_and_percent():
    absolute, percent = delta(11.0, 10.0)
    assert absolute == pytest.approx(1.0)
    assert percent == pytest.approx(10.0)


def test_delta_with_zero_baseline_has_no_percent():
    absolute, percent = delta(3.0, 0.0)
    assert absolute == 3.0
    assert math.isnan(percent)


def test_formatting():
    assert fmt_ms(6.42123) == "6.421"
    assert fmt_ms(None) == "—"
    assert fmt_ms(math.nan) == "—"
    assert fmt_delta(-0.5) == "-0.500"
    assert fmt_delta(0.5) == "+0.500"
