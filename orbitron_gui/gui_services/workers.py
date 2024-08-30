from datetime import datetime

from PyQt5 import QtCore

from ...tcp.orbitron_tcp_client import HOST as _ORB_HOST
from ...tcp.orbitron_tcp_client import PORT as _ORB_PORT
from ...tcp.orbitron_tcp_client import OrbitronTcpClient


class WorkersSignals(QtCore.QObject):
    trace_data_got = QtCore.pyqtSignal(dict)
    sessions_parameters_got = QtCore.pyqtSignal(dict)
    frequencies_changed = QtCore.pyqtSignal()
    prediction_completed = QtCore.pyqtSignal(dict)
    tle_updated = QtCore.pyqtSignal(dict)
    error_raised = QtCore.pyqtSignal(dict)


class GetTraceDataWorker(QtCore.QRunnable):
    def __init__(
        self,
        station_name: str,
        selected_satellite: int,
        dt_trace_points: list[datetime],
        trace_session_index: int,
    ):
        super().__init__()
        self.signals = WorkersSignals()

        self.station_name = station_name
        self.selected_satellite = selected_satellite
        self.trace_session_index = trace_session_index
        self.dt_trace_points = dt_trace_points

    @QtCore.pyqtSlot()
    def run(self):
        azimuths, elevations = [], []
        try:
            with OrbitronTcpClient(HOST=_ORB_HOST, PORT=_ORB_PORT) as orbitron_client:
                for dt in self.dt_trace_points:
                    point = orbitron_client.get_azimuth_elevation(
                        self.station_name, self.selected_satellite, dt
                    )
                    azimuths.append(point["azimuth"])
                    elevations.append(point["elevation"])
                self.signals.trace_data_got.emit(
                    {
                        "azimuths": azimuths,
                        "elevations": elevations,
                        "session_index": self.trace_session_index,
                        "satellite": self.selected_satellite,
                    }
                )
        except Exception:
            self.signals.error_raised.emit(
                {"request_name": "get azimuth and elevation"}
            )


class GetSessionsParametersWorker(QtCore.QRunnable):
    def __init__(self, station_name: str, selected_satellite: int):
        super().__init__()
        self.signals = WorkersSignals()
        self.station_name = station_name
        self.selected_satellite = selected_satellite

    @QtCore.pyqtSlot()
    def run(self):
        try:
            with OrbitronTcpClient(HOST=_ORB_HOST, PORT=_ORB_PORT) as orbitron_client:
                sessions = orbitron_client.get_comm_sessions_params(
                    self.station_name,
                    self.selected_satellite,
                )
                self.signals.sessions_parameters_got.emit({"sessions": sessions})
        except Exception:
            self.signals.error_raised.emit({"request_name": "get sessions parameters"})


class ChangeFrequenciesWorker(QtCore.QRunnable):
    def __init__(self, station_name: str, norad_id: int, uplink: int, downlink: int):
        super().__init__()
        self.signals = WorkersSignals()
        self.station_name = station_name
        self.norad_id = norad_id
        self.uplink = uplink
        self.downlink = downlink

    @QtCore.pyqtSlot()
    def run(self):
        try:
            with OrbitronTcpClient(HOST=_ORB_HOST, PORT=_ORB_PORT) as orbitron_client:
                orbitron_client.setup_new_frequencies(
                    self.station_name,
                    self.norad_id,
                    self.uplink,
                    self.downlink,
                )
                self.signals.frequencies_changed.emit()
        except Exception:
            self.signals.error_raised.emit({"request_name": "setup new frequencies"})


class PredictSatelliteWorker(QtCore.QRunnable):
    def __init__(self, station_name: str, norad_id: int):
        super().__init__()
        self.signals = WorkersSignals()
        self.station_name = station_name
        self.norad_id = norad_id

    @QtCore.pyqtSlot()
    def run(self):
        try:
            with OrbitronTcpClient(HOST=_ORB_HOST, PORT=_ORB_PORT) as orbitron_client:
                orbitron_client.predict_comm(self.station_name, self.norad_id)
                self.signals.prediction_completed.emit({"norad_id": self.norad_id})
        except Exception:
            self.signals.error_raised.emit({"request_name": "prediction"})


class SetupSatelliteStrTLE(QtCore.QRunnable):
    def __init__(
        self, station_name: str, norad_id: int, tle_line_1: str, tle_line_2: str
    ):
        super().__init__()
        self.signals = WorkersSignals()
        self.station_name = station_name
        self.norad_id = norad_id
        self.tle_line_1 = tle_line_1
        self.tle_line_2 = tle_line_2

    @QtCore.pyqtSlot()
    def run(self):
        try:
            with OrbitronTcpClient(HOST=_ORB_HOST, PORT=_ORB_PORT) as orbitron_client:
                orbitron_client.setup_satellite(self.station_name, self.norad_id)
                orbitron_client.setup_comm(self.station_name, self.norad_id)
                orbitron_client.setup_new_tle_by_str(
                    self.station_name,
                    self.norad_id,
                    self.tle_line_1 + "\n" + self.tle_line_2,
                )
                self.signals.tle_updated.emit({"norad_id": self.norad_id})
        except Exception:
            self.signals.error_raised.emit({"request_name": "setup new TLE by file"})


class SetupSatelliteSpacetrackTLE(QtCore.QRunnable):
    def __init__(self, station_name: str, norad_id: int):
        super().__init__()
        self.signals = WorkersSignals()
        self.station_name = station_name
        self.norad_id = norad_id

    @QtCore.pyqtSlot()
    def run(self):
        try:
            with OrbitronTcpClient(HOST=_ORB_HOST, PORT=_ORB_PORT) as orbitron_client:
                orbitron_client.setup_satellite(self.station_name, self.norad_id)
                orbitron_client.setup_comm(self.station_name, self.norad_id)
                orbitron_client.setup_new_tle_by_spacetrack(
                    self.station_name,
                    self.norad_id,
                )
                self.signals.tle_updated.emit({"norad_id": self.norad_id})
        except Exception:
            self.signals.error_raised.emit(
                {"request_name": "setup new TLE by spacetrack"}
            )
