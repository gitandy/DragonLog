# DragonLog (c) 2025 by Andreas Schawo is licensed under CC BY-SA 4.0.
# To view a copy of this license, visit http://creativecommons.org/licenses/by-sa/4.0/
# based on work of TobbY, DG1ATN

import logging

from PyQt6 import QtWidgets, QtCore, QtGui
# noinspection PyPackageRequirements
import cv2
from pyzbar import pyzbar
from adif_file import util

from . import QSLQRReader_ui
from .Logger import Logger


class QSLQRReaderDialog(QtWidgets.QDialog, QSLQRReader_ui.Ui_QSLQRReaderDialog):
    qslQrReceived = QtCore.pyqtSignal(list)

    def __init__(self, parent, dragonlog, settings: QtCore.QSettings, logger: Logger):
        super().__init__(parent)
        self.dragonlog = dragonlog
        self.setupUi(self)

        self.log = logging.getLogger('QSLQRReaderDialog')
        self.log.addHandler(logger)
        self.log.setLevel(logger.loglevel)
        self.logger = logger
        self.log.debug('Initialising...')

        self.setWindowTitle(self.tr('QSL-QR-Reader'))

        self.__settings__ = settings
        self.__video_thread__ = None

        self.qslQrReceived.connect(self.processQSL)

        self.updateDeviceList()

    def updateDeviceList(self):
        self.videoSrcComboBox.clear()
        devices = []
        for i in range(10):
            cap = cv2.VideoCapture(i)
            test, frame = cap.read()
            if test:
                devices.append(i)
                cap.release()
        self.videoSrcComboBox.insertItems(0, [f'Video #{d}' for d in devices])

    def stopCapturing(self):
        self.log.debug(f'Stopping capture...')
        if self.__video_thread__:
            self.__video_thread__.stop()
            self.__video_thread__ = None

    def videoSrcChanged(self, src: str):
        self.stopCapturing()
        self.log.debug(f'Capturing from {src}')
        self.__video_thread__ = CaptureThread(None, int(src[-1:]))
        self.__video_thread__.pixmapChanged.connect(self.displayImage)
        self.__video_thread__.qrReceived.connect(self.processQSLData)
        self.__video_thread__.codeTypeFound.connect(self.displayMessage)
        self.__video_thread__.start()

    def displayImage(self, image: QtGui.QPixmap):
        self.displayLabel.setPixmap(image)

    def displayMessage(self, msg: str):
        self.msgLabel.setText(str(msg))
        QtCore.QTimer.singleShot(3000, self.msgLabel.clear)

    def processQSLData(self, data: str):
        """Process the raw QR code data"""
        records = []
        call = ''
        own_call = ''
        rec = {}
        try:
            data = data.replace(': ', ';')
            for i, ln in enumerate(data.split('\n')):
                if i == 0:
                    if ln.startswith('From') and 'To' in ln:
                        call_kv, own_call_kv = ln.split(' ')
                        call = call_kv.split(';')[1]
                        own_call = own_call_kv.split(';')[1]
                    else:
                        raise ValueError('No valid QSL-QR-Code')
                else:
                    if ln.startswith('Date'):
                        if rec:
                            records.append(rec)

                        rec = {'CALL': call,
                               'STATION_CALL': own_call,
                               'QSL_RCVD': 'Y',
                               }

                        for kv in ln.split(' '):
                            try:
                                k, v = kv.split(';')
                                if k == 'Date':
                                    rec['QSO_DATE'] = f'20{v[6:]}{v[3:5]}{v[:2]}'
                                elif k == 'Time':
                                    rec['TIME_ON'] = v.replace(':', '')
                                elif k == 'Band':
                                    if not 'BAND' in rec:
                                        rec['BAND'] = v
                                    rec['BAND_RX'] = v
                                elif k == 'Band_RX':
                                    rec['BAND'] = v
                                elif k == 'Mode':
                                    rec['MODE'] = v
                                elif k == 'RST':
                                    rec['RST_RCVD'] = v
                                elif k == 'QSL':
                                    if v == 'PSE':
                                        rec['QSL_SENT'] = 'R'  # requested
                                    elif v == 'TNX':
                                        rec['QSL_SENT'] = 'Y'  # assume we sent QSL
                            except ValueError:
                                # if key/value can't be split
                                pass
                    elif ln.startswith('Comment'):
                        try:
                            rec['COMMENT'] = ln.split(';', 1)[1]
                        except IndexError:
                            pass
                    elif not ln.strip() and rec:
                        records.append(rec)
        except (ValueError, IndexError):
            self.log.warning('No valid QSL-QR-Code')
            self.log.debug(data.strip())
            self.displayMessage(self.tr('No valid QSL-QR-Code'))
            self.videoSrcChanged(self.videoSrcComboBox.currentText())

        if records:
            self.displayMessage(self.tr('Found valid QSL-QR-Code'))
            self.qslQrReceived.emit(records)

    def processQSL(self, data: list[dict]):
        """Process the resulting QSL"""

        report = []
        for i, qsl in enumerate(data):
            timestamp = util.adif_date2iso(qsl['QSO_DATE']) + ' ' + util.adif_time2iso(qsl['TIME_ON'])
            qso = self.dragonlog.findQSO(timestamp, qsl['CALL'], 5)

            if qso:
                # Update QSL sent anyway
                cur_qsl_sent = qso[self.dragonlog.__sql_cols__.index('qsl_sent')]
                if cur_qsl_sent != 'Y' and qsl['QSL_SENT'] == 'R':
                    self.dragonlog.updateQSOField('qsl_sent', qso[0], 'R')
                    report.append(f'QSL #{i + 1}: {self.tr("Marked QSL sent as requested for QSO ")} #{qso[0]}')

                # Skip QSLed QSO or mark QSL rcvd
                cur_qsl_rcvd = qso[self.dragonlog.__sql_cols__.index('qsl_rcvd')]
                if cur_qsl_rcvd == 'Y':
                    report.append(f'QSL #{i + 1}: {self.tr("QSL already marked as received for QSO ")} #{qso[0]}')
                    continue
                self.dragonlog.updateQSOField('qsl_rcvd', qso[0], 'Y')
                report.append(f'QSL #{i + 1}: {self.tr("Marked QSL as received for QSO ")} #{qso[0]}')
            else:
                self.dragonlog.logImportQRCode(qsl)
                report.append(f'QSL #{i + 1}: ' + self.tr('Imported QSO to logbook'))

        if report:
            QtWidgets.QMessageBox.information(self, self.tr('QSL-QR-Code import'),
                                              '\n'.join(report))
            self.log.info(', '.join(report))
        self.videoSrcChanged(self.videoSrcComboBox.currentText())

    def accept(self):
        self.stopCapturing()
        super().accept()

    def reject(self):
        self.stopCapturing()
        super().reject()


