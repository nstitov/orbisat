import logging
import math
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Union

from environs import EnvError
from pyorbital.orbital import Orbital
from spacetrack import SpaceTrackClient

from ..config_data.config import load_spacetrack_config
from ..exceptions.satellite_exceptions import SpaceTrackAuthError, TLEDataError

logger = logging.getLogger(__name__)


@dataclass
class SatPosition:
    """A class used to represent satellite coordinates position.

    Attributes:
        x (float): X-axis coordinate of satellite center mass in ECEF coordinate
            system
        y (float): Y-axis coordinate of satellite center mass in ECEF coordinate
            system
        z (float): Z-axis coordinate of satellite center mass in ECEF coordinate
            system
    """

    x: float
    y: float
    z: float


class Satellite:
    """A class used to represent a Satellite.
    To use downloading TLE files by SpaceTrack API put identity and password for
    SpaceTrack to .env file in config_data.

    Attributes:
        norad_id (int): The satellite NORAD ID
        uplink (float, optional): An uplink frequency to send coomand to satellite, [Hz]
        downlink (float, optional): An downlink frequency to send command from
            satellite, [Hz]
        tle_data_folder (str): The folder name for saving TLE file for satellite
        satellite_name (str): The satellite name
        tle_file_name (str): The TLE file name
        orbital (Orbital): Information obtained from TLE file (TLE data, SGP4 data)

    Methods:
        update_tle(token): update TLE file for the satellite
        predict_cm(start_dt, time_prediction, step_prediction): predict satellite center
            mass position in ECEF coordinate system
    """

    _MU = 398600.44e9
    _R_ECV = 6378.136e3
    _J_2 = 1082.627e-6
    _J_4 = -1.617608e-6
    _OMEGA_EARTH = 0.729211e-4

    def __init__(
        self,
        norad_id: int,
        uplink: Optional[float] = None,
        downlink: Optional[float] = None,
        *,
        tle_data_folder: str = "tle",
    ):
        """
        Args:
            norad_id (int): satellite NORAD ID
            uplink (float | optional): an uplink frequency to send coomand to
                satellite, [Hz]
                (default is None)
            downlink (float, optional): An downlink frequency to send command from
                satellite, [Hz]
                (default is None)
            tle_data_folder (str): The folder name for saving TLE file for satellite
                (default is "tle")
        """
        self.norad_id = norad_id
        self.uplink_freq = uplink
        self.downlink_freq = downlink

        self.tle_data_folder = os.path.join(
            os.path.dirname(__file__), "..", tle_data_folder
        )

        if not os.path.exists(self.tle_data_folder):
            os.makedirs(self.tle_data_folder)

    def _get_datetime_from_tle(self, tle_line_1: str) -> datetime:
        """Get TLE file creation datetime from first line of the TLE file.

        Args:
            tle_line_1 (str): First line of the TLE file

        Returns:
            datetime: TLE file creation datetime
        """
        epoch_year = int(tle_line_1[18:20])
        epoch_day = int(tle_line_1[20:23])
        if epoch_year <= 50:
            epoch_year += 2000
        else:
            epoch_year += 1900

        return datetime(epoch_year, 1, 1) + timedelta(days=epoch_day - 1)

    def _check_correct_tle(self, tle_line_1: str, tle_line_2: str) -> bool:
        first_line_pattern = r"\d \d{5}\w [\d ]{5}[\d\w ]{3} \d{5}\.\d{8} [ -]\.\d{8} [ -]\d{5}-\d [ -]\d{5}-\d 0 [ \d]\d{4}"
        second_line_pattern = r"\d \d{5} [\d ]{3}\.\d{4} [\d ]{3}\.\d{4} \d{7} [\d ]{3}\.\d{4} [\d ]{3}\.\d{4} [\d ]{2}\.\d{8}[ \d]{6}"
        if not re.fullmatch(first_line_pattern, tle_line_1) or not re.fullmatch(
            second_line_pattern, tle_line_2
        ):
            raise TLEDataError("TLE file has incorrect format.")

    def _save_tle_file(self, tle_line_1: str, tle_line_2: str) -> None:
        """Save TLE file to default tle folder with name format '{NORAD_ID}__%Y-%m-%d.'

        Args:
            tle_line_1 (str): First line of the TLE file
            tle_line_2 (str): Seconds line of the TLE file

        Returns:
        """
        self.tle_file_dt = self._get_datetime_from_tle(tle_line_1)
        norad_id = tle_line_2[2:7]

        tle_file_name = f"{norad_id}_{self.tle_file_dt.date()}.tle"
        tle_file_path = os.path.join(self.tle_data_folder, tle_file_name)
        self.tle_file_name = tle_file_path

        with open(tle_file_path, "w", encoding="utf-8") as tle_file:
            for line in [tle_line_1 + "\n", tle_line_2]:
                tle_file.write(line)

        logger.info(f"TLE file {tle_file_name} was saved in default tle folder.")

    def _process_tle(self) -> Orbital:
        """Parse TLE file and transfer data to orbital paramaters for prediction center
        mass motion.

        Returns:
            Orbital: Information obtained from TLE file
        """
        self._check_correct_tle(self.line_1, self.line_2)
        return Orbital("N", line1=self.line_1, line2=self.line_2)

    def _get_sat_position_eci(
        self, req_time: datetime
    ) -> List[tuple[float, float, float]]:
        """Get the satellite center mass coordinates and speeds in Earth Centered
        Inertial (ECI) coordinate system at required time.

        Args:
            req_time (datetime): Required datetime to get center mass motion parameters

        Returns:
            list: Two tuples, the first with coordinates in [m] and the second with
                speeds in [m/s] of satellite center mass
        """
        pos, vel = self.orbital.get_position(req_time, normalize=False)

        return [
            (pos[0] * 1000, pos[1] * 1000, pos[2] * 1000),
            (vel[0] * 1000, vel[1] * 1000, vel[2] * 1000),
        ]

    def _RP_centermass_ECI(
        self, x_0: float, y_0: float, z_0: float, Vx_0: float, Vy_0: float, Vz_0: float
    ) -> list[float]:
        """Right part of differential equations with 4-th harmonic of Earth geopotential
        to propagate satellite center mass motion.

        Args:
            x_0, y_0, z_0 (float): Center mass position in coordinate form in ECI
                coordinate system, [m]
            Vx_0, Vy_0, Vz_0 (flaot): Center mass speed components in ECI coordinate
                system, [m/s]

        Returns:
            list[floats]: x [m], y [m], z [m], Vx [m/s], Vy [m/s], Vz [m/s]
        """
        r: float = (x_0**2 + y_0**2 + z_0**2) ** (0.5)

        mun = self._MU / r**2
        xn = x_0 / r
        yn = y_0 / r
        zn = z_0 / r
        an = self._R_ECV / r

        x = Vx_0
        y = Vy_0
        z = Vz_0
        Vx = (
            -mun * xn
            - 1.5 * self._J_2 * mun * xn * an**2 * (1.0 - 5.0 * zn**2)
            + 0.625
            * self._J_4
            * mun
            * xn
            * an**4
            * (3.0 + (63.0 * zn**2 - 42.0) * zn**2)
        )
        Vy = (
            -mun * yn
            - 1.5 * self._J_2 * mun * yn * an**2 * (1.0 - 5.0 * zn**2)
            + 0.625
            * self._J_4
            * mun
            * yn
            * an**4
            * (3.0 + (63.0 * zn**2 - 42.0) * zn**2)
        )
        Vz = (
            -mun * zn
            - 1.5 * self._J_2 * mun * zn * an**2 * (3.0 - 5.0 * zn**2)
            + 0.625
            * self._J_4
            * mun
            * zn
            * an**4
            * (15.0 + (63.0 * zn**2 - 70.0) * zn**2)
        )

        return [x, y, z, Vx, Vy, Vz]

    def _propagate_centermass_ECI_RK4(
        self,
        pos_eci_init: tuple[float, float, float],
        vel_eci_init: tuple[float, float, float],
        step: Union[int, float],
    ) -> List[tuple[float, float, float]]:
        """Propagte satellite center mass motion by Runge-Kutta 4-th order method in ECI
        coordinate system.

        Args:
            pos_eci_init (tuple[float]): Center mass coordinate position in ECI
                coordinate system, [m]
            vel_eci_init (tuple[float]): Center mass speed components in ECI coordinate
                system, [m/s]
            step (int | float): Integration step, [s]

        Returns:
            list: Two tuples, the first with coordinates in [m] and the second with
                speeds in [m/s] of satellite center mass
        """
        step1_2: float = step / 2

        k_x_1, k_y_1, k_z_1, k_Vx_1, k_Vy_1, k_Vz_1 = self._RP_centermass_ECI(
            pos_eci_init[0],
            pos_eci_init[1],
            pos_eci_init[2],
            vel_eci_init[0],
            vel_eci_init[1],
            vel_eci_init[2],
        )
        k_x_2, k_y_2, k_z_2, k_Vx_2, k_Vy_2, k_Vz_2 = self._RP_centermass_ECI(
            pos_eci_init[0] + step1_2 * k_x_1,
            pos_eci_init[1] + step1_2 * k_y_1,
            pos_eci_init[2] + step1_2 * k_z_1,
            vel_eci_init[0] + step1_2 * k_Vx_1,
            vel_eci_init[1] + step1_2 * k_Vy_1,
            vel_eci_init[2] + step1_2 * k_Vz_1,
        )
        k_x_3, k_y_3, k_z_3, k_Vx_3, k_Vy_3, k_Vz_3 = self._RP_centermass_ECI(
            pos_eci_init[0] + step1_2 * k_x_2,
            pos_eci_init[1] + step1_2 * k_y_2,
            pos_eci_init[2] + step1_2 * k_z_2,
            vel_eci_init[0] + step1_2 * k_Vx_2,
            vel_eci_init[1] + step1_2 * k_Vy_2,
            vel_eci_init[2] + step1_2 * k_Vz_2,
        )
        k_x_4, k_y_4, k_z_4, k_Vx_4, k_Vy_4, k_Vz_4 = self._RP_centermass_ECI(
            pos_eci_init[0] + step * k_x_3,
            pos_eci_init[1] + step * k_y_3,
            pos_eci_init[2] + step * k_z_3,
            vel_eci_init[0] + step * k_Vx_3,
            vel_eci_init[1] + step * k_Vy_3,
            vel_eci_init[2] + step * k_Vz_3,
        )

        step_1_6 = step / 6
        x_0 = pos_eci_init[0] + step_1_6 * (k_x_1 + 2 * (k_x_2 + k_x_3) + k_x_4)
        y_0 = pos_eci_init[1] + step_1_6 * (k_y_1 + 2 * (k_y_2 + k_y_3) + k_y_4)
        z_0 = pos_eci_init[2] + step_1_6 * (k_z_1 + 2 * (k_z_2 + k_z_3) + k_z_4)
        Vx_0 = vel_eci_init[0] + step_1_6 * (k_Vx_1 + 2 * (k_Vx_2 + k_Vx_3) + k_Vx_4)
        Vy_0 = vel_eci_init[1] + step_1_6 * (k_Vy_1 + 2 * (k_Vy_2 + k_Vy_3) + k_Vy_4)
        Vz_0 = vel_eci_init[2] + step_1_6 * (k_Vz_1 + 2 * (k_Vz_2 + k_Vz_3) + k_Vz_4)

        return [(x_0, y_0, z_0), (Vx_0, Vy_0, Vz_0)]

    def _transform_eci_to_ecef(
        self,
        pos_eci: list[float, float, float],
        GST: float,
        curr_date_seconds: Union[float, int],
    ) -> List[float]:
        """Transform coordanates from Earth Centered Inertial (ECI) coordinate system to
        Earth Centered Earth Fixed (ECEF) coordinate system.

        Args:
            pos_eci (list[float]): Coordinates in ECI coordinate system, [m]
            GST (float): Greenwich Sidereal Time
            curr_date_seconds (float | int): Seconds amount since 00:00 current day, [s]

        Returns:
            list[float]: Coordinates in ECEF coordinate system, [m]
        """
        S = GST + self._OMEGA_EARTH * curr_date_seconds

        x = pos_eci[0] * math.cos(S) + pos_eci[1] * math.sin(S)
        y = -pos_eci[0] * math.sin(S) + pos_eci[1] * math.cos(S)
        z = pos_eci[2]

        return [x, y, z]

    def _calculate_GMST(self, req_time: datetime) -> float:
        """Calculate Greenwich Middle Sidereal Time.

        Args:
            req_time (datetime): The date on which the calculation is required

        Returns:
            float: Greenwich Sidereal Time
        """
        year = req_time.year - 1900
        month = req_time.month - 3
        if month < 0:
            month += 12
            year -= 1

        mjd = 15078 + 365 * year + int(year / 4) + int(0.5 + 30.6 * month)
        mjd += (
            req_time.day
            + req_time.hour / 24
            + req_time.minute / 1440
            + req_time.second / 86400
        )

        Tu = (math.floor(mjd) - 51544.5) / 36525.0
        GST = (
            1.753368559233266
            + (628.3319706888409 + (6.770714e-6 - 4.51e-10 * Tu) * Tu) * Tu
        )

        return GST

    def setup_tle_by_file(
        self, file_name: str, *, default_folder: bool = True, tle_format: str = "tle"
    ) -> None:
        """Setup tle information by TLE file. If TLE file will not be found, it will be
        downloaded by SpaceTrackAPI by satellite NORAD ID.

        Args:
            file_name (str): File name in default tle folder or full path of TLE file
            default_folder (bool): flag of location TLE file (default folder or not)
                (default is True)
            tle_format (str): Format of TLE file, possible "tle" and "3le"
                (default is "tle")

        Returns:
        """
        if default_folder:
            file_name = os.path.join(self.tle_data_folder, file_name)

        try:
            with open(file_name, "r", encoding="utf-8") as tle_file:
                if tle_format == "tle":
                    self.line_1, self.line_2, *_ = tle_file.read().split("\n")
                    self.tle_info = None
                elif tle_format == "3le":
                    line_0, self.line_1, self.line_2, *_ = tle_file.read().split("\n")
                    self.tle_info = line_0[2:]
            logger.info(f"TLE file {file_name} was succesfully handled.")
            self._save_tle_file(self.line_1, self.line_2)
            self.orbital = self._process_tle()
        except FileNotFoundError:
            logger.exception("Required TLE file wasn't found.")
        except ValueError as err:
            logger.exception("TLE file has incorrect format.")
            raise TLEDataError from err

    def setup_tle_by_spacetrack(self, *, tle_format: str = "tle") -> None:
        """Download TLE file for satellite by SpaceTrack API by satellite NORAD ID. To
        use it set identiy and password for SpaceTrack to .env file.

        Args:
            tle_format (str): Format of TLE file, possible "tle" and "3le"
                (default is "tle")

        Returns:
        """
        try:
            spacetrack_token = load_spacetrack_config().token
        except EnvError as err:
            logger.exception("Error during config SpaceTrack.")
            raise SpaceTrackAuthError from err

        try:
            st = SpaceTrackClient(
                identity=spacetrack_token.get("identity"),
                password=spacetrack_token.get("password"),
            )

            tle: str = st.tle_latest(
                norad_cat_id=self.norad_id,
                orderby="epoch desc",
                limit=1,
                format=tle_format,
            )
        except Exception as err:
            logger.exception("Error during downloading TLE by SpaceTrack.")
            raise TLEDataError("Error during downloading TLE by SpaceTrack.") from err

        if not tle:
            logger.warning(
                f"TLE file for the satellite with NORAD ID {self.norad_id} was "
                f"downloaded, but hasn't data."
            )
            raise TLEDataError(
                f"Downloaded TLE file for satellite with NORAD ID {self.norad_id} "
                f"hasn't data."
            )
        else:
            logger.info(
                f"TLE file for satellite with NORAD ID {self.norad_id} is downloaded."
            )
            if tle_format == "tle":
                self.line_1, self.line_2, *_ = tle.split("\n")
                self.tle_info = None
            elif tle_format == "3le":
                line_0, self.line_1, self.line_2, *_ = tle.split("\n")
                self.tle_info = line_0[2:]
            self._save_tle_file(self.line_1, self.line_2)
            self.orbital = self._process_tle()

    def setup_tle_by_str(self, tle: str, *, tle_format: str = "tle") -> None:
        """Setup tle information by string format.

        Args:
            tle (str): TLE in string format, i.e. two string separated by \n.
            tle_format (str): Format of TLE file, possible "tle" and "3le"
                (default is "tle")

        Returns:
        """
        try:
            if tle_format == "tle":
                line_1, line_2, *_ = tle.strip().split("\n")
                self.tle_info = None
            elif tle_format == "3le":
                line_0, line_1, line_2, *_ = tle.strip().split("\n")
                self.tle_info = line_0[2:]
            self.line_1, self.line_2 = line_1.strip(), line_2.strip()
            logger.info("TLE data was succesfully handled.")
            self._save_tle_file(self.line_1, self.line_2)
            self.orbital = self._process_tle()
        except ValueError as err:
            logger.exception("TLE file has incorrect format.")
            raise TLEDataError from err

    def update_tle_by_spacetrack(self) -> None:
        """Download TLE file for satellite by SpaceTrack API. To use it set identiy and
        password for SpaceTrack to .env file.

        Returns:
        """
        try:
            old_tle_file_name, tle_ext = os.path.splitext(self.tle_file_name)
            old_tle_file_name = f"{old_tle_file_name}_old{tle_ext}"
            os.rename(self.tle_file_name, old_tle_file_name)
        except FileNotFoundError:
            logger.exception(f"Old TLE file {self.tle_file_name} wasn't found.")

        self.setup_tle_by_spacetrack()

        try:
            os.remove(old_tle_file_name)
        except FileNotFoundError:
            logger.exception(f"Impossible to delete old TLE file {self.tle_file_name}.")

    def predict_cm(
        self,
        start_dt: datetime = datetime.utcnow().replace(microsecond=0),
        time_prediction: int = 86400,
        step_prediction: Union[int, float] = 1,
    ) -> None:
        """Predict satellite center mass motion for required time prediction with
        required time step prediction in ECI coordinate system. After propagation
        transform coordinates from ECI coordinate system to ECEF coordinate system.

        Args:
            start_dt (datetime): Datetime to start prediction
                (default is current datetime)
            time_prediction (int): Prediction duration, [s]
                (default is one day, i.e. 86400 seconds)
            step_prediction (int | float): Integration step, [s]
                (default is 1 second)

        Raises:
            TLEDataError: If TLE file doesn't exist unpossible to calculate position

        Returns:
        """
        if not self.orbital:
            logger.warning("Satellite hasn't setuped TLE file.")
            raise TLEDataError()

        pos_ecef: dict[datetime, SatPosition] = {}

        GST = self._calculate_GMST(start_dt)
        seconds_in_current_date = (
            start_dt - datetime(start_dt.year, start_dt.month, start_dt.day)
        ).total_seconds()

        pos_eci, vel_eci = self._get_sat_position_eci(start_dt)
        pos_ecef_lst = self._transform_eci_to_ecef(
            pos_eci, GST, seconds_in_current_date
        )
        pos_ecef[start_dt] = SatPosition(*pos_ecef_lst)
        current_dt = start_dt
        for _ in range(1, int(time_prediction / step_prediction)):
            seconds_in_current_date += step_prediction
            current_dt += timedelta(seconds=step_prediction)
            pos_eci, vel_eci = self._propagate_centermass_ECI_RK4(
                pos_eci, vel_eci, step_prediction
            )
            pos_ecef_lst = self._transform_eci_to_ecef(
                pos_eci, GST, seconds_in_current_date
            )
            pos_ecef[current_dt] = SatPosition(*pos_ecef_lst)

        self.pos_ecef = pos_ecef
        logger.info(
            f"Center mass prediction started from {start_dt.isoformat()} for "
            f"{time_prediction} seconds with {step_prediction} seconds step is "
            f"completed."
        )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="[{asctime}] #{levelname:8} {filename}:{lineno} - {name} - {message}",
        style="{",
    )

    tle = """
    1 24793U 97020B   24032.50148130  .00000467  00000-0  15686-3 0  9992
    2 24793  86.3955  27.0408 0002108  82.9242 277.2194 14.35058745399928
    """

    satellite_tle_spacetrack = Satellite(
        norad_id=24793, uplink=437399600, downlink=437399600
    )
    satellite_tle_file = Satellite(norad_id=11111, uplink=437399600, downlink=437399600)
    satellite_tle_str = Satellite(norad_id=22222, uplink=437399600, downlink=437399600)

    satellite_tle_spacetrack.setup_tle_by_spacetrack()
    satellite_tle_file.setup_tle_by_file("24793__2024-02-01.tle", tle_format="3le")
    satellite_tle_str.setup_tle_by_str(tle)

    satellite_tle_spacetrack.predict_cm()
    satellite_tle_file.predict_cm()
    satellite_tle_str.predict_cm()

    pass
