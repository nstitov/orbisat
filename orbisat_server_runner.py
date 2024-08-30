"""Script to run OrbiSat TCP server.

This script must be run *FROM OUTSIDE* the orbisat pack!
This script is added to orbisat pack to copy when deploying the module to the
server using gitlab commit.

To run locally or by another server you should use "localhost" or own HOST IP.
"""

from orbisat.tcp.orbisat_tcp_server import HOST, PORT, OrbisatTcpServer

server = OrbisatTcpServer(HOST=HOST, PORT=PORT)
