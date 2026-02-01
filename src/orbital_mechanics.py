"""
Orbital Mechanics Module

TLE parsing and satellite propagation using Skyfield/SGP4.
"""

import json
import os
from skyfield.api import load, wgs84
from datetime import timedelta, datetime, timezone

class OrbitalAvailabilityKernel:
    def __init__(self, tle_path='data/starlink_tle.txt', stations_path='data/stations.json'):
        """
        Initialize the kernel by loading TLEs and Ground Stations.
        """
        self.ts = load.timescale()
        
        # 1. Load Satellites
        if not os.path.exists(tle_path):
            raise FileNotFoundError(f"TLE file not found at {tle_path}")
        self.satellites = load.tle_file(tle_path)
        self.sat_dict = {sat.name: sat for sat in self.satellites}

        # 2. Load Ground Stations
        if not os.path.exists(stations_path):
            raise FileNotFoundError(f"Stations file not found at {stations_path}")
            
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
            elif event == 2:
                if current_rise is not None:
                    windows.append((current_rise.utc_datetime(), t.utc_datetime()))
                    current_rise = None
                else:
                    # Edge case: satellite was already visible at start_time
                    # (rise happened before t0, we only see the SET)
                    windows.append((start_time, t.utc_datetime()))

        return windows

    def is_client_available(self, satellite_name, station_id, current_time, required_training_time_sec=300):
        """
        Determines if a client (satellite) has enough remaining visibility 
        to complete a full training round. The Preemptive Filter: Returns True ONLY if the satellite is visible 
        AND has enough remaining time to complete the round.
        
        Args:
            current_time: The start time of the FL round.
            required_training_time_sec: How long the round takes (e.g., 5 mins).
            
        Returns:
            bool: True if safe to select, False otherwise.
        """
        # 1. Get all upcoming windows
        # We look ahead a bit to find the relevant pass
        windows = self.get_availability_window(
            satellite_name, station_id, current_time, duration_hours=2
        )
        
        needed_delta = timedelta(seconds=required_training_time_sec)
        
        for rise, set_time in windows:
            # Case A: The round starts BEFORE the window (Satellite hasn't risen yet)
            # We strictly need the satellite to be visible NOW for standard FL.
            # (Though advanced logic could 'schedule' it for the future).
            
            # Case B: The round starts DURING the window
            if rise <= current_time < set_time:
                remaining_time = set_time - current_time
                if remaining_time >= needed_delta:
                    return True  # Safe to select
                else:
                    return False # "Straggler" risk - connection will drop mid-training

        return False # Not visible at all


# --- Research Demo Script ---
if __name__ == "__main__":
    kernel = OrbitalAvailabilityKernel()

    sat_name = list(kernel.sat_dict.keys())[0]
    station = "gatech_atlanta"
    now = datetime.now(timezone.utc)

    print(f"Satellite: {sat_name}")
    print(f"Station: {station}")
    print(f"Current time: {now}")

    # Find actual visibility windows in the next 24 hours
    windows = kernel.get_availability_window(sat_name, station, now, duration_hours=24)

    if not windows:
        print("\nNo visibility windows found in next 24 hours.")
    else:
        print(f"\nFound {len(windows)} visibility windows:")
        for i, (rise, set_time) in enumerate(windows):
            duration = (set_time - rise).total_seconds() / 60
            print(f"  Pass {i+1}: {rise.strftime('%H:%M:%S')} - {set_time.strftime('%H:%M:%S')} ({duration:.1f} mins)")

        # --- TEST 1: "Safe" Window - Query at start of a long pass ---
        # Find a window with >= 6 minutes duration
        safe_window = next((w for w in windows if (w[1] - w[0]).total_seconds() >= 360), None)

        if safe_window:
            rise, set_time = safe_window
            # Query 1 minute after rise (plenty of time remaining)
            safe_time = rise + timedelta(minutes=1)
            remaining = (set_time - safe_time).total_seconds() / 60

            print(f"\n--- TEST 1: Safe Window ---")
            print(f"Query time: {safe_time.strftime('%H:%M:%S')} ({remaining:.1f} mins remaining)")
            result = kernel.is_client_available(sat_name, station, safe_time, required_training_time_sec=300)
            print(f"Result: {'ACCEPTED' if result else 'REJECTED'}")
        else:
            print("\n--- TEST 1: No window >= 6 mins found ---")

        # --- TEST 2: "Dangerous" Window - Query near end of pass ---
        # Use any window and query when only ~2 mins remain
        test_window = windows[0]
        rise, set_time = test_window
        # Query 2 minutes before set (not enough time for 5-min training)
        danger_time = set_time - timedelta(minutes=2)

        if danger_time > rise:  # Make sure we're still in the window
            remaining = (set_time - danger_time).total_seconds() / 60

            print(f"\n--- TEST 2: Dangerous Window ---")
            print(f"Query time: {danger_time.strftime('%H:%M:%S')} ({remaining:.1f} mins remaining)")
            result = kernel.is_client_available(sat_name, station, danger_time, required_training_time_sec=300)
            print(f"Result: {'ACCEPTED' if result else 'REJECTED'}")