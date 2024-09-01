"""Script to run OrbiSat TCP server.
To run locally or by another server you should use "localhost" or own HOST IP.
"""

from orbisat.tcp.orbisat_tcp_server import HOST, PORT, OrbisatTcpServer

server = OrbisatTcpServer(HOST=HOST, PORT=PORT)
