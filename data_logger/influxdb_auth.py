from dataclasses import dataclass, field, asdict
from typing import Any

import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS


@dataclass
class LogData:
    """A class used to represent data point for InfluxDB writing."""

    time: str
    measurement: str
    fields: dict[str, Any]
    tags: dict[str, Any] = field(default_factory=dict)

    dict = asdict

    # def __post_init__(self):
    #     self.tags = {"satellite": "TestSat"}


class InfluxdbAuth:
    def __init__(self, url: str, token: str, org: str, buket: str):
        self._buket = buket
        self._org = org

        self.client = influxdb_client.InfluxDBClient(url=url, token=token, org=org)
        self.writer = self.client.write_api(write_options=SYNCHRONOUS)

    def write_point(self, point: influxdb_client.Point) -> None:
        self.writer.write(
            bucket=self._buket, org=self._org, time_precision="ns", record=point
        )
