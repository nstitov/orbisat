import math
from collections import deque
from typing import Optional

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt5 import QtWidgets

if __name__ == "__main__":
    import os
    import sys

    from ...tcp.orbisat_tcp_client import OrbisatTcpClient

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class Radar(FigureCanvasQTAgg):
    """Class used to represent radar graphic in polar coordinate system to display
    location of the satellite position.
    """

    def __init__(self):
        radar = Figure()
        self.axes = radar.add_subplot(projection="polar")
        self.axes.set_theta_zero_location("N")
        self.axes.set_theta_direction(-1)
        self.axes.set_rmax(0)
        self.axes.set_rmin(90)
        self.axes.set_rticks([0, 15, 30, 45, 60, 75, 90])
        self.axes.set_thetagrids([0, 90, 180, 270])
        self.axes.grid(True)

        self.cur_trace = self.axes.plot([], [], lw=2, color="g")[0]
        self.trace = self.axes.plot([], [], lw=1, color="b")[0]
        self.sat_pos = self.axes.plot([], [], marker="o", lw=3, ms=7, color="r")[0]

        super(Radar, self).__init__(radar)
        self.draw()


class OrbisatRadar(QtWidgets.QWidget):
    """Class used to represent radar widget to display location of the satellite
    position.
    """

    _TIME_TRACE_UPDATING = 30  # s
    _TRACE_DISPLAY_DURATION = 900  # s
    _TRACE_DISPLAY_SIZE = int(_TRACE_DISPLAY_DURATION / _TIME_TRACE_UPDATING)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        """
        Args:
            parent (QWidget): Reference to the instance of central widget app class
        """

        QtWidgets.QWidget.__init__(self, parent)

        layout = QtWidgets.QVBoxLayout()

        self.radar = Radar()
        layout.addWidget(self.radar)
        self.setLayout(layout)

        self._azimuth_cur_trace = deque(maxlen=self._TRACE_DISPLAY_SIZE)
        self._elevation_cur_trace = deque(maxlen=self._TRACE_DISPLAY_SIZE)

    def clear_satellite_data(self) -> None:
        """Clear all satellite location data."""
        self.radar.cur_trace.set_data([], [])
        self.radar.trace.set_data([], [])
        self.radar.sat_pos.set_data(None, None)
        self._azimuth_cur_trace.clear()
        self._elevation_cur_trace.clear()
        self.radar.draw()

    def add_cur_trace_data(
        self, azimuths: list[Optional[float]], elevations: list[Optional[float]]
    ) -> None:
        """Add a new position point to satellite current trace.

        Args:
            azimuth (float): azimuth of position point to add to current trace data
            elevation (float): elevation of position point to add to current trace data

        Returns:
        """
        for azimuth, elevation in zip(azimuths, elevations):
            if azimuth and elevation:
                self._azimuth_cur_trace.append(math.radians(azimuth))
                self._elevation_cur_trace.append(elevation)

        self.radar.cur_trace.set_data(
            self._azimuth_cur_trace, self._elevation_cur_trace
        )

    def update_satellite_position(
        self, azimuth: Optional[float], elevation: Optional[float]
    ) -> None:
        """Set new satellite position at radar and update radar.

        Args:
            azimuth (float): azimuth of satellite position
            elevation (float): elevation of satellite position

        Returns:
        """
        if azimuth:
            azimuth = math.radians(azimuth)
            elevation = float(elevation if elevation > 0 else 0)

        self.radar.sat_pos.set_data(
            azimuth,
            elevation,
        )

        self.radar.draw()

    def update_selected_trace(
        self, azimuths: list[Optional[float]], elevations: list[Optional[float]]
    ):
        azimuths = [math.radians(azimuth) for azimuth in azimuths]
        self.radar.trace.set_data(azimuths, elevations)

    def clear_trace(self):
        """Clear data for trace showing communication session."""
        self.radar.trace.set_data([], [])


if __name__ == "__main__":
    orbisat_client = OrbisatTcpClient(HOST="localhost", PORT=5555)
    orbisat_client.create_connection()

    app = QtWidgets.QApplication([])
    tmp = OrbisatRadar(orbisat_client, "Samara", 57173)
    tmp.show()
    app.exec_()
