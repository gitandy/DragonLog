import socket

from PyQt6 import QtWidgets, QtCore

import DragonLog_QSOForm_ui
from DragonLog_Settings import Settings


class QSOForm(QtWidgets.QDialog, DragonLog_QSOForm_ui.Ui_QSOFormDialog):
    def __init__(self, parent, bands: dict, modes: dict, settings: QtCore.QSettings, settings_form: Settings,
                 cb_channels: dict):
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

    # noinspection PyBroadException
    def refreshRigData(self):
        if self.settings_form.isRigctldActive():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(('127.0.0.1', 4532))

                s.sendall(b'\\get_freq\n')
                freq_s = s.recv(1024).decode('utf-8')
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

                s.sendall(b'\\get_mode\n')
                mode_s = s.recv(1024).decode('utf-8').strip()
                try:
                    mode, passband = [v.strip() for v in mode_s.split('\n')]
                    if mode in self.rig_modes:
                        self.modeComboBox.setCurrentText(self.rig_modes[mode])
                except Exception:
                    pass

                if 'get power2mW' in self.settings_form.rig_caps:
                    s.sendall(b'\\power2mW\n')
                    pwr_s = s.recv(1024).decode('utf-8')
                    try:
                        pwr = int(float(pwr_s)*1000+.9)
                        self.powerSpinBox.setValue(pwr)
                    except Exception:
                        pass
                else:
                    self.powerSpinBox.setValue(0)
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

    def exec(self) -> int:
        if self.lastpos:
            self.move(self.lastpos)

        self.callSignLineEdit.setFocus()

        if self.settings_form.isRigctldActive():
            self.refreshTimer.start(500)

        return super().exec()

    def hideEvent(self, e):
        self.lastpos = self.pos()
        self.refreshTimer.stop()
        e.accept()
