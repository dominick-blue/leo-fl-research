"""
Orbital Mechanics Module

TLE parsing and satellite propagation using Skyfield/SGP4.
"""

from typing import List, Optional
from pathlib import Path

from skyfield.api import load, EarthSatellite, Timescale
from skyfield.iokit import parse_tle_file
import requests


def load_tle_file(filepath: str) -> List[EarthSatellite]:
    """
    Load satellites from a TLE file.

    Args:
        filepath: Path to TLE file

    Returns:
        List of EarthSatellite objects
    """
    ts = load.timescale()
    satellites = []

    with open(filepath, 'r') as f:
        lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    # Parse TLE triplets (name, line1, line2)
    i = 0
    while i < len(lines) - 2:
        name = lines[i]
        line1 = lines[i + 1]
        line2 = lines[i + 2]

        if line1.startswith('1 ') and line2.startswith('2 '):
            sat = EarthSatellite(line1, line2, name, ts)
            satellites.append(sat)
            i += 3
        else:
            i += 1

    return satellites


def fetch_tle_from_celestrak(group: str = "starlink") -> List[EarthSatellite]:
    """
    Fetch current TLE data from CelesTrak.

    Args:
        group: Satellite group name (e.g., 'starlink', 'oneweb', 'iridium')

    Returns:
        List of EarthSatellite objects
    """
    url = f"https://celestrak.org/NORAD/elements/gp.php?GROUP={group}&FORMAT=tle"
    response = requests.get(url)
    response.raise_for_status()

    ts = load.timescale()
    satellites = []
    lines = response.text.strip().split('\n')

    i = 0
    while i < len(lines) - 2:
        name = lines[i].strip()
        line1 = lines[i + 1].strip()
        line2 = lines[i + 2].strip()

        if line1.startswith('1 ') and line2.startswith('2 '):
            sat = EarthSatellite(line1, line2, name, ts)
            satellites.append(sat)
            i += 3
        else:
            i += 1

    return satellites


def propagate_satellite(
    satellite: EarthSatellite,
    times: list,
) -> tuple:
    """
    Propagate satellite position over time.

    Args:
        satellite: EarthSatellite object
        times: List of Skyfield Time objects

    Returns:
        Tuple of (positions, velocities) in GCRS frame
    """
    geocentric = satellite.at(times)
    return geocentric.position.km, geocentric.velocity.km_per_s


def get_orbital_period(satellite: EarthSatellite) -> float:
    """
    Get orbital period in minutes.

    Args:
        satellite: EarthSatellite object

    Returns:
        Orbital period in minutes
    """
    # Mean motion is in revolutions per day
    mean_motion = satellite.model.no_kozai * (1440.0 / (2 * 3.14159265))  # Convert to rev/day
    return 1440.0 / (satellite.model.no_kozai * 1440.0 / (2 * 3.14159265 * 1440.0 / 86400.0))
