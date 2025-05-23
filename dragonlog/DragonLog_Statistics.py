# DragonLog (c) 2025 by Andreas Schawo is licensed under CC BY-SA 4.0.
# To view a copy of this license, visit http://creativecommons.org/licenses/by-sa/4.0/

from PyQt6 import QtWidgets, QtSql

import numpy as np


class StatisticsWidget(QtWidgets.QDialog):
    def __init__(self, parent, title: str, db_con: QtSql.QSqlDatabase, bands: tuple):
        super().__init__(parent)

        self.__db_con__ = db_con
        self.__bands__ = bands

        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumSize(600, 300)
        verticalLayout = QtWidgets.QVBoxLayout()
        self.setLayout(verticalLayout)
        self.tabWidget = QtWidgets.QTabWidget()
        verticalLayout.addWidget(self.tabWidget)

        self.buildTableStat('QSO', (self.tr('QSOs'), self.tr('Modes'), self.tr('Bands'),
                                    self.tr('Gridsquares'), self.tr('Contest QSOs')))
        self.buildTableStat('QSL', (self.tr('QSOs'),
                                    self.tr('QSL sent'), self.tr('QSL rcvd'),
                                    self.tr('eQSL sent'), self.tr('eQSL rcvd'),
                                    self.tr('LotW sent'), self.tr('LotW rcvd')))
        self.buildTableStat('Mode', (self.tr('QSOs'),))
        self.buildBandStat()

        self.show()

    def fetchStat(self, name='qso') -> list[list]:
        stat = []
        if self.__db_con__ and name in ('qso', 'qsl', 'band', 'mode'):
            query = self.__db_con__.exec(f'SELECT * FROM {name}_stat')
            if query.lastError().text():
                raise Exception(query.lastError().text())

            rec = query.record()
            col_count = rec.count()
            stat.append([rec.fieldName(i) for i in range(col_count)])
            while query.next():
                stat.append([query.value(i) for i in range(col_count)])
        return stat

    def buildTableStat(self, title: str, header: tuple = (), stat: list[list] = None):
        stat = self.fetchStat(title.lower()) if not stat else stat
        if not stat:
            return

        tableWidget = QtWidgets.QTableWidget(len(stat) - 1, len(stat[0]) - 1)
        tableWidget.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        tableWidget.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        tableWidget.setVerticalHeaderLabels([r[0] for r in stat[1:]])

        if header:
            tableWidget.setHorizontalHeaderLabels(header)
        else:
            tableWidget.setHorizontalHeaderLabels([hl.capitalize() for hl in stat[0][1:]])

        self.tabWidget.addTab(tableWidget, f'{title}-{self.tr("Statistic")}')

        for r, row in enumerate(stat[1:]):
            for c, cell in enumerate(row[1:]):
                item = QtWidgets.QTableWidgetItem(str(cell))
                tableWidget.setItem(r, c, item)

        tableWidget.resizeColumnsToContents()

    def buildBandStat(self):
        band_stat = self.fetchStat('band')
        if band_stat and len(band_stat) > 1:
            band_stat_sorted = [band_stat[0]]
            band_stat = np.array(band_stat[1:]).transpose().tolist()
            for b in self.__bands__:
                if b in band_stat[0]:
                    band_stat_sorted.append([b, band_stat[1][band_stat[0].index(b)]])

            self.buildTableStat('Band', (self.tr('QSOs'),), band_stat_sorted)
