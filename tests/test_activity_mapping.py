"""Tests for activity type mapping."""

import pytest

from src.config.activity_mapping import (
    get_garmin_activity_type,
    get_available_polar_types,
    get_available_garmin_types,
)


class TestActivityMapping:
    """Tests for activity type mapping functions."""
    
    def test_running_mapping(self) -> None:
        """Test running activity type mapping."""
        assert get_garmin_activity_type("RUNNING") == "running"
        assert get_garmin_activity_type("running") == "running"
        assert get_garmin_activity_type("TRAIL_RUNNING") == "trail_running"
    
    def test_cycling_mapping(self) -> None:
        """Test cycling activity type mapping."""
        assert get_garmin_activity_type("CYCLING") == "cycling"
        assert get_garmin_activity_type("INDOOR_CYCLING") == "indoor_cycling"
        assert get_garmin_activity_type("MOUNTAIN_BIKING") == "mountain_biking"
    
    def test_swimming_mapping(self) -> None:
        """Test swimming activity type mapping."""
        assert get_garmin_activity_type("SWIMMING") == "swimming"
        assert get_garmin_activity_type("POOL_SWIMMING") == "lap_swimming"
        assert get_garmin_activity_type("OPEN_WATER_SWIMMING") == "open_water_swimming"
    
    def test_strength_training_mapping(self) -> None:
        """Test strength training activity type mapping."""
        assert get_garmin_activity_type("STRENGTH_TRAINING") == "strength_training"
        assert get_garmin_activity_type("WEIGHT_TRAINING") == "strength_training"
    
    def test_default_fallback(self) -> None:
        """Test default fallback for unknown activity types."""
        assert get_garmin_activity_type("UNKNOWN_ACTIVITY") == "other"
        assert get_garmin_activity_type("UNKNOWN_ACTIVITY", "custom") == "custom"
    
    def test_case_insensitivity(self) -> None:
        """Test that mapping is case-insensitive."""
        assert get_garmin_activity_type("Running") == "running"
        assert get_garmin_activity_type("RUNNING") == "running"
        assert get_garmin_activity_type("running") == "running"
    
    def test_space_handling(self) -> None:
        """Test that spaces are converted to underscores."""
        assert get_garmin_activity_type("strength training") == "strength_training"
    
    def test_available_polar_types(self) -> None:
        """Test getting available Polar types."""
        types = get_available_polar_types()
        assert isinstance(types, list)
        assert "RUNNING" in types
        assert "CYCLING" in types
        assert types == sorted(types)  # Should be sorted
    
    def test_available_garmin_types(self) -> None:
        """Test getting available Garmin types."""
        types = get_available_garmin_types()
        assert isinstance(types, list)
        assert "running" in types
        assert "cycling" in types
        assert len(types) == len(set(types))  # Should be unique
