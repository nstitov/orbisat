import logging
import logging.config
import os
import sys
import time
from datetime import datetime

import yaml

from influxdb_auth import LogData

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

with open("config_data/logging_config.yaml", "rt") as f:
    config = yaml.safe_load(f.read())
logging.config.dictConfig(config)

logger = logging.getLogger(__name__)

a = 0
b = 0
while a <= 100:
    a += 1
    b += 2
    data = {"a": a, "b": b}
    logdata = LogData(
        time=datetime.now().isoformat() + "+04:00",
        measurement="Cycle test",
        fields=data,
    )
    logger.info("DATA", extra=logdata.__dict__)
    time.sleep(10)
