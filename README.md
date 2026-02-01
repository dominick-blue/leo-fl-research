# LEO Federated Learning Research

## Project Overview

This project explores federated learning strategies for Low Earth Orbit (LEO) satellite constellations, focusing on orbital mechanics-aware scheduling and communication optimization.

The core component is the **Orbital Availability Kernel**, which provides:
- Satellite visibility window calculations using SGP4 propagation
- Preemptive straggler filtering to avoid mid-training connection drops
- Ground station management for federated learning coordination

## Requirements

- Python 3.6+
- pip3

## Getting Started

### 1. Clone the Repository

```bash
git clone <repository-url>
cd leo-fl-research
```

### 2. Install Dependencies

```bash
pip3 install -r requirements.txt
```

### 3. Download TLE Data

Before running the kernel, download current TLE data:

```bash
python3 tools/download_tles.py
```

This fetches Starlink constellation data from CelesTrak and saves it to `data/starlink_tle.txt`.

### 4. Verify Installation

Run the research demo to verify everything works:

```bash
python3 src/orbital_mechanics.py
```

Expected output:
```
Satellite: STARLINK-1007
Station: gatech_atlanta
...
--- TEST 1: Safe Window ---
Result: ACCEPTED

--- TEST 2: Dangerous Window ---
Result: REJECTED
```

## Running Tests

```bash
python3 -m pytest tests/
```

For verbose output:

```bash
python3 -m pytest tests/ -v
```

## Project Structure

```
leo-fl-research/
├── data/                   # TLE and ground station data
│   ├── starlink_tle.txt    # Satellite TLE data
│   └── stations.json       # Ground station coordinates
├── notebooks/              # Jupyter notebooks for experimentation
├── src/                    # Core orbital availability kernel
│   ├── orbital_mechanics.py    # OrbitalAvailabilityKernel class
│   ├── constellation.py        # Constellation management
│   └── visibility_utils.py     # Visibility calculations
├── tests/                  # Test suite
│   └── test_orbital_mechanics.py
├── tools/                  # Utility scripts
│   └── download_tles.py    # TLE data downloader
└── flame_integration/      # FL framework integration
```

## Core API

### OrbitalAvailabilityKernel

```python
from src.orbital_mechanics import OrbitalAvailabilityKernel

kernel = OrbitalAvailabilityKernel()

# Get visibility windows for a satellite
windows = kernel.get_availability_window(
    satellite_name="STARLINK-1007",
    station_id="gatech_atlanta",
    start_time=datetime.now(timezone.utc),
    duration_hours=24
)

# Check if client has enough time for training (straggler filter)
is_available = kernel.is_client_available(
    satellite_name="STARLINK-1007",
    station_id="gatech_atlanta",
    current_time=datetime.now(timezone.utc),
    required_training_time_sec=300  # 5 minutes
)
```

## TLE Source Documentation

Two-Line Element (TLE) data is sourced from:
- **CelesTrak**: https://celestrak.org/NORAD/elements/
- **Space-Track**: https://www.space-track.org/ (requires registration)

### TLE Format Reference
```
STARLINK-1234
1 44235U 19029A   24001.50000000  .00000000  00000-0  00000-0 0  9999
2 44235  53.0000 100.0000 0001000 100.0000 260.0000 15.00000000    00
```
