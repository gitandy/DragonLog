# DragonLog (c) 2023-2025 by Andreas Schawo is licensed under CC BY-SA 4.0.
# To view a copy of this license, visit http://creativecommons.org/licenses/by-sa/4.0/

import logging

from PyQt6 import QtWidgets, QtCore
from hamcc import hamcc

from . import CassiopeiaConsole_ui
from .Logger import Logger
from .RegEx import check_call
from .contest import CONTESTS, CONTEST_IDS, CONTEST_NAMES, ExchangeData, ContestLog
from .cty import Country
from .distance import distance
from .local_callbook import LocalCallbook


# noinspection PyPep8Naming
class CassiopeiaConsole(QtWidgets.QDialog, CassiopeiaConsole_ui.Ui_CassiopeiaConsoleWidget):
    qsosChached = QtCore.pyqtSignal()

    def __init__(self, parent, dragonlog, settings: QtCore.QSettings, logger: Logger, local_cb: LocalCallbook):
        super().__init__(parent)
        self.dragonlog = dragonlog
        self.setupUi(self)

        self.log = logging.getLogger('CassiopeiaConsole')
        self.log.addHandler(logger)
        self.log.setLevel(logger.loglevel)
        self.logger = logger
        self.log.debug('Initialising...')
        self.log.debug(f'HamCC version: {hamcc.__version_str__}...')

        self.__settings__ = settings
        self.__local_cb__ = local_cb

        self.__cc__ = hamcc.CassiopeiaConsole(self.__settings__.value('station/callSign', ''),
                                              self.__settings__.value('station/qth_loc', ''),
                                              self.__settings__.value('station/name', ''))
        self.__current_call__ = ''
        self.__current_rxexch__ = ''
        self.__cdata__ = None

        self.__initWidgets__()

        self.refreshDisplay()

    def refreshListings(self):
        self.bandComboBox.clear()
        bands: list = self.__settings__.value('ui/show_bands', [])
        if '11m' in bands:
            bands.remove('11m')
        self.bandComboBox.insertItems(0, [self.tr('Band')] + bands)
        self.modeComboBox.clear()
        self.modeComboBox.insertItems(0, [self.tr('Mode')] + self.__settings__.value('ui/show_modes', []))

    def __initWidgets__(self):
        self.refreshListings()
        self.eventComboBox.insertItems(3, CONTEST_IDS.keys())
        self.ctyCtyLabel.setText(f'? ?, ?')
        self.ctyAreaLabel.setText(f'DXCC=?, CQ=?, ITU=?')

    def _check_worked_before_(self, call):
        if check_call(call):
            worked_dict = self.dragonlog.workedBefore(call)
            worked_list = []
            if worked_dict:
                for call, data in zip(worked_dict.keys(), worked_dict.values()):
                    if self.__cc__.__event__ and data['event'] != self.__cc__.__event__:
                        continue
                    worked_list.append(f'{call} {self.tr("at")} {data["date_time"]}')
                    if len(worked_list) == 3:
                        break
            if worked_list:
                self.resultWidget.setStyleSheet('#resultWidget {background-color: rgba(0, 0, 255, 63)}')
                self.resultLabel.setText('\n'.join(worked_list))

    def _callbook_lookup_(self, call: str, contest: str = ''):
        self._lookup_cty_data_(call)

        if not self.__local_cb__:
            return

        if contest and self.__local_cb__.history_entries[0]:
            # Initialise
            exc_data = ExchangeData()
            if self.__cdata__:
                exc_data.itu_zone = self.__cdata__.itu

            ch_data = self.__local_cb__.lookup_history(contest, call, True)
            if ch_data:
                # Initialise from callbook
                if ch_data.callbook_data:
                    if ch_data.callbook_data.name:
                        self.evaluate(f'\'{ch_data.callbook_data.name} ')
                    if ch_data.callbook_data.locator:
                        exc_data.locator = ch_data.callbook_data.locator
                    if ch_data.callbook_data.darc_dok:
                        exc_data.darc_dok = ch_data.callbook_data.darc_dok

                # Overwrite from history if available
                if ch_data.history_data:
                    if ch_data.history_data.locator:
                        exc_data.locator = ch_data.history_data.locator
                    exc_data.power = ch_data.history_data.power_class
                    if ch_data.history_data.darc_dok:
                        exc_data.darc_dok = ch_data.history_data.darc_dok
                    if ch_data.history_data.itu_zone:
                        exc_data.itu_zone = ch_data.history_data.itu_zone
                    if ch_data.history_data.rda_number:
                        exc_data.rda_number = ch_data.history_data.rda_number

            contest = CONTESTS.get(contest, None)
            self.evaluate(f'%{contest.prepare_exchange(exc_data)} ')
        else:
            cb_data = self.__local_cb__.lookup(call, True)
            if cb_data:
                qso = self.__cc__.current_qso
                if cb_data.callbook_data.qth and cb_data.callbook_data.locator and not 'QTH' in qso:
                    self.evaluate(f'@{cb_data.callbook_data.qth} ({cb_data.callbook_data.locator}) ')
                elif cb_data.callbook_data.locator and not qso.get('GRIDSQUARE', ''):
                    self.evaluate(f'@{cb_data.callbook_data.locator} ')

                if cb_data.callbook_data.name and not qso.get('NAME', ''):
                    self.evaluate(f'\'{cb_data.callbook_data.name} ')

    def _lookup_cty_data_(self, call):
        if call:
            self.__cdata__: Country = self.dragonlog.cty_data(call)
            if self.__cdata__:
                self.ctyCtyLabel.setText(f'{self.__cdata__.code} {self.__cdata__.name}, {self.__cdata__.continent}')
                self.ctyAreaLabel.setText(
                    f'DXCC={self.__cdata__.dxcc}, CQ={self.__cdata__.cq}, ITU={self.__cdata__.itu}')
        else:
            self.__cdata__ = None
            self.ctyCtyLabel.setText(f'? ?, ?')
            self.ctyAreaLabel.setText(f'DXCC=?, CQ=?, ITU=?')

    def refreshDisplay(self):
        qso = self.__cc__.current_qso

        self.myCallLineEdit.setText(qso.get('STATION_CALLSIGN', ''))
        my_loc = f'{qso["MY_CITY"]} ({qso.get("MY_GRIDSQUARE", "")})' if 'MY_CITY' in qso else qso.get('MY_GRIDSQUARE',
                                                                                                       '')
        self.myLocLineEdit.setText(my_loc)
        self.myNameLineEdit.setText(qso.get('MY_NAME', ''))

        if 'CONTEST_ID' in qso:
            self.eventComboBox.setCurrentText(CONTEST_NAMES.get(qso['CONTEST_ID'], qso['CONTEST_ID']))
            self.exchTXLineEdit.setText(qso.get('STX_STRING', qso.get('STX', '')))
            self.exchRXLineEdit.setText(qso.get('SRX_STRING', qso.get('SRX', '')))

            contest: ContestLog | None = CONTESTS.get(qso['CONTEST_ID'], None)
            if contest:
                self.exchRXLineEdit.setPlaceholderText(contest.contest_exch_fmt)

                if not qso.get('SRX_STRING', ''):  # Reset exchange cache
                    self.__current_rxexch__ = ''
                elif qso.get('SRX_STRING', '') != self.__current_rxexch__:  # Only run if exchange changed
                    self.__current_rxexch__ = qso.get('SRX_STRING', '')
                    exch: ExchangeData = contest.extract_exchange(qso.get('SRX_STRING', ''))
                    if exch and exch.locator:
                        self.evaluate(f'@{exch.locator} ')
        elif 'MY_SIG' in qso:
            self.exchRXLineEdit.setPlaceholderText(self.tr('Exchange'))
            self.eventComboBox.setCurrentText(qso['MY_SIG'])
            self.exchTXLineEdit.setText(qso.get('MY_SIG_INFO', ''))
            self.exchRXLineEdit.setText(qso.get('SIG_INFO', ''))
        else:
            self.exchRXLineEdit.setPlaceholderText(self.tr('Exchange'))
            self.exchTXLineEdit.setText('')
            self.exchRXLineEdit.setText('')
            self.eventComboBox.setCurrentText(self.tr('Event ID'))

        self.onlineCheckBox.setChecked(self.__cc__.is_online())
        self.dateEdit.setDate(QtCore.QDate.fromString(qso['QSO_DATE'][:8], 'yyyyMMdd'))
        self.timeEdit.setTime(QtCore.QTime.fromString(qso['TIME_ON'][:4], 'HHmm'))
        self.dateEdit.setDisabled(self.onlineCheckBox.isChecked())
        self.timeEdit.setDisabled(self.onlineCheckBox.isChecked())
        self.dateEdit.blockSignals(self.onlineCheckBox.isChecked())
        self.timeEdit.blockSignals(self.onlineCheckBox.isChecked())

        self.bandComboBox.setCurrentText(qso['BAND'].lower() if qso['BAND'] else self.tr('Band'))
        self.modeComboBox.setCurrentText(qso['MODE'].upper() if qso['MODE'] else self.tr('Mode'))
        self.callLineEdit.setText(qso['CALL'])
        loc = f'{qso["QTH"]} ({qso["GRIDSQUARE"]})' if 'QTH' in qso else qso.get('GRIDSQUARE', '')
        self.locLineEdit.setText(loc)

        self.rstRXLineEdit.setText(qso.get('RST_RCVD', ''))
        self.rstTXLineEdit.setText(qso.get('RST_SENT', ''))
        self.nameLineEdit.setText(qso.get('NAME', ''))

        self.freqSpinBox.setValue(int(float(qso.get("FREQ", "0")) * 1000))
        self.powerSpinBox.setValue(int(qso.get('TX_PWR', '0')))
        self.qslCheckBox.setChecked(qso.get('QSL_RCVD', 'N') == 'Y')
        self.commentLineEdit.setText(qso.get('COMMENT', ''))

        call = self.__cc__.current_qso.get('CALL', '')
        if call != self.__current_call__:
            self.__current_call__ = call
            self._check_worked_before_(call)
            self._callbook_lookup_(call, self.__cc__.current_qso.get('CONTEST_ID', ''))

        if qso.get('GRIDSQUARE', '') and qso.get('MY_GRIDSQUARE', ''):
            # noinspection PyBroadException
            try:
                self.distLabel.setText(f'{distance(qso["GRIDSQUARE"], qso["MY_GRIDSQUARE"])} km')
            except Exception:
                self.distLabel.setText('? km')
        else:
            self.distLabel.setText('? km')

    def evaluate(self, text: str):
        if text.endswith('~'):
            self.clearInput()
        elif text.endswith('!'):
            self.inputLineEdit.setText(self.inputLineEdit.text()[:-1])
            self.inputLineEdit.clear()
            self.finaliseQSO()
            self.qsosChached.emit()
        elif text.endswith('?'):
            qso = str(self.__cc__.current_qso)
            for c in '{}\'':
                qso = qso.replace(c, '')
            self.resultLabel.setText(qso)
            self.resultWidget.setStyleSheet('#resultWidget {background-color: rgba(0, 255, 0, 63)}')
            self.inputLineEdit.clear()
        elif text.startswith('"'):
            if text.endswith('"'):
                self._evaluate_(text[1:-1])
        elif text.endswith(' '):
            self._evaluate_(text.strip())

        self.refreshDisplay()

    def setQSO(self, call: str, band: str = '', freq: float = .0):
        self.evaluate(f'{call} ')

        if band:
            self.evaluate(f'{band} ')
        if freq:
            freq_s = f'{freq:0.3f}'.rstrip('0').rstrip('.')
            self.evaluate(f'{freq_s}f ')

    def setFrequency(self, freq: float):
        freq_s = f'{freq:0.3f}'.rstrip('0').rstrip('.')
        self.evaluate(f'{freq_s}f ')

    def setBand(self, band: str):
        self.evaluate(f'{band} ')

    def setMode(self, mode: str):
        self.evaluate(f'{mode} ')

    def setPower(self, pwr: int):
        self.evaluate(f'{int(pwr)}p ')

    def _evaluate_(self, text):
        if text:
            res = self.__cc__.evaluate(text)
            self.resultLabel.setText(self.tr(res))
            if res.startswith('Error:'):
                self.resultWidget.setStyleSheet('#resultWidget {background-color: rgba(255, 0, 0, 63)}')
            elif res.startswith('Warning:'):
                self.resultWidget.setStyleSheet('#resultWidget {background-color: rgba(255, 127, 0, 63)}')
            else:
                self.resultWidget.setStyleSheet('#resultWidget {background-color: rgba(0, 255, 0, 63)}')
            self.inputLineEdit.clear()

    def finaliseQSO(self):
        text = self.inputLineEdit.text()
        if text.startswith('"'):
            self._evaluate_(text[1:])
        else:
            self._evaluate_(text)

        if self.__cc__.current_qso.get('CALL', ''):
            res = self.__cc__.finalize_qso()
            self.resultLabel.setText(self.tr(res))
            if res.startswith('Error:'):
                self.resultWidget.setStyleSheet('#resultWidget {background-color: rgba(255, 0, 0, 63)}')
            elif res.startswith('Warning:'):
                self.resultWidget.setStyleSheet('#resultWidget {background-color: rgba(255, 127, 0, 63)}')
            else:
                self.resultWidget.setStyleSheet('#resultWidget {background-color: rgba(0, 255, 0, 63)}')

            self.clearInput()
            self.qsosChached.emit()
        else:
            self.resultWidget.setStyleSheet('#resultWidget {background-color: rgba(255, 127, 0, 63)}')
            self.resultLabel.setText(self.tr('Error: Callsign missing for QSO'))

    def hasQSOs(self) -> bool:
        return self.__cc__.has_qsos()

    def retrieveQSO(self) -> dict[str, str]:
        qso = self.__cc__.pop_qso()
        return qso

    def clearInput(self):
        self.__cc__.clear()
        self.__current_call__ = ''
        self.inputLineEdit.clear()
        self.refreshDisplay()
        self.inputLineEdit.setFocus()

    def resetUserData(self):
        self._evaluate_('-c' + self.__settings__.value('station/callSign', ''))
        self._evaluate_('-l' + self.__settings__.value('station/qth_loc', ''))
        self._evaluate_('-n' + self.__settings__.value('station/name', ''))
        self.refreshDisplay()

    def tr(self, text: str, **kwargs) -> str:
        if text.startswith('Last QSO cached:'):
            text, call = text.split(':')
            return f'{super().tr(text)}:{call}'
        else:
            return super().tr(text)

    def __(self):
        # Stub for translations
        self.tr('Warning: Wrong call format')
        self.tr('Error: Wrong call format')
        self.tr('Error: Wrong QTH/maidenhead format')
        self.tr('Error: No active event')
        self.tr('Error: Unknown prefix')
        self.tr('Error: Wrong RST format')
        self.tr('Warning: Callsign missing for last QSO')
        self.tr('Last QSO cached')

    def callChanged(self, call: str):
        if len(call) > 2:
            self.evaluate(call + ' ')

    def locatorChanged(self):
        self.evaluate(f'@{self.locLineEdit.text()} ')

    def nameChanged(self):
        self._evaluate_('\'' + self.nameLineEdit.text())

    def commentChanged(self):
        self._evaluate_('#' + self.commentLineEdit.text())

    def bandChanged(self, band: str):
        if band and band != self.tr('Band'):
            self._evaluate_(band)
        self.refreshDisplay()

    def modeChanged(self, mode: str):
        if mode and mode != self.tr('Mode'):
            self._evaluate_(mode)
        self.refreshDisplay()

    def dateChanged(self, date: QtCore.QDate):
        self.evaluate(date.toString('yyyyMMdd') + 'd ')

    def timeChanged(self, time: QtCore.QTime):
        self.evaluate(time.toString('HHmm') + 't ')

    def freqChanged(self, freq: int):
        self._evaluate_(f'{freq}f')

    def powerChanged(self, power: int):
        self._evaluate_(f'{power}p')

    def qslChanged(self, state: bool):
        self._evaluate_('*')

    def rstRxChanged(self):
        if self.rstRXLineEdit.text():
            self._evaluate_('.' + self.rstRXLineEdit.text())

    def rstTxChanged(self):
        if self.rstTXLineEdit.text():
            self._evaluate_(',' + self.rstTXLineEdit.text())

    def myCallChanged(self):
        self._evaluate_('-c' + self.myCallLineEdit.text())

    def myLocChanged(self):
        self.evaluate(f'-l{self.myLocLineEdit.text()} ')

    def myNameChanged(self):
        self._evaluate_('-n' + self.myNameLineEdit.text())

    def eventChanged(self, event: str):
        if event and event != self.tr('Event ID'):
            event = CONTEST_IDS.get(event, self.eventComboBox.currentText().strip())
            self._evaluate_('$' + event)
        else:
            self._evaluate_('$')
        self.refreshDisplay()

    def exchRxChanged(self):
        event = self.eventComboBox.currentText()
        if event and event != self.tr('Event ID'):
            self._evaluate_('%' + self.exchRXLineEdit.text())

    def exchTxChanged(self):
        event = self.eventComboBox.currentText()
        if event and event != self.tr('Event ID'):
            self._evaluate_('-N' + self.exchTXLineEdit.text())

    def onlineChanged(self, _):
        self.evaluate('-o ')
