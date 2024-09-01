import logging.config
import os

import yaml

if not os.path.exists("Logs"):
    os.makedirs("Logs")

with open(os.path.join(os.path.dirname(__file__), "config_data/logging_config.yaml"), "rt") as f:
    config = yaml.safe_load(f.read())
logging.config.dictConfig(config)
