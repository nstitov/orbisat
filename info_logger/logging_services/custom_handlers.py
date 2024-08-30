import os
import re
import shutil
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


class LogRotatiingFileHandler(TimedRotatingFileHandler):
    """A class used to represent Handler for handling logs to file which changes name
    each day."""

    def __init__(
        self,
        filename,
        when="h",
        interval=1,
        backupCount=0,
        encoding=None,
        delay=False,
        utc=False,
        atTime=None,
        errors=None,
    ):
        super().__init__(
            filename, when, interval, backupCount, encoding, delay, utc, atTime, errors
        )

        self.suffix = "%Y-%m-%d"
        # self.suffix = "%Y-%m-%d_%H-%M-%S"
        self.namer = self._get_filename
        self.rotator = self._rotator_func
        # Regular expression should match suffix!
        self.extMatch = re.compile(r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}")

    def _get_filename(self, filename: Path):
        log_directory = os.path.split(filename)[0]
        old_filename = filename.split("\\")[-1]
        old_name_arr = old_filename.split(".")
        new_filename = os.path.join(
            log_directory,
            old_name_arr[0] + "." + old_name_arr[2] + "." + old_name_arr[1],
        )

        if not os.path.exists(new_filename):
            return new_filename

    def _rotator_func(self, source: Path, dest: Path):
        shutil.copy(source, dest)

        with open(source, "w", encoding="utf-8"):
            pass
