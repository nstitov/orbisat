class TLEDataError(Exception):
    """Satellite hasn't information from TLE file to calculate center mass
    coordinates."""


class DataPredictionError(Exception):
    """Center mass prediction wasn't completed for the satellite."""


class SpaceTrackAuthError(Exception):
    """Error in env variables to config spacetrack."""
