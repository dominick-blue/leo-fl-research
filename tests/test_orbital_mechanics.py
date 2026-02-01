"""
Tests for Orbital Mechanics Module
"""

import pytest
from datetime import datetime, timezone, timedelta
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


class TestIsClientAvailable:
    """Tests for the is_client_available method."""

    @pytest.fixture
    def kernel(self):
        """Fixture to create an OrbitalAvailabilityKernel instance."""
        from src.orbital_mechanics import OrbitalAvailabilityKernel
        return OrbitalAvailabilityKernel()

    def test_returns_true_when_enough_time_remaining(self, kernel):
        """Test that client is available when visibility window has sufficient time."""
        now = datetime.now(timezone.utc)
        # Create a window that started 1 min ago and ends in 10 mins
        mock_windows = [
            (now - timedelta(minutes=1), now + timedelta(minutes=10))
        ]

        with patch.object(kernel, 'get_availability_window', return_value=mock_windows):
            result = kernel.is_client_available(
                "TEST_SAT",
                "test_station",
                now,
                required_training_time_sec=300  # 5 minutes needed
            )
            assert result is True

    def test_returns_false_when_not_enough_time_remaining(self, kernel):
        """Test straggler risk: client not available when insufficient time remains."""
        now = datetime.now(timezone.utc)
        # Create a window that ends in only 2 minutes (less than 5 min required)
        mock_windows = [
            (now - timedelta(minutes=5), now + timedelta(minutes=2))
        ]

        with patch.object(kernel, 'get_availability_window', return_value=mock_windows):
            result = kernel.is_client_available(
                "TEST_SAT",
                "test_station",
                now,
                required_training_time_sec=300  # 5 minutes needed
            )
            assert result is False

    def test_returns_false_when_not_visible(self, kernel):
        """Test that client is not available when satellite is not visible."""
        now = datetime.now(timezone.utc)
        # No visibility windows
        mock_windows = []

        with patch.object(kernel, 'get_availability_window', return_value=mock_windows):
            result = kernel.is_client_available(
                "TEST_SAT",
                "test_station",
                now,
                required_training_time_sec=300
            )
            assert result is False

    def test_returns_false_when_window_is_in_future(self, kernel):
        """Test that client is not available when window hasn't started yet."""
        now = datetime.now(timezone.utc)
        # Window starts in 10 minutes (satellite hasn't risen yet)
        mock_windows = [
            (now + timedelta(minutes=10), now + timedelta(minutes=20))
        ]

        with patch.object(kernel, 'get_availability_window', return_value=mock_windows):
            result = kernel.is_client_available(
                "TEST_SAT",
                "test_station",
                now,
                required_training_time_sec=300
            )
            assert result is False

    def test_returns_false_when_window_has_passed(self, kernel):
        """Test that client is not available when window has already ended."""
        now = datetime.now(timezone.utc)
        # Window ended 5 minutes ago
        mock_windows = [
            (now - timedelta(minutes=15), now - timedelta(minutes=5))
        ]

        with patch.object(kernel, 'get_availability_window', return_value=mock_windows):
            result = kernel.is_client_available(
                "TEST_SAT",
                "test_station",
                now,
                required_training_time_sec=300
            )
            assert result is False

    def test_returns_true_with_exact_time_remaining(self, kernel):
        """Test boundary: client available when exactly enough time remains."""
        now = datetime.now(timezone.utc)
        # Exactly 5 minutes remaining
        mock_windows = [
            (now - timedelta(minutes=1), now + timedelta(seconds=300))
        ]

        with patch.object(kernel, 'get_availability_window', return_value=mock_windows):
            result = kernel.is_client_available(
                "TEST_SAT",
                "test_station",
                now,
                required_training_time_sec=300
            )
            assert result is True

    def test_checks_multiple_windows(self, kernel):
        """Test that method checks all windows and finds valid one."""
        now = datetime.now(timezone.utc)
        # First window has passed, second is current with enough time
        mock_windows = [
            (now - timedelta(minutes=30), now - timedelta(minutes=20)),
            (now - timedelta(minutes=2), now + timedelta(minutes=10))
        ]

        with patch.object(kernel, 'get_availability_window', return_value=mock_windows):
            result = kernel.is_client_available(
                "TEST_SAT",
                "test_station",
                now,
                required_training_time_sec=300
            )
            assert result is True

    def test_invalid_satellite_raises_error(self, kernel):
        """Test that invalid satellite name raises ValueError."""
        now = datetime.now(timezone.utc)

        with pytest.raises(ValueError, match="Satellite .* not found"):
            kernel.is_client_available(
                "NONEXISTENT_SAT",
                "gatech_atlanta",
                now
            )

    def test_invalid_station_raises_error(self, kernel):
        """Test that invalid station ID raises ValueError."""
        test_sat_name = list(kernel.sat_dict.keys())[0]
        now = datetime.now(timezone.utc)

        with pytest.raises(ValueError, match="Station .* not found"):
            kernel.is_client_available(
                test_sat_name,
                "nonexistent_station",
                now
            )

    @pytest.mark.integration
    def test_integration_with_real_data(self, kernel):
        """Integration test with real satellite and station data."""
        test_sat_name = list(kernel.sat_dict.keys())[0]
        test_station = "gatech_atlanta"
        now = datetime.now(timezone.utc)

        # Should return a boolean without error
        result = kernel.is_client_available(
            test_sat_name,
            test_station,
            now,
            required_training_time_sec=300
        )
        assert isinstance(result, bool)


