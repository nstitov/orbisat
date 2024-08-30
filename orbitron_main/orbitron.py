import csv
import logging
import logging.config
import os
import time
from datetime import datetime, timedelta
from typing import Literal, Optional, Union

from spacetrack import SpaceTrackClient

from ..exceptions.orbitron_exceptions import NewOrbitronDataError, NewOrbitronSetupError
from ..orbitron_services.communication import (
    CommParams,
    SatelliteStationComm,
    SessionParams,
)
from ..orbitron_services.ground_station import GroundStation
from ..orbitron_services.satellite import Satellite

logger = logging.getLogger(__name__)


NoradID = int
GroundStationName = str


class Orbitron:
    """A class used to represent Orbitron

    Attributes:
        stations (dict[str, GroundStation]): Dict of setuped ground stations into
            Orbitron with stations names as dict keys and instances of GroundStation as
            dict values
        satellites (dict[int, Satellite]): Dict of setuped satellites into Orbitron with
            satellites NORAD IDs as dict keys and instances of Satellite as dict values
        comms (dict[str, SatelliteStationComm]): Dict of setuped communications into
            Orbitron between satellite (instance of Satellite) and ground station
            (instance of GroundStation) with '{station name}_{norad_id}' as dict keys
            and instances of SatelliteStationComm as dict values

    Methods:
        setup_ground_station(longitude, latitude, altitude[, min_elevation, name]): Add
            ground station (instance of GroundStation class) into Orbitron. The default
            name of ground station is 'default'
        setup_satellite(norad_id[, uplink, downlink]): Add satellite (instance of
            Satellite class) into Orbitron
        setup_comm(station_name, norad_id): Add communication between satellite with NORAD ID
            and ground station by name (instance of SatelliteStationComm class) into
            Orbitron
        predict_comm(station_name, norad_id[, start_prediction, time_prediciton,
            step_prediction]): Predict communication data (azimuth, elevation, uplink
            and downlink frequencies) at each step for time_prediction duration from
            start_prediction datetime with step_prediction time step
        get_azimuth_elevation(station_name, norad_id): Get azimuth and elevation angles
            data at current UTC datetime
        get_grequencies(station_name, norad_id): Get uplink and downlink frequencies at
            current UTC datetime
        get_data(station_name, norad_id): Get azimuth and elevation angles, plink and
            downlink frequencies at current UTC datetime
        get_comm_sessions_params(station_name, norad_id): Get list of SessionParams
            instances with parameters of all possible communication sessions
        get_all_data(station_name, norad_id): Get all possible communication data
            (instances of CommParams) for communication
        update_tles(norad_ids): Update TLE files for all NORAD ID in list of norad_ids.
            The satellites with required NORAD ID must setuped into Orbitron
        __update_all_tles__(norad_ids, token, tle_data_folder): Update (download) TLE
            files for all NORAD IDs in norad_ids list
        __delete_all_tles__(tle_data_folder): Delete all TLE files in tle and .3le
            formats from required tle_data_folder

    Raises:
        NewOrbitronSetupError: If Orbitron hasn't setups for required satellite, ground
            station or communication
        NewOrbitronDataError: If communication for required satellite and ground
                station hasn't something data
    """

    def __init__(self):
        self.stations: dict[GroundStationName, GroundStation] = {}
        self.satellites: dict[GroundStationName, dict[NoradID, Satellite]] = {}
        self.comms: dict[GroundStationName, dict[NoradID, SatelliteStationComm]] = {}

    def _check_ground_station_setup(self, station_name: str) -> None:
        """Check ground station setup in Orbitron."""
        try:
            if station_name not in self.stations:
                raise NewOrbitronSetupError(
                    f"Trying setup satellite for '{station_name}' ground station which "
                    f"hasn't setup in Orbitron"
                )
        except NewOrbitronSetupError:
            logger.exception("Orbitron hasn't required setups.")
            raise

    def _check_satellite_setup_for_ground_station(
        self, station_name: str, norad_id: int
    ) -> None:
        """Check ground station setup and satellite setup for this ground station."""
        self._check_ground_station_setup(station_name)
        try:
            if norad_id not in self.satellites[station_name]:
                raise NewOrbitronSetupError(
                    f"Trying setup communication with satellite with NORAD ID "
                    f"{norad_id} which hasn't setup in Orbitron with '{station_name} "
                    f"ground station"
                )
        except NewOrbitronSetupError:
            logger.exception("Orbitron hasn't required setups.")
            raise

    def _check_comm_setup_for_satellite_with_ground_station(
        self, station_name: str, norad_id: int
    ) -> None:
        """Check ground station setup, satellite setup for this ground station and
        communication setup between them.
        """
        self._check_ground_station_setup(station_name)
        self._check_satellite_setup_for_ground_station(station_name, norad_id)
        try:
            if norad_id not in self.comms[station_name]:
                raise NewOrbitronSetupError(
                    f"Orbitron hasn't communication for satellite with NORAD ID "
                    f"{norad_id} with '{station_name}' ground station."
                )
        except NewOrbitronSetupError:
            logger.exception("Orbitron hasn't required setups.")
            raise

    def _check_comm_prediction_data(self, station_name: str, norad_id: int) -> None:
        """Check ground station setup, satellite setup for this ground station,
        communication setup between them and availability predicted data for them.
        """
        self._check_comm_setup_for_satellite_with_ground_station(station_name, norad_id)
        try:
            if not self.comms[station_name][norad_id].comm_data:
                raise NewOrbitronDataError(
                    f"Orbitron hasn't predicted data for communication between "
                    f"satellite with NORAD ID {norad_id} and '{station_name}' ground "
                    f"station."
                )
        except NewOrbitronDataError:
            logger.exception("Orbitron data error.")

    def setup_ground_station(
        self,
        longitude: float,
        latitude: float,
        altitude: float,
        min_elevation: Union[float, int] = 0,
        station_name: str = "default",
    ) -> None:
        """Setup ground station to Orbitron.

        Args:
            longitude (float): Longitude of ground station, [deg]
            latitude (float): Latitude of ground station, [deg]
            altitude (float): Altitude of ground station, [m]
            min_elevation (float | int): Minimal elevation angle between satellite and
                ground station for mutual visibility, [deg]
            name (str): Ground station name used to define communication between
                satellite and ground station
                (default is 'default')

        Returns:
        """
        self.stations[station_name] = GroundStation(
            (longitude, latitude, altitude), min_elevation, station_name
        )
        self.satellites[station_name] = {}
        self.comms[station_name] = {}
        logger.info(
            f"'{station_name}' ground station {longitude=} deg, {latitude=} deg and "
            f"{altitude=} m is defined."
        )

    def setup_satellite(
        self,
        station_name: str,
        norad_id: int,
        uplink: Union[int, float] = None,
        downlink: Union[int, float] = None,
    ) -> None:
        """Setup satellite for ground station to Orbitron by NORAD ID.

        Args:
            station_name (str): Name of ground station setuped into Orbitron
            norad_id (int): Satellite NORAD ID
            uplink (int | float, optional): An uplink frequency to send command to
                satellite, [Hz]
                (default is None)
            downlink (int | float, optional): An downlink frequency to get command from
                satellite, [Hz]
                (default is None)

        Raises:
            NewOrbitronSetupError: If Orbitron hasn't setup for required ground station

        Returns:
        """
        self._check_ground_station_setup(station_name)
        self.satellites[station_name][norad_id] = Satellite(norad_id, uplink, downlink)
        logger.info(
            f"Satellite with NORAD ID {norad_id} is defined for '{station_name}' "
            f"ground station."
        )

    def setup_comm(self, station_name: str, norad_id: int) -> None:
        """Setup communication with required satellite for required ground station which
        have setup.

        Args:
            station_name (str): Name of ground station setuped into Orbitron
            norad_id (int): NORAD ID setuped into Orbitron satellite for ground station

        Raises:
            NewOrbitronSetupError: If Orbitron hasn't setups for required ground station
                or satellite

        Returns:
        """
        self._check_satellite_setup_for_ground_station(station_name, norad_id)
        self.comms[station_name][norad_id] = SatelliteStationComm(
            self.satellites[station_name][norad_id], self.stations[station_name]
        )
        logger.info(
            f"Communication with satellite with NORAD ID {norad_id} for "
            f"'{station_name}' ground station is defined."
        )

    def setup_new_frequencies(
        self,
        station_name: str,
        norad_id: int,
        uplink: Union[int, float],
        downlink: Union[int, float],
    ) -> None:
        """Setup new uplink and downlink frequencies for satellite for required ground
        station.

        Args:
            station_name (str): Name of ground station setuped into Orbitron
            norad_id (int): NORAD ID setuped into Orbitron satellite for ground station
            uplink (int | float): An uplink frequency to send command to
                satellite, [Hz]
            downlink (int | float): An downlink frequency to get command from
                satellite, [Hz]

        Returns:
        """
        self._check_satellite_setup_for_ground_station(station_name, norad_id)
        self.satellites[station_name][norad_id].uplink_freq = uplink
        self.satellites[station_name][norad_id].downlink_freq = downlink
        logger.info(
            f"Uplink and downlink frequencies for satellite with NORAD ID {norad_id} "
            f"for '{station_name}' ground station are setuped at {uplink} Hz and "
            f"{downlink} Hz."
        )
        self.comms[station_name][norad_id].recalculate_uplink_downlink(
            datetime.utcnow() - timedelta(seconds=1)
        )
        logger.info(
            f"Frequencies for satellite with NORAD ID {norad_id} for '{station_name}' "
            f"ground station were recalculated for the rest predicted data."
        )

    def setup_new_tle_by_str(
        self, station_name: str, norad_id: int, tle_str: str
    ) -> None:
        """Setup new TLE data by string format for required satellite at required
        ground station.

        Args:
            station_name (str): Name of ground station setuped into Orbitron
            norad_id (int): NORAD ID setuped into Orbitron satellite for ground station
            tle (str): TLE in string format, i.e. two string separated by \n.

        Returns:
        """
        self._check_satellite_setup_for_ground_station(station_name, norad_id)
        self.satellites[station_name][norad_id].setup_tle_by_str(tle_str)

    def setup_new_tle_by_file(
        self,
        station_name: str,
        norad_id: int,
        tle_file_name: str,
        default_folder: bool = True,
    ) -> None:
        """Setup new TLE data by TLE file for required satellite at required ground
        station.

        Args:
            station_name (str): Name of ground station setuped into Orbitron
            norad_id (int): NORAD ID setuped into Orbitron satellite for ground station
            file_name (str): File name in default tle folder or full path of TLE file
            default_folder (bool): flag of location TLE file (default folder or not)
                (default is True)

        Returns:
        """
        self._check_satellite_setup_for_ground_station(station_name, norad_id)
        self.satellites[station_name][norad_id].setup_tle_by_file(
            tle_file_name, default_folder=default_folder
        )

    def setup_new_tle_by_spacetrack(self, station_name: str, norad_id: int) -> None:
        """Setup new TLE data by SpaceTrackAPI by satellite NORAD ID for required
        satellite at required ground station.

        Args:
            station_name (str): Name of ground station setuped into Orbitron
            norad_id (int): NORAD ID setuped into Orbitron satellite for ground station

        Returns:
        """
        self._check_satellite_setup_for_ground_station(station_name, norad_id)
        self.satellites[station_name][norad_id].setup_tle_by_spacetrack()

    def update_tles_by_spacetrack(
        self, station_name: str, norad_ids: list[int]
    ) -> None:
        """Updates TLE files for required setuped satellites for required ground station
        by SpaceTrack API.

        Args:
            station_name (str): Name of ground station setuped into Orbitron
            norad_ids (list[int]): NORAD IDs for satellites to update TLE files

        Returns:
        """
        for norad_id in norad_ids:
            if norad_id in self.satellites[station_name]:
                logger.info(
                    f"Request to update TLE file for satellite with NORAD ID "
                    f"{norad_id} for '{station_name}' ground station was successfully "
                    f"sent."
                )
                self.satellites[station_name][norad_id].update_tle_by_spacetrack()
            else:
                logger.warning(
                    f"Orbitron hasn't setup for satellite with NORAD ID {norad_id} for "
                    f"'{station_name}' ground station. Request to update TLE file "
                    f"wasn't sent."
                )

    def predict_comm(
        self,
        station_name: str,
        norad_id: int,
        start_prediction: Optional[datetime] = None,
        time_prediction: int = 86400,
        step_prediction: Union[int, float] = 1,
    ) -> None:
        """Predict communication with required satellite for required ground station for
        required start time and duration with required time step.

        Args:
            norad_id (int): Satellite NORAD ID
            station_name (str): Name of ground station setuped into Orbitron
            start_prediction (datetime): Datetime for start communication prediction. If
                start_prediction is None, then will be used current UTC datetime
                (default is None)
            time_prediction (int): Required prediction duration, [s]
                (default is 1d = 86400 s)
            step_prediction (int | float): Prediction time step, [s]
                (default is 1 s)

        Raises:
            NewOrbitronSetupError: If Orbitron hasn't communication setup for required
                satellite and ground station

        Returns:
        """
        if not start_prediction:
            start_prediction = datetime.utcnow()

        start_prediction = start_prediction.replace(microsecond=0)

        self._check_comm_setup_for_satellite_with_ground_station(station_name, norad_id)
        self.satellites[station_name][norad_id].predict_cm(
            start_prediction, time_prediction, step_prediction
        )
        self.comms[station_name][norad_id].calculate_comm_for_predicted_period()
        logger.info(
            f"Communication prediction for satellite with NORAD ID {norad_id} "
            f"with '{station_name}' ground station started from "
            f"{start_prediction.isoformat()} for {time_prediction} seconds with "
            f"{step_prediction} second(s) step was completed."
        )

    def get_azimuth_elevation(
        self, station_name: str, norad_id: int, dt: Optional[datetime] = None
    ) -> list[Union[datetime, Optional[float]]]:
        """Get azimuth and elevation angles values for required communication at
        required datetime.

        Args:
            norad_id (int): Satellite NORAD ID
            station_name (str): Name of ground station setuped into Orbitron
            dt (datetime): Required datetime to get azimuth and elevation data. If dt is
                None, then will be used current UTC datetime
                (default is None)

        Raises:
            NewOrbitronSetupError: If Orbitron hasn't communication setup for required
                satellite and ground station
            NewOrbitronDataError: If communication for required satellite and ground
                station hasn't prediction

        Returns:
            list[str, float | None, float | None]: datetime, azimuth if defined for
            current datetime else None and elevation if defined for current datetime
            else None
        """
        self._check_comm_prediction_data(station_name, norad_id)

        if dt is None:
            dt = datetime.utcnow()

        dt = dt.replace(microsecond=0)
        try:
            point = self.comms[station_name][norad_id].comm_data[dt]
            logger.info(
                f"Azimuth and elevation for communication between satellite with NORAD "
                f"ID {norad_id} and '{station_name}' ground station at "
                f"{dt.isoformat()} was successfully got."
            )
            return [dt, point.azimuth, point.elevation]
        except KeyError:
            logger.warning(
                f"Communication between satellite with NORAD ID {norad_id} and "
                f"'{station_name}' ground station hasn't prediction at "
                f"{dt.isoformat()}."
            )
            return [dt, None, None]

    def get_frequencies(
        self, station_name: str, norad_id: int, dt: Optional[datetime] = None
    ) -> list[Union[datetime, Optional[float]]]:
        """Get uplink and downlink frequencies calculated with Doppler shift for
        required communication at required datetime.

        Args:
            norad_id (int): Satellite NORAD ID
            station_name (str): Name of ground station setuped into Orbitron
            dt (datetime): Required datetime to get uplink and downlink frquencies data.
                If dt is None, then will be used current UTC datetime
                (default is None)

        Raises:
            NewOrbitronSetupError: If Orbitron hasn't communication setup for required
                satellite and ground station
            NewOrbitronDataError: If communication for required satellite and ground
                station hasn't prediction

        Returns:
            list[str, float | None, float | None]: datetime, uplink frequency if defined
                for current datetime else None and downlink frequency if defined for
                current datetime else None
        """
        self._check_comm_prediction_data(station_name, norad_id)

        if dt is None:
            dt = datetime.utcnow()

        dt = dt.replace(microsecond=0)
        try:
            point = self.comms[station_name][norad_id].comm_data[dt]
            logger.info(
                f"Uplink and downlink frequencies for communication between satellite "
                f"with NORAD ID {norad_id} and '{station_name}' ground station at "
                f"{dt.isoformat()} was successfully got."
            )
            return [dt, point.uplink, point.downlink]
        except KeyError:
            logger.warning(
                f"Communication between satellite with NORAD ID {norad_id} and "
                f"'{station_name}' ground station hasn't prediction at "
                f"{dt.isoformat()}."
            )
            return [dt, None, None]

    def get_data(
        self, station_name: str, norad_id: int, dt: Optional[datetime] = None
    ) -> list[Union[datetime, Optional[float]]]:
        """Get azimuth, elevation, uplink and downlink frequencies calculated with
        Doppler shift required communication at required datetime.

        Args:
            norad_id (int): Satellite NORAD ID
            station_name (str): Name of ground station setuped into Orbitron
            dt (datetime): Required datetime to get azimuth, elevation, downlink and
                uplink frequencies data. If dt is None, then will be used current UTC
                datetime
                (default is None)

        Raises:
            NewOrbitronSetupError: If Orbitron hasn't communication setup for required
                satellite and ground station
            NewOrbitronDataError: If communication for required satellite and ground
                station hasn't prediction

        Returns:
            list[str, float | None, float | None, float | None, float | None]: datetime,
                azimuth if defined for current datetime else None,
                elevation if defined for current datetime else None, uplink
                frequency if defined for current datetime else None and downlink
                frequency if defined for current datetime else None
        """
        self._check_comm_prediction_data(station_name, norad_id)

        if dt is None:
            dt = datetime.utcnow()

        dt = dt.replace(microsecond=0)
        try:
            point = self.comms[station_name][norad_id].comm_data[dt]
            logger.info(
                f"Azimuth, elevation, uplink and downlink frequencies for "
                f"communication between satellite with NORAD ID {norad_id} and "
                f"'{station_name}' ground station at {dt.isoformat()} successfully got."
            )
            return [
                dt,
                point.azimuth,
                point.elevation,
                point.uplink,
                point.downlink,
            ]
        except KeyError:
            logger.warning(
                f"Communication between satellite with NORAD ID {norad_id} and "
                f"'{station_name}' ground station hasn't prediction at "
                f"{dt.isoformat()}."
            )
            return [dt, None, None, None, None]

    def get_comm_sessions_params(
        self, station_name: str, norad_id: int
    ) -> dict[datetime, SessionParams]:
        """Get communication sessions parameters, which are described in SessionParams
        class for required communication.

        Args:
            norad_id (int): Satellite NORAD ID
            station_name (str): Name of ground station setuped into Orbitron

        Raises:
            NewOrbitronSetupError: If Orbitron hasn't communication setup for required
                satellite and ground station

        Returns:
            dict[datetime, SessionParams]: dict with starts datetime sessions as keys
                and values as instances of SessionParams class, each describes one
                communication session between satellite and ground station
        """
        self._check_comm_setup_for_satellite_with_ground_station(station_name, norad_id)
        self.comms[station_name][norad_id].define_session_params()
        logger.info(
            f"Total {len(self.comms[station_name][norad_id].session_params)} "
            f"communication sessions were defined for communication between satellite "
            f"with NORAD ID {norad_id} and '{station_name}' ground station for "
            f"predicted period."
        )

        return self.comms[station_name][norad_id].session_params

    def get_all_data(
        self, station_name: str, norad_id: int
    ) -> dict[datetime, CommParams]:
        """Get all communication data which are described in CommParams class for
        required communication.

        Args:
            norad_id (int): Satellite NORAD ID
            station_name (str): Name of ground station setuped into Orbitron

        Raises:
            NewOrbitronSetupError: If Orbitron hasn't communication setup for required
                satellite and ground station

        Returns:
            dict[str, CommParams]: Dict with datetime as keys and instances
                of the CommParams consisted communication parameters for satellite at
                key datetime as values
        """
        self._check_comm_setup_for_satellite_with_ground_station(station_name, norad_id)
        return self.comms[station_name][norad_id].comm_data

    def clear_ground_station_data(self, station_name: str) -> None:
        """Clear satellites and communication data for required ground station.

        Args:
            station_name (str): Name of ground station setuped into Orbitron

        Returns:
        """
        self.satellites[station_name].clear()
        self.comms[station_name].clear()
        logger.info(
            f"Data about satellites and communications for '{station_name}' ground "
            f"station was deleted."
        )

    @staticmethod
    def __update_all_tles__(
        norad_ids: list[int],
        token: dict[Literal["identity", "password"], str],
        tle_data_folder: str = "tle",
    ) -> None:
        """Download all required TLE files by SpaceTrack API.

        Args:
            norad_ids (list[int]): NORAD IDs for any required satellites
            token (dict):   identity (str) - Login for SpaceTrack
                            password (str) - Password for SpaceTrack
            tle_data_folder (str): folder name to save TLE files

        Returns:
        """
        tle_data_dir: str = os.path.join(os.path.dirname(__file__), tle_data_folder)
        if not os.path.exists(tle_data_dir):
            os.mkdir(tle_data_dir)

        st = SpaceTrackClient(
            identity=token.get("identity"), password=token.get("password")
        )
        for norad_id in norad_ids:
            tle: str = st.tle_latest(
                norad_cat_id=norad_id, orderby="epoch desc", limit=1, format="3le"
            )
            if not tle:
                logger.warning(
                    f"TLE file for satellite with NORAD ID {norad_id} wasn't found."
                )
                continue

            tle_info = tle.split("\n")[1]
            epoch_year = int(tle_info[18:20])
            epoch_day = int(tle_info[20:23])
            if epoch_year <= 50:
                epoch_year += 2000
            else:
                epoch_year += 1900

            epoch = datetime(epoch_year, 1, 1) + timedelta(days=epoch_day - 1)
            tle_file_name = f"{norad_id}__{str(epoch.date())}.tle"
            with open(
                os.path.join(tle_data_dir, tle_file_name), "w", encoding="utf-8"
            ) as tle_file:
                tle_file.write(tle)
            logger.info(
                f"TLE file for satellite with NORAD ID {norad_id} was downloaded."
            )

    @staticmethod
    def __delete_all_tles__(tle_data_folder: str = "tle") -> None:
        """Delete all existed TLE files in required folder.

        Args:
            tle_data_folder (str): required folder name to delete all TLE files

        Returns:
        """
        if not os.path.exists(tle_data_folder):
            logger.info(f"Folder '{tle_data_folder}' to delete TLE files wasn't found.")
            return

        tle_data_dir = os.path.join(os.path.dirname(__file__), tle_data_folder)
        files_lst = os.listdir(tle_data_dir)
        for file in files_lst:
            if ".tle" in file or ".3le" in file:
                os.remove(os.path.join(tle_data_dir, file))
                logger.info(f"TLE file '{file}' was deleted.")


