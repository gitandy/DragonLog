import math
import socket
import logging

import maidenhead
from PyQt6 import QtWidgets, QtCore

from . import DragonLog_QSOForm_ui
from .Logger import Logger
from .DragonLog_Settings import Settings
from .RegEx import REGEX_CALL, REGEX_RSTFIELD, REGEX_LOCATOR, REGEX_TIME, check_format, check_call, check_qth
from .CallBook import (HamQTHCallBook, QRZCQCallBook, CallBookData,
                       SessionExpiredException, LoginException, CallsignNotFoundException)
from . import ColorPalettes


class QSOForm(QtWidgets.QDialog, DragonLog_QSOForm_ui.Ui_QSOForm):
    def __init__(self, parent, dragonlog, bands: dict, modes: dict, prop: dict, settings: QtCore.QSettings,
                 settings_form: Settings, cb_channels: dict, hamlib_error: QtWidgets.QLabel, logger: Logger):
        super().__init__(parent)
        self.dragonlog = dragonlog
        self.setupUi(self)

        self.log = logging.getLogger('QSOForm')
        self.log.addHandler(logger)
        self.log.setLevel(logger.loglevel)
        self.logger = logger
        self.log.debug('Initialising...')

        self.lastpos = None
        self.bands = bands
        self.modes = modes
        self.prop = prop
        self.prop_trans = dict(zip(prop.values(), prop.keys()))
        self.settings = settings
        self.settings_form = settings_form
        self.qso_id = None

        self.__old_values__ = {}

        self.cb_channels = cb_channels
        self.channelComboBox.insertItems(0, ['-'] + list(cb_channels.keys()))

        self.refreshBands()

        self.propComboBox.insertItems(0, self.prop.values())

        self.stationChanged(True)
        self.identityChanged(True)

        self.hamlib_error = hamlib_error
        self.rig_modes = {'USB': ('SSB', 'USB'),
                          'LSB': ('SSB', 'LSB'),
                          'CW': ('CW', ''),
                          'CWR': ('CW', ''),
                          'RTTY': ('RTTY', ''),
                          'RTTYR': ('RTTY', ''),
                          'AM': ('AM', ''),
                          'FM': ('FM', ''),
                          'WFM': ('FM', ''),
                          'PKTUSB': ('SSB', 'USB'),
                          'PKTLSB': ('SSB', 'LSB'),
                          }
        self.__last_mode__ = ''
        self.__last_band__ = ''
        self.__last_freq__ = 0.0
        self.__last_pwr__ = ''

        self.settings_form.rigctldStatusChanged.connect(self.rigctldChanged)

        self.__change_mode__ = False

        self.refreshTimer = QtCore.QTimer(self)
        self.refreshTimer.timeout.connect(self.refreshRigData)

        self.timeTimer = QtCore.QTimer(self)
        self.timeTimer.timeout.connect(self.refreshTime)

        self.worked_dialog: QtWidgets.QListWidget = None
        self._create_worked_dlg_()

        self.callbook_hamqth = HamQTHCallBook(self.logger,
                                              f'{self.dragonlog.programName}-{self.dragonlog.programVersion}',
                                              )
        self.callbook_qrzcq = QRZCQCallBook(self.logger,
                                            f'{self.dragonlog.programName}-{self.dragonlog.programVersion}',
                                            )

        view_only_widgets = (
            self.qslAccBureauCheckBox,
            self.qslAccDirectCheckBox,
            self.qslAcceQSLCheckBox,
            self.qslAccLoTWCheckBox,
        )

        for w in view_only_widgets:
            w.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            w.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)

        self.refreshQTHList()
        self.refreshRadioList()
        self.refreshAntennaList()

        self.clear()

    def refreshBands(self):
        self.bandComboBox.clear()
        self.bandComboBox.insertItems(0, self.settings.value('ui/show_bands', self.bands.keys()))
        self.bandComboBox.setCurrentIndex(0)

    def refreshQTHList(self):
        self.ownQTHComboBox.clear()
        if self.settings.value('listings/qths'):
            self.ownQTHComboBox.insertItems(0, self.settings.value('listings/qths'))

    def refreshRadioList(self):
        self.radioComboBox.clear()
        if self.settings.value('listings/rigs'):
            self.radioComboBox.insertItems(0, self.settings.value('listings/rigs'))

    def refreshAntennaList(self):
        self.antennaComboBox.clear()
        if self.settings.value('listings/antennas'):
            self.antennaComboBox.insertItems(0, self.settings.value('listings/antennas'))

    def rigctldChanged(self, state):
        self.__last_mode__ = ''
        self.__last_band__ = ''
        self.__last_freq__ = 0.0
        self.__last_pwr__ = ''

    def startTimers(self, start: bool):
        if start:
            self.refreshTimer.start(500)
            self.timeTimer.start(1000)
        else:
            self.refreshTimer.stop()
            self.timeTimer.stop()

    def _create_worked_dlg_(self):
        self.worked_dialog = QtWidgets.QListWidget(self)
        self.worked_dialog.setMinimumHeight(100)
        self.worked_dialog.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        self.worked_dialog.setSortingEnabled(True)
        self.worked_dialog.hide()

    def setWorkedBefore(self, worked: list = None):
        self.worked_dialog.clear()
        if worked:
            self.worked_dialog.addItems(worked)
            call_edit_pos = self.callSignLineEdit.pos()
            call_edit_pos.setX(call_edit_pos.x() + 15)
            call_edit_pos.setY(call_edit_pos.y() + self.callSignLineEdit.height() + 40)
            self.worked_dialog.move(call_edit_pos)
            self.worked_dialog.show()
        else:
            self.worked_dialog.hide()

    def refreshTime(self):
        if self.autoDateCheckBox.isChecked():
            dt = QtCore.QDateTime.currentDateTimeUtc()
            self.dateOffEdit.setDate(dt.date())
            self.timeOffEdit.setText(dt.time().toString('HH:mm:ss'))

    def setStartTimeNow(self):
        dt = QtCore.QDateTime.currentDateTimeUtc()
        self.dateOnEdit.setDate(dt.date())
        self.timeOnEdit.setText(dt.time().toString('HH:mm:ss'))
        self.timeOnChanged(self.timeOnEdit.text())

    def autoDateCBChanged(self, checked: bool):
        if not checked:
            self.timeOffEdit.clear()
            self.timeOffChanged('')
        else:
            self.refreshTime()

    # noinspection PyBroadException
    def refreshRigData(self):
        if self.settings_form.isRigctldActive() and not self.__change_mode__:
            try:
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
                            if freq != self.__last_freq__:
                                for b in self.bands:
                                    if freq < self.bands[b][1]:
                                        if freq > self.bands[b][0]:
                                            if b != self.__last_band__:
                                                self.bandComboBox.setCurrentText(b)
                                                self.log.info(f'CAT changed band to {b}')
                                                self.__last_band__ = b
                                                self.__last_mode__ = ''
                                        break
                                self.freqDoubleSpinBox.setValue(freq)
                                self.__last_freq__ = freq
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
                                self.modeComboBox.setCurrentText(self.rig_modes[mode][0])
                                self.log.info(f'CAT changed mode to {self.rig_modes[mode][0]}')
                                if self.rig_modes[mode][1]:
                                    self.submodeComboBox.setCurrentText(self.rig_modes[mode][1])
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

                            if pwrlvl_s != self.__last_pwr__:
                                self.__last_pwr__ = pwrlvl_s
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
                                    self.log.info(f'CAT changed power to {pwr} W')
                                except Exception:
                                    pass
                    except socket.timeout:
                        self.hamlib_error.setText(self.tr('rigctld timeout'))
                        self.log.error('rigctld error: timeout')
            except ConnectionRefusedError:
                self.log.error('Could not connect to rigctld')
                self.refreshTimer.stop()

    def clear(self):
        self.__old_values__ = {}
        self.qso_id = None

        if self.__change_mode__:
            self.setChangeMode(False)

        self.callSignLineEdit.clear()
        self.nameLineEdit.clear()
        self.QTHLineEdit.clear()
        self.locatorLineEdit.clear()
        self.RSTSentLineEdit.setText('59')
        self.RSTRcvdLineEdit.setText('59')
        self.commentLineEdit.clear()
        self.remarksTextEdit.clear()

        self.callSignChanged('')
        self.locatorChanged('')
        self.ownCallSignChanged(self.ownCallSignLineEdit.text())
        self.rstSentChanged(self.RSTSentLineEdit.text())
        self.rstRcvdChanged(self.RSTRcvdLineEdit.text())
        self.ownQTHChanged(self.ownQTHComboBox.currentText())

        dt = QtCore.QDateTime.currentDateTimeUtc()
        self.dateOffEdit.setDate(dt.date())
        self.dateOnEdit.setDate(dt.date())
        if self.autoDateCheckBox.isChecked():
            self.timeOffEdit.setText(dt.time().toString('HH:mm:ss'))
        self.timeOnEdit.setText('')
        self.timeOnChanged('')

        if bool(int(self.settings.value('station_cb/cb_by_default', 0))):
            self.bandComboBox.setCurrentText('11m')

        if self.bandComboBox.currentIndex() < 0:
            self.bandComboBox.setCurrentIndex(0)
            self.submodeComboBox.setCurrentIndex(-1)
        if self.modeComboBox.currentIndex() < 0:
            self.modeComboBox.setCurrentIndex(0)

        self.bandComboBox.setPalette(ColorPalettes.PaletteOk)
        self.modeComboBox.setPalette(ColorPalettes.PaletteOk)

        self.qslBurDirGroupBox.setChecked(False)
        self.qslViaLineEdit.clear()
        self.qslBureauRadioButton.setChecked(False)
        self.qslDirectRadioButton.setChecked(False)
        self.qslAccBureauCheckBox.setChecked(False)
        self.qslAccDirectCheckBox.setChecked(False)
        self.qslAcceQSLCheckBox.setChecked(False)
        self.qslAccLoTWCheckBox.setChecked(False)
        self.qslMessageTextEdit.clear()
        self.qslSentCheckBox.setChecked(False)
        self.qslRcvdCheckBox.setChecked(False)

        self.contestComboBox.setCurrentText('')
        self.sentQSOSpinBox.setValue(0)
        self.rcvdQSOSpinBox.setValue(0)
        self.rcvdDataLineEdit.clear()

        self.eventComboBox.setCurrentIndex(0)
        self.txExchLineEdit.clear()
        self.rxExchLineEdit.clear()

        self.toolBox.setCurrentIndex(0)

    def reset(self):
        self.autoDateCheckBox.setEnabled(True)
        self.autoDateCheckBox.setChecked(True)
        self.stationGroupBox.setChecked(True)
        self.identityGroupBox.setChecked(True)

        self.radioComboBox.setCurrentText(self.settings.value('station/radio', ''))
        self.antennaComboBox.setCurrentText(self.settings.value('station/antenna', ''))

    def setChangeMode(self, activate=True):
        self.__change_mode__ = activate
        self.startTimers(not activate)

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
        self.__last_band__ = band

        if band in self.bands:
            self.bandComboBox.setPalette(ColorPalettes.PaletteOk)
            self.freqDoubleSpinBox.setMinimum(self.bands[band][0] - self.bands[band][2])
            self.freqDoubleSpinBox.setValue(self.bands[band][0] - self.bands[band][2])
            self.freqDoubleSpinBox.setMaximum(self.bands[band][1])
            self.freqDoubleSpinBox.setSingleStep(self.bands[band][2])
        elif not band:
            self.bandComboBox.setPalette(ColorPalettes.PaletteEmpty)
        else:
            self.bandComboBox.setPalette(ColorPalettes.PaletteFaulty)
            self.freqDoubleSpinBox.setMinimum(0)
            self.freqDoubleSpinBox.setValue(0)
            self.freqDoubleSpinBox.setMaximum(self.bands['submm'][1])
            self.freqDoubleSpinBox.setSingleStep(1)

        self.modeComboBox.clear()
        if band == '11m':
            self.modeComboBox.insertItems(0, self.modes['CB'].keys())
            self.modeComboBox.setCurrentIndex(0)
            self.powerSpinBox.setMaximum(12)
            self.channelComboBox.setVisible(True)
            self.channelLabel.setVisible(True)
            self.freqDoubleSpinBox.setEnabled(False)
            self.searchHamQTHPushButton.setEnabled(False)
            self.searchQRZCQPushButton.setEnabled(False)
            self.qslPage.setEnabled(False)
            self.contestPage.setEnabled(False)
            self.channelComboBox.setCurrentIndex(-1)
            self.channelComboBox.setCurrentIndex(0)

            if self.stationGroupBox.isChecked():
                self.radioComboBox.setCurrentText(self.settings.value('station_cb/radio', ''))
                self.antennaComboBox.setCurrentText(self.settings.value('station_cb/antenna', ''))

            if self.identityGroupBox.isChecked():
                self.ownCallSignLineEdit.setText(self.settings.value('station_cb/callSign', ''))
        else:
            self.modeComboBox.insertItems(0, self.settings.value('ui/show_modes', self.modes['AFU'].keys()))
            self.modeComboBox.setCurrentIndex(0)
            self.powerSpinBox.setMaximum(1000)
            self.channelComboBox.setVisible(False)
            self.channelLabel.setVisible(False)
            self.freqDoubleSpinBox.setEnabled(True)
            self.searchHamQTHPushButton.setEnabled(True)
            self.searchQRZCQPushButton.setEnabled(True)
            self.qslPage.setEnabled(True)
            self.contestPage.setEnabled(True)

            if self.stationGroupBox.isChecked():
                self.radioComboBox.setCurrentText(self.settings.value('station/radio', ''))
                self.antennaComboBox.setCurrentText(self.settings.value('station/antenna', ''))

            if self.identityGroupBox.isChecked():
                self.ownCallSignLineEdit.setText(self.settings.value('station/callSign', ''))

    def modeChanged(self, mode: str):
        self.__last_mode__ = mode

        self.submodeComboBox.clear()
        self.submodeComboBox.setEnabled(False)
        if self.bandComboBox.currentText() == '11m':
            if mode in self.modes['CB']:
                self.modeComboBox.setPalette(ColorPalettes.PaletteOk)
                if self.modes['CB'][mode]:
                    self.submodeComboBox.setEnabled(True)
                    self.submodeComboBox.insertItems(0, [''] + self.modes['CB'][mode])
            elif not mode:
                self.modeComboBox.setPalette(ColorPalettes.PaletteEmpty)
            else:
                self.modeComboBox.setPalette(ColorPalettes.PaletteFaulty)
        else:
            if mode in self.modes['AFU']:
                self.modeComboBox.setPalette(ColorPalettes.PaletteOk)
                if self.modes['AFU'][mode]:
                    self.submodeComboBox.setEnabled(True)
                    self.submodeComboBox.insertItems(0, [''] + self.modes['AFU'][mode])
            elif not mode:
                self.modeComboBox.setPalette(ColorPalettes.PaletteEmpty)
            else:
                self.modeComboBox.setPalette(ColorPalettes.PaletteFaulty)

    def stationChanged(self, checked):
        if checked:
            self.ownQTHComboBox.setCurrentText(self.settings.value('station/qth_loc', ''))

            if self.bandComboBox.currentText() == '11m':
                self.radioComboBox.setCurrentText(self.settings.value('station_cb/radio', ''))
                self.antennaComboBox.setCurrentText(self.settings.value('station_cb/antenna', ''))
            else:
                self.radioComboBox.setCurrentText(self.settings.value('station/radio', ''))
                self.antennaComboBox.setCurrentText(self.settings.value('station/antenna', ''))

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
            self.RSTRcvdLineEdit.setPalette(ColorPalettes.PaletteEmpty)
        elif check_format(REGEX_RSTFIELD, txt):
            self.RSTRcvdLineEdit.setPalette(ColorPalettes.PaletteOk)
        else:
            self.RSTRcvdLineEdit.setPalette(ColorPalettes.PaletteFaulty)

    def rstSentChanged(self, txt):
        if not txt:
            self.RSTSentLineEdit.setPalette(ColorPalettes.PaletteEmpty)
        elif check_format(REGEX_RSTFIELD, txt):
            self.RSTSentLineEdit.setPalette(ColorPalettes.PaletteOk)
        else:
            self.RSTSentLineEdit.setPalette(ColorPalettes.PaletteFaulty)

    def checkRequired(self):
        if self.callSignLineEdit.text() and self.timeOnEdit.text():
            self.savePushButton.setEnabled(True)
        else:
            self.savePushButton.setEnabled(False)

    def callSignChanged(self, txt):
        self.checkRequired()
        self.setWorkedBefore()
        if not txt:
            self.callSignLineEdit.setPalette(ColorPalettes.PaletteRequired)
        elif check_format(REGEX_CALL, txt):
            # worked_dict:dict = self.dragonlog.workedBefore(check_call(txt)[1])
            worked = self.dragonlog.workedBefore(check_call(txt)[1]).keys()
            # for call, data in zip(worked_dict.keys(), worked_dict.values()):
            #     worked.append(f'{call} on {data["date_time"]}')
            if not self.__change_mode__ and worked:
                self.setWorkedBefore(worked)
                self.callSignLineEdit.setPalette(ColorPalettes.PaletteWorked)
            else:
                self.callSignLineEdit.setPalette(ColorPalettes.PaletteOk)
        elif self.bandComboBox.currentText() == '11m':
            self.callSignLineEdit.setPalette(ColorPalettes.PaletteOk)
        else:
            self.callSignLineEdit.setPalette(ColorPalettes.PaletteFaulty)

    def locatorChanged(self, txt):
        if not txt:
            self.locatorLineEdit.setPalette(ColorPalettes.PaletteEmpty)
        elif check_format(REGEX_LOCATOR, txt):
            self.locatorLineEdit.setPalette(ColorPalettes.PaletteOk)
        else:
            self.locatorLineEdit.setPalette(ColorPalettes.PaletteFaulty)

    def ownCallSignChanged(self, txt):
        if not txt:
            self.ownCallSignLineEdit.setPalette(ColorPalettes.PaletteEmpty)
        elif check_format(REGEX_CALL, txt):
            self.ownCallSignLineEdit.setPalette(ColorPalettes.PaletteOk)
        elif self.bandComboBox.currentText() == '11m':
            self.ownCallSignLineEdit.setPalette(ColorPalettes.PaletteOk)
        else:
            self.ownCallSignLineEdit.setPalette(ColorPalettes.PaletteFaulty)

    def ownQTHChanged(self, txt):
        if not txt:
            self.ownQTHComboBox.setPalette(ColorPalettes.PaletteEmpty)
        elif check_qth(txt.strip()):
            self.ownQTHComboBox.setPalette(ColorPalettes.PaletteOk)
        else:
            self.ownQTHComboBox.setPalette(ColorPalettes.PaletteFaulty)

    def timeOnChanged(self, txt):
        self.checkRequired()
        if not txt:
            self.timeOnEdit.setPalette(ColorPalettes.PaletteRequired)
        elif check_format(REGEX_TIME, txt):
            self.timeOnEdit.setPalette(ColorPalettes.PaletteOk)
        else:
            self.timeOnEdit.setPalette(ColorPalettes.PaletteFaulty)

    def timeOffChanged(self, txt):
        if not txt:
            self.timeOffEdit.setPalette(ColorPalettes.PaletteEmpty)
        elif check_format(REGEX_TIME, txt):
            self.timeOffEdit.setPalette(ColorPalettes.PaletteOk)
        else:
            self.timeOffEdit.setPalette(ColorPalettes.PaletteFaulty)

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

        date_time_off = ''
        if check_format(REGEX_TIME, self.timeOffEdit.text()):
            date_time_off = self.dateOffEdit.text() + ' ' + self.timeOffEdit.text()
        else:
            self.log.warning(f'Wrong time format for end time')

        if check_format(REGEX_TIME, self.timeOnEdit.text()):
            date_time_on = self.dateOnEdit.text() + ' ' + self.timeOnEdit.text()
        else:
            self.log.warning(f'Wrong time format for start time. Fallback to current date time.')
            date_time_on = QtCore.QDateTime.currentDateTimeUtc().toString('yyyy-MM-dd HH:mm:ss')

        band = self.bandComboBox.currentText()

        prop = ''
        if self.propComboBox.currentText():
            prop = self.prop_trans[self.propComboBox.currentText()]

        own_qth = self.ownQTHComboBox.currentText()
        own_locator = ''
        if check_qth(self.ownQTHComboBox.currentText()):
            own_qth, own_locator = check_qth(self.ownQTHComboBox.currentText())

        qsl_via = ''
        qsl_path = ''
        qsl_msg = ''
        qsl_sent = 'N'
        qsl_rcvd = 'N'
        if self.qslBurDirGroupBox.isChecked():
            qsl_via = self.qslViaLineEdit.text()
            qsl_path = 'D' if self.qslDirectRadioButton.isChecked() else 'B'
            qsl_msg = self.qslMessageTextEdit.toPlainText().strip()

            if self.qslBurDirGroupBox.isChecked():
                qsl_sent = 'Y' if self.qslSentCheckBox.isChecked() else 'R'
                qsl_rcvd = 'Y' if self.qslRcvdCheckBox.isChecked() else 'R'

        return (
            date_time_on,
            date_time_off,
            self.ownCallSignLineEdit.text().strip().upper() if band != '11m' else self.ownCallSignLineEdit.text().strip(),
            self.callSignLineEdit.text().strip().upper() if band != '11m' else self.callSignLineEdit.text().strip(),
            self.nameLineEdit.text().strip(),
            self.QTHLineEdit.text().strip(),
            self.locatorLineEdit.text().strip(),
            self.RSTSentLineEdit.text().strip(),
            self.RSTRcvdLineEdit.text().strip(),
            band,
            self.modeComboBox.currentText().strip(),
            self.submodeComboBox.currentText().strip(),
            self.freqDoubleSpinBox.value() if self.freqDoubleSpinBox.value() > self.freqDoubleSpinBox.minimum() else '',
            self.channelComboBox.currentText() if band == '11m' else '-',
            self.powerSpinBox.value() if self.powerSpinBox.value() > 0 else '',
            prop,
            self.ownNameLineEdit.text().strip(),
            own_qth,
            own_locator,
            self.radioComboBox.currentText().strip(),
            self.antennaComboBox.currentText().strip(),
            self.remarksTextEdit.toPlainText().strip(),
            self.commentLineEdit.text().strip(),
            self.calc_distance(self.locatorLineEdit.text(), own_locator),
            qsl_via,
            qsl_path,
            qsl_msg,
            qsl_sent,
            qsl_rcvd,
            self.__old_values__['eqsl_sent'],
            self.__old_values__['eqsl_rcvd'],
            self.__old_values__['lotw_sent'],
            self.__old_values__['lotw_rcvd'],
            self.__old_values__['hamqth'],
            self.contestComboBox.currentText().strip(),
            self.sentQSOSpinBox.value() if self.contestComboBox.currentText().strip() else 0,
            self.rcvdQSOSpinBox.value() if self.contestComboBox.currentText().strip() else 0,
            self.rcvdDataLineEdit.text().strip() if self.contestComboBox.currentText().strip() else '',
            self.eventComboBox.currentText(),
            self.txExchLineEdit.text().strip() if self.eventComboBox.currentText().strip() else '',
            self.rxExchLineEdit.text().strip() if self.eventComboBox.currentText().strip() else '',
        )

    @values.setter
    def values(self, values: dict):
        """Set all form values"""
        self.__old_values__ = values.copy()

        self.qso_id = values['id']
        time_on = ''
        if values['date_time']:
            try:
                date_on, time_on = values['date_time'].split()
                self.dateOnEdit.setDate(QtCore.QDate.fromString(date_on, 'yyyy-MM-dd'))
            except ValueError:
                self.log.error(f'Wrong date time format for start time in QSO #{self.qso_id}')
        self.timeOnEdit.setText(time_on)
        self.timeOnChanged(self.timeOnEdit.text())

        time_off = ''
        if values['date_time_off']:
            try:
                date_off, time_off = values['date_time_off'].split()
                self.dateOffEdit.setDate(QtCore.QDate.fromString(date_off, 'yyyy-MM-dd'))
            except ValueError:
                self.log.error(f'Wrong date time format for end time in QSO #{self.qso_id}')
        self.timeOffEdit.setText(time_off)
        self.timeOffChanged(self.timeOffEdit.text())

        self.ownCallSignLineEdit.setText(values['own_callsign'])
        self.callSignLineEdit.setText(values['call_sign'])
        self.nameLineEdit.setText(values['name'])
        self.QTHLineEdit.setText(values['qth'])
        self.locatorLineEdit.setText(values['locator'])
        self.RSTSentLineEdit.setText(values['rst_sent'])
        self.RSTRcvdLineEdit.setText(values['rst_rcvd'])

        self.callSignChanged(self.callSignLineEdit.text())
        self.locatorChanged(self.locatorLineEdit.text())
        self.ownCallSignChanged(self.ownCallSignLineEdit.text())
        self.rstSentChanged(self.RSTSentLineEdit.text())
        self.rstRcvdChanged(self.RSTRcvdLineEdit.text())
        self.ownQTHChanged(self.ownQTHComboBox.currentText())

        band = values['band']
        self.bandComboBox.setCurrentText(band)

        self.modeComboBox.setCurrentText(values['mode'])
        if values['submode']:
            self.submodeComboBox.setCurrentText(values['submode'])

        freq = 0
        try:
            freq = float(values['freq'])
        except ValueError:
            if band in self.bands:
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

        if values['propagation']:
            self.propComboBox.setCurrentText(self.prop[values['propagation']])

        self.ownNameLineEdit.setText(values['own_name'])

        if values['own_qth'] and values['own_locator']:
            self.ownQTHComboBox.setCurrentText(f"{values['own_qth']} ({values['own_locator']})")
        elif values['own_qth']:
            self.ownQTHComboBox.setCurrentText(values['own_qth'])
        elif values['own_locator']:
            self.ownQTHComboBox.setCurrentText(f"({values['own_locator']})")

        self.radioComboBox.setCurrentText(values['radio'])
        self.antennaComboBox.setCurrentText(values['antenna'])
        self.remarksTextEdit.setText(values['remarks'])
        self.commentLineEdit.setText(values['comments'].replace('\n', ' ').replace('\r', ''))

        if values['qsl_sent'] in ('R', 'Y') or values['qsl_rcvd'] in ('R', 'Y'):
            self.qslViaLineEdit.setText(values['qsl_via'])
            self.qslBureauRadioButton.setChecked(values['qsl_path'] == 'B')
            self.qslDirectRadioButton.setChecked(values['qsl_path'] == 'D')
            self.qslMessageTextEdit.setText(values['qsl_msg'])

            if values['qsl_sent'] in ('R', 'Y') or values['qsl_rcvd'] in ('R', 'Y'):
                self.qslBurDirGroupBox.setChecked(True)
                self.qslSentCheckBox.setChecked(values['qsl_sent'] == 'Y')
                self.qslRcvdCheckBox.setChecked(values['qsl_rcvd'] == 'Y')

        self.contestComboBox.setCurrentText(values['contest_id'])
        self.rcvdDataLineEdit.setText(values['crx_data'])
        try:
            self.sentQSOSpinBox.setValue(int(values['ctx_qso_id']) if values['ctx_qso_id'] else -1)
        except ValueError:
            self.log.warning(f'Sent QSO ID "{values["ctx_qso_id"]}" is not a number')

        try:
            self.rcvdQSOSpinBox.setValue(int(values['crx_qso_id']) if values['crx_qso_id'] else -1)
        except ValueError:
            self.log.warning(f'Rcvd QSO ID "{values["crx_qso_id"]}" is not a number')
            if not values['crx_data']:
                self.rcvdDataLineEdit.setText(values['crx_qso_id'])
                self.log.info(f'Stored QSO ID as rcvd data instead')

        self.eventComboBox.setCurrentText(values['event'])
        self.txExchLineEdit.setText(values['evt_tx_exch'])
        self.rxExchLineEdit.setText(values['evt_rx_exch'])

    def searchHamQTH(self):
        self.searchCallbook(self.callbook_hamqth)

    def searchQRZCQ(self):
        self.searchCallbook(self.callbook_qrzcq)

    def searchCallbook(self, callbook):
        try:
            if not callbook.is_loggedin:
                callbook.login(self.settings.value(f'callbook/{callbook.callbook_type.name}_user', ''),
                               self.settings_form.callbookPassword(callbook.callbook_type))
                self.log.info(f'Logged into callbook {callbook.callbook_type.name}')

            data: CallBookData = None
            for _ in range(2):
                try:
                    data = callbook.get_dataset(self.callSignLineEdit.text())
                    break
                except SessionExpiredException:
                    self.log.debug('Callbook session expired')
                    callbook.login(self.settings.value(f'callbook/{callbook.callbook_type.name}_user', ''),
                                   self.settings_form.callbookPassword(callbook.callbook_type))

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
                self.qslAcceQSLCheckBox.setChecked(data.qsl_eqsl)
                self.qslAccLoTWCheckBox.setChecked(data.qsl_lotw)

                self.log.info(f'Fetched data from callbook {callbook.callbook_type.name}')
        except LoginException:
            QtWidgets.QMessageBox.warning(self, self.tr('Callbook search error'),
                                          self.tr('Login failed for user') + ': ' + self.settings.value(
                                              f'callbook/{callbook.callbook_type.name}_user', ''))
        except CallsignNotFoundException as exc:
            QtWidgets.QMessageBox.information(self, self.tr('Callbook search result'),
                                              self.tr('Callsign not found') + f': {exc.args[0]}')
        except Exception as exc:
            self.log.exception(exc)
            QtWidgets.QMessageBox.warning(self, self.tr('Callbook search error'),
                                          self.tr('During callbook search an error occured') + f':\n{exc}')

    def saveLog(self):
        if self.__change_mode__:
            self.dragonlog.updateQSO(self.qso_id)
        else:
            self.dragonlog.fetchQSO()

        self.toolBox.setCurrentIndex(0)
        self.clear()

    def contestChanged(self, text: str):
        self.xotaGroupBox.setDisabled(bool(text))

    def eventChanged(self, text: str):
        self.contestGroupBox.setDisabled(bool(text))

    def keyPressEvent(self, e):
        if e.key() != QtCore.Qt.Key.Key_Escape:
            super().keyPressEvent(e)
