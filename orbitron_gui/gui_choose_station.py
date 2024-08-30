import logging
import os
from math import degrees
from typing import Optional

from PyQt5 import QtCore, QtWidgets, uic
from PyQt5.QtGui import QCloseEvent

from ..exceptions.tcp_exceptions import (
    TCPServerResponseError,
    TCPServerUnexpectedResponseError,
)
from ..tcp.orbitron_tcp_client import OrbitronTcpClient
from .gui_services.services import StationInfo, StationName
from .gui_station_setup import StationSetupDialog
from .ui.ChooseGroundStationDialog import Ui_Dialog as Ui_ChooseStationDialog

logger = logging.getLogger(__name__)


class ChooseStationDialog(Ui_ChooseStationDialog, QtWidgets.QDialog):
    """Class used to represent window to choose ground station from awailable ground
    stations or add new ground stations.
    """

    DIALOG_NAME = "Orbiter: Choose ground station"
    DIALOG_UI_NAME = "choose_ground_station_dialog.ui"

    _DIALOG_WINDOW_HEIGHT = 265
    _DIALOG_WINDOW_WIDTH = 320

    _UI_PATH = os.path.join(os.path.dirname(__file__), "ui")
    _DIALOG_UI_FULLNAME = os.path.join(_UI_PATH, DIALOG_UI_NAME)

    def __init__(
        self,
        orbitron_client: OrbitronTcpClient,
        parent: QtWidgets.QWidget = None,
    ):
        super().__init__(parent)
        uic.loadUi(self._DIALOG_UI_FULLNAME, self)

        self.setWindowTitle(self.DIALOG_NAME)
        self.setFixedSize(self._DIALOG_WINDOW_WIDTH, self._DIALOG_WINDOW_HEIGHT)

        self.orbitron_client = orbitron_client

        self.selected_station_name: Optional[str] = None

        self._init_stations_list_widget()
        self._init_buttons()

        self.stations = self.get_orbitron_stations_info()
        for station_info in self.stations.values():
            self.add_station_to_listwidget(station_info)
        logger.info("Dialog to choose ground station is initialized.")

    def _init_buttons(self) -> None:
        """Initiate buttons."""
        self.add_new_station_button.pressed.connect(self.add_new_station_button_slot)
        self.choose_selected_station_button.pressed.connect(
            self.choose_selected_station_buttons_slot
        )

    def _init_stations_list_widget(self) -> None:
        """Initiate listwidget to display available ground stations."""
        self.sessions_listwidget = QtWidgets.QListWidget()
        self.sessions_listwidget.currentRowChanged.connect(
            self.save_selected_station_slot
        )
        self.available_stations_scroll_area.setWidget(self.sessions_listwidget)
        logger.debug("Listwidget for stations in scroll area is initialized.")

    def _form_station_name(self, station_info: StationInfo) -> str:
        """Form string with ground station parameters for listwidget item.

        Args:
            station_info (StationInfo): dataclass with ground stations parameters

        Returns:
            str: string for listwidget item
        """
        station_info_str = (
            f"{station_info.name} | "
            f"Lon. {degrees(station_info.longitude):.3f}°, "
            f"Lat. {degrees(station_info.latitude):.3f}°, "
            f"Alt. {station_info.altitude:.2f}m, "
            f"El. {degrees(station_info.elevation):.1f}°"
        )
        return station_info_str

    def get_orbitron_stations_info(self) -> dict[StationName, StationInfo]:
        """Request setuped ground stations from Orbitron Server.

        Returns:
            dict[str, StationInfo]: dict with names of ground stations as keys and
                ground stations parameteres in dataclasses as values
        """
        try:
            stations = {}
            setuped_stations = self.orbitron_client.get_setuped_stations()
            for station_name, station_info in setuped_stations.items():
                stations[station_name] = StationInfo(
                    station_name,
                    station_info["longitude"],
                    station_info["latitude"],
                    station_info["altitude"],
                    station_info["elevation"],
                )
            logger.info(
                f"{len(stations)} available stations are got from Orbitron server."
            )
            return stations
        except (TCPServerResponseError, TCPServerUnexpectedResponseError):
            logger.exception()
            QtWidgets.QMessageBox.warning(
                self,
                "Warning",
                f"Server error. Couldn't get a list of available stations.",
                QtWidgets.QMessageBox.Ok,
                QtWidgets.QMessageBox.Ok,
            )

    def save_selected_station_slot(self) -> None:
        """Slot to save station name from selected listwidget item."""
        selected_station_item = self.sessions_listwidget.currentItem()
        self.selected_station_name = selected_station_item.text().split(" | ")[0]
        logger.debug(f"{self.selected_station_name} station is chosen in listwidget.")

    def choose_selected_station_buttons_slot(self) -> None:
        """Button slot to choose selected ground station."""
        if self.selected_station_name:
            self.accept()
        else:
            QtWidgets.QMessageBox.warning(
                self,
                "Warning",
                f"Choose available station or add new station.",
                QtWidgets.QMessageBox.Ok,
                QtWidgets.QMessageBox.Ok,
            )

    def add_new_station_button_slot(self) -> None:
        """Open dialog window to fill ground station parameters and setup new ground
        station to Orbitron Server.
        """
        station_parameters_dialog = StationSetupDialog(self.orbitron_client)
        if station_parameters_dialog.exec():
            station_info = station_parameters_dialog.get_station_parameters()

            if station_info.name in self.stations:
                listwidget_item = self.sessions_listwidget.findItems(
                    station_info.name,
                    QtCore.Qt.MatchStartsWith,
                )[0]
                index = self.sessions_listwidget.indexFromItem(listwidget_item).row()
                self.sessions_listwidget.takeItem(index)

            self.stations[station_info.name] = station_info
            self.add_station_to_listwidget(station_info)

            logger.info(
                f"Ground station {station_info.name} was setuped to Orbitron by "
                f"StationSetupDialog."
            )
        station_parameters_dialog.deleteLater()

    def add_station_to_listwidget(self, station_info: StationInfo) -> None:
        """Add ground station to listwidget.

        Args:
            station_info (StationInfo): dataclass with ground station parameters
        """
        station_info_str = self._form_station_name(station_info)
        listwidget_item = QtWidgets.QListWidgetItem(station_info_str)
        self.sessions_listwidget.addItem(listwidget_item)

    def get_selected_station_info(self) -> StationInfo:
        """Returns selected ground station info in dataclass from dialog."""
        return self.stations[self.selected_station_name]

    def closeEvent(self, event: QCloseEvent) -> None:
        """Close window event."""
        reply = QtWidgets.QMessageBox.question(
            self,
            "Warning",
            "Station isn't chosen! Are you sure?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )

        if reply == QtWidgets.QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()
