import logging
import math
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Union

from .ground_station import GroundStation, StationPosition
from .satellite import Satellite, SatPosition
from .sun_model import calculate_sun_position

logger = logging.getLogger(__name__)


@dataclass
class CommParams:
    """A class used to represent communication paramaters for a satellite position

    Attributes:
        pos_sat_ecef (SatPosition): The instance of the class SatPosition with
            coordinates of satellite center mass in ECEF coordinate system
        elevation (float): Elevation angle between ground station and satellite,
            [deg]
        azimuth (float): Azimuth angle between ground station and satellite, [deg]
        visibility (bool): Visibility between satellite and ground station
            True - visibility exists
            False - visibility doesn't exist
        uplink (float, optional): An uplink frequency to send coomand to satellite, [Hz]
            (default is None)
        downlink (float, optional): An downlink frequency to send command from
            satellite, [Hz]
            (default is None)
    """

    pos_sat_ecef: SatPosition
    elevation: float
    azimuth: float
    visibility: bool
    uplink: Optional[float] = None
    downlink: Optional[float] = None


@dataclass
class SessionParams:
    """A class used to represent communication sessions parameters with satellite

    Attributes:
        start_session_dt (datetime): Datetime of communication session start
        end_session_dt (datetime): Datetime of communication session end

        start_elevation (float): Elevation angle between ground station and
            satellite at the start of communication session, [deg]
        start_azimuth (float): Azimuth angle between ground station and
            satellite at the start of communication session, [deg]
        start_sun_elevation (float): Elevation angle between ground station
            and the Sun at the start of communication session, [deg]
        start_sun_azimuth (float): Azimuth angle between ground station
            and the Sun at the start of communication session, [deg]

        max_session_dt (datetime): Datetime of communication session at the moment of
            maximal elevation angle
        max_elevation (float): The maximal elevation angle between ground
            station and satellite during communication session, [deg]
        max_azimuth (float): Azimuth angle between ground station and
            satellite at the moment of maximal elevation angle, [deg]
        max_sun_elevation (float): Elevation angle between ground station
            and the Sun at the moment of maximal elevation angle, [deg]
        max_sun_azimuth (float): Azimuth angle between ground station
            and the Sun at the moment of maximal elevation angle, [deg]

        end_elevation (float): Elevation angle between ground station and
            satellite at the end of communication session, [deg]
        end_azimuth (float): Azimuth angle between ground station and
            satellite at the end of communication session, [deg]
        end_sun_elevation (float): Elevation angle between ground station
            and the Sun at the end of communication session, [deg]
        end_sun_azimuth (float): Azimuth angle between ground station
            and the Sun at the end of communication session, [deg]

        zero_crossing_azimuth_flag (bool):  True - if azimuth crosses zero value
                                            False - if azimuth not crosses zero value
    """

    # Parameters value at the start session
    start_session_dt: datetime
    start_elevation: float
    start_azimuth: float
    start_sun_elevation: float
    start_sun_azimuth: float

    # Parameters values when elevation angle value is max
    max_session_dt: datetime
    max_elevation: float
    max_azimuth: float
    max_sun_elevation: float
    max_sun_azimuth: float

    # Parameters values at the end session
    end_session_dt: datetime
    end_elevation: float
    end_azimuth: float
    end_sun_elevation: float
    end_sun_azimuth: float

    zero_crossing_azimuth_flag: bool


