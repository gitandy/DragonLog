import logging
from audioop import reverse
from collections.abc import Generator

import requests
from PyQt6 import QtWidgets, QtCore

from . import DxSpots_ui
from .Logger import Logger


class DxSpots(QtWidgets.QDialog, DxSpots_ui.Ui_DxSpotsForm):
    spotSelected = QtCore.pyqtSignal(str, str, float)

    def __init__(self, parent, dragonlog, settings: QtCore.QSettings, logger: Logger):
        super().__init__(parent)

        self.setupUi(self)

        self.log = logging.getLogger('DxSpots')
        self.log.addHandler(logger)
        self.log.setLevel(logger.loglevel)
        self.logger = logger
        self.log.debug('Initialising...')

        self.__settings__ = settings

        self.__refresh_timer__ = QtCore.QTimer(self)

        bands: list = self.__settings__.value('ui/show_bands', dragonlog.bands.keys())
        bands.pop(bands.index('11m'))
        self.bandComboBox.insertItem(0, self.tr('- all -'))
        self.bandComboBox.insertItems(1, bands)

        header = [
            self.tr('Spotter'),
            self.tr('Freq.'),
            self.tr('DX Call'),
            self.tr('Comments'),
            self.tr('Time'),
            self.tr('Cont.'),
            self.tr('Band'),
            self.tr('Country'),
        ]

        self.tableWidget.setColumnCount(len(header))
        self.tableWidget.setHorizontalHeaderLabels(header)

        self.__refresh__ = False
        self.__spots_idx__ = []

        self.__url__ = 'https://www.hamqth.com/dxc_csv.php'

    def retreiveSpots(self) -> Generator[list[str]]:
        band = self.bandComboBox.currentText().upper()
        params = {'limits': self.nrSpotsSpinBox.value()}
        if band and band != self.tr('- all -').upper():
            self.log.debug(f'Request DX Spots for {band.lower()} band...')
            params['band'] = band
        else:
            self.log.debug(f'Request DX Spots for all bands...')

        r = requests.get(self.__url__, params=params)
        if r.status_code == 200:
            for row in reversed(r.text.split('\n')):
                if not row.strip():
                    continue
                yield row.split('^')
        else:
            raise Exception(f'error: HTTP-Error {r.status_code}')

    def control(self, state: bool):
        if state:
            self.__refresh__ = True
            self.refreshSpotsView()
            self.startPushButton.setText(self.tr('Stop'))
        else:
            self.__refresh__ = False
            self.__refresh_timer__.stop()
            self.startPushButton.setText(self.tr('Start'))

    def refreshSpotsView(self):
        # ['NU4N', '14336.0', 'NC4XL', 'US POTA 10406 N.C.', '1411 2024-09-26', 'L', '', 'NA', '20M', 'United States', '291']]
        today = QtCore.QDateTime.currentDateTimeUtc().date().toString('yyyy-MM-dd')

        for spot in self.retreiveSpots():
            tstamp, dstamp = spot[4].split()

            if (spot[2] + spot[4]) not in self.__spots_idx__ and dstamp == today:
                self.__spots_idx__.append(spot[2] + spot[4])
                self.tableWidget.insertRow(0)
                self.tableWidget.setItem(0, 0, QtWidgets.QTableWidgetItem(spot[0]))
                self.tableWidget.setItem(0, 1, QtWidgets.QTableWidgetItem(spot[1]))
                self.tableWidget.setItem(0, 2, QtWidgets.QTableWidgetItem(spot[2]))
                self.tableWidget.setItem(0, 3, QtWidgets.QTableWidgetItem(spot[3]))
                self.tableWidget.setItem(0, 4, QtWidgets.QTableWidgetItem(f'{tstamp[:2]}:{tstamp[2:]}'))
                self.tableWidget.setItem(0, 5, QtWidgets.QTableWidgetItem(spot[7]))
                self.tableWidget.setItem(0, 6, QtWidgets.QTableWidgetItem(spot[8].lower()))
                self.tableWidget.setItem(0, 7, QtWidgets.QTableWidgetItem(spot[9]))


            if self.tableWidget.rowCount() > self.nrSpotsSpinBox.value():
                self.tableWidget.removeRow(self.tableWidget.rowCount() - 1)

        self.tableWidget.resizeColumnsToContents()

        if self.__refresh__:
            self.__refresh_timer__.singleShot(self.refreshRateSpinBox.value() * 1000, self.refreshSpotsView)

    def selectSpot(self, row: int, col: int):
        call = self.tableWidget.item(row, 2).text()
        band = self.tableWidget.item(row, 6).text()
        try:
            freq = float(self.tableWidget.item(row, 1).text())
        except ValueError:
            freq = 0.0

        self.log.debug(f'Selected spot {call}, {band}, {freq}')
        self.spotSelected.emit(call, band, freq)

