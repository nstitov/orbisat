import logging
import math
from dataclasses import dataclass
from typing import Union

logger = logging.getLogger(__name__)


@dataclass
class StationPosition:
    """A class used to represent ground station position in Earth Centered Earth Fixed
    (ECEF) and geodetic coordinate systems

    Attributes:
        x (float): X-axis coordinate of ground station in ECEF coordinate system, [m]
        y (float): Y-axis coordinate of ground station in ECEF coordinate system, [m]
        z (float): Z-axis coordinate of ground station in ECEF coordinate system, [m]
        lam (float): longitude of ground station position in geodetic coordinate system,
            [rad]
        phi (float): latitude of ground station position in geodetic coordinate system,
            [rad]
        alt (float): altitude of ground station position in geodetic coordinate system,
            [rad]
    """

    x: float
    y: float
    z: float
    lam: float
    phi: float
    alt: float


class GroundStation:
    """A class used to represent GroundStation (mission control center)

    Attributes:
        pos (StationPosition): the instance of StationPosition class with coordinates of
            ground station in ECEF and geodetic coordinate systems
        elevation_min (float | int): Minimal elevation angle of satellite visibility
        name (str): Ground station name
    """

    _R_ECV = 6378.136e3
    _R_POL = 6356.7523e3
    _E_SQUARE = 1 - _R_POL**2 / _R_ECV**2
    _F = 1 - _R_POL / _R_ECV

    def __init__(
        self,
        position: Union[list[float, float, float], tuple[float, float, float]],
        elevation_min: Union[float, int] = 0,
        name: str = "default",
    ):
        """
        Args:
            position (list[float]): Longitude [deg], latitude [deg] and altitude [m] of
                ground station position in geodetic coordinate system
            elevation_min (float | int): Minimal elevation angle of satellite visibility,
                [deg]
                (default is 0)
            name (str): Ground station name
                (default is "default")
        """
        lam = math.radians(position[0])
        phi = math.radians(position[1])
        alt = position[2]

        x, y, z = self._transform_geodetic_to_ecef([lam, phi, alt])

        self.pos = StationPosition(x, y, z, lam, phi, alt)
        self.elevation_min = math.radians(elevation_min)
        self.name = name

        logger.info(
            f"Ground station '{name}' with lam={position[0]}, phi={position[1]} "
            f"and alt={position[2]} is setuped successfully."
        )

    def _transform_geodetic_to_ecef(self, geod) -> list[float, float, float]:
        """Transform  coordinates from geodetic coordinate system to ECEF coordinate
        system.

        Args:
            geod (list[float]): ground station coordinates in geodetic coordinate system
                (longitude [radian], latitude [radian], altiude [m])

        Returns:
            list[float]: list of ground station coordinates in ECEF coordinate system
                (x [m], y [m], z [m])
        """
        N = self._R_ECV / (1 - self._E_SQUARE * math.sin(geod[1]) ** 2) ** (0.5)
        x = (N + geod[2]) * math.cos(geod[1]) * math.cos(geod[0])
        y = (N + geod[2]) * math.cos(geod[1]) * math.sin(geod[0])
        z = ((1 - self._F) ** 2 * N + geod[2]) * math.sin(geod[1])

        logger.debug(
            "Coordinates from geodetic coordinate system are successfully "
            f"transformed to ECEF coordinate system {x=}, {y=} and {z=}."
        )

        return [x, y, z]


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="[(asctime)] #{levelname:8} {filename}:{lineno} - {name} - {message}",
        style="{",
    )

    station = GroundStation(
        position=[50.1776, 53.2120, 137], elevation_min=0, name="Samara station"
    )
