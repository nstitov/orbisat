"""Script to run GUI for satellite communication visualization.
To run with nonlocal OrbiSat TCP Server you should use your own HOST IP.
"""

import sys

from PyQt5 import QtWidgets
from PyQt5.QtGui import QFont

from orbisat.orbisat_gui.gui_main_full import OrbisatWindow
from orbisat.tcp.orbisat_tcp_client import HOST, PORT, OrbisatTcpClient

with OrbisatTcpClient(HOST=HOST, PORT=PORT) as orbisat_client:
    app = QtWidgets.QApplication(sys.argv)

    font = QFont()
    font.setPointSize(10)
    app.setFont(font)

    window = OrbisatWindow(orbisat_client)
    window.show()
    sys.exit(app.exec_())
