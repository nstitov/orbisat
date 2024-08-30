import logging
from datetime import datetime
from typing import Any, Optional, Union

from ..exceptions.tcp_exceptions import TCPServerBodyRequestError
from ..orbitron_main.orbitron import Orbitron
from .TcpServerABC import ResponseType, TCPServer

logger = logging.getLogger(__name__)

HOST = "0.0.0.0"
PORT = 5555


class OrbitronTcpServer(TCPServer):
    """A class used to represent TCP Server for intercation with Orbitron.

    Attributes:
        Orbitron (Orbitron): instance of the Orbitron class

    Methods:
        handle_request_message(msg): Method called Orbitron functions depends on msg.
            msg is message in JSON format with Orbitron function by "request"
            key and key-value arguments for Orbitron function by "body" key
    """

    def __init__(self, HOST: Union[str, int] = HOST, PORT: int = PORT):
        self.orbitron = Orbitron()
        super().__init__(HOST, PORT)

    def handle_request_message(
        self, msg: dict[str, Union[str, dict[str, Any], list]]
    ) -> tuple[ResponseType, Optional[dict[str, Any]]]:

        if msg["request"] == "setup_ground_station":
            if "body" in msg:
                self.orbitron.setup_ground_station(
                    msg["body"]["longitude"],
                    msg["body"]["latitude"],
                    msg["body"]["altitude"],
                    msg["body"].get("elevation", 0),
                    msg["body"].get("station_name", "default"),
                )
                logger.info("Command setup_ground_station is succesfully completed.")
                return (ResponseType.CONFIGURE,)
            raise TCPServerBodyRequestError("setup_ground_station")

        elif msg["request"] == "setup_satellite":
            if "body" in msg:
                self.orbitron.setup_satellite(
                    msg["body"]["station_name"],
                    msg["body"]["norad_id"],
                    msg["body"].get("uplink", None),
                    msg["body"].get("downlink", None),
                )
                logger.info("Command setup_satellite is succesfully completed.")
                return (ResponseType.CONFIGURE,)
            raise TCPServerBodyRequestError("setup_satellite")

        elif msg["request"] == "setup_comm":
            if "body" in msg:
                self.orbitron.setup_comm(
                    msg["body"]["station_name"], msg["body"]["norad_id"]
                )
                logger.info("Command setup_comm is succesfully completed.")
                return (ResponseType.CONFIGURE,)
            raise TCPServerBodyRequestError("setup_comm")

        elif msg["request"] == "setup_new_frequencies":
            if "body" in msg:
                self.orbitron.setup_new_frequencies(
                    msg["body"]["station_name"],
                    msg["body"]["norad_id"],
                    msg["body"]["uplink"],
                    msg["body"]["downlink"],
                )
                logger.info("Command setup_new_frequencies is succesfully completed.")
                return (ResponseType.CONFIGURE,)
            raise TCPServerBodyRequestError("setup_new_frequencies")

        elif msg["request"] == "setup_new_tle_by_str":
            if "body" in msg:
                self.orbitron.setup_new_tle_by_str(
                    msg["body"]["station_name"],
                    msg["body"]["norad_id"],
                    msg["body"]["tle_str"],
                )
                logger.info("Command setup_new_tle_by_str is succesfully completed.")
                return (ResponseType.TLE_UPDATE,)
            raise TCPServerBodyRequestError("setup_new_tle_by_str")

        elif msg["request"] == "setup_new_tle_by_file":
            if "body" in msg:
                self.orbitron.setup_new_tle_by_file(
                    msg["body"]["station_name"],
                    msg["body"]["norad_id"],
                    msg["body"]["tle_file_name"],
                    msg["body"]["default_folder"],
                )
                logger.info("Command setup_new_tle_by_file is succesfully completed.")
                return (ResponseType.TLE_UPDATE,)
            raise TCPServerBodyRequestError("setup_new_tle_by_file")

        elif msg["request"] == "setup_new_tle_by_spacetrack":
            if "body" in msg:
                self.orbitron.setup_new_tle_by_spacetrack(
                    msg["body"]["station_name"], msg["body"]["norad_id"]
                )
                logger.info(
                    "Command setup_new_tle_by_spacetrack is succesfully completed."
                )
                return (ResponseType.TLE_UPDATE,)
            raise TCPServerBodyRequestError("setup_new_tle_by_spacetrack")

        elif msg["request"] == "update_tles_by_spacetrack":
            if "body" in msg:
                self.orbitron.update_tles_by_spacetrack(
                    msg["body"]["station_name"], msg["body"]["norad_ids"]
                )
                logger.info(
                    "Command update_tles_by_spacetrack is succesfully completed."
                )
                return (ResponseType.TLE_UPDATE,)
            raise TCPServerBodyRequestError("update_tles_by_spacetrack")

        elif msg["request"] == "predict_comm":
            if "body" in msg:
                self.orbitron.predict_comm(
                    msg["body"]["station_name"],
                    msg["body"]["norad_id"],
                    (
                        datetime.fromisoformat(dt)
                        if (dt := msg["body"].get("start_prediction"))
                        else None
                    ),
                    msg["body"].get("time_prediction", 86400),
                    msg["body"].get("step_prediction", 1),
                )
                logger.info("Command predict_comm is succesfully completed.")
                return (ResponseType.PREDICT,)
            raise TCPServerBodyRequestError("predict_comm")

        elif msg["request"] == "get_setuped_stations":
            stations_info = {}
            for station_name, station in self.orbitron.stations.items():
                station_parameters = {}
                station_parameters["longitude"] = station.pos.lam
                station_parameters["latitude"] = station.pos.phi
                station_parameters["altitude"] = station.pos.alt
                station_parameters["elevation"] = station.elevation_min
                stations_info[station_name] = station_parameters

            return (ResponseType.GET_DATA, stations_info)

        elif msg["request"] == "get_station_satellites_info":
            if "body" in msg:
                satellites = self.orbitron.satellites[msg["body"]["station_name"]]
                js_satellites_info = {}
                for norad_id, satellite in satellites.items():
                    satellite_info = {
                        "uplink": satellite.uplink_freq,
                        "downlink": satellite.downlink_freq,
                        "tle_dt": satellite.tle_file_dt.isoformat(),
                    }
                    js_satellites_info[norad_id] = satellite_info
                logger.info(
                    "Command get_station_satellites_info is succesfully completed."
                )
                return (ResponseType.GET_DATA, js_satellites_info)
            raise TCPServerBodyRequestError("get_station_satellites_info")

        elif msg["request"] == "get_azimuth_elevation":
            if "body" in msg:
                dt = msg["body"].get("dt", None)
                if dt:
                    dt = datetime.fromisoformat(dt)

                data = self.orbitron.get_azimuth_elevation(
                    msg["body"]["station_name"],
                    msg["body"]["norad_id"],
                    dt,
                )
                logger.info("Command get_azimuth_elevation is succesfully completed.")
                return (
                    ResponseType.GET_DATA,
                    {
                        "dt": data[0].isoformat(),
                        "azimuth": data[1],
                        "elevation": data[2],
                    },
                )
            raise TCPServerBodyRequestError("get_azimuth_elevation")

        elif msg["request"] == "get_frequencies":
            if "body" in msg:
                dt = msg["body"].get("dt", None)
                if dt:
                    dt = datetime.fromisoformat(dt)

                data = self.orbitron.get_frequencies(
                    msg["body"]["station_name"],
                    msg["body"]["norad_id"],
                    dt,
                )
                logger.info("Command get_frequencies is succesfully completed.")
                return (
                    ResponseType.GET_DATA,
                    {"dt": data[0].isoformat(), "uplink": data[1], "downlink": data[2]},
                )
            raise TCPServerBodyRequestError("get_frequencies")

        elif msg["request"] == "get_data":
            if "body" in msg:
                dt = msg["body"].get("dt", None)
                if dt:
                    dt = datetime.fromisoformat(dt)

                data = self.orbitron.get_data(
                    msg["body"]["station_name"],
                    msg["body"]["norad_id"],
                    dt,
                )
                logger.info("Command get_data is succesfully completed.")
                return (
                    ResponseType.GET_DATA,
                    {
                        "dt": data[0].isoformat(),
                        "azimuth": data[1],
                        "elevation": data[2],
                        "uplink": data[3],
                        "downlink": data[4],
                    },
                )
            raise TCPServerBodyRequestError("get_data")

        elif msg["request"] == "get_comm_sessions_params":
            if "body" in msg:
                sessions = self.orbitron.get_comm_sessions_params(
                    msg["body"]["station_name"], msg["body"]["norad_id"]
                )
                js = {}
                for dt_session_start, session_params in sessions.items():
                    session_params_js = {
                        "start_session_dt": session_params.start_session_dt.isoformat(),
                        "start_elevation": session_params.start_elevation,
                        "start_azimuth": session_params.start_azimuth,
                        "start_sun_azimuth": session_params.start_sun_azimuth,
                        "start_sun_elevation": session_params.start_sun_elevation,
                        "end_session_dt": session_params.end_session_dt.isoformat(),
                        "end_elevation": session_params.end_elevation,
                        "end_azimuth": session_params.end_azimuth,
                        "end_sun_azimuth": session_params.end_sun_azimuth,
                        "end_sun_elevation": session_params.end_sun_elevation,
                        "max_session_dt": session_params.max_session_dt.isoformat(),
                        "max_elevation": session_params.max_elevation,
                        "max_azimuth": session_params.max_azimuth,
                        "max_sun_azimuth": session_params.max_sun_azimuth,
                        "max_sun_elevation": session_params.max_sun_elevation,
                        "zero_crossing_azimuth_flag": session_params.zero_crossing_azimuth_flag,
                    }
                    js[dt_session_start.isoformat()] = session_params_js
                logger.info(
                    "Command get_comm_sessions_params is succesfully completed."
                )
                return (ResponseType.GET_DATA, js)
            raise TCPServerBodyRequestError("get_comm_sessions_params")

        elif msg["request"] == "get_all_data":
            if "body" in msg:
                all_comm_data = self.orbitron.get_all_data(
                    msg["body"]["station_name"], msg["body"]["norad_id"]
                )
                js = []
                for dt, comm_params in sorted(all_comm_data.items()):
                    data = {
                        "dt": dt.isoformat(),
                        "azimuth": comm_params.azimuth,
                        "elevation": comm_params.elevation,
                        "uplink": comm_params.uplink,
                        "downlink": comm_params.downlink,
                        "visibility": comm_params.visibility,
                    }
                    js.append(data)
                logger.info("Command get_all_data is succesfully completed.")
                return (ResponseType.GET_DATA, js)
            raise Exception("get_all_data")

        elif msg["request"] == "clear_ground_station_data":
            if "body" in msg:
                self.orbitron.clear_ground_station_data(msg["body"]["station_name"])
                logger.info(
                    "Command clear_ground_station_data is succesfully completed."
                )
                return (ResponseType.CONFIGURE,)
            raise TCPServerBodyRequestError("clear_ground_station_data")

        else:
            return (ResponseType.NONE,)


if __name__ == "__main__":
    server = OrbitronTcpServer(HOST=HOST, PORT=PORT)
    pass
