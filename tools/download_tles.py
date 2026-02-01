from skyfield.api import load
import os

# Define the path
data_dir = 'data'
tle_filename = 'starlink_tle.txt'
file_path = os.path.join(data_dir, tle_filename)

# Ensure data directory exists
os.makedirs(data_dir, exist_ok=True)

# URL for Starlink TLEs
stations_url = 'https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=tle'

print(f"Downloading TLEs from {stations_url}...")

# Skyfield can download directly to a file if we use the underlying loader,
# but a simple way to control the filename is to fetch and save.
# We'll use skyfield's loader to fetch it to a specific local file.
load.tle_file(stations_url, filename=file_path)

print(f"Saved TLE data to: {file_path}")