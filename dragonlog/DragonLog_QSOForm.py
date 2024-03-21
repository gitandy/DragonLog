import os
import math
import socket
import logging

import maidenhead
from PyQt6 import QtWidgets, QtCore, QtGui

from . import DragonLog_QSOForm_ui
from .Logger import Logger
from .DragonLog_Settings import Settings
from .DragonLog_RegEx import REGEX_CALL, REGEX_RSTFIELD, REGEX_LOCATOR, check_format, check_call
from .DragonLog_CallBook import (CallBook, CallBookType, CallBookData, SessionExpiredException,
                                 MissingADIFFieldException, LoginException, CallsignNotFoundException)
from .DragonLog_eQSL import (EQSL, EQSLADIFFieldException, EQSLLoginException,
                             EQSLRequestException, EQSLUserCallMatchException, EQSLQSODuplicateException)
from .DragonLog_LoTW import LoTW


class QSOForm(QtWidgets.QDialog, DragonLog_QSOForm_ui.Ui_QSOFormDialog):
    def __init__(self, parent, bands: dict, modes: dict, settings: QtCore.QSettings, settings_form: Settings,
                 cb_channels: dict, hamlib_error: QtWidgets.QLabel, logger: Logger):
        super().__init__(parent)
        self.setupUi(self)

        self.log = logging.getLogger('QSOForm')
        self.log.addHandler(logger)
        self.log.setLevel(logger.loglevel)
        self.logger = logger
        self.log.debug('Initialising...')

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
        self.__last_mode__ = ''

        self.__change_mode__ = False

        self.refreshTimer = QtCore.QTimer(self)
        self.refreshTimer.timeout.connect(self.refreshRigData)

        self.timeTimer = QtCore.QTimer(self)
        self.timeTimer.timeout.connect(self.refreshTime)

        self.palette_default = QtGui.QPalette()
        self.palette_default.setColor(QtGui.QPalette.ColorGroup.Active, QtGui.QPalette.ColorRole.Base,
                                      QtGui.QColor(255, 255, 255))
        self.palette_ok = QtGui.QPalette()
        self.palette_ok.setColor(QtGui.QPalette.ColorGroup.Active, QtGui.QPalette.ColorRole.Base,
                                 QtGui.QColor(204, 255, 204))
        self.palette_empty = QtGui.QPalette()
        self.palette_empty.setColor(QtGui.QPalette.ColorGroup.Active, QtGui.QPalette.ColorRole.Base,
                                    QtGui.QColor(255, 255, 204))
        self.palette_faulty = QtGui.QPalette()
        self.palette_faulty.setColor(QtGui.QPalette.ColorGroup.Active, QtGui.QPalette.ColorRole.Base,
                                     QtGui.QColor(255, 204, 204))
        self.palette_worked = QtGui.QPalette()
        self.palette_worked.setColor(QtGui.QPalette.ColorGroup.Active, QtGui.QPalette.ColorRole.Base,
                                     QtGui.QColor(204, 204, 255))

        self.worked_dialog: QtWidgets.QListWidget = None
        self._create_worked_dlg_()

        self.callbook = CallBook(CallBookType.HamQTH,
                                 f'{self.parent().programName}-{self.parent().programVersion}',
                                 self.logger)
        self.eqsl = EQSL(self.parent().programName, self.logger)
        self.eqsl_url = ''

        self.lotw = LoTW()

        view_only_widgets = (
            self.qslAccBureauCheckBox,
            self.qslAccDirectCheckBox,
            self.qslAccElectronicCheckBox,
            self.eqslSentCheckBox,
            self.eqslRcvdCheckBox,
            self.hamQTHuplRadioButton,
            self.hamQTHmodRadioButton,
        )

        for w in view_only_widgets:
            w.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            w.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)

    def _create_worked_dlg_(self):
        self.worked_dialog = QtWidgets.QListWidget(self)
        self.worked_dialog.setMinimumHeight(100)
        self.worked_dialog.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        self.worked_dialog.setSortingEnabled(True)

    def setWorkedBefore(self, worked: list = None):
        self.worked_dialog.clear()
        if worked:
            self.worked_dialog.addItems(worked)
            call_edit_pos = self.callSignLineEdit.pos()
            call_edit_pos.setX(call_edit_pos.x())
            call_edit_pos.setY(call_edit_pos.y() + self.callSignLineEdit.height())
            self.worked_dialog.move(call_edit_pos)
            self.worked_dialog.show()
        else:
            self.worked_dialog.hide()

    def refreshTime(self):
        if self.autoDateCheckBox.isChecked():
            dt = QtCore.QDateTime.currentDateTimeUtc()
            self.dateEdit.setDate(dt.date())
            self.timeEdit.setTime(dt.time())

    def setStartTimeNow(self):
        dt = QtCore.QDateTime.currentDateTimeUtc()
        self.dateOnEdit.setDate(dt.date())
        self.timeOnEdit.setTime(dt.time())

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
                        self.log.error(f'rigctld error get_freq: {freq_s.split()[1]}')
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
                        self.log.error(f'rigctld error get_mode: {mode_s.split()[1]}')
                        return

                    try:
                        mode, passband = [v.strip() for v in mode_s.split('\n')]
                        if mode in self.rig_modes and mode != self.__last_mode__:
                            self.modeComboBox.setCurrentText(self.rig_modes[mode])
                            self.__last_mode__ = mode
                    except Exception:
                        pass

                    # Get power
                    if 'get level' in self.settings_form.rig_caps and 'get power2mw' in self.settings_form.rig_caps:
                        # Get power level
                        s.sendall(b'\\get_level RFPOWER\n')
                        pwrlvl_s = s.recv(1024).decode('utf-8').strip()
                        if pwrlvl_s.startswith('RPRT'):
                            self.hamlib_error.setText(self.tr('Error') + ':' + pwrlvl_s.split()[1])
                            self.log.error(f'rigctld error get_level: {pwrlvl_s.split()[1]}')
                            return

                        # Convert level to W
                        s.sendall(f'\\power2mW {pwrlvl_s} {freq_s} {mode}\n'.encode())
                        pwr_s = s.recv(1024).decode('utf-8').strip()
                        if pwr_s.startswith('RPRT'):
                            self.hamlib_error.setText(self.tr('Error') + ':' + pwr_s.split()[1])
                            self.log.error(f'rigctld error power2mW: {pwr_s.split()[1]}')
                            return

                        try:
                            pwr = int(int(pwr_s) / 1000 + .9)
                            self.powerSpinBox.setValue(pwr)
                        except Exception:
                            pass
                    else:
                        self.powerSpinBox.setValue(0)
                except socket.timeout:
                    self.hamlib_error.setText(self.tr('rigctld timeout'))
                    self.log.error('rigctld error: timeout')
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

        self.qslBurDirGroupBox.setChecked(False)
        self.qslViaLineEdit.clear()
        self.qslBureauRadioButton.setChecked(False)
        self.qslDirectRadioButton.setChecked(False)
        self.qslAccBureauCheckBox.setChecked(False)
        self.qslAccDirectCheckBox.setChecked(False)
        self.qslAccElectronicCheckBox.setChecked(False)
        self.qslMessageTextEdit.clear()
        self.qslSentCheckBox.setChecked(False)
        self.qslRcvdCheckBox.setChecked(False)

        self.eqslSentCheckBox.setChecked(False)
        self.eqslRcvdCheckBox.setChecked(False)
        self.eqslLinkLabel.setEnabled(False)
        self.eqslLinkLabel.setText(self.tr('Link to eQSL Card'))
        self.eqslDownloadPushButton.setEnabled(False)

        self.hamQTHGroupBox.setChecked(False)
        self.hamQTHmodRadioButton.setChecked(True)  # Just not check upload

        self.toolBox.setCurrentIndex(0)

    def reset(self):
        self.autoDateCheckBox.setEnabled(True)
        self.autoDateCheckBox.setChecked(True)
        self.stationGroupBox.setChecked(True)
        self.identityGroupBox.setChecked(True)

        self.setWindowTitle(self.default_title)

    def setChangeMode(self, activate=True):
        self.__change_mode__ = activate

        if activate:
            self.stationGroupBox.setChecked(False)
            self.stationGroupBox.setCheckable(False)
            self.stationGroupBox.setTitle(self.tr('Station'))
            self.identityGroupBox.setChecked(False)
            self.identityGroupBox.setCheckable(False)
            self.identityGroupBox.setTitle(self.tr('Identity'))
            self.autoDateCheckBox.setChecked(False)
            self.autoDateCheckBox.setEnabled(False)
            self.timeNowPushButton.setEnabled(False)
        else:
            self.stationGroupBox.setCheckable(True)
            self.stationGroupBox.setTitle(self.tr('Configured station'))
            self.stationGroupBox.setChecked(True)
            self.identityGroupBox.setCheckable(True)
            self.identityGroupBox.setTitle(self.tr('Configured identity'))
            self.identityGroupBox.setChecked(True)
            self.autoDateCheckBox.setChecked(True)
            self.autoDateCheckBox.setEnabled(True)
            self.timeNowPushButton.setEnabled(True)

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
            self.searchCallbookPushButton.setEnabled(False)
            self.uploadPushButton.setEnabled(False)
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
            self.searchCallbookPushButton.setEnabled(True)
            self.uploadPushButton.setEnabled(True)

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
        elif check_format(REGEX_RSTFIELD, txt):
            self.RSTRcvdLineEdit.setPalette(self.palette_ok)
        else:
            self.RSTRcvdLineEdit.setPalette(self.palette_faulty)

    def rstSentChanged(self, txt):
        if not txt:
            self.RSTSentLineEdit.setPalette(self.palette_empty)
        elif check_format(REGEX_RSTFIELD, txt):
            self.RSTSentLineEdit.setPalette(self.palette_ok)
        else:
            self.RSTSentLineEdit.setPalette(self.palette_faulty)

    def callSignChanged(self, txt):
        self.setWorkedBefore()
        if not txt:
            self.callSignLineEdit.setPalette(self.palette_empty)
        elif check_format(REGEX_CALL, txt):
            worked = self.parent().workedBefore(check_call(txt)[1])
            if not self.__change_mode__ and worked:
                self.setWorkedBefore(worked)
                self.callSignLineEdit.setPalette(self.palette_worked)
            else:
                self.callSignLineEdit.setPalette(self.palette_ok)
        elif self.bandComboBox.currentText() == '11m':
            self.callSignLineEdit.setPalette(self.palette_ok)
        else:
            self.callSignLineEdit.setPalette(self.palette_faulty)

    def locatorChanged(self, txt):
        if not txt:
            self.locatorLineEdit.setPalette(self.palette_empty)
        elif check_format(REGEX_LOCATOR, txt):
            self.locatorLineEdit.setPalette(self.palette_ok)
        else:
            self.locatorLineEdit.setPalette(self.palette_faulty)

    def ownCallSignChanged(self, txt):
        if not txt:
            self.ownCallSignLineEdit.setPalette(self.palette_empty)
        elif check_format(REGEX_CALL, txt):
            self.ownCallSignLineEdit.setPalette(self.palette_ok)
        elif self.bandComboBox.currentText() == '11m':
            self.ownCallSignLineEdit.setPalette(self.palette_ok)
        else:
            self.ownCallSignLineEdit.setPalette(self.palette_faulty)

    def ownLocatorChanged(self, txt):
        if not txt:
            self.ownLocatorLineEdit.setPalette(self.palette_empty)
        elif check_format(REGEX_LOCATOR, txt):
            self.ownLocatorLineEdit.setPalette(self.palette_ok)
        else:
            self.ownLocatorLineEdit.setPalette(self.palette_faulty)

    def calc_distance(self, mh_pos1: str, mh_pos2: str):
        # noinspection PyBroadException
        try:
            pos1 = maidenhead.to_location(mh_pos1, True)
            pos2 = maidenhead.to_location(mh_pos2, True)

            mlat = math.radians(pos1[0])
            mlon = math.radians(pos1[1])
            plat = math.radians(pos2[0])
            plon = math.radians(pos2[1])

            return int(6371.01 * math.acos(
                math.sin(mlat) * math.sin(plat) + math.cos(mlat) * math.cos(plat) * math.cos(mlon - plon)))
        except Exception:
            self.log.warning(f'Exception calcing distance between "{mh_pos1}" amd "{mh_pos2}"')
            return 0

    @property
    def values(self) -> tuple:
        """Retreiving all values from the form"""

        if not self.__change_mode__:
            if self.autoDateCheckBox.isChecked():
                date_time_off = QtCore.QDateTime.currentDateTimeUtc().toString('yyyy-MM-dd HH:mm:ss')
            else:
                date_time_off = self.dateEdit.text() + ' ' + self.timeEdit.text()
        else:
            date_time_off = self.dateEdit.text() + ' ' + self.timeEdit.text()

        band = self.bandComboBox.currentText()

        qsl_via = ''
        qsl_path = ''
        qsl_msg = ''
        qsl_sent = 'N'
        qsl_rcvd = 'N'
        eqsl_sent = 'N'
        eqsl_rcvd = 'N'
        if self.qslBurDirGroupBox.isChecked() or self.eqslGroupBox.isChecked():
            qsl_via = self.qslViaLineEdit.text()
            qsl_path = 'D' if self.qslDirectRadioButton.isChecked() else 'B'
            qsl_msg = self.qslMessageTextEdit.toPlainText().strip()

            if self.qslBurDirGroupBox.isChecked():
                qsl_sent = 'Y' if self.qslSentCheckBox.isChecked() else 'R'
                qsl_rcvd = 'Y' if self.qslRcvdCheckBox.isChecked() else 'R'

            if self.eqslGroupBox.isChecked():
                eqsl_sent = 'Y' if self.eqslSentCheckBox.isChecked() else 'R'
                eqsl_rcvd = 'Y' if self.eqslRcvdCheckBox.isChecked() else 'R'

        hamqth_state = 'N'
        if self.hamQTHGroupBox.isChecked():
            if self.hamQTHuplRadioButton.isChecked():
                hamqth_state = 'Y'
            if self.hamQTHmodRadioButton.isChecked():
                hamqth_state = 'M'

        return (
            self.dateOnEdit.text() + ' ' + self.timeOnEdit.text(),
            date_time_off,
            self.ownCallSignLineEdit.text().upper() if band != '11m' else self.ownCallSignLineEdit.text(),
            self.callSignLineEdit.text().upper() if band != '11m' else self.callSignLineEdit.text(),
            self.nameLineEdit.text(),
            self.QTHLineEdit.text(),
            self.locatorLineEdit.text(),
            self.RSTSentLineEdit.text(),
            self.RSTRcvdLineEdit.text(),
            band,
            self.modeComboBox.currentText(),
            self.freqDoubleSpinBox.value() if self.freqDoubleSpinBox.value() >= self.bands[band][
                0] else '',
            self.channelComboBox.currentText() if band == '11m' else '-',
            self.powerSpinBox.value() if self.powerSpinBox.value() > 0 else '',
            self.ownNameLineEdit.text(),
            self.ownQTHLineEdit.text(),
            self.ownLocatorLineEdit.text(),
            self.radioLineEdit.text(),
            self.antennaLineEdit.text(),
            self.remarksTextEdit.toPlainText().strip(),
            self.commentsTextEdit.toPlainText().strip(),
            self.calc_distance(self.locatorLineEdit.text(), self.ownLocatorLineEdit.text()),
            qsl_via,
            qsl_path,
            qsl_msg,
            qsl_sent,
            qsl_rcvd,
            eqsl_sent,
            eqsl_rcvd,
            hamqth_state,
        )

    @values.setter
    def values(self, values: dict):
        """Set all form values"""

        date, time = values['date_time'].split()
        self.dateOnEdit.setDate(QtCore.QDate.fromString(date, 'yyyy-MM-dd'))
        self.timeOnEdit.setTime(QtCore.QTime.fromString(time))

        if values['date_time_off']:
            date_off, time_off = values['date_time_off'].split()
        else:
            date_off, time_off = date, time
        self.dateEdit.setDate(QtCore.QDate.fromString(date_off, 'yyyy-MM-dd'))
        self.timeEdit.setTime(QtCore.QTime.fromString(time_off))

        self.ownCallSignLineEdit.setText(values['own_callsign'])
        self.callSignLineEdit.setText(values['call_sign'])
        self.nameLineEdit.setText(values['name'])
        self.QTHLineEdit.setText(values['qth'])
        self.locatorLineEdit.setText(values['locator'])
        self.RSTSentLineEdit.setText(values['rst_sent'])
        self.RSTRcvdLineEdit.setText(values['rst_rcvd'])

        band = values['band']
        self.bandComboBox.setCurrentText(band)

        self.modeComboBox.setCurrentText(values['mode'])

        try:
            freq = float(values['freq'])
        except ValueError:
            freq = self.bands[band][0] - self.bands[band][2]
        self.freqDoubleSpinBox.setValue(freq)

        if band == '11m':
            self.channelComboBox.setCurrentIndex(-1)
            channel = values['channel']
            self.channelComboBox.setCurrentText(str(channel) if channel else '-')

        try:
            power = int(values['power'])
        except ValueError:
            power = 0
        self.powerSpinBox.setValue(power)
        self.ownNameLineEdit.setText(values['own_name'])
        self.ownQTHLineEdit.setText(values['own_qth'])
        self.ownLocatorLineEdit.setText(values['own_locator'])
        self.radioLineEdit.setText(values['radio'])
        self.antennaLineEdit.setText(values['antenna'])
        self.remarksTextEdit.setText(values['remarks'])
        self.commentsTextEdit.setText(values['comments'])

        if (values['qsl_sent'] in ('R', 'Y') or values['qsl_rcvd'] in ('R', 'Y') or
                values['eqsl_sent'] in ('R', 'Y') or values['eqsl_rcvd'] in ('R', 'Y')):

            self.qslViaLineEdit.setText(values['qsl_via'])
            self.qslBureauRadioButton.setChecked(values['qsl_path'] == 'B')
            self.qslDirectRadioButton.setChecked(values['qsl_path'] == 'D')
            self.qslMessageTextEdit.setText(values['qsl_msg'])

            if values['qsl_sent'] in ('R', 'Y') or values['qsl_rcvd'] in ('R', 'Y'):
                self.qslBurDirGroupBox.setChecked(True)
                self.qslSentCheckBox.setChecked(values['qsl_sent'] == 'Y')
                self.qslRcvdCheckBox.setChecked(values['qsl_rcvd'] == 'Y')

            if values['eqsl_sent'] in ('R', 'Y') or values['eqsl_rcvd'] in ('R', 'Y'):
                self.eqslGroupBox.setChecked(True)
                self.eqslSentCheckBox.setChecked(values['eqsl_sent'] == 'Y')
                self.eqslRcvdCheckBox.setChecked(values['eqsl_rcvd'] == 'Y')
                if self.eqslRcvdCheckBox.isChecked():
                    self.eqslLinkLabel.setEnabled(True)
                    self.eqslDownloadPushButton.setEnabled(True)

        match values['hamqth']:
            case 'Y':
                self.hamQTHGroupBox.setChecked(True)
                self.hamQTHuplRadioButton.setChecked(True)
            case 'M':
                self.hamQTHGroupBox.setChecked(True)
                self.hamQTHmodRadioButton.setChecked(True)
            case _:
                self.hamQTHGroupBox.setChecked(False)
                self.hamQTHmodRadioButton.setChecked(True)  # Just don't check uploaded

    def searchCallbook(self):
        try:
            if not self.callbook.is_loggedin:
                self.callbook.login(self.settings.value('callbook/username', ''),
                                    self.settings_form.callbookPassword())
                self.log.info('Logged into callbook')

            data: CallBookData = None
            for _ in range(2):
                try:
                    data = self.callbook.get_dataset(self.callSignLineEdit.text())
                    break
                except SessionExpiredException:
                    self.log.debug('Callbook session expired')
                    self.callbook.login(self.settings.value('callbook/username', ''),
                                        self.settings_form.callbookPassword())

            if data:
                if data.nickname and not self.nameLineEdit.text().strip():
                    self.nameLineEdit.setText(data.nickname)
                if data.locator and not self.locatorLineEdit.text().strip():
                    self.locatorLineEdit.setText(data.locator)
                    self.locatorChanged(data.locator)
                if data.qth and not self.QTHLineEdit.text().strip():
                    self.QTHLineEdit.setText(data.qth)
                if data.qsl_via and not self.qslViaLineEdit.text().strip():
                    self.qslViaLineEdit.setText(data.qsl_via)

                self.qslAccBureauCheckBox.setChecked(data.qsl_bureau)
                self.qslAccDirectCheckBox.setChecked(data.qsl_direct)
                self.qslAccElectronicCheckBox.setChecked(data.qsl_eqsl)

                self.log.info(f'Fetched data from callbook {self.callbook.callbook_type.name}')
        except LoginException:
            QtWidgets.QMessageBox.warning(self, self.tr('Callbook search error'),
                                          self.tr('Login failed for user') + ': ' + self.settings.value(
                                              'callbook/username', ''))
        except CallsignNotFoundException as exc:
            QtWidgets.QMessageBox.information(self, self.tr('Callbook search result'),
                                              self.tr('Callsign not found') + f': {exc.args[0]}')
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, self.tr('Callbook search error'),
                                          self.tr('During callbook search an error occured') + f':\n{exc}')

    def saveLog(self):
        self.hamQTHmodRadioButton.setChecked(True)

        # finally accept dialog anyway
        self.accept()

    def uploadLog(self):
        if self.hamQTHGroupBox.isChecked() or self.eqslGroupBox.isChecked():
            record = self._build_record_()

            adif_doc = {'HEADER':
                {
                    'ADIF_VER': '3.1.4',
                    'PROGRAMID': self.parent().programName,
                    'PROGRAMVERSION': self.parent().programVersion,
                    'CREATED_TIMESTAMP': QtCore.QDateTime.currentDateTimeUtc().toString(
                        'yyyyMMdd HHmmss')
                },
                'RECORDS': [record]}

            if self.hamQTHGroupBox.isChecked() and not self.hamQTHuplRadioButton.isChecked():
                try:
                    self.callbook.upload_log(self.settings.value('callbook/username', ''),
                                             self.settings_form.callbookPassword(),
                                             adif_doc)

                    self.hamQTHuplRadioButton.setChecked(True)
                    self.log.info(f'Uploaded log to {self.callbook.callbook_type.name}')
                except LoginException:
                    QtWidgets.QMessageBox.warning(self, self.tr('Upload log error'),
                                                  self.tr('Login failed for user') + ': ' + self.settings.value(
                                                      'callbook/username', ''))
                except MissingADIFFieldException as exc:
                    QtWidgets.QMessageBox.warning(self, self.tr('Upload log error'),
                                                  self.tr('A field is missing for log upload') + f':\n"{exc.args[0]}"')

            if self.eqslGroupBox.isChecked() and not self.eqslSentCheckBox.isChecked():
                try:
                    self.eqsl.upload_log(self.settings.value('eqsl/username', ''),
                                         self.settings_form.eqslPassword(),
                                         record)

                    self.eqslSentCheckBox.setChecked(True)
                    self.log.info(f'Uploaded log to eQSL')
                except EQSLLoginException:
                    QtWidgets.QMessageBox.warning(self, self.tr('Upload eQSL error'),
                                                  self.tr('Login failed for user') + ': ' + self.settings.value(
                                                      'eqsl/username', ''))
                except EQSLADIFFieldException as exc:
                    QtWidgets.QMessageBox.warning(self, self.tr('Upload eQSL error'),
                                                  self.tr('A field is missing for log upload') + f':\n"{exc.args[0]}"')
                except EQSLQSODuplicateException:
                    QtWidgets.QMessageBox.warning(self, self.tr('Upload eQSL error'),
                                                  self.tr('The QSO is a duplicate'))
                except EQSLUserCallMatchException:
                    QtWidgets.QMessageBox.warning(self, self.tr('Upload eQSL error'),
                                                  self.tr('User call does not match') + ': ' + self.settings.value(
                                                      'eqsl/username', ''))
                except EQSLRequestException as exc:
                    QtWidgets.QMessageBox.information(self, self.tr('Upload eQSL error'),
                                                      self.tr('Error on upload') + f':\n"{exc.args[0]}"')

        # finally accept dialog anyway
        self.accept()

    def _build_record_(self):
        record = {
            'QSO_DATE': self.dateOnEdit.text().replace('-', ''),
            'TIME_ON': self.timeOnEdit.text().replace(':', ''),
            'TIME_OFF': self.timeEdit.text().replace(':', ''),
            'BAND': self.bandComboBox.currentText(),
            'MODE': self.modeComboBox.currentText(),
        }
        if self.ownCallSignLineEdit.text():
            record['STATION_CALLSIGN'] = self.ownCallSignLineEdit.text().upper()
        if self.callSignLineEdit.text():
            record['CALL'] = self.callSignLineEdit.text().upper()
        if self.nameLineEdit.text():
            record['NAME'] = self.parent().replaceUmlautsLigatures(self.nameLineEdit.text())
        if self.QTHLineEdit.text():
            record['QTH'] = self.parent().replaceUmlautsLigatures(self.QTHLineEdit.text())
        if self.locatorLineEdit.text():
            record['GRIDSQUARE'] = self.locatorLineEdit.text()
        if self.RSTSentLineEdit.text():
            record['RST_SENT'] = self.RSTSentLineEdit.text()
        if self.RSTRcvdLineEdit.text():
            record['RST_RCVD'] = self.RSTRcvdLineEdit.text()
        if self.freqDoubleSpinBox.value() >= self.bands[self.bandComboBox.currentText()][0]:
            record['FREQ'] = f'{self.freqDoubleSpinBox.value() / 1000:0.3f}'
        if self.powerSpinBox.value() > 0:
            record['TX_PWR'] = self.powerSpinBox.value()
        if self.ownLocatorLineEdit.text():
            record['MY_GRIDSQUARE'] = self.ownLocatorLineEdit.text()
        if self.remarksTextEdit.toPlainText().strip() and not bool(
                self.settings.value('imp_exp/own_notes_adif', 0)):
            record['NOTES'] = self.parent().replaceUmlautsLigatures(self.remarksTextEdit.toPlainText().strip())
        if self.commentsTextEdit.toPlainText().strip():
            record['COMMENTS'] = self.parent().replaceUmlautsLigatures(self.commentsTextEdit.toPlainText().strip())
        if self.qslMessageTextEdit.toPlainText().strip():
            record['QSLMSG'] = self.parent().replaceUmlautsLigatures(self.qslMessageTextEdit.toPlainText().strip())

        return record

    def eqslCheckInbox(self, only_url: bool = False):
        try:
            res = self.eqsl.check_inbox(self.settings.value('eqsl/username', ''),
                                        self.settings_form.eqslPassword(),
                                        self._build_record_())
            if res:
                self.eqsl_url = res
                self.eqslLinkLabel.setText(f'''<html>
                <head/>
                <body>
                <p><a href="{res}">
                <span style=" text-decoration: underline; color:#0000ff;">{self.tr('Link to eQSL Card')}</span>
                </a></p>
                </body>
                </html>''')
                self.log.debug(f'eQSL available at "{res}"')

                if not only_url:
                    self.eqslRcvdCheckBox.setChecked(True)
                    self.eqslLinkLabel.setEnabled(True)
                    self.eqslDownloadPushButton.setEnabled(True)

                return
        except EQSLLoginException as exc:
            QtWidgets.QMessageBox.warning(self, self.tr('Check eQSL Inbox error'),
                                          self.tr('Login failed for user') + ': ' + self.settings.value(
                                              'eqsl/username', '') + f'\n{exc}')
        except EQSLUserCallMatchException:
            QtWidgets.QMessageBox.warning(self, self.tr('Check eQSL Inbox error'),
                                          self.tr('User call does not match') + ': ' + self.settings.value(
                                              'eqsl/username', ''))
        except EQSLRequestException:
            QtWidgets.QMessageBox.information(self, self.tr('Check eQSL Inbox error'),
                                              self.tr('No eQSL available'))
        except EQSLADIFFieldException as exc:
            QtWidgets.QMessageBox.warning(self, self.tr('Check eQSL Inbox error'),
                                          self.tr('A field is missing for inbox check') + f':\n"{exc.args[0]}"')

        if not only_url:
            self.eqslLinkLabel.setEnabled(False)
            self.eqslDownloadPushButton.setEnabled(False)

    def eqslDownload(self):
        if not self.eqsl_url:
            self.eqslCheckInbox(True)

        if self.eqsl_url:
            res = QtWidgets.QFileDialog.getExistingDirectory(
                self,
                self.tr('Select eQSL folder'),
                self.settings.value('eqsl/lastExportDir', os.path.abspath(os.curdir)))

            if res:
                image_type = self.eqsl_url.split('/')[-1].split('.')[-1]
                call_sign = self.callSignLineEdit.text().replace("/ ?%&§$!=.()´`#'+*-:;<>|~{[]}", "_")
                image_name = (f'{self.dateOnEdit.text()} {call_sign} {self.modeComboBox.currentText()} '
                              f'{self.bandComboBox.currentText()}.{image_type}')
                image_path = os.path.join(res, image_name)

                eqsl_image = self.eqsl.receive_qsl_card(self.eqsl_url)
                with open(image_path, 'wb') as eqslf:
                    eqslf.write(eqsl_image)

                self.log.info(f'Stored eQSL to "{image_path}"')
                self.settings.setValue('eqsl/lastExportDir', res)

    def lotwCheckInbox(self):
        self.lotw.check_inbox(self.settings.value('lotw/username', ''),
                              self.settings_form.lotwPassword(),
                              self._build_record_())

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
        self.ownCallSignChanged(self.ownCallSignLineEdit.text())
        self.ownLocatorChanged(self.ownLocatorLineEdit.text())

        self.timeTimer.start(1000)

        return super().exec()

    def hideEvent(self, e):
        self.lastpos = self.pos()
        self.refreshTimer.stop()
        self.timeTimer.stop()
        e.accept()
