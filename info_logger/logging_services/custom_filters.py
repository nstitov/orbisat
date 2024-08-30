from logging import Filter, LogRecord


class InfoLogFilter(Filter):
    """A class used to represent Filter for choosing logs with level INFO and without
    data.
    """

    def filter(self, record: LogRecord):
        return record.levelname == "INFO" and not hasattr(record, "fields")
