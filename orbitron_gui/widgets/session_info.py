import os

from PyQt5 import QtWidgets, uic

from ..ui.SessionInfoWidget import Ui_Form as Ui_SessionInfo


class SessionInfo(Ui_SessionInfo, QtWidgets.QWidget):
    """Class used to represnt widget with main session parameters (azimuth, elevation,
    sun azimuth and sun elevation) at required time.
    """

    WIDGET_UI_NAME = "session_info_widget.ui"

    _UI_PATH = os.path.join(os.path.dirname(__file__), "..", "ui")
    _WIDGET_UI_FULLNAME = os.path.join(_UI_PATH, WIDGET_UI_NAME)

    def __init__(
        self,
        dt: str,
        azimuth: float,
        elevation: float,
        sun_azimuth: float,
        sun_elevation: float,
    ):
        super().__init__()
        uic.loadUi(self._WIDGET_UI_FULLNAME, self)

        self.session_time_label.setText(dt)
        self.azimuth_session_label.setText(str(round(azimuth, 1)))
        self.elevation_session_label.setText(str(round(elevation, 1)))
        self.sun_azimuth_label.setText(str(round(sun_azimuth, 1)))
        self.sun_elevation_label.setText(str(round(sun_elevation, 1)))