class TestGetAvailabilityWindowEdgeCases:
    """Tests for edge cases in get_availability_window."""

    @pytest.fixture
    def kernel(self):
        """Fixture to create an OrbitalAvailabilityKernel instance."""
        from src.orbital_mechanics import OrbitalAvailabilityKernel
        return OrbitalAvailabilityKernel()

    @pytest.mark.integration
    def test_satellite_already_visible_at_query_time(self, kernel):
        """
        Test edge case: querying when satellite is already visible.

        When a satellite rose BEFORE our query time, we should still
        detect the current pass (from query_time to set_time).
        """
        test_sat_name = list(kernel.sat_dict.keys())[0]
        test_station = "gatech_atlanta"
        now = datetime.now(timezone.utc)

        # First, find windows starting from now
        windows = kernel.get_availability_window(
            test_sat_name, test_station, now, duration_hours=24
        )

        if windows:
            # Get the first window
            rise, set_time = windows[0]
            window_duration = (set_time - rise).total_seconds()

            # Query 1 minute after rise (satellite already visible)
            mid_pass_time = rise + timedelta(minutes=1)

            # Get windows starting from mid-pass
            mid_pass_windows = kernel.get_availability_window(
                test_sat_name, test_station, mid_pass_time, duration_hours=2
            )

            # Should detect we're in an active pass
            assert len(mid_pass_windows) >= 1

            # First window should start at or near mid_pass_time
            detected_rise, detected_set = mid_pass_windows[0]
            assert detected_rise <= mid_pass_time
            # Set times should be within 1 second (floating-point precision)
            set_time_diff = abs((detected_set - set_time).total_seconds())
            assert set_time_diff < 1.0

    @pytest.mark.integration
    def test_is_client_available_during_active_pass(self, kernel):
        """
        Integration test: is_client_available returns True during active pass
        with sufficient remaining time.
        """
        test_sat_name = list(kernel.sat_dict.keys())[0]
        test_station = "gatech_atlanta"
        now = datetime.now(timezone.utc)

        # Find a window with at least 6 minutes duration
        windows = kernel.get_availability_window(
            test_sat_name, test_station, now, duration_hours=24
        )

        long_window = next(
            (w for w in windows if (w[1] - w[0]).total_seconds() >= 360),
            None
        )

        if long_window:
            rise, set_time = long_window
            # Query 1 minute after rise
            query_time = rise + timedelta(minutes=1)

            result = kernel.is_client_available(
                test_sat_name,
                test_station,
                query_time,
                required_training_time_sec=300
            )
            assert result is True
