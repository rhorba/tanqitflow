"""Unit tests for Isolation Forest domain module."""
import pickle

import pytest

from domain.isolation_forest import (
    IFFeatureVector,
    IFResult,
    build_feature_vector,
    score_isolation_forest,
    train_isolation_forest,
)


def _sample_feature() -> IFFeatureVector:
    return IFFeatureVector(
        hourly_mean_flow=10.0,
        hourly_std_flow=1.5,
        mnf_m3h=3.0,
        daily_range_flow=8.0,
        night_day_ratio=0.3,
        mean_pressure=4.5,
        std_pressure=0.2,
    )


def _normal_rows(n: int = 20) -> list[IFFeatureVector]:
    return [
        IFFeatureVector(
            hourly_mean_flow=10.0 + (i % 3) * 0.1,
            hourly_std_flow=1.5,
            mnf_m3h=3.0,
            daily_range_flow=8.0,
            night_day_ratio=0.3,
            mean_pressure=4.5,
            std_pressure=0.2,
        )
        for i in range(n)
    ]


class TestTrainIsolationForest:

    def test_trains_and_returns_bytes(self):
        rows = _normal_rows(20)
        result = train_isolation_forest(rows)
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_pickle_contains_sklearn_model(self):
        rows = _normal_rows(20)
        model_bytes = train_isolation_forest(rows)
        model = pickle.loads(model_bytes)  # noqa: S301
        assert hasattr(model, "decision_function")
        assert hasattr(model, "predict")


class TestScoreIsolationForest:

    def _trained_model(self) -> bytes:
        return train_isolation_forest(_normal_rows(30))

    def test_normal_data_low_score(self):
        model_bytes = self._trained_model()
        fv = _sample_feature()  # same distribution as training
        result = score_isolation_forest(model_bytes, fv)
        assert isinstance(result, IFResult)
        assert result.score is not None
        assert 0.0 <= result.score <= 1.0

    def test_anomalous_data_higher_score(self):
        model_bytes = self._trained_model()
        # Extreme values — very different from training data
        anomaly_fv = IFFeatureVector(
            hourly_mean_flow=10000.0,
            hourly_std_flow=500.0,
            mnf_m3h=9000.0,
            daily_range_flow=8000.0,
            night_day_ratio=5.0,
            mean_pressure=100.0,
            std_pressure=50.0,
        )
        result = score_isolation_forest(model_bytes, anomaly_fv)
        assert result.score is not None
        # Anomalous data should have a higher score than a normal point
        normal_result = score_isolation_forest(model_bytes, _sample_feature())
        assert result.score >= normal_result.score

    def test_score_clamped_0_1(self):
        model_bytes = self._trained_model()
        result = score_isolation_forest(model_bytes, _sample_feature())
        assert 0.0 <= result.score <= 1.0

    def test_custom_flag_threshold(self):
        model_bytes = self._trained_model()
        fv = _sample_feature()
        result_low_threshold = score_isolation_forest(model_bytes, fv, flag_threshold=0.0)
        result_high_threshold = score_isolation_forest(model_bytes, fv, flag_threshold=1.0)
        # Low threshold → everything is flagged; high threshold → nothing is
        assert result_low_threshold.if_flag is True
        assert result_high_threshold.if_flag is False


class TestBuildFeatureVector:

    def test_returns_feature_vector(self):
        fv = build_feature_vector(
            flow_readings=[5.0, 6.0, 7.0, 5.5, 4.5],
            night_flows=[3.0, 2.5, 3.2],
            day_flows=[8.0, 9.0, 7.5],
            pressure_readings=[4.0, 4.2, 4.1],
        )
        assert fv is not None
        assert isinstance(fv, IFFeatureVector)
        assert fv.hourly_mean_flow == pytest.approx(5.6)

    def test_returns_none_on_empty_flows(self):
        fv = build_feature_vector(
            flow_readings=[],
            night_flows=[],
            day_flows=[],
            pressure_readings=[],
        )
        assert fv is None

    def test_handles_missing_pressure(self):
        fv = build_feature_vector(
            flow_readings=[5.0, 6.0, 7.0],
            night_flows=[3.0],
            day_flows=[8.0],
            pressure_readings=[],  # no pressure data
        )
        assert fv is not None
        assert fv.mean_pressure == 0.0
        assert fv.std_pressure == 0.0

    def test_to_list_length(self):
        fv = _sample_feature()
        vec = fv.to_list()
        assert len(vec) == 7  # 7 features
        assert all(isinstance(v, float) for v in vec)
