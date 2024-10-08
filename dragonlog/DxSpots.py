# DragonLog (c) 2023-2024 by Andreas Schawo is licensed under CC BY-SA 4.0.
# To view a copy of this license, visit http://creativecommons.org/licenses/by-sa/4.0/

import json
import socket
import logging
from audioop import reverse
from collections.abc import Generator

import requests
from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtCore import QModelIndex
from PyQt6.QtGui import QStandardItem

from . import DxSpots_ui
from .Logger import Logger
from . import cty


class DxCluster(QtCore.QThread):
    spotReceived = QtCore.pyqtSignal(str)

    def __init__(self, parent, logger: Logger, address: str, port: int, call: str):
        super().__init__()

        self.log = logging.getLogger('DxCluster')
        self.log.addHandler(logger)
        self.log.setLevel(logger.loglevel)
        self.logger = logger
        self.log.debug('Initialising...')

        self.__address__ = address, port
        self.__callsign__ = call
        self.__receive__ = True
        self.__socket__ = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__is_connected__ = False
        self.__connect__()

    def __connect__(self):
        self.__socket__.connect(self.__address__)
        data = self.__socket__.recv(1024).decode()
        self.log.debug('Received login request')
        if data.startswith('login:'):
            self.__socket__.sendall(f'{self.__callsign__}\n'.encode())
            data = self.__socket__.recv(1024).decode()
            if data.startswith(f'Hello {self.__callsign__}'):
                self.__is_connected__ = True
                self.log.info(
                    f'Loggedin to DX cluster {self.__address__[0]}:{self.__address__[1]} as {self.__callsign__}')
            elif data.startswith(f'Sorry {self.__callsign__} is an invalid callsign'):
                raise Exception(f'Login error with call "{self.__callsign__}": valid callsign required')
            else:
                raise Exception(f'Login failed to DX cluster {self.__address__[0]}:{self.__address__[1]}')

    @property
    def isConnected(self) -> bool:
        return self.__is_connected__

    def stop(self):
        self.__receive__ = False
        self.__is_connected__ = False
        self.__socket__.close()
        self.log.debug('Stopped receiving spots')

    def run(self):
        while self.__receive__:
            try:
                data = self.__socket__.recv(1024).decode()
                if data.startswith('DX de'):
                    self.spotReceived.emit(data.strip())
            except ConnectionAbortedError:
                self.__receive__ = False
            except UnicodeDecodeError:
                pass


class DxSpotsFilterProxy(QtCore.QSortFilterProxyModel):
    def __init__(self, parent, columns: int):
        super().__init__(parent)

        self.columns = columns
        self.filter: dict[int, str] = None
        self.clearFilter()

    def clearFilter(self):
        self.filter = dict(enumerate([''] * self.columns))

    def setFilter(self, column: int, filter: str):
        self.filter[column] = filter
        self.invalidateFilter()

    def filterAcceptsRow(self, sourceRow, sourceParent):
        indexes = [self.sourceModel().index(sourceRow, i, sourceParent) for i in range(self.columns)]

        return all([self.filter[i] == '' or self.sourceModel().data(indexes[i]) == self.filter[i] for i in
                    range(self.columns)])


