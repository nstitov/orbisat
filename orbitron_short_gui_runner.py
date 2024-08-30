"""Script to run short version of GUI for satellite communication visualization.

This script must be run *FROM OUTSIDE* the new_orbitron pack!

To run with nonlocal Orbitron TCP Server you should use your own HOST IP.
"""

import sys

from PyQt5 import QtWidgets

from new_orbitron.orbitron_gui.gui_main_short import MainWindow
from new_orbitron.tcp.orbitron_tcp_client import HOST, PORT, OrbitronTcpClient

with OrbitronTcpClient(HOST=HOST, PORT=PORT) as orbitron_client:
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow(orbitron_client, "Samara", 57173)
    window.show()
    sys.exit(app.exec_())
