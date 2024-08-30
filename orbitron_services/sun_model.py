from datetime import datetime
from math import asin, atan2, cos, degrees, pi, radians, sin


def calculate_sun_position(
    dt: datetime, station_lon: float, station_lat: float
) -> tuple[float, float]:
    """
    https://stjarnhimlen.se/comp/tutorial.html
    Function to calculate Sun elevation and azimuth for required datetime and position
    on Earth surface

    Args:
        dt (datetime): required datetime in UTC
        station_lon (float): longitude of required Earth surface position, [rad]
        station_lat (float): latitude of required Eart surface position, [rad]

    Returns:
        tuple(float, float): Sun elevation and azimuth, [deg]
    """

    d = (
        367 * dt.year
        - 7 * (dt.year + (dt.month + 9) // 12) // 4
        + (275 * dt.month) // 9
        + dt.day
        - 730530
    )
    # Longitude of perihelion, [deg]
    w = 282.9404 + 4.70935e-5 * d
    # Eccentricity
    e = 0.016709 - 1.151e-9 * d
    # Mean anomaly, [deg]
    M = (356.0470 + 0.9856002585 * d) % 360
    # Obliquity of the ecliptic, [deg]
    oblecl = (23.4393 - 3.563e-7 * d) % 360
    # Sun's mean longitude, [deg]
    L = (w + M) % 360
    # Eccentric anomaly, [deg]
    E = M + (180 / pi) * e * sin(radians(M)) * (1 + e * cos(radians(M)))
    # Sun's rectangular coordinates in the plane of the ecliptic, where the X
    # axis points towards the perihelion, []
    x = cos(radians(E)) - e
    y = sin(radians(E)) * (1 - e**2) ** 0.5
    # Convert to distance and true anomaly, [] and [deg]
    r = (x**2 + y**2) ** 0.5
    v = degrees(atan2(y, x))
    # Longitude of the Sun, [deg]
    lon = (v + w) % 360
    # Sun's ecliptic rectangular coordinates, []
    x = r * cos(radians(lon))
    y = r * sin(radians(lon))
    z = 0.0
    # Sun's ecliptic equatorial coordinates, []
    xequat = x
    yequat = y * cos(radians(oblecl)) - z * sin(radians(oblecl))
    zequat = y * sin(radians(oblecl)) + z * cos(radians(oblecl))
    # RA and Decl, [deg]
    RA = degrees(atan2(yequat, xequat))
    Decl = degrees(atan2(zequat, (xequat**2 + yequat**2) ** 0.5))

    # Sidereal Time at the Greenwich meridian at 00:00 right now, [Hours]
    GMST0 = (L + 180) / 15
    # Local Sidereal Time, [Hours]
    UT = dt.hour + dt.minute / 60 + dt.second / 3600
    SIDTIME = GMST0 + UT + degrees(station_lon) / 15
    # Hour Angle, [deg]
    HA = SIDTIME * 15 - RA
    # Sun in ectangular (x,y,z) coordinate system where the X axis points to
    # the celestial equator in the south, the Y axis to the horizon in the
    # west, and the Z axis to the north celestial pole, []
    x = cos(radians(HA)) * cos(radians(Decl))
    y = sin(radians(HA)) * cos(radians(Decl))
    z = sin(radians(Decl))
    # rotate this x,y,z system along an axis going east-west, i.e. the Y axis,
    # in such a way that the Z axis will point to the zenith, []
    xhor = x * sin(station_lat) - z * cos(station_lat)
    yhor = y
    zhor = x * cos(station_lat) + z * sin(station_lat)

    # Azimuth and elevation, [deg]
    azimuth = degrees(atan2(yhor, xhor) + pi)
    elevation = degrees(asin(zhor))
    return elevation, azimuth


if __name__ == "__main__":
    dt = datetime(2024, 4, 25, 7, 39, 0)
    lon = radians(50.1776)
    lat = radians(53.2120)

    elevation, azimuth = calculate_sun_position(dt, lon, lat)
    print(f"{elevation=}\n{azimuth=}")
