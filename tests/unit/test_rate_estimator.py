"""Unit tests for EMA RateEstimator (consensus Phase 1)."""

from __future__ import annotations

import pytest

from m3utolocal.downloader import RateEstimator


def test_rate_estimator_initial_sample_zero():
    est = RateEstimator(alpha=0.15)
    assert est.update(0, now=1.0) == 0.0


def test_rate_estimator_constant_throughput():
    est = RateEstimator(alpha=0.15)
    assert est.update(0, now=0.0) == 0.0
    rate = est.update(1_048_576, now=1.0)
    assert rate == pytest.approx(1_048_576.0, rel=1e-6)


def test_rate_estimator_dampens_sudden_spikes():
    est = RateEstimator(alpha=0.15)
    est.update(0, now=0.0)
    # Steady 1 MB/s for a few samples
    est.update(1_000_000, now=1.0)
    est.update(2_000_000, now=2.0)
    before = est.update(3_000_000, now=3.0)
    # Sudden 10 MB burst in 1s
    after = est.update(13_000_000, now=4.0)
    # Must not jump 10x immediately
    assert after < before * 3
    assert after > before  # moves toward the spike


def test_rate_estimator_ignores_micro_intervals():
    est = RateEstimator(alpha=0.15)
    est.update(0, now=0.0)
    rate = est.update(1_000_000, now=1.0)
    cached = est.update(1_050_000, now=1.05)  # dt < 0.1
    assert cached == rate


def test_eta_string_from_smoothed_rate():
    from m3utolocal.utils import format_time

    remaining = 5_000_000
    rate = 1_000_000.0
    assert f"ETA: {format_time(remaining / rate)}" == "ETA: 5s"
    stalled_rate = 0.0
    eta = "ETA: --" if stalled_rate <= 0 else f"ETA: {format_time(remaining / stalled_rate)}"
    assert eta == "ETA: --"
