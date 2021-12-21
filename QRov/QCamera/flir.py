import PySpin
import cv2

from PyQt5.QtCore import QObject, QTimer, pyqtSignal, pyqtSlot, pyqtProperty
from PyQt5.QtGui import QImage

from . import QCamera


class QFlirTimers(QObject):
    acquisitionTimer = QTimer()
    connectionTimer = QTimer()


class QFlirSignals(QObject):
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    acquired = pyqtSignal(QImage)


class QFlirCamera(QObject):
    signals = QFlirSignals()
    timers = QFlirTimers()

    def __init__(self, parent=None):
        QObject.__init__(self, parent)

        self.__system: PySpin.System = PySpin.System.GetInstance()

        self.__streaming = False
        self.__connected = False
        self.__tryingToConnect = False

        self.timers.acquisitionTimer.timeout.connect(self.read)
        self.timers.connectionTimer.timeout.connect(self.try_connect)
        self.signals.connected.connect(self.timers.connectionTimer.stop)

    def __del__(self):
        self.release()

    @pyqtProperty(bool)
    def connected(self) -> bool:
        return self.__connected

    @pyqtProperty(bool)
    def streaming(self) -> bool:
        return self.__streaming

    def try_connect(self) -> None:
        self.__tryingToConnect = True
        print("TRY CONNECTING TO CAMERA")
        if self.connected:
            return

        self.__cameraList: PySpin.CameraList = self.__system.GetCameras()

        if self.__cameraList.GetSize() == 0:
            self.__cameraList.Clear()
            return

        self.__camera: PySpin.Camera = self.__cameraList.GetByIndex(0)
        self.__camera.Init()

        if self.__camera.AcquisitionMode.GetAccessMode() == PySpin.RW:
            self.__camera.AcquisitionMode.SetValue(
                PySpin.AcquisitionMode_Continuous)

        if self.__camera.PixelFormat.GetAccessMode() == PySpin.RW:
            self.__camera.PixelFormat.SetValue(PySpin.PixelFormat_BayerRG8)

        self.__connected = True
        self.__tryingToConnect = False
        self.__camera.BeginAcquisition()

        self.timers.acquisitionTimer.start(16)
        self.signals.connected.emit()

    def connect(self) -> None:
        if self.connected:
            return

        self.timers.connectionTimer.start(1000)

    @pyqtSlot()
    def disconnect(self) -> None:
        if self.__tryingToConnect or self.__connected:
            self.__tryingToConnect = False
            self.timers.connectionTimer.stop()

            self.__camera.EndAcquisition()

            self.timers.acquisitionTimer.stop()
            self.__streaming = False

            if self.__camera:
                self.__camera.DeInit()
                del self.__camera

            if self.__cameraList:
                self.__cameraList.Clear()

            self.__connected = False
            self.signals.disconnected.emit()

    @pyqtSlot()
    def stream(self) -> None:
        if not self.connected or self.streaming:
            return

        self.__camera.BeginAcquisition()

        self.timers.acquisitionTimer.start(16)
        self.__streaming = True

    @pyqtSlot()
    def stop(self) -> None:
        if not self.connected or not self.streaming:
            return

        self.__camera.EndAcquisition()

        self.timers.acquisitionTimer.stop()
        self.__streaming = False

    @pyqtSlot()
    def read(self):
        if not self.connected:
            return

        try:
            camera_image: PySpin.Image = self.__camera.GetNextImage()
            if camera_image.IsIncomplete():
                return

            h = camera_image.GetHeight()
            w = camera_image.GetWidth()

            num_channels = camera_image.GetNumChannels()
            if num_channels > 1:
                camera_image_data = camera_image.GetNDArray().reshape(h, w, num_channels)
            else:
                camera_image_data = camera_image.GetData().reshape(h, w)

            frame = cv2.cvtColor(camera_image_data, cv2.COLOR_BAYER_RG2RGB)
            image = QImage(
                frame.data, frame.shape[1], frame.shape[0], QImage.Format_RGB888).rgbSwapped()

            self.signals.acquired.emit(image)

            camera_image.Release()
        except:
            pass

    def release(self):
        self.disconnect()

        self.__system.ReleaseInstance()
