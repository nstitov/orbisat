"""Script to run short version of GUI for satellite communication visualization.

This script must be run *FROM OUTSIDE* the orbisat pack!

To run with nonlocal OrbiSat TCP Server you should use your own HOST IP.
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
