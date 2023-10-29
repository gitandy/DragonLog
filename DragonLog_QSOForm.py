import re
import socket

from PyQt6 import QtWidgets, QtCore, QtGui

import DragonLog_QSOForm_ui
from DragonLog_Settings import Settings


class QSOForm(QtWidgets.QDialog, DragonLog_QSOForm_ui.Ui_QSOFormDialog):
    REGEX_RSTFIELD = re.compile(r'[1-5][1-9][1-9aAcCkKmMsSxX]?')
    REGEX_LOCATOR = re.compile(r'[a-rA-R]{2}[0-9]{2}([a-xA-X]{2}([0-9]{2})?)?')

    def __init__(self, parent, bands: dict, modes: dict, settings: QtCore.QSettings, settings_form: Settings,
                 cb_channels: dict, hamlib_error: QtWidgets.QLabel):
        super().__init__(parent)
        self.setupUi(self)

        self.default_title = self.windowTitle()
        self.lastpos = None
        self.bands = bands
        self.modes = modes
        self.settings = settings
        self.settings_form = settings_form

        self.cb_channels = cb_channels
        self.channelComboBox.insertItems(0, ['-'] + list(cb_channels.keys()))

        self.bandComboBox.insertItems(0, bands.keys())

        self.stationChanged(True)
        self.identityChanged(True)

        self.hamlib_error = hamlib_error
        self.rig_modes = {'USB': 'SSB',
                          'LSB': 'SSB',
                          'CW': 'CW',
                          'CWR': 'CW',
                          'RTTY': 'RTTY',
                          'RTTYR': 'RTTY',
                          'AM': 'AM',
                          'FM': 'FM',
                          'WFM': 'FM',
                          }

        self.refreshTimer = QtCore.QTimer(self)
        self.refreshTimer.timeout.connect(self.refreshRigData)

        self.palette_default = QtGui.QPalette()
        self.palette_default.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor(255, 255, 255))
        self.palette_ok = QtGui.QPalette()
        self.palette_ok.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor(204, 255, 204))
        self.palette_empty = QtGui.QPalette()
        self.palette_empty.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor(255, 255, 204))
        self.palette_faulty = QtGui.QPalette()
        self.palette_faulty.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor(255, 204, 204))

    # noinspection PyBroadException
    def refreshRigData(self):
        if self.settings_form.isRigctldActive():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(('127.0.0.1', 4532))
                s.settimeout(1)
                try:
                    # Get frequency
                    s.sendall(b'\\get_freq\n')
                    freq_s = s.recv(1024).decode('utf-8').strip()
                    if freq_s.startswith('RPRT'):
                        self.hamlib_error.setText(self.tr('Error') + ':' + freq_s.split()[1])
                        print(f'rigctld error get_freq: {freq_s.split()[1]}')
                        return

                    try:
                        freq = float(freq_s) / 1000
                        for b in self.bands:
                            if freq < self.bands[b][1]:
                                if freq > self.bands[b][0]:
                                    self.bandComboBox.setCurrentText(b)
                                    self.freqDoubleSpinBox.setValue(freq)
                                break
                    except Exception:
                        pass

                    # Get mode
                    s.sendall(b'\\get_mode\n')
                    mode_s = s.recv(1024).decode('utf-8').strip()
                    if mode_s.startswith('RPRT'):
                        self.hamlib_error.setText(self.tr('Error') + ':' + mode_s.split()[1])
                        print(f'rigctld error get_mode: {mode_s.split()[1]}')
                        return

                    try:
                        mode, passband = [v.strip() for v in mode_s.split('\n')]
                        if mode in self.rig_modes:
                            self.modeComboBox.setCurrentText(self.rig_modes[mode])
                    except Exception:
                        pass

                    # Get power
                    if 'get level' in self.settings_form.rig_caps and 'get power2mW' in self.settings_form.rig_caps:
                        # Get power level
                        s.sendall(b'\\get_level RFPOWER\n')
                        pwrlvl_s = s.recv(1024).decode('utf-8').strip()
                        if pwrlvl_s.startswith('RPRT'):
                            self.hamlib_error.setText(self.tr('Error') + ':' + pwrlvl_s.split()[1])
                            print(f'rigctld error get_level: {pwrlvl_s.split()[1]}')
                            return

                        # Convert level to W
                        s.sendall(f'\\power2mW {pwrlvl_s} {freq_s} {mode}\n')
                        pwr_s = s.recv(1024).decode('utf-8').strip()
                        if pwr_s.startswith('RPRT'):
                            self.hamlib_error.setText(self.tr('Error') + ':' + pwr_s.split()[1])
                            print(f'rigctld error power2mW: {pwr_s.split()[1]}')
                            return

                        try:
                            pwr = int(int(pwr_s)/1000+.9)
                            self.powerSpinBox.setValue(pwr)
                        except Exception:
                            pass
                    else:
                        self.powerSpinBox.setValue(0)
                except socket.timeout:
                    self.hamlib_error.setText(self.tr('rigctld timeout'))
                    print('rigctld error: timeout')
                    self.refreshTimer.stop()
        else:
            self.refreshTimer.stop()

    def clear(self):
        self.callSignLineEdit.clear()
        self.nameLineEdit.clear()
        self.QTHLineEdit.clear()
        self.locatorLineEdit.clear()
        self.RSTSentLineEdit.setText('59')
        self.RSTRcvdLineEdit.setText('59')
        self.remarksTextEdit.clear()
        self.powerSpinBox.setValue(0)

        if bool(self.settings.value('station_cb/cb_by_default', 0)):
            self.bandComboBox.setCurrentText('11m')

        if self.bandComboBox.currentIndex() < 0:
            self.bandComboBox.setCurrentIndex(0)
        if self.modeComboBox.currentIndex() < 0:
            self.modeComboBox.setCurrentIndex(0)

    def reset(self):
        self.autoDateCheckBox.setEnabled(True)
        self.stationGroupBox.setCheckable(True)
        self.identityGroupBox.setCheckable(True)
        self.autoDateCheckBox.setChecked(True)
        self.stationGroupBox.setChecked(True)
        self.identityGroupBox.setChecked(True)

        self.setWindowTitle(self.default_title)

    def bandChanged(self, band: str):
        self.freqDoubleSpinBox.setMinimum(self.bands[band][0] - self.bands[band][2])
        self.freqDoubleSpinBox.setValue(self.bands[band][0] - self.bands[band][2])
        self.freqDoubleSpinBox.setMaximum(self.bands[band][1])
        self.freqDoubleSpinBox.setSingleStep(self.bands[band][2])

        self.modeComboBox.clear()
        if band == '11m':
            self.powerSpinBox.setMaximum(12)
            self.channelComboBox.setVisible(True)
            self.channelLabel.setVisible(True)
            self.freqDoubleSpinBox.setEnabled(False)
            self.channelComboBox.setCurrentIndex(-1)
            self.channelComboBox.setCurrentIndex(0)

            if self.stationGroupBox.isChecked():
                self.radioLineEdit.setText(self.settings.value('station_cb/radio', ''))
                self.antennaLineEdit.setText(self.settings.value('station_cb/antenna', ''))

            if self.identityGroupBox.isChecked():
                self.ownCallSignLineEdit.setText(self.settings.value('station_cb/callSign', ''))
        else:
            self.modeComboBox.insertItems(0, self.modes['AFU'].keys())
            self.modeComboBox.setCurrentIndex(0)
            self.powerSpinBox.setMaximum(1000)
            self.channelComboBox.setVisible(False)
            self.channelLabel.setVisible(False)
            self.freqDoubleSpinBox.setEnabled(True)

            if self.stationGroupBox.isChecked():
                self.radioLineEdit.setText(self.settings.value('station/radio', ''))
                self.antennaLineEdit.setText(self.settings.value('station/antenna', ''))

            if self.identityGroupBox.isChecked():
                self.ownCallSignLineEdit.setText(self.settings.value('station/callSign', ''))

    def stationChanged(self, checked):
        if checked:
            self.ownQTHLineEdit.setText(self.settings.value('station/QTH', ''))
            self.ownLocatorLineEdit.setText(self.settings.value('station/locator', ''))

            if self.bandComboBox.currentText() == '11m':
                self.radioLineEdit.setText(self.settings.value('station_cb/radio', ''))
                self.antennaLineEdit.setText(self.settings.value('station_cb/antenna', ''))
            else:
                self.radioLineEdit.setText(self.settings.value('station/radio', ''))
                self.antennaLineEdit.setText(self.settings.value('station/antenna', ''))

    def identityChanged(self, checked):
        if checked:
            self.ownNameLineEdit.setText(self.settings.value('station/name', ''))

            if self.bandComboBox.currentText() == '11m':
                self.ownCallSignLineEdit.setText(self.settings.value('station_cb/callSign', ''))
            else:
                self.ownCallSignLineEdit.setText(self.settings.value('station/callSign', ''))

    def channelChanged(self, ch):
        if ch and ch != '-':
            self.freqDoubleSpinBox.setValue(self.cb_channels[ch]['freq'])
            self.modeComboBox.clear()
            self.modeComboBox.insertItems(0, self.cb_channels[ch]['modes'])
            self.modeComboBox.setCurrentIndex(0)
        else:
            self.freqDoubleSpinBox.setValue(self.bands['11m'][0] - self.bands['11m'][2])

    def rstRcvdChanged(self, txt):
        if not txt:
            self.RSTRcvdLineEdit.setPalette(self.palette_empty)
        elif re.fullmatch(self.REGEX_RSTFIELD, txt):
            self.RSTRcvdLineEdit.setPalette(self.palette_ok)
        else:
            self.RSTRcvdLineEdit.setPalette(self.palette_faulty)

    def rstSentChanged(self, txt):
        if not txt:
            self.RSTSentLineEdit.setPalette(self.palette_empty)
        elif re.fullmatch(self.REGEX_RSTFIELD, txt):
            self.RSTSentLineEdit.setPalette(self.palette_ok)
        else:
            self.RSTSentLineEdit.setPalette(self.palette_faulty)

    def callSignChanged(self, txt):
        if not txt:
            self.callSignLineEdit.setPalette(self.palette_empty)
        else:
            self.callSignLineEdit.setPalette(self.palette_ok)

    def locatorChanged(self, txt):
        if not txt:
            self.locatorLineEdit.setPalette(self.palette_empty)
        elif re.fullmatch(self.REGEX_LOCATOR, txt):
            self.locatorLineEdit.setPalette(self.palette_ok)
        else:
            self.locatorLineEdit.setPalette(self.palette_faulty)

    def exec(self) -> int:
        if self.lastpos:
            self.move(self.lastpos)

        self.callSignLineEdit.setFocus()

        if self.settings_form.isRigctldActive():
            self.refreshTimer.start(500)

        self.callSignChanged(self.callSignLineEdit.text())
        self.locatorChanged(self.locatorLineEdit.text())
        self.rstSentChanged(self.RSTSentLineEdit.text())
        self.rstRcvdChanged(self.RSTRcvdLineEdit.text())

        return super().exec()

    def hideEvent(self, e):
        self.lastpos = self.pos()
        self.refreshTimer.stop()
        e.accept()
