import os
from dataclasses import dataclass
from typing import Literal

from environs import Env


@dataclass
class SpaceTrackConfig:
    identity: str
    password: str

    def __post_init__(self):
        self.token: dict[Literal["identity", "password"], str] = {
            "identity": self.identity,
            "password": self.password,
        }


def load_spacetrack_config() -> SpaceTrackConfig:
    env = Env()
    env.read_env(os.path.join(os.path.dirname(__file__), ".env.spacetrack"))
    return SpaceTrackConfig(
        identity=env("spacetrack_identity"), password=env("spacetrack_password")
    )
