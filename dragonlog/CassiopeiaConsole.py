import logging

from PyQt6 import QtWidgets, QtCore
from hamcc import hamcc

from . import CassiopeiaConsole_ui
from .Logger import Logger


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

        self.refreshDisplay()

    def refreshDisplay(self):
        qso = self.__cc__.current_qso

        self.myCallLineEdit.setText(qso.get('STATION_CALLSIGN', ''))
        my_loc = f'{qso["MY_CITY"]} ({qso.get("MY_GRIDSQUARE", "")})' if 'MY_CITY' in qso else qso.get('MY_GRIDSQUARE', '')
        self.myLocLineEdit.setText(my_loc)
        self.myNameLineEdit.setText(qso.get('MY_NAME', ''))

        if 'CONTEST_ID' in qso:
            self.eventLineEdit.setText(qso['CONTEST_ID'])
            self.exchTXLineEdit.setText(qso.get('STX', qso.get('STX_STRING', '')))
            self.exchRXLineEdit.setText(qso.get('SRX', qso.get('SRX_STRING', '')))
        elif 'MY_SIG' in qso:
            self.eventLineEdit.setText(qso['MY_SIG'])
            self.exchTXLineEdit.setText(qso.get('MY_SIG_INFO', ''))
            self.exchRXLineEdit.setText(qso.get('SIG_INFO', ''))

        self.dateLineEdit.setText(hamcc.adif_date2iso(qso['QSO_DATE']))
        self.timeLineEdit.setText(hamcc.adif_time2iso(qso['TIME_ON']))
        self.bandLineEdit.setText(qso['BAND'])
        self.modeLineEdit.setText(qso['MODE'])
        self.callLineEdit.setText(qso['CALL'])
        loc = f'{qso["QTH"]} ({qso["GRIDSQUARE"]})' if 'QTH' in qso else qso["GRIDSQUARE"]
        self.locLineEdit.setText(loc)

        self.rstRXLineEdit.setText(qso.get('RST_RCVD', ''))
        self.rstTXLineEdit.setText(qso.get('RST_SENT', ''))
        self.nameLineEdit.setText(qso.get('NAME', ''))
        self.freqLineEdit.setText(qso.get('FREQ', ''))
        self.pwrLineEdit.setText(qso.get('TX_POWER', ''))
        self.qslLineEdit.setText(qso.get('QSL_RCVD', ''))
        self.commentLineEdit.setText(qso.get('COMMENT', ''))

    def evaluate(self, text: str):
        if text.endswith('~'):
            self.__cc__.clear()
            self.inputLineEdit.clear()
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
            self._evaluate_(text[:-1])

        self.refreshDisplay()

    def _evaluate_(self, text):
        if text:
            res = self.__cc__.evaluate(text)
            self.resultLabel.setText(self.tr(res))
            if res.startswith('Error:'):
                self.resultWidget.setStyleSheet('#resultWidget {background-color: rgba(255, 0, 0, 63)}')
            else:
                self.resultWidget.setStyleSheet('#resultWidget {background-color: rgba(0, 255, 0, 63)}')
            self.inputLineEdit.clear()

    def finaliseQSO(self):
        text = self.inputLineEdit.text()
        if text.startswith('"'):
            self._evaluate_(text[1:])
        else:
            self._evaluate_(text)
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

    def hasQSOs(self) -> bool:
        return self.__cc__.has_qsos()

    def retrieveQSO(self) -> dict[str, str]:
        qso = self.__cc__.pop_qso()
        self.refreshDisplay()
        return qso

    def clearInput(self):
        self.__cc__.clear()
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
        self.tr('Error: Wrong call format')
        self.tr('Error: Wrong QTH/maidenhead format')
        self.tr('Error: No active event')
        self.tr('Error: Unknown prefix')
        self.tr('Error: Wrong RST format')
        self.tr('Warning: Callsign missing for last QSO')
        self.tr('Last QSO cached')

