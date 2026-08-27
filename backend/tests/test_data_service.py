import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

import data_service


def setup_function(_):
    data_service.reload_data()


def test_get_all_zips_returns_list_of_dicts():
    zips = data_service.get_all_zips()
    assert isinstance(zips, list)
    assert len(zips) > 0
    for z in zips:
        assert set(z.keys()) == {"zip_code", "borough", "areas"}


def test_get_zip_metadata_valid():
    meta = data_service.get_zip_metadata("10310")
    assert meta["zip_code"] == "10310"
    assert meta["borough"] == "Staten Island"


def test_get_zip_metadata_unknown_raises():
    with pytest.raises(data_service.ZipNotFoundError):
        data_service.get_zip_metadata("99999")


def test_get_latest_features_has_required_columns():
    features = data_service.get_latest_features("10310")
    for col in data_service.REQUIRED_FEATURE_COLUMNS:
        assert col in features


def test_get_latest_features_unknown_zip_raises():
    with pytest.raises(data_service.ZipNotFoundError):
        data_service.get_latest_features("00000")


def test_zip_code_stays_string_not_float():
    features = data_service.get_latest_features("10310")
    assert isinstance(features["zip_code"], str)
    assert features["zip_code"] == "10310"
    assert "." not in features["zip_code"]


def test_zip_normalization_pads_leading_zero():
    # A ZIP passed without a leading zero should still resolve correctly.
    meta = data_service.get_zip_metadata("10310")
    meta_unpadded = data_service.get_zip_metadata("10310")
    assert meta == meta_unpadded


def test_get_history_sorted_chronologically():
    history = data_service.get_history("10310")
    weeks = [h["week"] for h in history]
    assert weeks == sorted(weeks)
    for row in history:
        assert set(row.keys()) == {"year", "week", "positive_detections"}


def test_get_history_unknown_zip_raises():
    with pytest.raises(data_service.ZipNotFoundError):
        data_service.get_history("00000")
