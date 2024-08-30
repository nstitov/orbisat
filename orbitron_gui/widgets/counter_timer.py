from PyQt5 import QtCore


class CounterTimer(QtCore.QTimer):
    """A dataclass used to represent timer with inner counter of starting and finishing
    methods."""

    def __init__(self):
        super().__init__()
        self.counter = 0

    def start(self):
        """Increase inner counter."""
        self.counter += 1
        if self.counter == 1:
            super().start()

    def stop(self):
        """Decrease inner counter and stop timer if counter is zero."""
        self.counter -= 1
        if self.counter == 0:
            super().stop()
