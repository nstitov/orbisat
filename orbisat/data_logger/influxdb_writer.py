import os
import sys

import teleUnpackAndWrite
from config_data.config import load_server_config
from influxdb_auth import InfluxdbAuth
from rabbit_auth import QUEUE_NAME, RabbitAuth

config = load_server_config()


def main():
    influxdb = InfluxdbAuth(
        config.influxdb.url,
        config.influxdb.token,
        config.influxdb.org,
        config.influxdb.buket,
    )
    rabbit = RabbitAuth(
        config.rabbitmq.token, config.rabbitmq.HOST, config.rabbitmq.PORT
    )

    def callback_sender_to_influxdb(ch, method, properties, body):
        print("\n----------------------------------")
        print(f"Received: {body}")
        try:
            point = teleUnpackAndWrite.json_to_point(body)
            influxdb.write_point(point)
        except KeyboardInterrupt:
            raise KeyboardInterrupt()
        except Exception as e:
            print(f"Exception: ({e})")

    rabbit.channel.basic_consume(
        queue=QUEUE_NAME, on_message_callback=callback_sender_to_influxdb, auto_ack=True
    )
    print("[*] Waiting for messages. To exit press CTRL+C.")
    rabbit.channel.start_consuming()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