class FlagsTableModel(QtGui.QStandardItemModel):
    """Show flags in country column"""

    def __init__(self, parent, dragonlog, country_col: int, ):
        super(FlagsTableModel, self).__init__(parent)

        self.country_col = country_col

        self.countries: dict = {}
        with open(dragonlog.searchFile(f'icons:flags/flags_map.json')) as fm_f:
            self.countries: dict = json.load(fm_f)

        for c in self.countries:
            self.countries[c] = QtGui.QIcon(dragonlog.searchFile(f'icons:flags/{self.countries[c]}.png'))

    def data(self, idx, role=QtCore.Qt.ItemDataRole.DisplayRole):
        value = super().data(idx, role)

        if role == QtCore.Qt.ItemDataRole.DecorationRole:
            if idx.column() == self.country_col:
                txt = super().data(idx, QtCore.Qt.ItemDataRole.DisplayRole).replace('&', 'and')
                if txt in self.countries:
                    return self.countries[txt]

        return value


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

        self.__dragonlog__ = dragonlog
        self.__settings__ = settings

        self.__refresh_timer__ = QtCore.QTimer(self)

        header = [
            self.tr('Spotter'),
            self.tr('Sp.Cnt.'),
            self.tr('Freq.'),
            self.tr('DX Call'),
            self.tr('Comments'),
            self.tr('Time'),
            self.tr('Cont.'),
            self.tr('Band'),
            self.tr('Country'),
        ]

        self.tableModel = FlagsTableModel(self, dragonlog, 8)
        self.filterModel = DxSpotsFilterProxy(self, len(header))
        self.filterModel.setSourceModel(self.tableModel)
        self.tableView.setModel(self.filterModel)

        self.tableModel.setHorizontalHeaderLabels(header)
        self.tableView.resizeColumnsToContents()

        bands: list = self.__settings__.value('ui/show_bands', list(dragonlog.bands.keys()))
        bands.pop(bands.index('11m'))
        self.bandComboBox.insertItem(0, self.tr('- all -'))
        self.bandComboBox.insertItems(1, bands)

        self.spContComboBox.insertItems(0, [self.tr('- all -'), 'AF', 'AN', 'AS', 'EU', 'NA', 'OC', 'SA'])

        self.__refresh__ = False

        self.__cty__ = None
        self.load_cty(self.__settings__.value('dx_spots/cty_data', ''))

        self.dxc = None

    def load_cty(self, cty_path: str):
        try:
            self.__cty__ = cty.CountryData(cty_path)
            self.log.debug(f'Using country data from "{cty_path}"')
        except Exception:
            self.__cty__ = cty.CountryData(self.__dragonlog__.searchFile('data:cty/cty.csv'))
            self.log.debug(f'Using country data default')

    @property
    def cty_version(self):
        return self.__cty__.version

    @property
    def cty_ver_entity(self):
        cty = self.__cty__.country('VERSION')
        return f'{cty.name}, {cty.code}'

    def control(self, state: bool):
        if state:
            try:
                self.__refresh__ = True
                self.dxc = DxCluster(self, self.logger,
                                     self.__settings__.value('dx_spots/address', 'hamqth.com'),
                                     int(self.__settings__.value('dx_spots/port', 7300)),
                                     self.__settings__.value('station/callSign', ''))
                self.dxc.spotReceived.connect(self.processSpot)
                self.dxc.start()
                self.startPushButton.setText(self.tr('Stop'))
            except Exception as exc:
                self.log.error(str(exc))
                self.startPushButton.setChecked(False)
                QtWidgets.QMessageBox.warning(self, self.tr('DX Spot'),
                                              self.tr('Error connecting to DX Cluster'))
        else:
            self.__refresh__ = False
            if self.dxc:
                self.dxc.stop()
            self.startPushButton.setText(self.tr('Start'))

    def band_from_freq(self, freq: float) -> str:
        """Get band from frequenzy
        :param freq: frequency in kHz
        :return: band"""
        freq = float(freq)
        for b in self.__dragonlog__.bands:
            if freq < self.__dragonlog__.bands[b][1]:
                if freq > self.__dragonlog__.bands[b][0]:
                    return b
        return ''

    def processSpot(self, data: str):
        self.log.debug(data)
        spot = [''] * 9
        try:
            spotter, freq = data[6:24].split(':')
            call = data[26:39].strip()
            comment = data[39:70].strip()
            tstamp = f'{data[70:72]}:{data[72:74]}'

            spot[0] = spotter
            spot[2] = freq.strip()
            spot[3] = call
            spot[4] = comment
            spot[5] = tstamp
            spot[7] = self.band_from_freq(float(freq.strip()))

            if self.__cty__:
                sp_cty = self.__cty__.country(spotter)
                spot[1] = sp_cty.continent
                cty = self.__cty__.country(call)
                spot[6] = cty.continent
                spot[8] = cty.name
        except Exception as exc:
            self.log.exception(exc)

        self.addSpotToTable(spot)

    def addSpotToTable(self, data: list):
        self.tableModel.insertRow(0, [QStandardItem(d) for d in data])
        self.tableView.resizeColumnsToContents()

        if self.tableModel.rowCount() > self.nrSpotsSpinBox.value():
            self.tableModel.removeRow(self.tableModel.rowCount() - 1)

    def bandChanged(self, band: str):
        if not band.startswith('-'):
            self.filterModel.setFilter(7, band)
        else:
            self.filterModel.setFilter(7, '')

    def spContChanged(self, cont: str):
        if not cont.startswith('-'):
            self.filterModel.setFilter(1, cont)
        else:
            self.filterModel.setFilter(1, '')

    def selectSpot(self, index: QModelIndex):
        call = self.tableModel.item(index.row(), 2).text()
        band = self.tableModel.item(index.row(), 6).text()
        try:
            freq = float(self.tableModel.item(index.row(), 1).text())
        except ValueError:
            freq = 0.0

        self.log.debug(f'Selected spot {call}, {band}, {freq}')
        self.spotSelected.emit(call, band, freq)
