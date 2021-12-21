from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QImage


class QCamera(QObject):
    connected = pyqtSignal(bool)
    imageAcquired = pyqtSignal(QImage)

    __streaming = False

    def stream(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def connect(self) -> None:
        pass

    def release(self) -> None:
        pass

    @property
    def is_streaming(self) -> bool:
        return self.__streaming
