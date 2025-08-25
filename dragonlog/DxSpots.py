# DragonLog (c) 2023-2025 by Andreas Schawo is licensed under CC BY-SA 4.0.
# To view a copy of this license, visit http://creativecommons.org/licenses/by-sa/4.0/

import json
import socket
import logging
import time

from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtCore import QModelIndex
from PyQt6.QtGui import QStandardItem

from . import DxSpots_ui
from .Logger import Logger
from .cty import CountryNotFoundException, CountryCodeNotFoundException


class DxCluster(QtCore.QThread):
    spotReceived = QtCore.pyqtSignal(str)
    auroraBeaconReceived = QtCore.pyqtSignal(str)
    announcementReceived = QtCore.pyqtSignal(str)
    dataReceived = QtCore.pyqtSignal(str)
    newMailReceived = QtCore.pyqtSignal(str)

    def __init__(self, logger: Logger, address: str, port: int, call: str):
        super().__init__()

        self.log = logging.getLogger('DxCluster')
        self.log.addHandler(logger)
        self.log.setLevel(logger.loglevel)
        self.logger = logger
        self.log.debug('Initialising...')

        self.__address__ = address, port
        self.__callsign__ = call.upper()
        self.__receive__ = True
        self.__socket__ = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__is_connected__ = False
        self.__connect__()
        self.__cmds__: list = []
        self.__lock__ = QtCore.QMutex()

        self.dataReceived.connect(self.logData)
        self.newMailReceived.connect(self.logMessage)
        self.announcementReceived.connect(self.logMessage)
        self.auroraBeaconReceived.connect(self.logAuroraBeacon)

    def __connect__(self):
        self.__socket__.connect(self.__address__)
        self.__socket__.settimeout(.1)
        data = ''
        login_rcvd = False
        t_start = time.time()
        while not login_rcvd and time.time() - t_start < 2000:
            try:
                data += self.__socket__.recv(1024).replace(b'\r', b'').decode()
                if data.endswith('login: '):
                    login_rcvd = True
            except TimeoutError:
                pass

        if login_rcvd:
            self.log.debug('Received login request')
            self.__socket__.sendall(f'{self.__callsign__}\n'.encode())

            try:
                data = self.__socket__.recv(1024).decode()
                if data.startswith('Hello'):
                    self.__is_connected__ = True
                    self.log.info(
                        f'Loggedin to DX cluster {self.__address__[0]}:{self.__address__[1]} as {self.__callsign__}')
                    for dt in data.split('\n'):
                        if dt.startswith('New mail has arrived for you'):
                            self.newMailReceived.emit(dt.strip())
                            break
                elif data.startswith('Sorry'):
                    raise Exception(f'Login error with call "{self.__callsign__}": valid callsign required')
                else:
                    self.log.debug(data)
                    raise Exception(f'Login failed to DX cluster {self.__address__[0]}:{self.__address__[1]}')
            except TimeoutError:
                pass
        else:
            raise Exception(f'Connection failed to DX cluster {self.__address__[0]}:{self.__address__[1]}')

    @property
    def isConnected(self) -> bool:
        return self.__is_connected__

    def stop(self):
        self.sendCmd('bye')
        time.sleep(.1)
        self.__receive__ = False
        self.__is_connected__ = False
        time.sleep(.1)
        self.__socket__.close()
        self.log.debug('Diconnected from cluster')

    def run(self):
        self.__socket__.sendall(b'show/dx 10 real\nset/dx\n')
        while self.__receive__:
            try:
                data = self.__socket__.recv(1024).replace(b'\r', b'').decode()
                for dt in reversed(data.strip().split('\n')):
                    if dt.startswith('DX de'):
                        # DX de S52WW:     14268.0  SK6BA        USB                            0636Z
                        self.spotReceived.emit(dt.strip())
                    elif dt.startswith('WCY de'):
                        # WCY de DK0WCY-2 <08> : K=1 expK=0 A=22 R=95 SFI=214 SA=act GMF=act Au=no
                        self.auroraBeaconReceived.emit(dt.strip())
                    # elif dt.startswith('WWV de'):
                    # WWV de AE5E <09>:   SFI=214, A=20, K=1, Minor w/G1 -> No Storms
                    # self.auroraBeaconReceived.emit(dt.strip())
                    elif dt.startswith('To ALL de'):
                        # To ALL de ON5CAZ: Onff-0189 wca on-02734 pota be-0239
                        self.announcementReceived.emit(dt.strip())
                    elif dt.startswith('New mail has arrived for you'):
                        self.newMailReceived.emit(dt.strip())
                    else:
                        self.dataReceived.emit(dt.strip())
                if self.__cmds__:
                    self.__lock__.lock()
                    cmd = self.__cmds__.pop(0)
                    self.__socket__.sendall(f'{cmd}\n'.encode())
                    self.__lock__.unlock()
            except TimeoutError:
                pass
            except (ConnectionAbortedError, OSError):
                self.__receive__ = False
            except UnicodeDecodeError:
                pass
            except Exception as exc:
                self.log.exception(exc)

    def logData(self, data: str):
        self.log.debug(data.replace('\a', ''))

    def logMessage(self, data: str):
        self.log.warning(data.replace('\a', ''))

    def logAuroraBeacon(self, data: str):
        self.log.info(data.replace('\a', ''))

    def sendCmd(self, cmd: str):
        self.__lock__.lock()
        self.__cmds__.append(cmd)
        self.__lock__.unlock()


