import logging
from typing import Literal, Union

import pika
import pika.exceptions

HOST = "192.168.100.89"
PORT = 5672
QUEUE_NAME = "hello"


class RabbitAuth:
    """A class used to represent channel in RabbitMQ to transmit messages.

    Methods:
        send_message(msg[, exchange[, routing_key]]): Send message to RabbitMQ exchange
    """

    def __init__(
        self,
        token: dict[Literal["username", "password"], str],
        HOST: Union[str, int] = PORT,
        PORT: int = HOST,
        *,
        queue_name: str = QUEUE_NAME,
    ):
        """
        Args:
            token (dict):   username (str) - Login for RabbitMQ
                            password (str) - Password for RabbitMQ
            HOST (str | int): Hostname or IP Address to connect to
            PORT (int): TCP port to connect to
            queue_name (str): RabbitMQ queue name for trasmition data
        """
        self._queue_name = queue_name

        self._credentials = pika.PlainCredentials(
            username=token.get("username"), password=token.get("password")
        )
        self._parameters = pika.ConnectionParameters(
            host=HOST,
            port=PORT,
            credentials=self._credentials,
        )

        self._create_blocking_channel()

    def __del__(self) -> None:
        """Close channel and connection with RabbitMQ."""
        if hasattr(self, "channel") and self.channel:
            self.channel.close()
        if hasattr(self, "_connection") and self._connection:
            self._connection.close()

    def _create_blocking_channel(self) -> None:
        """Create blocking connection with RabbitMQ and channel.

        Returns:
        """
        self._connection = pika.BlockingConnection(self._parameters)
        self.channel = self._connection.channel()
        self.channel.queue_declare(queue=self._queue_name)

    def _retry_send_message(self, msg: str, exchange: str, routing_key: str) -> None:
        """Create blocking connection with RabbitMQ and send message retry.

        Args:
            exchange (str): Name of the exchange to publish to
            msg (str): Sending message
            routing_key (str): Routing key to bind on

        Raises:
            Any error becouse retry sending and this don't care.

        Returns:
        """
        try:
            self._create_blocking_channel()
            self.channel.basic_publish(
                exchange=exchange, body=msg, routing_key=routing_key
            )
        except Exception:
            self.logger.exception("Connection retry to RabbitMQ failed.")

    def send_message(
        self, msg: str, exchange: str = "", routing_key: str = QUEUE_NAME
    ) -> None:
        """Send message to RabbitMQ.

        Args:
            msg (str): Sending message
            exchange (str): Name of the exchange to publish to
                (default is "")
            routing_key (str): Routing key to bind on
                (default is "hello")

        Returns:
        """
        # Logger is here because this module used to in global logging config, so at the
        # start of file logging haven't information about logger with this filename
        self.logger = logging.getLogger(__name__)

        while True:
            try:
                self.channel.basic_publish(
                    exchange=exchange, body=msg, routing_key=routing_key
                )
                break
            except pika.exceptions.ConnectionClosedByBroker:
                self.logger.exception("RabbitMQ closed connection.")
                continue
            except pika.exceptions.AMQPChannelError:
                self.logger.exception(f"RabbitMQ chanel error, retrying connection.")
                self._retry_send_message(msg, exchange, routing_key)
                continue
            except pika.exceptions.AMQPConnectionError:
                self.logger.exception(
                    "RabbitMQ connection was closed, retrying connection."
                )
                self._retry_send_message(msg, exchange, routing_key)
                continue


if __name__ == "__main__":
    import json
    from datetime import datetime

    from config_data.config import load_client_config

    config = load_client_config()

    rabbit_sender = RabbitAuth(config.rabbitmq.token, HOST=HOST, PORT=PORT)

    data = {
        "time": datetime.now().isoformat() + "+04:00",
        "measurement": "TEST",
        "tags": {"location": "TEST"},
        "fields": {"a": 1, "b": 2},
    }
    rabbit_sender.send_message(json.dumps(data))
