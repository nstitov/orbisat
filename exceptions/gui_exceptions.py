class StationNotSetupedError(Exception):
    def __init__(self, station_name: str):
        self.station_name = station_name
        super().__init__(f"Ground station with name {station_name} isn't setuped.")


class StationSetupedError(Exception):
    def __init__(self, station_name: str):
        self.station_name = station_name
        super().__init__(
            f"Error during ground station {station_name} setup is occured."
        )
