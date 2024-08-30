import logging
from datetime import datetime, timedelta
from typing import Literal, Optional, Union

from PyQt5 import QtCore, QtWidgets, uic
from PyQt5.QtGui import QCloseEvent

from ..tcp.orbitron_tcp_client import OrbitronTcpClient
from .gui_services.workers import (
    ChangeFrequenciesWorker,
    GetSessionsParametersWorker,
    GetTraceDataWorker,
)
from .ui.MainWindowShort import Ui_MainWindow
from .widgets.session_info import SessionInfo

logger = logging.getLogger(__name__)


class MainWindow(Ui_MainWindow, QtWidgets.QMainWindow):
    """Class used to represent GUI for interaction with Orbitron TCP Server."""

    _DT_PATTERN = "%H:%M:%S %d.%m.%Y"
    _DATE_PATTERN = "%d.%m.%Y"
    _DATA_UPDATING_PERIOD = 1  # s
    _WAITING_INFO_SHOW_PERIOD = 0.25  # s

    def __init__(
        self,
        orbitron_client: OrbitronTcpClient,
        station_name: str,
        norad_id: int,
        *args,
        **kwargs,
    ):
        super(MainWindow, self).__init__(*args, **kwargs)
        uic.loadUi("new_orbitron/orbitron_gui/ui/main_window_short.ui", self)

        self.station_name = station_name
        self.norad_id = norad_id
        self.orbitron_client = orbitron_client

        self.setWindowTitle("Orbitron")
        self.setFixedSize(775, 430)

        self._threadpool = QtCore.QThreadPool()

        self._waiting_counter = 0

        self._init_line_edits()
        self._init_timers()
        self._init_buttons()

        self._data_updating_timer.start()
        self._waiting_info_timer.start()

        self.update_main_info_gui()
        self.update_sessions_info()
        self.update_init_trace()

    def _init_line_edits(self) -> None:
        self.set_uplink_lineedit.editingFinished.connect(self.save_new_uplink_freq_slot)
        self.set_downlink_lineedit.editingFinished.connect(
            self.save_new_downlink_freq_slot
        )
        logger.debug("All lines edits are successfully initialized.")

    def _init_timers(self) -> None:
        self._data_updating_timer = QtCore.QTimer()
        self._data_updating_timer.setInterval(self._DATA_UPDATING_PERIOD * 1000)
        self._data_updating_timer.timeout.connect(self.data_updating_timer_slot)

        self._trace_updating_timer = QtCore.QTimer()
        self._trace_updating_timer.setInterval(
            self.radar_widget._TIME_TRACE_UPDATING * 1000
        )
        self._trace_updating_timer.timeout.connect(self.trace_updating_timer_slot)

        self._waiting_info_timer = QtCore.QTimer()
        self._waiting_info_timer.setInterval(int(self._WAITING_INFO_SHOW_PERIOD * 1000))
        self._waiting_info_timer.timeout.connect(self.waiting_info_updating_timer_slot)
        logger.debug("All timers are successfully initialized.")

    def _init_buttons(self) -> None:
        self.set_new_freqs_button.pressed.connect(self.set_new_frequencies_button_slot)
        logger.debug("All buttons are successfully initialized.")

    def _init_sessions_info_widget(self):
        self._sessions_widget = QtWidgets.QWidget()
        self._sessions_layout = QtWidgets.QVBoxLayout()
        self._sessions_layout.setSpacing(0)
        self._sessions_layout.setContentsMargins(0, 0, 0, 0)
        self._sessions_layout.setAlignment(QtCore.Qt.AlignTop)

        logger.debug("Sessions widget successfully is initialized.")

    def _get_satellite_info(self):
        satellites_info = self.orbitron_client.get_station_satellites_info(
            self.station_name
        )
        return satellites_info[self.norad_id]

    def _update_data_gui(
        self,
        azimuth: Optional[float],
        elevation: Optional[float],
        uplink: Optional[float],
        downlink: Optional[float],
        dt: datetime,
    ) -> None:
        """Set communication data to GUI."""
        self.time_label.setText(dt.strftime(self._DT_PATTERN))

        if azimuth:
            azimuth = round(azimuth, 1)
            elevation = round(elevation, 1)
        self.azimuth_label.setText(str(azimuth))
        self.eleavtion_label.setText(str(elevation))

        if uplink:
            uplink = round(uplink)
        if downlink:
            downlink = round(downlink)
        self.uplink_label.setText(str(uplink))
        self.downlink_label.setText(str(downlink))
        logger.debug("Communication data at GUI were updated.")

    def _update_sessions_info_gui(self, widgets: list[QtWidgets.QWidget]):
        for widget in widgets:
            if isinstance(widget, QtWidgets.QWidget):
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

    def _update_init_trace_gui(
        self,
        data: dict[
            Literal["azimuths", "elevations", "session_index", "satellite"],
            Union[list, int],
        ],
    ) -> None:
        self.radar_widget.add_cur_trace_data(data["azimuths"], data["elevations"])
        self._waiting_info_timer.stop()
        self.statusBar().showMessage("Successed")
        self._trace_updating_timer.start()

    def save_new_uplink_freq_slot(self) -> None:
        try:
            self.new_uplink = int(self.set_uplink_lineedit.text())
            logger.info(f"New uplink frequency {self.new_uplink} Hz is saved.")
        except ValueError:
            self.set_uplink_lineedit.setText("Frequency must be integer!")

    def save_new_downlink_freq_slot(self) -> None:
        try:
            self.new_downlink = int(self.set_downlink_lineedit.text())
            logger.info(f"New downlink frequency {self.new_downlink} Hz is saved.")
        except ValueError:
            self.set_downlink_lineedit.setText("Frequency must be integer!")

    def set_new_frequencies_button_slot(self) -> None:
        if self.new_uplink == self.uplink and self.new_downlink == self.downlink:
            self.statusBar().showMessage("Noone frequency wasn't changed.")
        else:
            self._waiting_info_timer.start()
            worker = ChangeFrequenciesWorker(
                self.station_name,
                self.norad_id,
                self.new_uplink,
                self.new_downlink,
            )
            worker.signals.frequencies_changed.connect(self.frequencies_changed_slot)
            self._threadpool.start(worker)
            logger.debug("Worker to change frequencies is run.")

    def frequencies_changed_slot(self) -> None:
        self.uplink = self.new_uplink
        self.downlink = self.new_downlink
        self._waiting_info_timer.stop()
        self.statusBar().showMessage("Successed")
        logger.info("Communication parameters with new frequencies was recalculated.")

    def waiting_info_updating_timer_slot(self) -> None:
        self._waiting_counter += 1
        self.statusBar().showMessage(f"Calculations{'.' * (self._waiting_counter % 3)}")

    def data_updating_timer_slot(self) -> None:
        comm_data = self.orbitron_client.get_data(
            self.station_name,
            self.norad_id,
        )
        self.radar_widget.update_satellite_position(
            comm_data["azimuth"],
            comm_data["elevation"],
        )
        self._update_data_gui(
            comm_data["azimuth"],
            comm_data["elevation"],
            comm_data["uplink"],
            comm_data["downlink"],
            datetime.fromisoformat(comm_data["dt"]),
        )
        logger.debug(f"Communication data for satellite {self.norad_id} are got.")

    def trace_updating_timer_slot(self) -> None:
        point = self.orbitron_client.get_azimuth_elevation(
            self.station_name,
            self.norad_id,
            datetime.utcnow()
            + timedelta(seconds=self.radar_widget._TRACE_DISPLAY_DURATION),
        )
        self.radar_widget.add_cur_trace_data(
            [point["azimuth"]],
            [point["elevation"]],
        )
        logger.debug(
            f"Data to update satellite trace for satellite with NORAD ID "
            f"{self.norad_id} are got."
        )

    def create_sessions_info_wigets_slot(self, data: dict[Literal["sessions"], dict]):
        sessions_widgets = []
        for _, session in sorted(data["sessions"].items()):
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
        self._update_sessions_info_gui(sessions_widgets)

    def update_main_info_gui(self):
        satellite_info = self._get_satellite_info()
        self.uplink = satellite_info["uplink"]
        self.downlink = satellite_info["downlink"]
        self.new_uplink = self.uplink
        self.new_downlink = self.downlink

        tle_dt = datetime.fromisoformat(satellite_info["tle_dt"])

        self.station_name_label.setText(self.station_name)
        self.norad_id_label.setText(str(self.norad_id))
        self.tle_date_label.setText(tle_dt.strftime(self._DATE_PATTERN))
        self.set_uplink_lineedit.setText(str(satellite_info["uplink"]))
        self.set_downlink_lineedit.setText(str(satellite_info["downlink"]))

    def update_sessions_info(self) -> None:
        self._init_sessions_info_widget()

        worker = GetSessionsParametersWorker(
            self.station_name,
            self.norad_id,
        )
        worker.signals.sessions_parameters_got.connect(
            self.create_sessions_info_wigets_slot
        )
        self._threadpool.start(worker)
        logger.debug("Worker to request data for sessions info is run.")

    def update_init_trace(self) -> None:
        trace_points_dts = [
            datetime.utcnow() + timedelta(seconds=seconds)
            for seconds in range(
                0,
                self.radar_widget._TRACE_DISPLAY_DURATION,
                self.radar_widget._TIME_TRACE_UPDATING,
            )
        ]
        worker = GetTraceDataWorker(
            self.station_name,
            self.norad_id,
            trace_points_dts,
            0,
        )
        worker.signals.trace_data_got.connect(self._update_init_trace_gui)
        self._threadpool.start(worker)
        logger.debug("Worker to request data for initial trace is run.")

    def closeEvent(self, a0: QCloseEvent) -> None:
        """Closed connection with Orbitron TCP server at close GUI window."""
        super().closeEvent(a0)
        logger.info("GUI was closed.")
