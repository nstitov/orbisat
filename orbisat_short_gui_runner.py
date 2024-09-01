"""Script to run short version of GUI for satellite communication visualization.
To run with nonlocal OrbiSat TCP Server you should use your own HOST IP.

Before running this script you should run orbisat_client_runner to add required data to
server.
"""

import sys

from PyQt5 import QtWidgets

from orbisat.orbisat_gui.gui_main_short import MainWindow
from orbisat.tcp.orbisat_tcp_client import HOST, PORT, OrbisatTcpClient

with OrbisatTcpClient(HOST=HOST, PORT=PORT) as orbisat_client:
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow(orbisat_client, "Samara", 57173)
    window.show()
    sys.exit(app.exec_())
