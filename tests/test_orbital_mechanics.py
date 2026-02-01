"""
Tests for Orbital Mechanics Module
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock


class TestOrbitalAvailabilityKernel:
    """Tests for the OrbitalAvailabilityKernel class."""

    @pytest.fixture
    def kernel(self):
        """
        Fixture to create an OrbitalAvailabilityKernel instance.
        Requires TLE and stations data files to exist.
        """
        from src.orbital_mechanics import OrbitalAvailabilityKernel
        return OrbitalAvailabilityKernel()

    @pytest.mark.integration
    def test_kernel_loads_satellites(self, kernel):
        """Test that the kernel loads satellites from TLE file."""
        assert len(kernel.satellites) > 0
        assert len(kernel.sat_dict) > 0

    @pytest.mark.integration
    def test_kernel_loads_ground_stations(self, kernel):
        """Test that the kernel loads ground stations."""
        assert len(kernel.ground_stations) > 0
        assert "gatech_atlanta" in kernel.ground_stations

    @pytest.mark.integration
    def test_get_availability_window_returns_list(self, kernel):
        """Test that get_availability_window returns a list of windows."""
        test_sat_name = list(kernel.sat_dict.keys())[0]
        test_station = "gatech_atlanta"
        now = datetime.now(timezone.utc)

        windows = kernel.get_availability_window(
            test_sat_name,
            test_station,
            now,
            duration_hours=24
        )

        assert isinstance(windows, list)
        for start, end in windows:
            assert isinstance(start, datetime)
            assert isinstance(end, datetime)
            assert end > start

    def test_get_availability_window_invalid_satellite(self, kernel):
        """Test that invalid satellite name raises ValueError."""
        now = datetime.now(timezone.utc)

        with pytest.raises(ValueError, match="Satellite .* not found"):
            kernel.get_availability_window(
                "NONEXISTENT_SAT",
                "gatech_atlanta",
                now
            )

    def test_get_availability_window_invalid_station(self, kernel):
        """Test that invalid station ID raises ValueError."""
        test_sat_name = list(kernel.sat_dict.keys())[0]
        now = datetime.now(timezone.utc)

        with pytest.raises(ValueError, match="Station .* not found"):
            kernel.get_availability_window(
                test_sat_name,
                "nonexistent_station",
                now
            )


class TestOrbitalAvailabilityKernelInit:
    """Tests for OrbitalAvailabilityKernel initialization error handling."""

    def test_missing_tle_file_raises_error(self, tmp_path):
        """Test that missing TLE file raises FileNotFoundError."""
        from src.orbital_mechanics import OrbitalAvailabilityKernel

        with pytest.raises(FileNotFoundError, match="TLE file not found"):
            OrbitalAvailabilityKernel(
                tle_path=str(tmp_path / "nonexistent.txt"),
                stations_path="data/stations.json"
            )

    def test_missing_stations_file_raises_error(self, tmp_path):
        """Test that missing stations file raises FileNotFoundError."""
        from src.orbital_mechanics import OrbitalAvailabilityKernel

        # Create a dummy TLE file
        tle_file = tmp_path / "test.txt"
        tle_file.write_text("")

        with pytest.raises(FileNotFoundError, match="Stations file not found"):
            OrbitalAvailabilityKernel(
                tle_path=str(tle_file),
                stations_path=str(tmp_path / "nonexistent.json")
            )
