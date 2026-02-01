"""
Orbital Mechanics Module

TLE parsing and satellite propagation using Skyfield/SGP4.
"""

import json
import os
from skyfield.api import load, wgs84
from datetime import timedelta

class OrbitalAvailabilityKernel:
    def __init__(self, tle_path='data/starlink_tle.txt', stations_path='data/stations.json'):
        """
        Initialize the kernel by loading TLEs and Ground Stations.
        """
        self.ts = load.timescale()
        
        # 1. Load the Satellites (Physics)
        if not os.path.exists(tle_path):
            raise FileNotFoundError(f"TLE file not found at {tle_path}. Run tools/download_tles.py first.")
        
        print(f"Loading TLEs from {tle_path}...")
        self.satellites = load.tle_file(tle_path)
        # Convert list of satellites to a dict for easy lookup by name
        self.sat_dict = {sat.name: sat for sat in self.satellites}
        print(f"Loaded {len(self.satellites)} satellites.")

        # 2. Load the Ground Stations (Clients)
        if not os.path.exists(stations_path):
            raise FileNotFoundError(f"Stations file not found at {stations_path}.")
            
        with open(stations_path, 'r') as f:
            self.stations_data = json.load(f)
            
        # Convert to Skyfield 'wgs84' objects
        self.ground_stations = {}
        for s in self.stations_data:
            # Create a WGS84 position object
            self.ground_stations[s['id']] = wgs84.latlon(
                s['latitude'], 
                s['longitude'], 
                elevation_m=s['elevation_m']
            )
            
    def get_availability_window(self, satellite_name, station_id, start_time, duration_hours=1, min_elevation=10.0):
        """
        Calculates when a satellite is 'Available' (visible above min_elevation).
        Returns a list of (rise_time, set_time) tuples.
        """
        if satellite_name not in self.sat_dict:
            raise ValueError(f"Satellite {satellite_name} not found.")
        if station_id not in self.ground_stations:
            raise ValueError(f"Station {station_id} not found.")

        sat = self.sat_dict[satellite_name]
        station = self.ground_stations[station_id]

        # Define the time window for the search
        t0 = self.ts.from_datetime(start_time)
        t1 = self.ts.from_datetime(start_time + timedelta(hours=duration_hours))

        # 3. The Core Calculation: find_events
        # events: 0=Rise, 1=Culminate (Peak), 2=Set
        times, events = sat.find_events(station, t0, t1, altitude_degrees=min_elevation)

        windows = []
        current_rise = None

        for t, event in zip(times, events):
            # event 0 is Rise (AOS - Acquisition of Signal)
            if event == 0:
                current_rise = t
            # event 2 is Set (LOS - Loss of Signal)
            elif event == 2 and current_rise is not None:
                windows.append((current_rise.utc_datetime(), t.utc_datetime()))
                current_rise = None
            # If the window started before t0, we might see a SET without a RISE.
            # You can handle edge cases here depending on FL requirements.

        return windows