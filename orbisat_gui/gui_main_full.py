import logging
import os
from datetime import datetime, timedelta
from math import degrees
from typing import Iterable, Literal, Optional, Union

from PyQt5 import QtCore, QtWidgets, uic
from PyQt5.QtGui import QCloseEvent

from ..exceptions.tcp_exceptions import (
    TCPServerResponseError,
    TCPServerUnexpectedResponseError,
)
from ..tcp.orbisat_tcp_client import OrbisatTcpClient
from .gui_choose_station import ChooseStationDialog
from .gui_services.services import NoradID, SatelliteInfo, StationInfo, StationName
from .gui_services.workers import (
    ChangeFrequenciesWorker,
    GetSessionsParametersWorker,
    GetTraceDataWorker,
    PredictSatelliteWorker,
    SetupSatelliteSpacetrackTLE,
    SetupSatelliteStrTLE,
)
from .ui.MainWindowFull import Ui_MainWindow
from .widgets.counter_timer import CounterTimer
from .widgets.session_info import SessionInfo

logger = logging.getLogger(__name__)


class OrbisatWindow(Ui_MainWindow, QtWidgets.QMainWindow):
    """Class used to represent GUI for interaction with OrbiSat TCP Server."""

    PROGRAM_NAME = "Orbiter"
    MAIN_WINDOW_UI_NAME = "main_window_full.ui"

    _MAIN_WINDOW_HEIGHT = 450
    _MAIN_WINDOW_WIDTH = 775

    _DT_PATTERN = "%H:%M:%S %d.%m.%Y"
    _DATE_PATTERN = "%d.%m.%Y"

    _TLE_PATH = os.path.join(os.path.dirname(__file__), "..", "tle")
    _UI_PATH = os.path.join(os.path.dirname(__file__), "ui")

    _MAIN_WINDOW_UI_FULLNAME = os.path.join(_UI_PATH, MAIN_WINDOW_UI_NAME)

    _DATA_UPDATING_PERIOD = 1  # s
    _WAITING_INFO_SHOW_PERIOD = 0.25  # s

    def __init__(self, orbisat_client: OrbisatTcpClient, *args, **kwargs):
        super(OrbisatWindow, self).__init__(*args, **kwargs)
        uic.loadUi(self._MAIN_WINDOW_UI_FULLNAME, self)

        self.setWindowTitle(self.PROGRAM_NAME)
        self.setFixedSize(self._MAIN_WINDOW_WIDTH, self._MAIN_WINDOW_HEIGHT)

        self.orbisat_client = orbisat_client

        self.station_info: Optional[StationInfo] = None

        self.satellite_info: Optional[SatelliteInfo] = None
        self.orbisat_stations: dict[StationName, StationInfo] = {}
        self.station_satellites: dict[NoradID, SatelliteInfo] = {}

        self.trace_session_index: Optional[int] = None
        self.spacetrack_norad_id: Optional[NoradID] = None

        self._waiting_counter = 0

        self._threadpool = QtCore.QThreadPool()

        self.station_info = self.choose_station_by_dialog()
        if self.station_info:
            self.statusBar().showMessage(
                f"{self.station_info.name} ground station is chosen"
            )
        else:
            self.statusBar().showMessage(
                f"Ground station isn't setuped. Use 'Change station' button in Station "
                f"menu to choose ground station"
            )
            logger.info("User didn't choose ground station at started GUI.")
        self.update_selected_station_data()

        self._init_timers()
        self._init_buttons()
        self._init_menu_buttons()
        self._init_lineedits()

        self.data_updating_timer.start()
        logger.info("OrbiSat GUI is successfully initialized.")

    def _init_timers(self) -> None:
        """Initiate timers."""
        self.data_updating_timer = QtCore.QTimer()
        self.data_updating_timer.setInterval(self._DATA_UPDATING_PERIOD * 1000)
        self.data_updating_timer.timeout.connect(self.data_updating_timer_slot)

        self.trace_updating_timer = QtCore.QTimer()
        self.trace_updating_timer.setInterval(
            self.radar_widget._TIME_TRACE_UPDATING * 1000
        )
        self.trace_updating_timer.timeout.connect(self.trace_updating_timer_slot)

        self.waiting_info_timer = CounterTimer()
        self.waiting_info_timer.setInterval(int(self._WAITING_INFO_SHOW_PERIOD * 1000))
        self.waiting_info_timer.timeout.connect(self.waiting_info_updating_timer_slot)
        logger.debug("All timers are successfully initialized.")

    def _init_buttons(self) -> None:
        """Initiate GUI buttons."""
        self.predict_button.pressed.connect(self.predict_button_slot)
        self.next_session_button.pressed.connect(self.show_next_radar_trace_button_slot)
        self.prev_session_button.pressed.connect(self.show_prev_radar_trace_button_slot)
        self.clear_session_button.pressed.connect(self.clear_radar_trace_button_slot)
        self.set_new_freqs_button.pressed.connect(self.set_new_frequencies_button_slot)
        self.tle_spacetrack_button.pressed.connect(self.tle_spacetrack_button_slot)
        self.tle_file_button.pressed.connect(self.choose_tle_file_button_slot)
        logger.debug("All buttons are successfully initialized.")

    def _init_menu_buttons(self):
        """Initiate GUI menu buttons."""
        self.clear_station_data_menu_button.triggered.connect(
            self.clear_station_data_menu_button_slot
        )
        self.change_station_menu_button.triggered.connect(
            self.change_station_menu_button_slot
        )
        logger.debug("All menu buttons are successfully initialized.")

    def _init_lineedits(self) -> None:
        """Initiate GUI lineedits."""
        self.set_uplink_lineedit.editingFinished.connect(
            self.save_new_uplink_freq_lineedit_slot
        )
        self.set_downlink_lineedit.editingFinished.connect(
            self.save_new_downlink_freq_lineedit_slot
        )
        self.spacetrack_norad_id_lineedit.editingFinished.connect(
            self.save_spacetrack_norad_id_lineedit_slot
        )
        logger.debug("All lineedits are successfully initialized.")

    def _init_available_satellites_widget(self) -> None:
        """Initiate widget to add radio buttons with available satellites for ground
        station to the scroll area.
        """
        self._satellites_buttons: dict[NoradID, QtWidgets.QRadioButton] = {}
        self._satellites_buttons_group = QtWidgets.QButtonGroup()
        self._satellites_buttons_group.buttonPressed.connect(
            self.change_selected_satellite_rb_slot
        )

        self._satellites_widget = QtWidgets.QWidget()
        self._satellites_layout = QtWidgets.QVBoxLayout()
        self._satellites_layout.setSpacing(0)
        self._satellites_layout.setContentsMargins(2, 0, 0, 0)
        self._satellites_layout.setAlignment(QtCore.Qt.AlignTop)
        logger.debug("Satellites widget for scroll area is successfully initialized.")

    def _init_sessions_info_widget(self) -> None:
        """Initiate widget to add sessions info and radio buttons for selected satellite
        to the scroll area.
        """
        self._sessions_widget = QtWidgets.QWidget()
        self._sessions_layout = QtWidgets.QVBoxLayout()
        self._sessions_layout.setSpacing(0)
        self._sessions_layout.setContentsMargins(0, 0, 0, 0)
        self._sessions_layout.setAlignment(QtCore.Qt.AlignTop)

        self._sessions_buttons_group = QtWidgets.QButtonGroup()
        self._sessions_buttons_group.buttonPressed.connect(self.change_trace_rb_slot)
        logger.debug("Sessions widget for scroll area is successfully initialized.")

    def _process_tle_file(self, filename: str) -> tuple[NoradID, str, str]:
        """Handle TLE file.

        Args:
            filename(str): absolute TLE filename path

        Returns:
            tuple[int, str, str]: tuple with NORAD ID is got from TLE file, tle_line_1
                and tle_line_2
        """
        with open(filename, "r", encoding="utf-8") as tle_file:
            lines = tle_file.read().strip().split("\n")
            if len(lines) == 2:
                line_1, line_2 = lines[0], lines[1]
            elif len(lines) == 3:
                _, line_1, line_2 = lines[0], lines[1], lines[2]
            else:
                logger.warning(
                    f"Chosen TLE file {filename} has incorrect lines amount."
                )
                self.statusBar().showMessage("TLE file has incorrect lines amount")
                return
        try:
            norad_id = int(line_1[2:7])
        except ValueError:
            logger.warning(f"Inccorect NORAD ID in chosen TLE file {filename}.")
            self.statusBar().showMessage("Incorrect NORAD ID in chosen TLE file")
            return

        logger.debug(f"TLE file {filename} is successfully processed.")
        return norad_id, line_1, line_2

    def _calculate_trace_dt_points(
        self, start_session: datetime, end_session: datetime
    ) -> list[datetime]:
        """Calculate datetime points to request azimuth and elevation for radar trace
        display.

        Args:
            start_session (datetime): start datetime to request data
            end_session (datetime): end datetime to request data

        Returns:
            list[datetime]: list with datetime points to request data
        """
        session_duration = int((end_session - start_session).total_seconds())
        trace_points_step = session_duration // self.radar_widget._TRACE_DISPLAY_SIZE
        trace_dt_points = [
            start_session + timedelta(seconds=seconds)
            for seconds in range(0, session_duration, trace_points_step)
        ]
        return trace_dt_points

    def _check_selected_satellite(self) -> bool:
        """Check if some satellite is selected.

        Returns:
            bool: True if selected, False if not
        """
        if self.satellite_info:
            return True
        self.statusBar().showMessage("Before this action you should choose satellite!")

    def _check_spacetrack_norad_id(self) -> bool:
        """Check if some NORAD ID is specified.

        Returns:
            bool: True if specified, False if not
        """
        if self.spacetrack_norad_id:
            return True
        self.statusBar().showMessage("Before add new TLE file specify NORAD ID")

    def _set_satellite_button_enable(self, norad_id: NoradID, enable: bool) -> None:
        """Set radio button for satellite selection is active or nonactive.

        Args:
            norad_id (int): satellite NORAD ID
            enable (bool):
                True: radio button is setuped as enable
                False: radio button is setuped as disable
        """
        if norad_id in self._satellites_buttons:
            self._satellites_buttons[norad_id].setEnabled(enable)

    def _clear_gui(self):
        """Clear all GUI to default."""
        self.trace_session_index = None
        self.spacetrack_norad_id = None
        self.satellite_info = None
        self.station_satellites.clear()
        self._waiting_counter = 0

        self.station_name_label.setText("None")
        self.longitude_label.setText("None")
        self.latitude_label.setText("None")
        self.altitude_label.setText("None")
        self.station_elevation_label.setText("None")

        self.norad_id_label.setText("None")
        self.tle_date_label.setText("None")
        self.azimuth_label.setText("None")
        self.elevation_label.setText("None")
        self.uplink_label.setText("None")
        self.downlink_label.setText("None")

        self.set_uplink_lineedit.setText("")
        self.set_downlink_lineedit.setText("")
        self.spacetrack_norad_id_lineedit.setText("")

        self.gui_update_station_available_satellites([])
        self.gui_update_sessions_info([])
        self.radar_widget.clear_satellite_data()
        logger.debug("GUI is successfully cleared.")

    def gui_update_selected_station_info(self) -> None:
        """Update ground station info (name, longitude, latitude, altitude and minimal
        elevation angle) on GUI.
        """
        self.station_name_label.setText(self.station_info.name)
        self.station_elevation_label.setText(
            str(round(degrees(self.station_info.elevation), 1))
        )
        self.longitude_label.setText(
            str(round(degrees(self.station_info.longitude), 4))
        )
        self.latitude_label.setText(str(round(degrees(self.station_info.latitude), 4)))
        self.altitude_label.setText(str(round(self.station_info.altitude, 1)))
        logger.debug(f"Ground station {self.station_info.name} info is updated.")

    def gui_update_selected_satellite_info(self) -> None:
        """Update selected satellite main info (NORAD ID, TLE date, carrier uplink and
        carrier downlink frequencies) on GUI.
        """
        self.norad_id_label.setText(str(self.satellite_info.norad_id))
        self.set_uplink_lineedit.setText(str(self.satellite_info.uplink))
        self.set_downlink_lineedit.setText(str(self.satellite_info.downlink))
        self.tle_date_label.setText(
            self.satellite_info.tle_dt.strftime(self._DATE_PATTERN)
        )
        logger.debug(f"Satellite {self.satellite_info.norad_id} info is updated.")

    def gui_update_dt(self, dt: datetime) -> None:
        """Update current datetime on the GUI.

        Args:
            dt (datetime): datetime to set at GUI
        """
        self.time_label.setText(dt.strftime(self._DT_PATTERN))

    def gui_update_comm_data(
        self,
        azimuth: Optional[float],
        elevation: Optional[float],
        uplink: Optional[float],
        downlink: Optional[float],
    ) -> None:
        """Update current communication data (azimuth, elevation, uplink and downlink)
        on GUI.

        Args:
            azimuth (float): azimuth to set on GUI
            elevation (float): elevation to set on GUI
            uplink (float): uplink frequency to set on GUI
            downlink (float): downlink frequency to set on GUI
        """
        if azimuth:
            azimuth = round(azimuth, 1)
            elevation = round(elevation, 1)
        self.azimuth_label.setText(str(azimuth))
        self.elevation_label.setText(str(elevation))

        if uplink:
            uplink = round(uplink)
        if downlink:
            downlink = round(downlink)
        self.uplink_label.setText(str(uplink))
        self.downlink_label.setText(str(downlink))
        logger.debug("Communication data on GUI are updated.")

    def gui_update_station_available_satellites(self, norad_ids: Iterable) -> None:
        """Fill scroll area with available satellites by radio buttons with available
        satellites NORAD ID.

        Args:
            norad_ids (list): list of available satellites NORAD IDs
        """
        self._init_available_satellites_widget()
        for norad_id in norad_ids:
            radio_button = QtWidgets.QRadioButton(str(norad_id))
            self._satellites_buttons[norad_id] = radio_button
            self._satellites_buttons_group.addButton(radio_button)
            self._satellites_layout.addWidget(radio_button)
        self._satellites_widget.setLayout(self._satellites_layout)
        self.orbisat_norad_ids_scroll_area.setWidget(self._satellites_widget)
        logger.debug("Radio buttons for available satellites are successfully created.")

    def gui_update_sessions_info(self, widgets: list[QtWidgets.QWidget]) -> None:
        """Fill scroll area with sessions info by available sessions and update info on
        GUI.
        """
        self._init_sessions_info_widget()
        for widget in widgets:
            if isinstance(widget, QtWidgets.QWidget):
                if isinstance(widget, QtWidgets.QRadioButton):
                    self._sessions_buttons_group.addButton(widget)
                self._sessions_layout.addWidget(widget)
            elif isinstance(widget, QtWidgets.QSpacerItem):
                self._sessions_layout.addItem(widget)
            else:
                logger.warning(
                    f"Trying to add unexpected type '{type(widget)}' of QtWdigets to "
                    f"sessions_scroll_area."
                )
        self._sessions_widget.setLayout(self._sessions_layout)
        self.sessions_scroll_area.setWidget(self._sessions_widget)
        logger.debug("Sessions info filling is completed.")

    def waiting_info_updating_timer_slot(self) -> None:
        """Timer slot to visualize calculation process."""
        self._waiting_counter += 1
        self.statusBar().showMessage(f"Calculations{'.' * (self._waiting_counter % 3)}")

    def data_updating_timer_slot(self) -> None:
        """Timer slot to request and update communication data for selected
        satellite.
        """
        if self.station_info and self.satellite_info:
            try:
                comm_data = self.orbisat_client.get_data(
                    self.station_info.name,
                    self.satellite_info.norad_id,
                )
            except TCPServerResponseError:
                self.statusBar().showMessage("Error during get data request")
                return
            except TCPServerUnexpectedResponseError:
                self.statusBar().showMessage("Unexpected result of get data request")
                return

            self.radar_widget.update_satellite_position(
                comm_data["azimuth"],
                comm_data["elevation"],
            )
            self.gui_update_dt(datetime.fromisoformat(comm_data["dt"]))
            self.gui_update_comm_data(
                comm_data["azimuth"],
                comm_data["elevation"],
                comm_data["uplink"],
                comm_data["downlink"],
            )
            logger.debug(
                f"Communication data for satellite {self.satellite_info.norad_id} "
                f"are got."
            )
        else:
            self.gui_update_dt(datetime.utcnow())
            logger.debug("Satellite to request data to update data isn't selected.")

    def trace_updating_timer_slot(self) -> None:
        """Timer slot to request ahead azimuth and elevation for selected satellite to
        radar display.
        """
        if self.satellite_info:
            try:
                point = self.orbisat_client.get_azimuth_elevation(
                    self.station_info.name,
                    self.satellite_info.norad_id,
                    datetime.utcnow()
                    + timedelta(seconds=self.radar_widget._TRACE_DISPLAY_DURATION),
                )
            except TCPServerResponseError:
                self.statusBar().showMessage(
                    "Error during get_azimuth_elevation request"
                )
                return
            except TCPServerUnexpectedResponseError:
                self.statusBar().showMessage(
                    "Unexpected result of get_azimuth_elevation request"
                )
                return

            self.radar_widget.add_cur_trace_data(
                [point["azimuth"]],
                [point["elevation"]],
            )
            logger.debug(
                f"Data to update trace for satellite {self.satellite_info.norad_id}"
                f" are got."
            )
        else:
            logger.debug(f"Satellite to request data to update trace isn't selected.")

    def save_spacetrack_norad_id_lineedit_slot(self) -> None:
        """Slot to save new NORAD ID from lineedit at GUI."""
        try:
            norad_id = self.spacetrack_norad_id_lineedit.text()

            if len(norad_id) != 5:
                raise ValueError

            self.spacetrack_norad_id = int(norad_id)
            logger.info(
                f"New NORAD ID {self.spacetrack_norad_id} is saved for spacetrack TLE"
                f" downloading request."
            )
        except ValueError:
            self.spacetrack_norad_id_lineedit.setText(
                "NORAD ID must consist of 5 digits!"
            )

    def save_new_uplink_freq_lineedit_slot(self) -> None:
        """Slot to save uplink frequency from lineedit at GUI."""
        if self._check_selected_satellite():
            try:
                self.satellite_info.new_uplink = int(self.set_uplink_lineedit.text())
                logger.info(
                    f"New uplink frequency {self.satellite_info.new_uplink} Hz for "
                    f"{self.satellite_info.norad_id} satellite is saved."
                )
            except ValueError:
                self.set_uplink_lineedit.setText("Frequency must be integer!")

    def save_new_downlink_freq_lineedit_slot(self) -> None:
        """Slot to save downlink frequency from lineedit at GUI."""
        if self._check_selected_satellite():
            try:
                self.satellite_info.new_downlink = int(
                    self.set_downlink_lineedit.text()
                )
                logger.info(
                    f"New downlink frequency {self.satellite_info.new_downlink} Hz for "
                    f"{self.satellite_info.norad_id} satellite is saved."
                )
            except ValueError:
                self.set_downlink_lineedit.setText("Frequency must be integer!")

    def change_selected_satellite_rb_slot(self, button: QtWidgets.QRadioButton) -> None:
        """Radio button slot to change selected satellite.

        Args:
            button (QRadioButton): pressed radio button instance with selected satellite
        """
        self.satellite_info = self.station_satellites[int(button.text())]

        self.radar_widget.clear_satellite_data()
        self.gui_update_selected_satellite_info()
        self.update_sessions_info_by_worker()
        self.update_init_trace_by_worker()
        logger.info(f"User was switched to {self.satellite_info.norad_id} satellite.")

    def change_trace_rb_slot(self, button: QtWidgets.QRadioButton) -> None:
        """Radio button slot to change selected session trace.

        Args:
            button (QRadioButton): pressed radio button instance with selected trace
        """
        self.radar_widget.clear_trace()
        session_index = int(button.text()[0])

        start_session_dt_str, end_session_dt_str = button.text()[3:].split(" - ")
        start_session_dt = datetime.fromisoformat(start_session_dt_str)
        end_session_dt = datetime.fromisoformat(end_session_dt_str)
        self.update_selected_trace_by_worker(
            start_session_dt, end_session_dt, session_index
        )
        logger.debug(f"{session_index} session is chosen for radar displaying.")

    def set_new_frequencies_button_slot(self) -> None:
        """Button slot to set new frequencies and recalculate communication data by
        worker.
        """
        if self._check_selected_satellite():
            if (
                self.satellite_info.uplink == self.satellite_info.new_uplink
                and self.satellite_info.downlink == self.satellite_info.new_downlink
            ):
                self.statusBar().showMessage("Noone frequency wasn't changed.")
            else:
                self.recalculate_new_frequencies_by_worker()

    def choose_tle_file_button_slot(self) -> None:
        """Button slot to choose TLE file by file system. Base directory for file system
        is set in the _TLE_PATH class variable.
        """
        dlg = QtWidgets.QFileDialog()
        dlg.setFileMode(QtWidgets.QFileDialog.ExistingFile)
        dlg.setNameFilter(self.tr("Text files (*.tle *.txt *.3le)"))
        dlg.setViewMode(QtWidgets.QFileDialog.Detail)
        dlg.setDirectory(self._TLE_PATH)
        if dlg.exec_():
            filename = dlg.selectedFiles()[0]
            logger.info(f"File {filename} is chosen as TLE file.")

            new_norad_id, line_1, line_2 = self._process_tle_file(filename)
            self.add_new_satellite_by_worker(new_norad_id, line_1, line_2)

    def tle_spacetrack_button_slot(self) -> None:
        """Download (update) TLE file by spacetrack API slot."""
        if self._check_spacetrack_norad_id():
            logger.info(
                f"Command to spacetrack to download TLE file for "
                f"{self.spacetrack_norad_id} satellite is sent"
            )
            self.add_new_satellite_by_worker(self.spacetrack_norad_id)

    def clear_radar_trace_button_slot(self) -> None:
        """Button slot to clear selected trace."""
        if not self._check_selected_satellite():
            return

        self.trace_session_index = None
        self.radar_widget.clear_trace()
        logger.debug("Selected trace is cleared.")

    def show_next_radar_trace_button_slot(self) -> None:
        """Button slot to display next session."""
        if not self._check_selected_satellite():
            return

        if not self.trace_session_index:
            self.trace_session_index = 1
        elif self.trace_session_index == len(self._sessions_buttons_group.buttons()):
            self.trace_session_index = 1
        else:
            self.trace_session_index += 1
        self._sessions_buttons_group.buttons()[self.trace_session_index - 1].click()

    def show_prev_radar_trace_button_slot(self) -> None:
        """Button slot to display prevouse session."""
        if not self._check_selected_satellite():
            return

        if not self.trace_session_index:
            self.trace_session_index = len(self._sessions_buttons_group.buttons())
        elif self.trace_session_index == 1:
            self.trace_session_index = len(self._sessions_buttons_group.buttons())
        else:
            self.trace_session_index -= 1
        self._sessions_buttons_group.buttons()[self.trace_session_index - 1].click()

    def predict_button_slot(self) -> None:
        """Button slot to run prediction for selected satellite."""
        if not self._check_selected_satellite():
            return
        self.predict_satellite_by_worker(self.satellite_info.norad_id)

    def clear_station_data_menu_button_slot(self) -> None:
        """Menu button slot to delete all data for selected ground station from OrbiSat
        Server and clear GUI.
        """
        reply = QtWidgets.QMessageBox.question(
            self,
            "Warning",
            "Are you want to delete all selected ground station data from "
            "OrbiSat Server?",
        )

        if reply == QtWidgets.QMessageBox.Yes:
            try:
                self.orbisat_client.clear_ground_station_data(self.station_info.name)
            except TCPServerResponseError:
                self.statusBar().showMessage("Error during clear station data request")
                return
            except TCPServerUnexpectedResponseError:
                self.statusBar().showMessage(
                    "Unexpected result of clear station data request"
                )
                return
            self._clear_gui()
            self.update_selected_station_data()
            self.statusBar().showMessage(
                f"All data for {self.station_info.name} station are deleted"
            )
            logger.info(f"All data for {self.station_info.name} station are deleted.")

    def change_station_menu_button_slot(self) -> None:
        """Menu button slot to change selected ground station by dialog."""
        new_station_info = self.choose_station_by_dialog()
        if new_station_info:
            if new_station_info == self.station_info:
                self.statusBar().showMessage(
                    f"Same station '{self.station_info.name}' was chosen"
                )
            else:
                self.statusBar().showMessage(
                    f"Station '{new_station_info.name}' was chosen"
                )
                self.station_info = new_station_info
                logger.info(
                    f"Ground station {self.station_info.name} is chosen by menu button."
                )
                self._clear_gui()
                self.update_selected_station_data()
        else:
            self.statusBar().showMessage(f"New station isn't chosen")

    def update_init_trace_worker_slot(
        self,
        data: dict[
            Literal["azimuths", "elevations", "satellite"],
            Union[list, int],
        ],
    ) -> None:
        """Slot to finish initial radar trace display after requesting data by worker.

        Args:
            data[dict]: dict with 3 keys:
                "azimuths": list with azimuths for initial current radar trace
                "elevations": list with elevation for initial current radar trace
                "satellite": satellite NORAD ID
        """
        self.radar_widget.add_cur_trace_data(data["azimuths"], data["elevations"])
        self.waiting_info_timer.stop()
        self.statusBar().showMessage(
            f"Precalculations for satellite {data['satellite']} is finished"
        )
        logger.debug(f"Initial trace for {data['satellite']} is got.")
        self.trace_updating_timer.start()

    def update_selected_trace_worker_slot(
        self,
        data: dict[
            Literal["azimuths", "elevations", "session_index", "satellite"],
            Union[list, int],
        ],
    ) -> None:
        """Slot to finish selected radar trace display after requesting data by worker.

        Args:
            data[dict]: dict with 4 keys:
                "azimuths": list with azimuths for selected radar trace
                "elevations": list with elevation for selected radar trace
                "session_index": index of selected session
                "satellite": satellite NORAD ID
        """
        self.trace_session_index = data["session_index"]
        self.radar_widget.update_selected_trace(data["azimuths"], data["elevations"])
        self.waiting_info_timer.stop()
        logger.debug(
            f"Trace {self.trace_session_index} for {data['satellite']} is displayed."
        )
        self.statusBar().showMessage(
            f"Trace for session {self.trace_session_index} for satellite "
            f"{data['satellite']} is displayed"
        )

    def create_sessions_info_wigets_worker_slot(
        self, data: dict[Literal["sessions"], dict]
    ) -> None:
        """Slot to fill scroll area with sessions info after request sessions paramaters
        by worker.

        Args:
            data[dict]: dict with 1 key:
                "sessions": dict with sessions parameters
        """
        sessions_widgets = []
        for index, (_, session) in enumerate(sorted(data["sessions"].items()), start=1):
            session_radio_button = QtWidgets.QRadioButton(
                f"{index}) {session['start_session_dt']} - {session['end_session_dt']}"
            )
            sessions_widgets.append(session_radio_button)

            start_session_info = SessionInfo(
                session["start_session_dt"],
                session["start_azimuth"],
                session["start_elevation"],
                session["start_sun_azimuth"],
                session["start_sun_elevation"],
            )
            sessions_widgets.append(start_session_info)

            max_elevation_session_info = SessionInfo(
                session["max_session_dt"],
                session["max_azimuth"],
                session["max_elevation"],
                session["max_sun_azimuth"],
                session["max_sun_elevation"],
            )
            sessions_widgets.append(max_elevation_session_info)

            end_session_info = SessionInfo(
                session["end_session_dt"],
                session["end_azimuth"],
                session["end_elevation"],
                session["end_sun_azimuth"],
                session["end_sun_elevation"],
            )
            sessions_widgets.append(end_session_info)

            sessions_spacer = QtWidgets.QSpacerItem(
                50, 10, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed
            )
            sessions_widgets.append(sessions_spacer)
        logger.debug("Widgets for sessions scroll area are created.")
        self.gui_update_sessions_info(sessions_widgets)
        self.waiting_info_timer.stop()

    def prediction_completed_worker_slot(
        self, data: dict[Literal["norad_id"], int]
    ) -> None:
        """Slot to finish prediction after prediction by worker.

        Args:
            data[dict]: dict with 1 key
                "norad_id" satellite NORAD ID
        """
        logger.info(f"Prediction for satellite {data['norad_id']} was completed.")
        self._set_satellite_button_enable(data["norad_id"], True)
        self.waiting_info_timer.stop()
        self.statusBar().showMessage(
            f"Prediction for satellite {data['norad_id']} is completed"
        )
        if self.satellite_info and data["norad_id"] == self.satellite_info.norad_id:
            self._satellites_buttons[data["norad_id"]].click()

    def frequencies_recalculated_worker_slot(self) -> None:
        """Slot to finish frequencies recalculation after recalculation by worker."""
        self.satellite_info.uplink = self.satellite_info.new_uplink
        self.satellite_info.downlink = self.satellite_info.new_downlink
        self.waiting_info_timer.stop()
        self.statusBar().showMessage(f"Frequencies recalculation is finished")
        logger.info(
            f"Communication parameters for {self.satellite_info.norad_id} satellite "
            f"with new frequencies were recalculated."
        )

    def tle_updated_worker_slot(self, data: dict[Literal["norad_id"], int]) -> None:
        """Slot to finish TLE updating after handling TLE file by worker.

        Args:
            data[dict]: dict with 1 key:
                "norad_id": satellite NORAD ID
        """
        self.update_selected_station_available_satellites()
        self.predict_satellite_by_worker(data["norad_id"])
        self.waiting_info_timer.stop()
        logger.info(f"{data['norad_id']} satellite is added to GUI.")

    def show_raised_error_worker_slot(
        self, data: dict[Literal["request_name"], str]
    ) -> None:
        """Slot to show error that occurred as a result of the worker's work.

        Args:
            data (dict): dict with 1 key
                "request_name": the request during which error occurred
        """
        self.waiting_info_timer.stop()
        self.statusBar().showMessage(
            f"Error was occurred during {data['request_name']}"
        )

    def update_init_trace_by_worker(self) -> None:
        """Request data for initial current radar trace by worker."""
        self.waiting_info_timer.start()
        trace_dt_points = self._calculate_trace_dt_points(
            datetime.utcnow(),
            datetime.utcnow()
            + timedelta(seconds=self.radar_widget._TRACE_DISPLAY_DURATION),
        )
        worker = GetTraceDataWorker(
            self.station_info.name,
            self.satellite_info.norad_id,
            trace_dt_points,
            0,
        )
        worker.signals.trace_data_got.connect(self.update_init_trace_worker_slot)
        worker.signals.error_raised.connect(self.show_raised_error_worker_slot)
        self._threadpool.start(worker)
        logger.debug("Worker to request data for initial trace is run.")

    def update_selected_trace_by_worker(
        self,
        start_session_dt: datetime,
        end_session_dt: datetime,
        trace_session_index: int,
    ) -> None:
        """Request data for selected radar trace by worker.

        Args:
            start_session_dt (datetime): start datetime of session
            end_session_dt (datetime): stop datetime of session
            trace_session_index (int): index of selected session
        """
        self.waiting_info_timer.start()
        trace_dt_points = self._calculate_trace_dt_points(
            start_session_dt, end_session_dt
        )

        worker = GetTraceDataWorker(
            self.station_info.name,
            self.satellite_info.norad_id,
            trace_dt_points,
            trace_session_index,
        )

        worker.signals.trace_data_got.connect(self.update_selected_trace_worker_slot)
        worker.signals.error_raised.connect(self.show_raised_error_worker_slot)
        self._threadpool.start(worker)
        logger.debug(f"Worker to request data for {trace_session_index} trace is run.")

    def update_sessions_info_by_worker(self) -> None:
        """Request available sessions parameters for selected satellite by worker."""
        self.waiting_info_timer.start()

        worker = GetSessionsParametersWorker(
            self.station_info.name,
            self.satellite_info.norad_id,
        )
        worker.signals.sessions_parameters_got.connect(
            self.create_sessions_info_wigets_worker_slot
        )
        worker.signals.error_raised.connect(self.show_raised_error_worker_slot)
        self._threadpool.start(worker)
        logger.debug("Worker to request data for sessions info is run.")

    def predict_satellite_by_worker(self, norad_id: NoradID) -> None:
        """Predict satellite position and available communcation parameters for one day
        by worker.

        Args:
            norad_id (int): satellite NORAD ID
        """
        self.waiting_info_timer.start()
        self._set_satellite_button_enable(norad_id, False)
        worker = PredictSatelliteWorker(self.station_info.name, norad_id)
        worker.signals.prediction_completed.connect(
            self.prediction_completed_worker_slot
        )
        worker.signals.error_raised.connect(self.show_raised_error_worker_slot)
        self._threadpool.start(worker)
        logger.debug(f"Worker to predict satellite {norad_id} is run.")

    def recalculate_new_frequencies_by_worker(self) -> None:
        """Recalculate communication data with new frequencies by worker."""
        self.waiting_info_timer.start()
        worker = ChangeFrequenciesWorker(
            self.station_info.name,
            self.satellite_info.norad_id,
            self.satellite_info.new_uplink,
            self.satellite_info.new_downlink,
        )
        worker.signals.frequencies_changed.connect(
            self.frequencies_recalculated_worker_slot
        )
        worker.signals.error_raised.connect(self.show_raised_error_worker_slot)
        self._threadpool.start(worker)
        logger.debug("Worker to change frequencies is run.")

    def add_new_satellite_by_worker(
        self, norad_id: NoradID, tle_line_1: str = None, tle_line_2: str = None
    ) -> None:
        """Add new satellite to OrbiSat TCP server and on GUI by worker.

        Args:
            norad_id(int): satellite NORAD ID
            tle_line_1(str): first line of the TLE file
            tle_line_2(str): seconds line of the TLE file
        """
        self.waiting_info_timer.start()
        self._set_satellite_button_enable(norad_id, False)
        if tle_line_1:
            worker = SetupSatelliteStrTLE(
                self.station_info.name,
                norad_id,
                tle_line_1,
                tle_line_2,
            )
        else:
            worker = SetupSatelliteSpacetrackTLE(
                self.station_info.name,
                norad_id,
            )
        worker.signals.tle_updated.connect(self.tle_updated_worker_slot)
        worker.signals.error_raised.connect(self.show_raised_error_worker_slot)
        self._threadpool.start(worker)
        logger.debug(f"Worker to setup TLE for satellite {norad_id} is run.")

    def choose_station_by_dialog(self) -> Optional[StationInfo]:
        """Choose setuped ground station from OrbiSat Server and setup new ground
        stations to OrbiSat Server by Dialog.

        Returns:
            StationInfo: dataclass with parameters of selected ground station if station
                is chosen, else None
        """
        stations_dialog = ChooseStationDialog(self.orbisat_client)
        if stations_dialog.exec():
            selected_station_info = stations_dialog.get_selected_station_info()
            logger.info(f"{selected_station_info.name} station is chosen for GUI.")
        else:
            selected_station_info = None
        stations_dialog.deleteLater()
        return selected_station_info

    def get_station_available_satellites(
        self, station_name: StationName
    ) -> dict[NoradID, SatelliteInfo]:
        """Request setuped satellites from Oribtron Server for ground station.

        Args:
            station_name (str): name of ground station

        Returns:
            dict[int, SatelliteInfo]: dict with satellite NORAD ID as keys and
                satellites parameters in dataclasses as values
        """
        try:
            satellites = self.orbisat_client.get_station_satellites_info(station_name)
            satellites_info = {}
            for norad_id, satellite_info_dict in satellites.items():
                satellite_info = SatelliteInfo(
                    norad_id=norad_id,
                    tle_dt=datetime.fromisoformat(satellite_info_dict["tle_dt"]),
                    uplink=satellite_info_dict["uplink"],
                    downlink=satellite_info_dict["downlink"],
                )
                satellites_info[norad_id] = satellite_info

            logger.info(
                f"{len(satellites)} is got for {self.station_info.name} ground station."
            )
            return satellites_info
        except TCPServerResponseError:
            self.statusBar().showMessage(
                "Error during initial station satellites info request"
            )
            return
        except TCPServerUnexpectedResponseError:
            self.statusBar().showMessage(
                "Unexpected result of initial station satellites info request"
            )
            return

    def update_selected_station_available_satellites(self) -> None:
        """Get setuped satellites from OrbiSat Server for selected ground station and
        update list of available satellites by radio buttons in the scroll area.
        """
        self.station_satellites = self.get_station_available_satellites(
            self.station_info.name
        )
        self.gui_update_station_available_satellites(self.station_satellites.keys())

    def update_selected_station_data(self) -> None:
        """Update GUI data for selected ground station."""
        if self.station_info:
            self.gui_update_selected_station_info()
            self.update_selected_station_available_satellites()

    def closeEvent(self, a0: QCloseEvent) -> None:
        """Slot to close GUI window."""
        super().closeEvent(a0)
        logger.info("GUI was closed.")
