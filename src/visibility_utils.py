"""
Visibility Utilities Module

Visibility cone calculations and contact window analysis.
"""

from typing import List, Tuple, Optional
from dataclasses import dataclass
import numpy as np

from skyfield.api import load, wgs84, EarthSatellite
from skyfield.toposlib import GeographicPosition


@dataclass
class VisibilityWindow:
    """Represents a satellite visibility window."""
    satellite_name: str
    start_time: float  # Julian date
    end_time: float    # Julian date
    max_elevation: float  # degrees
    aos_azimuth: float  # Acquisition of signal azimuth
    los_azimuth: float  # Loss of signal azimuth


def elevation_angle(
    satellite: EarthSatellite,
    ground_station: GeographicPosition,
    time,
) -> float:
    """
    Calculate elevation angle of satellite from ground station.

    Args:
        satellite: EarthSatellite object
        ground_station: Ground station position
        time: Skyfield Time object

    Returns:
        Elevation angle in degrees
    """
    difference = satellite - ground_station
    topocentric = difference.at(time)
    alt, az, distance = topocentric.altaz()
    return alt.degrees


def compute_visibility_windows(
    satellite: EarthSatellite,
    ground_station: GeographicPosition,
    start_time,
    end_time,
    min_elevation: float = 10.0,
    step_minutes: float = 1.0,
) -> List[VisibilityWindow]:
    """
    Compute visibility windows for a satellite over a time period.

    Args:
        satellite: EarthSatellite object
        ground_station: Ground station position
        start_time: Start time (Skyfield Time)
        end_time: End time (Skyfield Time)
        min_elevation: Minimum elevation angle in degrees
        step_minutes: Time step for search in minutes

    Returns:
        List of VisibilityWindow objects
    """
    ts = load.timescale()
    windows = []

    # Generate time array
    duration_days = end_time.tt - start_time.tt
    num_steps = int(duration_days * 24 * 60 / step_minutes)
    times = ts.tt_jd(np.linspace(start_time.tt, end_time.tt, num_steps))

    # Calculate elevation angles
    difference = satellite - ground_station
    topocentric = difference.at(times)
    alt, az, _ = topocentric.altaz()
    elevations = alt.degrees
    azimuths = az.degrees

    # Find visibility windows
    visible = elevations > min_elevation

    # Detect transitions
    in_window = False
    window_start = None
    max_el = 0
    aos_az = 0

    for i, (v, el, azm, t) in enumerate(zip(visible, elevations, azimuths, times)):
        if v and not in_window:
            # Start of window
            in_window = True
            window_start = t.tt
            max_el = el
            aos_az = azm
        elif v and in_window:
            # Continue window
            if el > max_el:
                max_el = el
        elif not v and in_window:
            # End of window
            in_window = False
            windows.append(VisibilityWindow(
                satellite_name=satellite.name,
                start_time=window_start,
                end_time=t.tt,
                max_elevation=max_el,
                aos_azimuth=aos_az,
                los_azimuth=azm,
            ))

    return windows


def compute_inter_satellite_visibility(
    sat1: EarthSatellite,
    sat2: EarthSatellite,
    time,
    max_range_km: float = 5000.0,
) -> Tuple[bool, float]:
    """
    Check if two satellites can communicate (line of sight, within range).

    Args:
        sat1: First satellite
        sat2: Second satellite
        time: Skyfield Time object
        max_range_km: Maximum communication range in km

    Returns:
        Tuple of (can_communicate, distance_km)
    """
    pos1 = sat1.at(time).position.km
    pos2 = sat2.at(time).position.km

    distance = np.linalg.norm(pos2 - pos1)

    # Simple range check (could add Earth obstruction check)
    can_communicate = distance <= max_range_km

    return can_communicate, distance
