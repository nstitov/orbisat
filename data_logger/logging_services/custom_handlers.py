from logging import Handler, LogRecord

from ..config_data.config import load_client_config
from ..rabbit_auth import RabbitAuth


class InfluxdbDataHandler(Handler):
    """A class used to represent Handler for handling data logs and sending them to
    RabbitMQ. After this the special script get logs from RabbitMQ and send them to
    InfluxDB.
    """

    def __init__(self):
        config = load_client_config()
        try:
            self.rabbit = RabbitAuth(
                token=config.rabbitmq.token,
                HOST=config.rabbitmq.HOST,
                PORT=config.rabbitmq.PORT,
            )
        except:
            self.rabbit = None
        super().__init__()




    def emit(self, record: LogRecord):
        if self.rabbit:
            msg = self.format(record)
            self.rabbit.send_message(msg)
