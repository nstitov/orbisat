"""Script to run Orbitron TCP server.

This script must be run *FROM OUTSIDE* the new_orbitron pack!
This script is added to new_orbitron pack to copy when deploying the module to the
server using gitlab commit.

To run locally or by another server you should use "localhost" or own HOST IP.
"""

from new_orbitron.tcp.orbitron_tcp_server import HOST, PORT, OrbitronTcpServer

server = OrbitronTcpServer(HOST=HOST, PORT=PORT)
