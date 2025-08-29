# DragonLog (c) 2023-2025 by Andreas Schawo is licensed under CC BY-SA 4.0.
# To view a copy of this license, visit http://creativecommons.org/licenses/by-sa/4.0/

import logging

from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtGui import QStandardItem

from .Logger import Logger
from . import ContestStatistics_ui
from .contest import CONTESTS, CONTEST_IDS
from .contest.base import ContestLog, Address, CategoryBand, CategoryMode, BandStatistics
from .cty import CountryData


class ContestStatistics(QtWidgets.QDialog, ContestStatistics_ui.Ui_ContestStatistics):
    contestSelected = QtCore.pyqtSignal(str)
    toDateSelected = QtCore.pyqtSignal(str)
    fromDateSelected = QtCore.pyqtSignal(str)

    def __init__(self, parent, dragonlog, settings: QtCore.QSettings, logger: Logger, cty: CountryData):
        super().__init__(parent)

        self.setupUi(self)

        self.log = logging.getLogger('ContestStatistics')
        self.log.addHandler(logger)
        self.log.setLevel(logger.loglevel)
        self.logger = logger
        self.log.debug('Initialising...')

        self.__dragonlog__ = dragonlog
        self.__settings__ = settings
        self.__cty__ = cty

        self.__header__ = [
            self.tr('QSOs'),
            self.tr('Rated'),
            self.tr('Points'),
            self.tr('Multis'),
            self.tr('Multis2'),
            self.tr('Total'),
        ]

        self.__statsModel__ = QtGui.QStandardItemModel(self)
        self.tableView.setModel(self.__statsModel__)
        self.tableView.horizontalHeader().setStyleSheet('font-weight: bold;')
        self.tableView.verticalHeader().setStyleSheet('font-weight: bold;')

        self.clear()

        self.contest: type[ContestLog] | None = None
        self.contestComboBox.insertItem(0, '')
        self.contestComboBox.insertItems(1, CONTEST_IDS.keys())

        dt = QtCore.QDateTime.currentDateTimeUtc()
        self.fromDateEdit.setDate(dt.date())
        self.toDateEdit.setDate(dt.date())

    def clear(self):
        self.__statsModel__.clear()
        self.__statsModel__.setHorizontalHeaderLabels(self.__header__)
        self.__statsModel__.setVerticalHeaderLabels(('',))
        self.tableView.resizeColumnsToContents()

        self.infosLabel.setText('0')
        self.warningsLabel.setText('0')
        self.errorsLabel.setText('0')

    def contestChanged(self, contest: str):
        self.contestSelected.emit(contest)
        self.clear()
        if contest:
            self.contest = CONTESTS[CONTEST_IDS[contest]]
            self.toDateEdit.setEnabled(not self.contest.is_single_day())
            self.fromDateSelected.emit(self.fromDateEdit.text())
            self.toDateSelected.emit(self.toDateEdit.text())
            self.fetchQSOs()
            self.__settings__.setValue('contest/id', contest)
        else:
            self.contest = None
            self.toDateSelected.emit('')
            self.fromDateSelected.emit('')
            self.toDateEdit.setEnabled(False)
            self.toDateEdit.setMinimumDate(self.fromDateEdit.date())
            self.toDateEdit.setDate(self.fromDateEdit.date())

        if self.contest and self.contest.needs_specific():
            self.specificLabel.setText(self.contest.descr_specific())
            self.specificLabel.setEnabled(True)
            self.specificLineEdit.setEnabled(True)
        else:
            self.specificLabel.setText(self.tr('Specific'))
            self.specificLabel.setEnabled(False)
            self.specificLineEdit.clear()
            self.specificLineEdit.setEnabled(False)

    def specificChanged(self):
        self.clear()
        if self.contest:
            self.fetchQSOs()
            self.__settings__.setValue('contest/specific', self.specificLineEdit.text())

    def fromDateChanged(self, date: QtCore.QDate):
        self.clear()
        if self.contest:
            self.fromDateSelected.emit(date.toString('yyyy-MM-dd'))
            if self.contest.is_single_day():
                self.toDateEdit.setMinimumDate(date)
                self.toDateEdit.setDate(date)
                self.toDateSelected.emit(date.toString('yyyy-MM-dd'))
            else:
                self.toDateEdit.setMinimumDate(date)
            self.fetchQSOs()
            self.__settings__.setValue('contest/from_date', self.fromDateEdit.text())
            self.__settings__.setValue('contest/to_date', self.toDateEdit.text())

    def toDateChanged(self, date: QtCore.QDate):
        if self.toDateEdit.isEnabled():
            self.clear()
            if self.contest:
                self.toDateSelected.emit(date.toString('yyyy-MM-dd'))
                self.fetchQSOs()
                self.__settings__.setValue('contest/to_date', self.toDateEdit.text())

    def fetchQSOs(self):
        if not self.contest:
            return

        doc = self.__dragonlog__.build_adif_export(f"SELECT * FROM qsos WHERE "
                                                   f"contest_id = '{CONTEST_IDS.get(self.contestComboBox.currentText(), '')}' AND "
                                                   f"DATE(date_time) >= DATE('{self.fromDateEdit.text()}') AND "
                                                   f"DATE(date_time) <= DATE('{self.toDateEdit.text()}') "
                                                   "ORDER BY date_time",
                                                   include_id=True)

        # noinspection PyTypeChecker
        contest: ContestLog = self.contest(self.__settings__.value('station/callSign', 'XX1XXX').upper(),
                                           '', '', Address('', '', '', ''), '', '',
                                           CategoryBand.B_ALL, CategoryMode.MIXED,
                                           specific=self.specificLineEdit.text(),
                                           logger=self.logger,
                                           cty=self.__cty__)

        if doc['RECORDS']:
            try:
                for rec in doc['RECORDS']:
                    contest.append(rec)
                self.infosLabel.setText(str(contest.infos))
                self.warningsLabel.setText(str(contest.warnings))
                self.errorsLabel.setText(str(contest.errors))
                self.showStats(contest.statistics)
                self.multisPlainTextEdit.setPlainText(', '.join(contest.multis_set))
                self.multis2PlainTextEdit.setPlainText(', '.join(contest.multis2_set))
            except Exception as exc:
                self.log.exception(exc)

    def showStats(self, stats: dict[str, BandStatistics]):
        self.__statsModel__.setVerticalHeaderLabels(list(stats.keys())[:-1] + [self.tr('Total')])
        for i, b in enumerate(stats):
            values = stats[b].values()
            for j, s in enumerate(values):
                item = QStandardItem(str(values[j]))
                item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
                self.__statsModel__.setItem(i, j, item)
        self.tableView.resizeColumnsToContents()
