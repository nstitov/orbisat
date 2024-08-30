import dataclasses
import json
from abc import abstractmethod
from datetime import datetime
from logging import Formatter, LogRecord

from ..influxdb_auth import LogData


class DataFormatter(Formatter):
    """A class used to represent Formatter for logging data."""

    def json_fmt(self, record: LogRecord) -> str:
        data = {}
        for attr in dataclasses.fields(LogData):
            if attr.name == "tags":
                data[attr.name] = {}
                for k, v in getattr(record, attr.name).items():
                    data[attr.name][k] = v
            else:
                data[attr.name] = getattr(record, attr.name)

        return json.dumps(data)

    @abstractmethod
    def format(self, record: LogRecord):
        pass


class FileDataFormatter(DataFormatter):
    """A class used to represent Formatter for logging data to logfile."""

    def format(self, record: LogRecord):
        data_json = self.json_fmt(record)
        asctime = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        return f"[{asctime}] #{'DATA':8} - {data_json}"
    

class ConsoleDataFormatter(DataFormatter):
    """A class used to represent Formatter for logging data to logfile."""

    def format(self, record: LogRecord):
        data_json = self.json_fmt(record)
        data = json.loads(data_json)
        data_cut = { 'measurement' : data['measurement'], 'fields' : data['fields'] }
        data_json_cut = json.dumps(data_cut)
        asctime = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        return f"[{asctime}] #{'DATA':8} - {data_json_cut}"


class InfluxdbDataFormatter(DataFormatter):
    """A class used to represent Formatter for logging data to indluxdb in JSON format
    with keys defined in LogData dataclass.
    """

    def format(self, record: LogRecord):
        return self.json_fmt(record)


class NoDataFormatter(Formatter):
    def format(self, record: LogRecord):
        asctime = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        return f"[{asctime}] #{'ERROR':8} - {record.exc_info[1].args[0]}"
