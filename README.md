# LEO Federated Learning Research

## Project Overview

This project explores federated learning strategies for Low Earth Orbit (LEO) satellite constellations, focusing on orbital mechanics-aware scheduling and communication optimization.

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

## Project Structure

```
leo-fl-research/
├── data/                   # TLE and ground station data
├── notebooks/              # Jupyter notebooks for experimentation
├── src/                    # Core orbital availability kernel
└── flame_integration/      # FL framework integration
```

## Getting Started

```bash
pip3 install -r requirements.txt
```
