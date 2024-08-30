from logging import Filter


class LogDataFilter(Filter):
    """A class used to represent Filter for choosing logs with data."""

    def filter(self, record):
        return hasattr(record, "fields")


class NoDataFilter(Filter):
    def filter(self, record):
        return record.exc_info[1].args[0] == "No response"


class ErrorFilter(Filter):
    def filter(self, record):
        return record.exc_info[1].args[0] != "No response"
