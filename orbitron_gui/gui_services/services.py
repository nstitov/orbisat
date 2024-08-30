from dataclasses import dataclass
from datetime import datetime
from typing import Optional

NoradID = int
StationName = str


@dataclass()
class StationInfo:
    """A dataclass used to represent ground station parameters.

    Attributes:
        name (str): ground station name
        longitude (float): ground station longitude, [rad]
        latitute (float): ground station latitude, [rad]
        altitude (float): ground station altitude, [m]
        elevation (float): ground station elevation angle, [rad]
    """

    name: StationName
    longitude: float
    latitude: float
    altitude: float
    elevation: float

    def __eq__(self, other):
        if isinstance(other, StationInfo):
            return (
                self.name == other.name
                and self.longitude == other.longitude
                and self.latitude == other.latitude
                and self.altitude == other.altitude
                and self.elevation == other.elevation
            )
        else:
            return False


@dataclass()
class SatelliteInfo:
    """A dataclass used to represent satellite parameters.

    Attributes:
        norad_id (str): satellite NORAD ID
        tle_dt (datetime): datetime of TLE file creation
        uplink (float): satellite uplink frequency, [Hz]
        downlink (float): satellite downlink frequency, [Hz]
        new_uplink (float): satellite new uplink frequency to recalulate communication
            parameters, [Hz]
        new_downlink (float): satellite new downlink frequency to recalculate
            communication parameters, [Hz]
    """

    norad_id: NoradID
    tle_dt: Optional[datetime]
    uplink: Optional[float]
    downlink: Optional[float]

    def __post_init__(self):
        self.new_uplink: Optional[float] = self.uplink
        self.new_downlink: Optional[float] = self.downlink
