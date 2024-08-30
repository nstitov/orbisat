import logging
import os
from math import degrees, radians

from PyQt5 import QtWidgets, uic
from PyQt5.QtGui import QCloseEvent

from ..exceptions.tcp_exceptions import (
    TCPServerResponseError,
    TCPServerUnexpectedResponseError,
)
from ..tcp.orbitron_tcp_client import OrbitronTcpClient
from .gui_services.services import StationInfo
from .ui.GroundStationSetupDialog import Ui_Dialog

logger = logging.getLogger(__name__)


class StationSetupDialog(Ui_Dialog, QtWidgets.QDialog):
    """Class used to represent window to setup new ground station to Orbitron Server."""

    DIALOG_NAME = "Orbiter: Setup ground station"
    DIALOG_UI_NAME = "ground_station_setup_dialog.ui"

    _DIALOG_WINDOW_HEIGHT = 195
    _DIALOG_WINDOW_WIDTH = 228

    _UI_PATH = os.path.join(os.path.dirname(__file__), "ui")
    _DIALOG_UI_FULLNAME = os.path.join(_UI_PATH, DIALOG_UI_NAME)

    SAMARA_STATION_INFO = StationInfo(
        name="Samara",
        longitude=radians(50.1776),
        latitude=radians(53.2120),
        altitude=137,
        elevation=radians(0),
    )

    def __init__(
        self,
        orbitron_client: OrbitronTcpClient,
        parent: QtWidgets.QWidget = None,
    ):
        super().__init__(parent)

        uic.loadUi(self._DIALOG_UI_FULLNAME, self)
        self.setWindowTitle(self.DIALOG_NAME)

        self.orbitron_client = orbitron_client
        self.station_info = self.SAMARA_STATION_INFO

        self._init_lineedits()
        self._init_buttons()

        self.set_lineedit_values(self.station_info)
        logger.info("Dialog to setup ground station is initialized.")

    def _init_buttons(self) -> None:
        """Initiate buttons."""
        self.confirm_button.clicked.connect(self.setup_station_parameters_button_slot)
        logger.debug("All buttons are successfully initialized.")

    def _init_lineedits(self) -> None:
        """Initiate lineedits."""
        self.station_name_lineedit.editingFinished.connect(
            self.save_station_name_lineedit_slot
        )
        self.elevation_lineedit.editingFinished.connect(
            self.save_elevation_lineedit_slot
        )
        self.longitude_lineedit.editingFinished.connect(
            self.save_longitude_lineedit_slot
        )
        self.latitude_lineedit.editingFinished.connect(self.save_latitude_lineedit_slot)
        self.altitude_lineedit.editingFinished.connect(self.save_altitude_lineedit_slot)
        logger.debug("All lineedits are successfully initialized.")

    def _check_data_filling(self) -> bool:
        """Check the availability of all station parameters.

        Return:
            bool: if all station parameters is available returns True, else False
        """
        if (
            isinstance(self.station_info.longitude, (float, int))
            and isinstance(self.station_info.latitude, (float, int))
            and isinstance(self.station_info.altitude, (float, int))
            and isinstance(self.station_info.elevation, (float, int))
            and self.station_info.name
        ):
            return True
        return False

    def set_lineedit_values(self, station_info: StationInfo) -> None:
        """Set values of ground station parameters to lineedits.

        Args:
            station_info (StationInfo): dataclass with station parameters
        """
        self.station_name_lineedit.setText(station_info.name)
        self.longitude_lineedit.setText(str(round(degrees(station_info.longitude), 3)))
        self.latitude_lineedit.setText(str(round(degrees(station_info.latitude), 3)))
        self.altitude_lineedit.setText(str(round(station_info.altitude, 2)))
        self.elevation_lineedit.setText(str(round(degrees(station_info.elevation), 1)))

    def save_longitude_lineedit_slot(self) -> None:
        """Slot to save longitude from lineedit."""
        try:
            self.station_info.longitude = radians(float(self.longitude_lineedit.text()))
            logger.info(f"Longitude {self.station_info.longitude} is saved.")
        except ValueError:
            self.station_info.longitude = None
            self.longitude_lineedit.setText("Longitude must be float/int!")

    def save_latitude_lineedit_slot(self) -> None:
        """Slot to save latitude from lineedit."""
        try:
            self.station_info.latitude = radians(float(self.latitude_lineedit.text()))
            logger.info(f"Latitude {self.station_info.latitude} is saved.")
        except ValueError:
            self.station_info.latitude = None
            self.latitude_lineedit.setText("Latitude must be float/int!")

    def save_altitude_lineedit_slot(self) -> None:
        """Slot to save altitude from lineedit."""
        try:
            self.station_info.altitude = float(self.altitude_lineedit.text())
            logger.info(f"Altitude {self.station_info.altitude} is saved.")
        except ValueError:
            self.station_info.altitude = None
            self.altitude_lineedit.setText("Altitude must be float/int!")

    def save_elevation_lineedit_slot(self) -> None:
        """Slot to save elevation from lineedit."""
        try:
            self.station_info.elevation = radians(float(self.elevation_lineedit.text()))
            logger.info(f"Elevation {self.station_info.elevation} is saved.")
        except ValueError:
            self.station_info.elevation = None
            self.elevation_lineedit.setText("Elevation must be float/int!")

    def save_station_name_lineedit_slot(self) -> None:
        """Slot to save ground station name from lineedit."""
        try:
            self.station_info.name = self.station_name_lineedit.text()
            if not self.station_info.name:
                raise ValueError
            logger.info(f"Name {self.station_info.name} is saved.")
        except ValueError:
            self.station_info.name = None
            self.station_name_lineedit.setText("Enter at least one character!")

    def setup_station_parameters_button_slot(self) -> None:
        """Button slot to setup new ground station by required parameters."""
        if self._check_data_filling():
            try:
                self.orbitron_client.setup_ground_station(
                    longitude=degrees(self.station_info.longitude),
                    latitude=degrees(self.station_info.latitude),
                    altitude=self.station_info.altitude,
                    elevation=degrees(self.station_info.elevation),
                    station_name=self.station_info.name,
                )
                self.accept()
            except (TCPServerResponseError, TCPServerUnexpectedResponseError):
                QtWidgets.QMessageBox.warning(
                    self,
                    "Warning",
                    f"Server error. Station with specified parameters isn't setuped.",
                    QtWidgets.QMessageBox.Ok,
                    QtWidgets.QMessageBox.Ok,
                )
        else:
            QtWidgets.QMessageBox.warning(
                self,
                "Warning",
                f"You must fill in all fields!",
                QtWidgets.QMessageBox.Ok,
                QtWidgets.QMessageBox.Ok,
            )

    def get_station_parameters(self) -> StationInfo:
        """Return parameters of setuped ground station from dialog."""
        return self.station_info

    def closeEvent(self, event: QCloseEvent) -> None:
        """Close window event."""
        reply = QtWidgets.QMessageBox.question(
            self,
            "Warning",
            "Station wasn't setuped yet! Are you sure?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )

        if reply == QtWidgets.QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()
