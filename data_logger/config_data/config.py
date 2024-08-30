import os
from dataclasses import dataclass
from typing import Union

from environs import Env


@dataclass
class RabbitMQ_config:
    username: str
    password: str
    HOST: Union[str, int]
    PORT: int

    def __post_init__(self):
        self.token = {"username": self.username, "password": self.password}


@dataclass
class InfluxDB_config:
    token: str
    url: str
    buket: str
    org: str


@dataclass
class ServerConfig:
    rabbitmq: RabbitMQ_config
    influxdb: InfluxDB_config


@dataclass
class ClientConfig:
    rabbitmq: RabbitMQ_config


def load_server_config() -> ServerConfig:
    env = Env()
    env.read_env(os.path.join(os.path.dirname(__file__), ".env.server"))
    return ServerConfig(
        rabbitmq=RabbitMQ_config(
            username=env("rabbit_username"),
            password=env("rabbit_password"),
            HOST=env("rabbit_host"),
            PORT=int(env("rabbit_port")),
        ),
        influxdb=InfluxDB_config(
            token=env("influxdb_token"),
            url=env("influxdb_url"),
            buket=env("influxdb_bucket"),
            org=env("influxdb_org"),
        ),
    )


def load_client_config() -> ClientConfig:
    env = Env()
    env.read_env(os.path.join(os.path.dirname(__file__), ".env.client"))
    return ClientConfig(
        rabbitmq=RabbitMQ_config(
            username=env("rabbit_username"),
            password=env("rabbit_password"),
            HOST=env("rabbit_host"),
            PORT=int(env("rabbit_port")),
        )
    )


if __name__ == "__main__":
    server_config = load_server_config()
    cleint_config = load_client_config()
    pass
