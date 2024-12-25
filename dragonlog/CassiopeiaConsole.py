import logging

from PyQt6 import QtWidgets, QtCore
from hamcc import hamcc

from . import CassiopeiaConsole_ui
from .Logger import Logger
from .RegEx import check_call
from .adi2contest import CONTEST_NAMES, CONTEST_IDS


class CassiopeiaConsole(QtWidgets.QDialog, CassiopeiaConsole_ui.Ui_CassiopeiaConsoleWidget):
    qsosChached = QtCore.pyqtSignal()

    def __init__(self, parent, dragonlog, settings: QtCore.QSettings, logger: Logger):
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

        self.__cc__ = hamcc.CassiopeiaConsole(self.__settings__.value('station/callsign', ''),
                                              self.__settings__.value('station/qth_loc', ''),
                                              self.__settings__.value('station/name', ''))
        self.__current_call__ = ''

        self.__initWidgets__()

        self.refreshDisplay()

    def __initWidgets__(self):
        self.bandComboBox.insertItems(1, self.__settings__.value('ui/show_bands', []))
        self.modeComboBox.insertItems(1, self.__settings__.value('ui/show_modes', []))
        self.eventComboBox.insertItems(3, CONTEST_IDS.keys())

    def refreshDisplay(self):
        qso = self.__cc__.current_qso

        self.myCallLineEdit.setText(qso.get('STATION_CALLSIGN', ''))
        my_loc = f'{qso["MY_CITY"]} ({qso.get("MY_GRIDSQUARE", "")})' if 'MY_CITY' in qso else qso.get('MY_GRIDSQUARE',
                                                                                                       '')
        self.myLocLineEdit.setText(my_loc)
        self.myNameLineEdit.setText(qso.get('MY_NAME', ''))

        if 'CONTEST_ID' in qso:
            self.eventComboBox.setCurrentText(CONTEST_NAMES.get(qso['CONTEST_ID'], qso['CONTEST_ID']))
            self.exchTXLineEdit.setText(qso.get('STX', qso.get('STX_STRING', '')))
            self.exchRXLineEdit.setText(qso.get('SRX', qso.get('SRX_STRING', '')))
        elif 'MY_SIG' in qso:
            self.eventComboBox.setCurrentText(qso['MY_SIG'])
            self.exchTXLineEdit.setText(qso.get('MY_SIG_INFO', ''))
            self.exchRXLineEdit.setText(qso.get('SIG_INFO', ''))
        else:
            self.exchTXLineEdit.setText('')
            self.exchRXLineEdit.setText('')
            # self.eventComboBox.setCurrentText(self.tr('Event ID'))

        self.dateEdit.setDate(QtCore.QDate.fromString(qso['QSO_DATE'], 'yyyyMMdd'))
        self.timeEdit.setTime(QtCore.QTime.fromString(qso['TIME_ON'], 'HHmm'))
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

    def setQSO(self, call: str, band: str, freq: float):
        self.evaluate(f'{call} ')
        self.evaluate(f'{band} ')
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

            call = self.__cc__.current_qso.get('CALL', '')
            if call != self.__current_call__:
                self.__current_call__ = call
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
            self._evaluate_(call)

    def locatorChanged(self):
        self._evaluate_('@' + self.locLineEdit.text())

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
        self._evaluate_(date.toString('yyyyMMdd') + 'd')

    def timeChanged(self, time: QtCore.QTime):
        self._evaluate_(time.toString('HHmm') + 't')

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
        self._evaluate_('-l' + self.myLocLineEdit.text())

    def myNameChanged(self):
        self._evaluate_('-n' + self.myNameLineEdit.text())

    def eventChanged(self, event: str):
        if event and event != self.tr('Event ID'):
            event = CONTEST_IDS.get(self.eventComboBox.currentText().strip(), self.eventComboBox.currentText().strip())
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
