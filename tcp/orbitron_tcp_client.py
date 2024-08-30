import json
import logging
import time
from datetime import datetime
from typing import Literal, Optional, Union

from .TcpServerABC import ResponseType, TCPClient

logger = logging.getLogger(__name__)

HOST = "localhost"
PORT = 5555

NoradID = int
StationName = str


class OrbitronTcpClient(TCPClient):
    """A class used to represent Orbitron TCP Client to communicate with Orbitron TCP
    Server. OrbitronTcpClient consists total represenation of the Orbitron functions and
    some additional functions.

    Attributes:
        sock (socket): socket to connect to TCP server. Socket is set by HOST and PORT.

    OrbitonTcpClient should be used with context manager!
    """

    def setup_ground_station(
        self,
        longitude: Union[int, float],
        latitude: Union[int, float],
        altitude: Union[int, float],
        elevation: Optional[Union[int, float]] = 0,
        station_name: Optional[str] = "default",
    ) -> None:
        """Send command to Orbitron TCP server to setup ground station."""

        js = {
            "request": "setup_ground_station",
            "body": {
                "longitude": longitude,
                "latitude": latitude,
                "altitude": altitude,
                "elevation": elevation,
                "station_name": station_name,
            },
        }

        self.sock.sendall(json.dumps(js).encode("utf-8"))
        resp = self.sock.recv(self._RESP_SIZE).decode("utf-8")
        self._check_resp(resp, ResponseType.CONFIGURE, "setup_ground_station")

    def setup_satellite(
        self,
        station_name: str,
        norad_id: int,
        uplink: Union[int, float] = None,
        downlink: Union[int, float] = None,
    ) -> None:
        """Send command to Orbitron TCP server to setup satellite."""

        js = {
            "request": "setup_satellite",
            "body": {
                "station_name": station_name,
                "norad_id": norad_id,
                "uplink": uplink,
                "downlink": downlink,
            },
        }
        self.sock.sendall(json.dumps(js).encode("utf-8"))
        resp = self.sock.recv(self._RESP_SIZE).decode("utf-8")
        self._check_resp(resp, ResponseType.CONFIGURE, "setup_satellite")

    def setup_comm(self, station_name: str, norad_id: int) -> None:
        """Send command to Orbitron TCP server to setup communication with required
        satellite for required ground station.
        """

        js = {
            "request": "setup_comm",
            "body": {
                "station_name": station_name,
                "norad_id": norad_id,
            },
        }
        self.sock.sendall(json.dumps(js).encode("utf-8"))
        resp = self.sock.recv(self._RESP_SIZE).decode("utf-8")
        self._check_resp(resp, ResponseType.CONFIGURE, "setup_comm")

    def setup_new_frequencies(
        self,
        station_name: str,
        norad_id: int,
        uplink: Union[int, float],
        downlink: Union[int, float],
    ) -> None:
        """Send command to Orbitron TCP server to setup new uplink and downlink
        frequencies for satellite for required ground station.
        """

        js = {
            "request": "setup_new_frequencies",
            "body": {
                "station_name": station_name,
                "norad_id": norad_id,
                "uplink": uplink,
                "downlink": downlink,
            },
        }
        self.sock.sendall(json.dumps(js).encode("utf-8"))
        resp = self.sock.recv(self._RESP_SIZE).decode("utf-8")
        self._check_resp(resp, ResponseType.CONFIGURE, "setup_new_frequencies")

    def setup_new_tle_by_str(
        self, station_name: str, norad_id: int, tle_str: str
    ) -> None:
        """Send command to Orbitron TCP server to setup new TLE data by string
        format for required satellite at required ground station.
        """
        js = {
            "request": "setup_new_tle_by_str",
            "body": {
                "station_name": station_name,
                "norad_id": norad_id,
                "tle_str": tle_str,
            },
        }
        self.sock.sendall(json.dumps(js).encode("utf-8"))
        resp = self.sock.recv(self._RESP_SIZE).decode("utf-8")
        self._check_resp(resp, ResponseType.TLE_UPDATE, "setup_new_tle_by_str")

    def setup_new_tle_by_file(
        self,
        station_name: str,
        norad_id: int,
        tle_file_name: str,
        default_folder: bool = True,
    ) -> None:
        """Send command to Orbitron TCP server to setup new TLE data by TLE file for
        required satellite at required ground station.
        """
        js = {
            "request": "setup_new_tle_by_file",
            "body": {
                "station_name": station_name,
                "norad_id": norad_id,
                "tle_file_name": tle_file_name,
                "default_folder": default_folder,
            },
        }

        self.sock.sendall(json.dumps(js).encode("utf-8"))
        resp = self.sock.recv(self._RESP_SIZE).decode("utf-8")
        self._check_resp(resp, ResponseType.TLE_UPDATE, "setup_new_tle_by_file")

    def setup_new_tle_by_spacetrack(self, station_name: str, norad_id: int) -> None:
        """Send command to Orbitron TCP server to setup new TLE data by SpaceTrackAPI
        by satellite NORAD ID for required satellite at required ground station.
        """

        js = {
            "request": "setup_new_tle_by_spacetrack",
            "body": {
                "station_name": station_name,
                "norad_id": norad_id,
            },
        }

        self.sock.sendall(json.dumps(js).encode("utf-8"))
        resp = self.sock.recv(self._RESP_SIZE).decode("utf-8")
        self._check_resp(resp, ResponseType.TLE_UPDATE, "setup_new_tle_by_spacetrack")

    def update_tles_by_spacetrack(
        self, station_name: str, norad_ids: list[int]
    ) -> None:
        """Send command to Orbitron TCP server to updates TLE files for required setuped
        satellites for required ground station by SpaceTrack API.
        """

        js = {
            "request": "update_tles_by_spacetrack",
            "body": {
                "station_name": station_name,
                "norad_ids": norad_ids,
            },
        }

        self.sock.sendall(json.dumps(js).encode("utf-8"))
        resp = self.sock.recv(self._RESP_SIZE).decode("utf-8")
        self._check_resp(resp, ResponseType.TLE_UPDATE, "update_tles_by_spacetrack")

    def predict_comm(
        self,
        station_name: str,
        norad_id: int,
        start_prediction: Optional[datetime] = None,
        time_prediction: int = 86400,
        step_prediction: Union[int, float] = 1,
    ) -> None:
        """Send command to Orbitron TCP server to predict communication with required
        satellite for required ground station for required start time and duration with
        required time step.
        """
        if start_prediction:
            start_prediction = start_prediction.isoformat()

        js = {
            "request": "predict_comm",
            "body": {
                "station_name": station_name,
                "norad_id": norad_id,
                "start_prediction": start_prediction,
                "time_prediction": time_prediction,
                "step_prediction": step_prediction,
            },
        }

        self.sock.sendall(json.dumps(js).encode("utf-8"))
        resp = self.sock.recv(self._RESP_SIZE).decode("utf-8")
        self._check_resp(resp, ResponseType.PREDICT, "predict_comm")

    def get_setuped_stations(
        self,
    ) -> dict[
        StationName,
        dict[Literal["longitude", "latitude", "altitude", "elevation"], float],
    ]:
        """Send command to Orbitron TCP server to get setuped ground stations info:
        longitude, latitude, altitude and elevation.
        """
        js = {"request": "get_setuped_stations"}
        self.sock.sendall(json.dumps(js).encode("utf-8"))
        data = self.sock.recv(self._DATA_RESP_SIZE).decode("utf-8")
        resp = data[-1]
        self._check_resp(resp, ResponseType.GET_DATA, "get_setuped_stations")
        return json.loads(data[:-1])

    def get_station_satellites_info(
        self, station_name: str
    ) -> dict[
        int, dict[Literal["uplink", "downlink", "tle_dt"], Union[float, str, None]]
    ]:
        """Send command to Orbitron TCP server to get main info setuped satellites for
        required ground station.
        """
        js = {
            "request": "get_station_satellites_info",
            "body": {"station_name": station_name},
        }
        self.sock.sendall(json.dumps(js).encode("utf-8"))
        data = self.sock.recv(self._DATA_RESP_SIZE).decode("utf-8")
        resp = data[-1]
        self._check_resp(resp, ResponseType.GET_DATA, "get_station_satellites_info")
        data: dict = json.loads(data[:-1])
        return {int(norad_id): info for norad_id, info in data.items()}

    def get_azimuth_elevation(
        self, station_name: str, norad_id: int, dt: Optional[datetime] = None
    ) -> dict[Literal["dt", "azimuth", "elevation"], Union[str, Optional[float]]]:
        """Send command to Orbitron TCP server to get azimuth and elevation angles
        values for required communication at required datetime.
        """

        if isinstance(dt, datetime):
            dt = dt.isoformat()

        js = {
            "request": "get_azimuth_elevation",
            "body": {
                "station_name": station_name,
                "norad_id": norad_id,
                "dt": dt,
            },
        }

        self.sock.sendall(json.dumps(js).encode("utf-8"))
        time.sleep(0.1)
        data = self.sock.recv(self._DATA_RESP_SIZE).decode("utf-8")
        resp = data[-1]
        self._check_resp(resp, ResponseType.GET_DATA, "get_azimuth_elevation")
        return json.loads(data[:-1])

    def get_frequencies(
        self, station_name: str, norad_id: int, dt: Optional[datetime] = None
    ) -> dict[Literal["dt", "uplink", "downlink"], Union[str, Optional[float]]]:
        """Send command to Orbitron TCP server to get uplink and downlink frequencies
        calculated with Doppler shift for required communication at required datetime.
        """

        if isinstance(dt, datetime):
            dt = dt.isoformat()

        js = {
            "request": "get_frequencies",
            "body": {
                "station_name": station_name,
                "norad_id": norad_id,
                "dt": dt,
            },
        }

        self.sock.sendall(json.dumps(js).encode("utf-8"))
        time.sleep(0.1)
        data = self.sock.recv(self._DATA_RESP_SIZE).decode("utf-8")
        resp = data[-1]
        self._check_resp(resp, ResponseType.GET_DATA, "get_frequencies")
        return json.loads(data[:-1])

    def get_data(
        self, station_name: str, norad_id: int, dt: Optional[datetime] = None
    ) -> dict[
        Literal["dt", "azimuth", "elevation", "uplink", "downlink"],
        Union[str, Optional[float]],
    ]:
        """Send command to Orbitron TCP server to get azimuth, elevation, uplink and
        downlink frequencies calculated with Doppler shift required communication at
        required datetime.
        """

        if isinstance(dt, datetime):
            dt = dt.isoformat()

        js = {
            "request": "get_data",
            "body": {
                "station_name": station_name,
                "norad_id": norad_id,
                "dt": dt,
            },
        }

        self.sock.sendall(json.dumps(js).encode("utf-8"))
        time.sleep(0.1)
        data = self.sock.recv(self._DATA_RESP_SIZE).decode("utf-8")
        resp = data[-1]
        self._check_resp(resp, ResponseType.GET_DATA, "get_data")
        return json.loads(data[:-1])

    def get_comm_sessions_params(
        self, station_name: str, norad_id: int
    ) -> dict[str, dict[str, Union[str, float, None]]]:
        """Send command to Orbitron TCP server to get communication sessions parameters,
        which are described in SessionParams class for required communication.
        """

        js = {
            "request": "get_comm_sessions_params",
            "body": {
                "station_name": station_name,
                "norad_id": norad_id,
            },
        }

        self.sock.sendall(json.dumps(js).encode("utf-8"))
        time.sleep(1)  # Time for calculations at server, if less data isn't full
        data = self.sock.recv(self._DATA_RESP_EXTRA_SIZE).decode("utf-8")
        resp = data[-1]
        self._check_resp(resp, ResponseType.GET_DATA, "get_comm_sessions_params")
        return json.loads(data[:-1])

    def _get_all_data(self, station_name: str, norad_id: int) -> list[
        dict[
            Literal["dt", "azimuth", "elevation", "uplink", "downlink", "visibility"],
            str,
        ]
    ]:
        """Send command to Orbitron TCP server to get all communication data which are
        described in CommParams class for required communication.
        """

        js = {
            "request": "get_all_data",
            "body": {
                "station_name": station_name,
                "norad_id": norad_id,
            },
        }

        self.sock.sendall(json.dumps(js).encode("utf-8"))
        time.sleep(1)
        # TODO: this data is too large, need check size
        data = self.sock.recv(self._DATA_RESP_EXTRA_SIZE).decode("utf-8")
        resp = data[-1]
        self._check_resp(resp, ResponseType.GET_DATA, "get_all_data")
        return json.loads(data[:-1])

    def clear_ground_station_data(self, station_name: str) -> None:
        """Send command to Orbitron TCP server to clear satellites and communication
        data for required ground station.
        """

        js = {
            "request": "clear_ground_station_data",
            "body": {
                "station_name": station_name,
            },
        }

        self.sock.sendall(json.dumps(js).encode("utf-8"))
        resp = self.sock.recv(self._RESP_SIZE).decode("utf-8")
        self._check_resp(resp, ResponseType.CONFIGURE, "clear_ground_station_data")