class CaptureThread(QtCore.QThread):
    pixmapChanged = QtCore.pyqtSignal(QtGui.QPixmap)
    qrReceived = QtCore.pyqtSignal(str)
    codeTypeFound = QtCore.pyqtSignal(str)

    def __init__(self, parent, device):
        super().__init__(parent)
        self.device_id = device
        self.__run__ = True

    def run(self):
        cap = cv2.VideoCapture(self.device_id)
        while self.__run__:
            ret, cv_img = cap.read()
            if ret:
                self.pixmapChanged.emit(self.convertImage(cv_img))
                barcode = pyzbar.decode(cv_img)
                if barcode:
                    self.codeTypeFound.emit(self.tr('Found code type') + ': ' + barcode[0].type)
                    if barcode[0].type == 'QRCODE':
                        self.__run__ = False
                        self.qrReceived.emit(barcode[0].data.decode())
        cap.release()

    def stop(self):
        self.__run__ = False
        self.wait()

    @staticmethod
    def convertImage(cv_img):
        """Convert from an opencv image to QPixmap"""
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        pixmap = QtGui.QImage(bytes(rgb_image.data), w, h, bytes_per_line, QtGui.QImage.Format.Format_RGB888)
        p = pixmap.scaled(480, 360, QtCore.Qt.AspectRatioMode.KeepAspectRatio)
        return QtGui.QPixmap.fromImage(p)
