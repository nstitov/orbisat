"""Script to run Orbitron TCP client.

This script must be run *FROM OUTSIDE* the new_orbitron pack!
This script should be run to add initial data to orbitron TCP server for SamSat-ION.

To run with nonlocal Orbitron TCP Server you should use your own HOST IP.
"""

from new_orbitron.tcp.orbitron_tcp_client import HOST, PORT, OrbitronTcpClient

HOST = "localhost"

station = {
    "longitude": 50.17763,
    "latitude": 53.21204,
    "altitude": 137,
    "elevation": 0,
    "station_name": "Samara",
}

satellite = {"norad_id": 57173, "uplink": 437398600, "downlink": 437398600}

with OrbitronTcpClient(HOST=HOST, PORT=PORT) as client:
    client.setup_ground_station(
        longitude=station["longitude"],
        latitude=station["latitude"],
        altitude=station["altitude"],
        elevation=station["elevation"],
        station_name=station["station_name"],
    )

    client.setup_satellite(
        station_name=station["station_name"],
        norad_id=satellite["norad_id"],
        uplink=satellite["uplink"],
        downlink=satellite["downlink"],
    )

    client.setup_comm(
        station_name=station["station_name"],
        norad_id=satellite["norad_id"],
    )

    client.setup_new_tle_by_spacetrack(
        station_name=station["station_name"],
        norad_id=satellite["norad_id"],
    )

    client.predict_comm(
        station_name=station["station_name"],
        norad_id=satellite["norad_id"],
    )

    print("SamSat-ION data is ready to be used at Orbitron TCP Server!")