def log_comm_data(
    norad_id: int,
    uplink: float,
    downlink: float,
    longitude: float,
    latitude: float,
    altitude: Union[float, int],
    min_elevation: float,
    start_dt: datetime = datetime.now().replace(microsecond=0),
    time_prediction: int = 86400,
    step_prediction: int = 1,
) -> None:
    """Define communication parameters for required satellite and
    ground station and logs it into csv file.

    Args:
        norad_id (int): satellite NORAD ID
        uplink (float, optional): An uplink frequency to send coomand to
            satellite, [Hz]
            (default is None)
        downlink (float, optional): An downlink frequency to get command from
            satellite, [Hz]
            (default is None)
        longitude (float): Longitude of ground station, [deg]
        latitude (float): Latitude of ground station, [deg]
        altitude (float): Altitude of ground station, [m]
        min_elevation (float | int): Minimal elevation angle between satellite and
            ground station for mutual visibility, [deg]
        start_prediction (datetime): datetime for start communication prediction
            (default is current UTC datetime)
        time_prediction (int): required prediction duration, [s]
            (default is 1d = 86400 s)
        step_prediction (int | float): prediction time step, [s]
            (default is 1 s)
    """
    orbitron = Orbitron()
    orbitron.setup_satellite(norad_id, uplink, downlink)
    orbitron.setup_ground_station(longitude, latitude, altitude, min_elevation, "test")
    orbitron.setup_comm(norad_id, "test")
    orbitron.predict_comm(norad_id, "test", start_dt, time_prediction, step_prediction)

    comm_data = orbitron.get_all_data(norad_id, "test")

    if not os.path.exists("LogData"):
        os.mkdir("LogData")

    with open(
        "LogData\\" + str(norad_id) + "__new_orbLog.csv",
        "w",
        encoding="utf-8",
        newline="",
    ) as data_file:
        writer = csv.writer(data_file)
        for dt, data in sorted(comm_data.items()):
            writer.writerow(
                [
                    f"{dt.strftime('%c'):.2f}",
                    f"{data.azimuth:.2f}",
                    f"{data.elevation:.2f}",
                    f"{data.uplink:.2f}",
                    f"{data.downlink:.2f}",
                ]
            )


if __name__ == "__main__":
    longitude = 50.17763
    latitude = 53.21204
    altitude = 137
    min_elevation = 0
    station_name = "Samara"

    norad_id = 24793
    uplink = 437399600
    downlink = 437399600

    orbitron = Orbitron()
    orbitron.setup_ground_station(
        longitude, latitude, altitude, min_elevation, station_name
    )
    orbitron.setup_satellite(station_name, norad_id, uplink, downlink)
    orbitron.setup_new_tle_by_spacetrack(station_name, norad_id)
    orbitron.setup_comm(station_name, norad_id)
    orbitron.predict_comm(station_name, norad_id)

    sessions_params = orbitron.get_comm_sessions_params(station_name, norad_id)
    comm_params = orbitron.get_all_data(station_name, norad_id)

    for i in range(10):
        time.sleep(1)
        data_angles = orbitron.get_azimuth_elevation(
            station_name, norad_id, datetime.utcnow()
        )
        data_freqs = orbitron.get_frequencies(station_name, norad_id, datetime.utcnow())
        data = orbitron.get_data(station_name, norad_id, datetime.utcnow())

    print("Finished!")
    orbitron.clear_ground_station_data(station_name)
    pass
