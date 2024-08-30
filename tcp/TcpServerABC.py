import json
import logging
import socket
import threading
import time
from abc import ABC, abstractmethod
from datetime import datetime
from enum import IntEnum
from typing import Any, Optional, Union

from ..exceptions.tcp_exceptions import (
    TCPServerBodyRequestError,
    TCPServerResponseError,
    TCPServerUnexpectedResponseError,
)

logger = logging.getLogger(__name__)

HOST = "localhost"
PORT = 33333


class ResponseType(IntEnum):
    """An ENUM class to represent TCP server response types."""

    NONE = 0
    CONFIGURE = 1
    PREDICT = 2
    TLE_UPDATE = 3
    SYNC = 4
    RADAR = 5
    GET_DATA = 6
    ERROR = 7


class TCPServer(ABC):
    """An abstract class to represent a TCP server.

    Methods:
        handle_request_msg(msg): Abstract method which should be reloaded. Handle
            request message depends on its body.
    """

    _ThreadCounter: int = 0

    def __init__(self, HOST: Union[str, int] = HOST, PORT: int = PORT):
        """
        Args:
            HOST (str | int): Hostname or IP Address to connect to
                (default is localhost, i.e. "127.0.0.1")
            PORT (int): TCP port to connect to
                (default is 32768)
        """
        self._HOST = HOST
        self._PORT = PORT
        sock = socket.socket()

        try:
            sock.bind((self._HOST, self._PORT))
        except socket.error:
            logger.exception("Error during bind TCP Server to HOST and PORT.")

        sock.listen()
        logger.info(f"Server is listing on the port {self._PORT}...")

        while True:
            self._accept_connections(sock)

    def _accept_connections(self, sock: socket.socket) -> None:
        """Accept a connection and run communication in separated thread.

        Args:
            sock (socket): Socket used to accept connections

        Returns:
        """
        Client, address = sock.accept()
        self._ThreadCounter += 1
        logger.info(
            f"Connected to: {address[0]}:{str(address[1])}, "
            f"{self._ThreadCounter} active threads."
        )
        threading.Thread(target=self._client_handler, args=(Client, address)).start()

    def _client_handler(self, connection: socket.socket, address) -> None:
        """Get messages from socket in cycle and send requested data back to socket if
        required. To stop cycle send message "CLOSE".

        Args:
            connections (socket): The socket from which messages (data) is coming

        Returns:
        """
        while True:
            data = connection.recv(2048)
            message = data.decode("utf-8")
            if message == "CLOSE":
                self._ThreadCounter -= 1
                logger.info(
                    f"Disconnected from: {address[0]}:{str(address[1])}, "
                    f"{self._ThreadCounter} active threads."
                )
                break

            if message:
                msg: dict = json.loads(message)

                if "request" in msg:
                    logger.info(f'{datetime.utcnow()}: {msg["request"]}')
                    try:
                        resp = self.handle_request_message(msg)
                    except TCPServerBodyRequestError:
                        logger.exception("Command to TCP server is failed.")
                        resp = (ResponseType.ERROR,)
                    except Exception:
                        logger.exception("Unexpected error during message handle.")
                        resp = (ResponseType.ERROR,)

                    if resp[0] == ResponseType.GET_DATA:
                        data = json.dumps(resp[1]) + json.dumps(resp[0])
                        connection.sendall(data.encode("utf-8"))
                    else:
                        connection.sendall(json.dumps(resp[0]).encode("utf-8"))

        connection.close()

    @abstractmethod
    def handle_request_message(
        self, msg: dict
    ) -> tuple[ResponseType, Optional[dict[str, Any]]]:
        """Processes the request massage depending on its body.

        Args:
            msg (dict): message from incoming socket in JSON (dict) format

        Returns:
            tuple[ResponseType, Optional[dict[str, Any]]]: the first tuple element is
                ResponseType and the second is some data if required else None
        """
        pass


class TCPClient(ABC):
    """An abstract class to represent TCP client. TCP client should be used with context
    manager to control connection. To use this inherit from this and add new methods to
    send (get) messages to (from) TCP server.

    Attributes:
        sock (socket): socket to connect to TCP server. Socket is set by HOST and PORT.
    """

    _RESP_SIZE = 4
    _DATA_RESP_SIZE = 2048
    _DATA_RESP_EXTRA_SIZE = 8192

    def __init__(self, HOST: Union[str, int] = HOST, PORT: int = PORT):
        """
        Args:
            HOST (str | int): Hostname or IP Address to connect to
                (default is localhost, i.e. "127.0.0.1")
            PORT (int): TCP port to connect to
                (default is 32768)
        """
        self._HOST = HOST
        self._PORT = PORT
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def __enter__(self):
        self.create_connection()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close_connection()
        if isinstance(exc_type, OSError):
            logger.exception(f"Error during connection to TCP server: {exc_value}.")
            return True
        return False

    def _check_resp(self, resp: str, req_resp: ResponseType, request_name: str) -> None:
        if int(resp) == req_resp.value:
            logger.info(
                f"Request {request_name} to TCP server is successfully completed."
            )
        elif int(resp) == ResponseType.ERROR.value:
            logger.warning(f"Error during {request_name} request.")
            raise TCPServerResponseError(request_name)
        else:
            logger.warning(f"Unexpected result of {request_name} request.")
            raise TCPServerUnexpectedResponseError(request_name)

    def create_connection(self):
        try:
            self.sock.connect((self._HOST, self._PORT))
            time.sleep(1)
        except TimeoutError:
            logger.exception("TCP server socket is unavailable.")
        except OSError:
            logger.exception("TCP server socket already is opened.")
        except Exception:
            logger.exception("Unexpected error during connection to TCP server.")

    def close_connection(self):
        self.sock.sendall("CLOSE".encode("utf-8"))
        self.sock.close()