# noinspection PyPep8Naming
class DxSpotsFilterProxy(QtCore.QSortFilterProxyModel):
    def __init__(self, parent, columns: int):
        super().__init__(parent)

        self.columns = columns
        self.filter: dict[int, str] | None = None
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

    def __init__(self, parent, dragonlog, country_col: int, call_cols: tuple[int, int]):
        super(FlagsTableModel, self).__init__(parent)

        self.country_col = country_col
        self.call_cols = call_cols

        self.countries: dict = {}
        with open(dragonlog.searchFile(f'icons:flags/flags_map.json')) as fm_f:
            self.countries: dict = json.load(fm_f)

        for c in self.countries:
            self.countries[c] = QtGui.QIcon(dragonlog.searchFile(f'icons:flags/{self.countries[c]}.png'))

    def data(self, idx, role=QtCore.Qt.ItemDataRole.DisplayRole):
        value = super().data(idx, role)

        if role == QtCore.Qt.ItemDataRole.DecorationRole:
            if idx.column() == self.country_col:
                txt = super().data(idx,
                                   QtCore.Qt.ItemDataRole.DisplayRole).replace('&', 'and').replace('St. ', 'Saint ')
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

        self.header = [
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

        self.tableModel = FlagsTableModel(self, dragonlog, 8, (0, 3))
        self.filterModel = DxSpotsFilterProxy(self, len(self.header))
        self.filterModel.setSourceModel(self.tableModel)
        self.tableView.setModel(self.filterModel)

        self.clear()

        bands: list = self.__settings__.value('ui/show_bands', list(dragonlog.bands.keys()))
        if '11m' in bands:
            bands.remove('11m')
        self.bandComboBox.insertItem(0, self.tr('- all -'))
        self.bandComboBox.insertItems(1, bands)

        self.spContComboBox.insertItems(0, [self.tr('- all -'), 'AF', 'AN', 'AS', 'EU', 'NA', 'OC', 'SA'])

        self.__refresh__ = False

        self.dxc = None

    def clear(self):
        self.tableModel.clear()
        self.tableModel.setHorizontalHeaderLabels(self.header)
        self.tableView.resizeColumnsToContents()

    def control(self, state: bool):
        if state:
            try:
                self.__refresh__ = True
                dx_call = self.__settings__.value('dx_spots/call', '')
                self.dxc = DxCluster(self.logger,
                                     self.__settings__.value('dx_spots/address', 'hamqth.com'),
                                     int(self.__settings__.value('dx_spots/port', 7300)),
                                     dx_call if dx_call else self.__settings__.value('station/callSign', ''))
                self.clear()
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
        if len(data) < 74 and not data.startswith('DX de'):
            return

        spot = [''] * 9
        spot[1] = '-'
        spot[6] = '-'
        spot[8] = self.tr('- unknown -')

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

            sp_cty = self.__dragonlog__.cty_data(spotter)
            if sp_cty:
                spot[1] = sp_cty.continent

            cty_d = self.__dragonlog__.cty_data(call)
            if cty_d:
                spot[6] = cty_d.continent
                spot[8] = cty_d.name
        except (CountryCodeNotFoundException, CountryNotFoundException) as exc:
            self.log.error(exc)
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
        call = index.siblingAtColumn(3).data()
        band = index.siblingAtColumn(7).data()
        try:
            freq = float(index.siblingAtColumn(2).data())
        except ValueError:
            freq = 0.0
        self.log.debug(f'Selected spot {call}, {band}, {freq}')
        self.spotSelected.emit(call, band, freq)