if __name__ == "__main__":
    station = {
        "longitude": 50.17763,
        "latitude": 53.21204,
        "altitude": 137,
        "elevation": 0,
        "station_name": "Samara",
    }
    satellite = {
        "norad_id": 57173,
        "uplink": 437398600,
        "downlink": 437398600,
        "new_uplink": 437398800,
        "new_downlink": 437398400,
    }

    tle_str = """1 24793U 97020B   24037.03377183  .00000569  00000-0  19293-3 0  9998
    2 24793  86.3959  25.1423 0002044  81.6965 278.4463 14.35063644400799"""
    tle_file_name = "57173_2024-02-13.tle"

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

        client.setup_new_frequencies(
            station_name=station["station_name"],
            norad_id=satellite["norad_id"],
            uplink=satellite["new_uplink"],
            downlink=satellite["new_downlink"],
        )

        client.setup_new_tle_by_str(
            station_name=station["station_name"],
            norad_id=satellite["norad_id"],
            tle_str=tle_str,
        )

        client.setup_new_tle_by_file(
            station_name=station["station_name"],
            norad_id=satellite["norad_id"],
            tle_file_name=tle_file_name,
            default_folder=True,
        )

        client.setup_new_tle_by_spacetrack(
            station_name=station["station_name"],
            norad_id=satellite["norad_id"],
        )

        client.update_tles_by_spacetrack(
            station_name=station["station_name"],
            norad_ids=[satellite["norad_id"]],
        )

        client.predict_comm(
            station_name=station["station_name"],
            norad_id=satellite["norad_id"],
        )

        direction_data = client.get_azimuth_elevation(
            station_name=station["station_name"],
            norad_id=satellite["norad_id"],
        )

        frequencies_data = client.get_frequencies(
            station_name=station["station_name"],
            norad_id=satellite["norad_id"],
        )

        position_data = client.get_data(
            station_name=station["station_name"],
            norad_id=satellite["norad_id"],
        )

        sessions_data = client.get_comm_sessions_params(
            station_name=station["station_name"],
            norad_id=satellite["norad_id"],
        )

        print("All functions is completed!")