class SatelliteStationComm:
    """A class used to represent communication between satellite and ground station

    Attributes:
        satellite (Satellite): The instance of the class Satellite, with satellite
            parameters
        station (GroundStation): The instance of the class GroundStation, with ground
            station parameters
        session_params (list[SessionParams]): List of the instances of the class
            SessionParams, with main information about communication sessions between
            satellite and station
        comm_data (dict[dt, CommParams]): Dict with datetime keys and the instance
            CommParams values for each position of the satellite center mass propogation

    Methods:
        calculate_comm_for_predicted_period: Calculate communication parameters
            (instances of the CommParams class) for each predicted position of the
            satellite center mass
        define_session_params: Define communication sessions parameters which are
            described in the SessionParams class for each possible communication session
    """

    _R_E = 6371.302e3
    _R_ECV = 6378.136e3
    _ALF_CZJ = 1 / 298.257223563
    _c = 299792458

    def __init__(self, satellite: Satellite, station: GroundStation):
        """
        Args:
            satellite (Satellite): The instance of the class Satellite
            station (GroundStation): The instance of the class GroundStation
        """
        self.satellite = satellite
        self.station = station
        self.session_params: dict[datetime, SessionParams] = {}
        self.comm_data: dict[datetime, CommParams] = {}

        logger.info(
            f"Communication between satellite with norad_id {satellite.norad_id} and "
            f"ground station '{station.name}' is setuped."
        )

    def _transform_ecef_to_geodetic(
        self, pos_ecef: Union[SatPosition, StationPosition]
    ) -> list[float]:
        """Transform coordinates from Earth Centered Earth Fixed (ECEF) coordinate
        system to geodetic coordinate system.

        Args:
            pos_ecef (list[float]): The instance of SatPosition or StationPosition
                classes with x, y, z attributes.

        Returns:
            list[float]: Coordinates in geodetic coordinate system (longitude [radian],
            latitude [radian], altitude [m])
        """
        phi = math.atan2(pos_ecef.z, (pos_ecef.x**2 + pos_ecef.y**2) ** 0.5)
        lam = math.atan2(pos_ecef.y, pos_ecef.x)
        r_g = (pos_ecef.x**2 + pos_ecef.y**2 + pos_ecef.z**2) ** 0.5
        R_z = self._R_ECV * (1 - self._ALF_CZJ * math.sin(phi) ** 2)
        alt = r_g - R_z

        logger.debug(
            f"Position from ECEF coordinate system {pos_ecef} is successfully "
            f"transformed to geodetic coordinate system {lam=}, {phi=} and {alt=}."
        )

        return [lam, phi, alt]

    def _calculate_visibility(self, xyz_ecef_sat: SatPosition) -> bool:
        """Calculate visibility between satellite and ground station by ECEF
        coordinates.

        Args:
            xyz_ecef_sat (SatPosition): The instance of the class SatPosition with
                coordinates of satellite center mass in ECEF coordinate system

        Returns:
            bool:   True - visibility exists
                    False - visibility doesn't exist
        """
        r1 = [
            xyz_ecef_sat.x - self.station.pos.x,
            xyz_ecef_sat.y - self.station.pos.y,
            xyz_ecef_sat.z - self.station.pos.z,
        ]
        r2 = [
            self.station.pos.x,
            self.station.pos.y,
            self.station.pos.z,
        ]
        dot_r1r2 = r1[0] * r2[0] + r1[1] * r2[1] + r1[2] * r2[2]
        mod_r1 = (r1[0] ** 2 + r1[1] ** 2 + r1[2] ** 2) ** (0.5)
        visibility = dot_r1r2 - mod_r1 * self._R_E * math.sin(
            self.station.elevation_min
        )

        if visibility > 0:
            return True
        return False

    def _calculate_uplink_downlink(
        self, xyz_ecef_sat1: SatPosition, xyz_ecef_sat2: SatPosition
    ) -> list[Optional[float], Optional[float]]:
        """Caclulate uplink and downlink frequencies using two nearest positions of the
        satellite.

        Args:
            xyz_ecef_sat1 (SatPosition): The instance of the class SatPosition with
                coordinates of satellite center mass in ECEF coordinate system at 't1'
            xyz_ecef_sat2 (SatPosition): The instance of the class SatPosition with
                coordinates of satellite center mass in ECEF coordinate system at 't2'

        Returns:
            list[float]: Uplink and downlink frequencies for transmitting and receiving
                information to and from satellite
        """
        r1 = (
            (xyz_ecef_sat1.x - self.station.pos.x) ** 2
            + (xyz_ecef_sat1.y - self.station.pos.y) ** 2
            + (xyz_ecef_sat1.z - self.station.pos.z) ** 2
        ) ** (0.5)
        r2 = (
            (xyz_ecef_sat2.x - self.station.pos.x) ** 2
            + (xyz_ecef_sat2.y - self.station.pos.y) ** 2
            + (xyz_ecef_sat2.z - self.station.pos.z) ** 2
        ) ** (0.5)
        v = r2 - r1

        if self.satellite.uplink_freq:
            uplink = self.satellite.uplink_freq / (1 - v / self._c)
        else:
            uplink = None

        if self.satellite.downlink_freq:
            downlink = self.satellite.downlink_freq / (1 + v / self._c)
        else:
            downlink = None

        return [uplink, downlink]

    def _calculate_azimuth_elevation(
        self, xyz_ecef_sat: SatPosition
    ) -> list[float, float]:
        """Calculate azimuth and elevation angle between the satellite and the ground
        station and return azimuth and elevation in DEGREES!.

        Args:
            xyz_ecef_sat (SatPosition): The instance of the class SatPosition with
                coordinates of satellite center mass in ECEF coordinate system

        Returns:
            list[float]: azimuth [deg] and elevation [deg] between satellite and ground
                station
        """
        # Azimuth calculation
        lam_sat, phi_sat, _ = self._transform_ecef_to_geodetic(xyz_ecef_sat)
        delta = lam_sat - self.station.pos.lam
        Az: float = math.atan2(
            math.sin(delta) * math.cos(phi_sat),
            math.cos(self.station.pos.phi) * math.sin(phi_sat)
            - math.sin(self.station.pos.phi) * math.cos(phi_sat) * math.cos(delta),
        )
        if Az < 0:
            Az += 2 * math.pi

        # Elevation angle calculation
        r1 = [
            xyz_ecef_sat.x - self.station.pos.x,
            xyz_ecef_sat.y - self.station.pos.y,
            xyz_ecef_sat.z - self.station.pos.z,
        ]
        r2 = [self.station.pos.x, self.station.pos.y, self.station.pos.z]
        dot_r1r2 = r1[0] * r2[0] + r1[1] * r2[1] + r1[2] * r2[2]
        mod_r1 = (r1[0] ** 2 + r1[1] ** 2 + r1[2] ** 2) ** (0.5)
        mod_r2 = (r2[0] ** 2 + r2[1] ** 2 + r2[2] ** 2) ** (0.5)
        sin_El = dot_r1r2 / (mod_r1 * mod_r2)
        El = math.asin(sin_El)

        return [math.degrees(Az), math.degrees(El)]

    def _calculate_comm_session_times_for_predicted_period(
        self,
    ) -> list[tuple[datetime, datetime]]:
        """Define all communication session times between satellite and station in
        predicted satellite center mass motion period.

        Returns:
            list[tuple[datetime]]: List of tuples with start and end datetimes of
                communication sessions between satellite and station
        """
        session_times: list[tuple[datetime, datetime]] = []

        if not hasattr(self.satellite, "pos_ecef"):
            logger.warning(
                f"Satellite with NORAD ID {self.satellite.norad_id} hasn't predicted "
                f"center mass positions. Prediction will run with default parameters."
            )
            self.satellite.predict_cm()

        comm_flag = False
        for dt, pos_ecef_sat in self.satellite.pos_ecef.items():
            visibility = self._calculate_visibility(pos_ecef_sat)
            if visibility and not comm_flag:
                start_comm_session = dt
                comm_flag = True
            elif not visibility and comm_flag:
                end_comm_session = dt
                session_times.append((start_comm_session, end_comm_session))

                logger.debug(
                    f"Communication session between satellite with NORAD ID "
                    f"{self.satellite.norad_id} and ground station "
                    f"'{self.station.name}' from {start_comm_session.isoformat()} to"
                    f"{end_comm_session.isoformat()} is defined."
                )

                start_comm_session, end_comm_session = None, None
                comm_flag = False

        if comm_flag and not end_comm_session:
            session_times.append((start_comm_session, dt))

        logger.info(
            f"Total {len(session_times)} communication sessions between satellite with "
            f"NORAD ID {self.satellite.norad_id} and ground station "
            f"'{self.station.name}' were defined."
        )

        return session_times

    def calculate_comm_for_predicted_period(self) -> None:
        """Calculate parameters described in the class CommParams (azimuth, elevation,
        uplink and downlink frequencies) for each position of satellite center mass in
        ECEF coordinate system in predicted period.
        Results write to dict comm_data.

        Returns:
        """
        if not hasattr(self.satellite, "pos_ecef"):
            logger.warning(
                f"Satellite with NORAD ID {self.satellite.norad_id} hasn't predicted "
                f"center mass positions. Prediction will run with default parameters."
            )
            self.satellite.predict_cm()

        prev_dt = list(self.satellite.pos_ecef.keys())[0]
        prev_pos_ecef_sat = self.satellite.pos_ecef.pop(prev_dt)

        for dt, pos_ecef_sat in self.satellite.pos_ecef.items():
            azimuth, elevation = self._calculate_azimuth_elevation(pos_ecef_sat)
            uplink, downlink = self._calculate_uplink_downlink(
                prev_pos_ecef_sat, pos_ecef_sat
            )

            prev_pos_ecef_sat = pos_ecef_sat

            self.comm_data[dt] = CommParams(
                pos_ecef_sat,
                elevation,
                azimuth,
                self._calculate_visibility(pos_ecef_sat),
                uplink,
                downlink,
            )

        logger.info(
            f"Communication calculation for satellite with NORAD ID  "
            f"{self.satellite.norad_id} and ground station '{self.station.name}' "
            f"is completed."
        )

    def define_session_params(self) -> None:
        """Define parameters of communication sessions which are described in the class
        SessionParams.

        Returns:
        """
        if not self.comm_data:
            logger.warning(
                f"Communication calculation for satellite with NORAD ID "
                f"{self.satellite.norad_id} and ground station '{self.station.name}' "
                f"wasn't completed. Calculation will run automatically."
            )
            self.calculate_comm_for_predicted_period()

        session_times = self._calculate_comm_session_times_for_predicted_period()
        for start_session, end_session in session_times:
            one_session_params = list(
                filter(lambda k: (start_session <= k <= end_session), self.comm_data)
            )

            start_session_params = self.comm_data[one_session_params[0]]
            start_sun_elevation, start_sun_azimuth = calculate_sun_position(
                dt=start_session,
                station_lon=self.station.pos.lam,
                station_lat=self.station.pos.phi,
            )

            end_session_params = self.comm_data[one_session_params[-1]]
            end_sun_elevation, end_sun_azimuth = calculate_sun_position(
                dt=end_session,
                station_lon=self.station.pos.lam,
                station_lat=self.station.pos.phi,
            )

            azimuth_prev: float = None
            max_elevation = -90
            zero_crossing_azimuth_flag = False
            for dt in one_session_params:
                azimuth = self.comm_data[dt].azimuth
                elevation = self.comm_data[dt].elevation

                if azimuth_prev:
                    if abs(azimuth_prev - azimuth) > 330:
                        zero_crossing_azimuth_flag = True
                azimuth_prev = azimuth

                if elevation > max_elevation:
                    max_elevation = elevation
                    max_azimuth = azimuth
                    max_session_dt = dt

            max_sun_elevation, max_sun_azimuth = calculate_sun_position(
                dt=max_session_dt,
                station_lon=self.station.pos.lam,
                station_lat=self.station.pos.phi,
            )

            session = SessionParams(
                start_session_dt=start_session,
                start_elevation=start_session_params.elevation,
                start_azimuth=start_session_params.azimuth,
                start_sun_elevation=start_sun_elevation,
                start_sun_azimuth=start_sun_azimuth,
                max_session_dt=max_session_dt,
                max_elevation=max_elevation,
                max_azimuth=max_azimuth,
                max_sun_elevation=max_sun_elevation,
                max_sun_azimuth=max_sun_azimuth,
                end_session_dt=end_session,
                end_elevation=end_session_params.elevation,
                end_azimuth=end_session_params.azimuth,
                end_sun_elevation=end_sun_elevation,
                end_sun_azimuth=end_sun_azimuth,
                zero_crossing_azimuth_flag=zero_crossing_azimuth_flag,
            )
            self.session_params[start_session.replace(second=0)] = session

    def recalculate_uplink_downlink(self, start_dt: datetime) -> None:
        """Recalculate uplink and downlink frequencies for for each position of
        satellite center mass from start_dt to end of prediction.

        Args:
            start_dt (datetime): the datetime from which to start recalculation

        Returns:
        """
        if hasattr(self.satellite, "pos_ecef"):
            dts_for_recalcualtion = sorted(
                filter(lambda dt: dt >= start_dt, self.satellite.pos_ecef)
            )
            prev_dt = dts_for_recalcualtion.pop(0)
            for dt in dts_for_recalcualtion:
                uplink, downlink = self._calculate_uplink_downlink(
                    self.satellite.pos_ecef[prev_dt], self.satellite.pos_ecef[dt]
                )

                self.comm_data[dt].uplink = uplink
                self.comm_data[dt].downlink = downlink
                prev_dt = dt
            logger.info(
                f"Frquencies for satellite with NORAD ID {self.satellite.norad_id} are "
                f"recalculated."
            )
        else:
            logger.warning(
                f"Satellite with NORAD ID {self.satellite.norad_id} hasn't completed "
                f"prediction and frquencies for satellite aren't recalculated."
            )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="[{asctime}] #{levelname:8} {filename}:{lineno} - {name} - {message}",
        style="{",
    )

    satellite = Satellite(norad_id=57173, uplink=437399600, downlink=437399600)
    satellite.setup_tle_by_spacetrack()
    satellite.predict_cm()

    station = GroundStation(
        position=[50.1776, 53.2120, 137], elevation_min=0, name="Samara station"
    )

    comm = SatelliteStationComm(satellite=satellite, station=station)
    comm.calculate_comm_for_predicted_period()
    comm.define_session_params()
    pass
