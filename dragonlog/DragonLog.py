import os
import csv
import platform
import sys
import json
import datetime
from typing import Iterable

from PyQt6 import QtCore, QtWidgets, QtSql, QtGui
import adif_file
from adif_file import adi, adx
import xmltodict

OPTION_OPENPYXL = False
try:
    import openpyxl
    from openpyxl.styles import Font

    OPTION_OPENPYXL = True
except ImportError:
    pass

from . import DragonLog_MainWindow_ui
from .Logger import Logger
from .RegEx import find_non_ascii, check_format, REGEX_DATE
from .DragonLog_QSOForm import QSOForm
from .DragonLog_Settings import Settings
from .DragonLog_AppSelect import AppSelect
from .LoTW import LoTW, LoTWADIFFieldException, LoTWRequestException, LoTWCommunicationException
from . import ColorPalettes

__prog_name__ = 'DragonLog'
__prog_desc__ = 'Log QSO for Ham radio'
__author_name__ = 'Andreas Schawo, DF1ASC'
__author_email__ = 'andreas@schawo.de'
__copyright__ = 'Copyright 2023-2024 by Andreas Schawo,licensed under CC BY-SA 4.0'

from . import __version__ as version

__version__ = version.__version__

if version.__branch__:
    __version__ += '-' + version.__branch__
if version.__unclean__:
    __version__ += '-unclean'


class DatabaseOpenException(Exception):
    pass


class DatabaseWriteException(Exception):
    pass


class BackgroundBrushDelegate(QtWidgets.QStyledItemDelegate):
    """A delegate to change background color depending on a columns content and translation of different columns"""

    def __init__(self, color_map: dict, column: int):
        super(BackgroundBrushDelegate, self).__init__()

        self.color_map: dict = color_map
        self.column: int = column

    def getColor(self, value):
        color = [255, 255, 255, 0]  # white as fallback

        if value in self.color_map:
            color = self.color_map[value]
        elif 'default' in self.color_map:
            color = self.color_map['default']

        return color

    def initStyleOption(self, option: QtWidgets.QStyleOptionViewItem, index: QtCore.QModelIndex):
        super().initStyleOption(option, index)

        option.backgroundBrush = QtGui.QBrush(
            QtGui.QColor(*self.getColor(index.model().data(index.siblingAtColumn(self.column)))))


class TranslatedTableModel(QtSql.QSqlTableModel):
    """Translate propagation values and status to clear text and fancy icon for status"""

    def __init__(self, parent, db_conn, status_cols: Iterable, prop_col: int, prop_tr: dict):
        super(TranslatedTableModel, self).__init__(parent, db_conn)

        self.status_cols = status_cols
        self.status_translation = {
            'Y': self.tr('Y'),
            'N': self.tr('N'),
            'M': self.tr('M'),
            'R': self.tr('R'),
        }

        self.prop_col = prop_col
        self.prop_translation = prop_tr

        self.ok_icon = QtGui.QIcon(self.parent().searchFile('icons:ok.png'))
        self.no_icon = QtGui.QIcon(self.parent().searchFile('icons:no.png'))

    def data(self, idx, role=QtCore.Qt.ItemDataRole.DisplayRole):
        value = super().data(idx, role)
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            if idx.column() in self.status_cols and value in self.status_translation:
                return self.status_translation[value]
            elif idx.column() == self.prop_col and value in self.prop_translation:
                return self.prop_translation[value]

        if role == QtCore.Qt.ItemDataRole.DecorationRole:
            txt = super().data(idx, QtCore.Qt.ItemDataRole.DisplayRole)
            if idx.column() in self.status_cols:
                if txt in ('Y', 'M'):
                    return self.ok_icon
                else:
                    return self.no_icon

        return value


class DragonLog(QtWidgets.QMainWindow, DragonLog_MainWindow_ui.Ui_MainWindow):
    __sql_cols__ = (
        'id', 'date_time', 'date_time_off', 'own_callsign', 'call_sign', 'name', 'qth', 'locator',
        'rst_sent', 'rst_rcvd', 'band', 'mode', 'submode', 'freq', 'channel', 'power', 'propagation',
        'own_name', 'own_qth', 'own_locator', 'radio', 'antenna',
        'remarks', 'comments', 'dist',
        'qsl_via', 'qsl_path', 'qsl_msg', 'qsl_sent', 'qsl_rcvd',
        'eqsl_sent', 'eqsl_rcvd', 'lotw_sent', 'lotw_rcvd', 'hamqth',
        'contest_id', 'ctx_qso_id', 'crx_qso_id', 'crx_data',
    )

    __adx_cols__ = (
        'QSO_DATE/TIME_ON', 'QSO_DATE/TIME_OFF', 'STATION_CALLSIGN', 'CALL', 'NAME_INTL', 'QTH_INTL', 'GRIDSQUARE',
        'RST_SENT', 'RST_RCVD', 'BAND', 'MODE', 'SUBMODE', 'FREQ', 'APP_DRAGONLOG_CBCHANNEL', 'TX_PWR', 'PROP_MODE',
        'MY_NAME_INTL', 'MY_CITY_INTL', 'MY_GRIDSQUARE', 'MY_RIG_INTL', 'MY_ANTENNA_INTL',
        'NOTES_INTL', 'COMMENT_INTL', 'DISTANCE',
        'QSL_VIA', 'QSL_SENT_VIA', 'QSLMSG_INTL', 'QSL_SENT', 'QSL_RCVD',
        'EQSL_QSL_SENT', 'EQSL_QSL_RCVD', 'LOTW_QSL_SENT', 'LOTW_QSL_RCVD', 'HAMQTH_QSO_UPLOAD_STATUS',
        'CONTEST_ID', 'STX', 'SRX', 'SRX_STRING',
    )

    __db_create_stmnt__ = '''CREATE TABLE IF NOT EXISTS "qsos" (
                            "id"    INTEGER PRIMARY KEY NOT NULL,
                            "date_time"   NUMERIC,
                            "date_time_off"   NUMERIC,
                            "own_callsign" TEXT,
                            "call_sign"  TEXT,
                            "name"  TEXT,
                            "qth"    TEXT,
                            "locator" TEXT,
                            "rst_sent" TEXT,
                            "rst_rcvd" TEXT,
                            "band"    TEXT,
                            "mode"   TEXT,
                            "submode"  TEXT,
                            "freq"  REAL,
                            "channel"  INTEGER,
                            "power"  REAL,
                            "propagation"  TEXT,
                            "own_name"  TEXT,
                            "own_qth"   TEXT,
                            "own_locator" TEXT,
                            "radio"   TEXT,
                            "antenna"   TEXT,
                            "remarks"   TEXT,
                            "comments"   TEXT,
                            "dist" INTEGER,
                            "qsl_via"   TEXT,
                            "qsl_path"   TEXT,
                            "qsl_msg"   TEXT,
                            "qsl_sent"   TEXT,
                            "qsl_rcvd"   TEXT,
                            "eqsl_sent"   TEXT,
                            "eqsl_rcvd"   TEXT,
                            "lotw_sent"   TEXT,
                            "lotw_rcvd"   TEXT,
                            "hamqth"   TEXT,
                            "contest_id" TEXT,
                            "ctx_qso_id" INTEGER,
                            "crx_qso_id" INTEGER,
                            "crx_data" TEXT
                        );'''

    __db_create_idx_stmnt__ = '''CREATE INDEX IF NOT EXISTS "find_qso" ON "qsos" (
                                    "date_time",
                                    "call_sign"
                                )'''

    __db_insert_stmnt__ = 'INSERT INTO qsos (' + ",".join(__sql_cols__[1:]) + ') ' \
                                                                              'VALUES (' + ",".join(
        ["?"] * (len(__sql_cols__) - 1)) + ')'
    __db_update_stmnt__ = 'UPDATE qsos SET ' + "=?,".join(__sql_cols__[1:]) + '=? ' \
                                                                              'WHERE id = ?'
    __db_select_stmnt__ = 'SELECT * FROM qsos'

    @staticmethod
    def searchFile(name):
        file = QtCore.QFile(name)
        if file.exists():
            return file.fileName()

    def __init__(self, file=None, app_path='.'):
        super().__init__()

        self.setupUi(self)

        self.app_path = app_path
        self.help_dialog = None

        self.settings = QtCore.QSettings(self.tr(__prog_name__))

        self.log = Logger(self.logTextEdit, self.settings)
        self.log.info(f'Starting {__prog_name__} {__version__}...')

        if int(self.settings.value('ui/log_dock_float', 0)):
            self.logDockWidget.setFloating(True)
        else:
            log_dock_area = self.int2dock_area(int(self.settings.value('ui/log_dock_area',
                                                                       QtCore.Qt.DockWidgetArea.BottomDockWidgetArea.value)))
            self.addDockWidget(log_dock_area, self.logDockWidget)
        self.logDockWidget.setVisible(bool(int(self.settings.value('ui/show_log', 0))))

        if int(self.settings.value('ui/filter_dock_float', 0)):
            self.filterDockWidget.setFloating(True)
            self.filterDockWidget.resize(10, 10)
        else:
            filter_dock_area = self.int2dock_area(int(self.settings.value('ui/filter_dock_area',
                                                                          QtCore.Qt.DockWidgetArea.TopDockWidgetArea.value)))
            self.addDockWidget(filter_dock_area, self.filterDockWidget)
        self.filterDockWidget.setVisible(bool(int(self.settings.value('ui/show_filter', 0))))

        self.__table_filter__ = ''
        self.filterDockWidget.visibilityChanged.connect(self.resetTableFilter)
        self.filterDockWidget.dockLocationChanged.connect(self.filterWidgetResize)

        self.dummy_status = QtWidgets.QLabel()
        self.statusBar().addPermanentWidget(self.dummy_status)
        self.watch_status = QtWidgets.QLabel(self.tr('Watching file') + ': ' + self.tr('inactiv'))
        self.statusBar().addPermanentWidget(self.watch_status)
        self.hamlib_status = QtWidgets.QLabel(self.tr('Hamlib') + ': ' + self.tr('inactiv'))
        self.statusBar().addPermanentWidget(self.hamlib_status)
        self.hamlib_error = QtWidgets.QLabel('')
        self.statusBar().addPermanentWidget(self.hamlib_error)

        with open(self.searchFile('data:bands.json')) as bj:
            self.bands: dict = json.load(bj)
        with open(self.searchFile('data:modes.json')) as mj:
            self.modes: dict = json.load(mj)
        with open(self.searchFile('data:cb_channels.json')) as cj:
            self.cb_channels: dict = json.load(cj)
        with open(self.searchFile('data:color_map.json')) as cmj:
            color_map: dict = json.load(cmj)
        self.QSOTableView.setItemDelegate(BackgroundBrushDelegate(color_map, self.__sql_cols__.index('band')))

        self.fBandComboBox.insertItem(0, '')
        self.fModeComboBox.insertItem(0, '')
        self.fBandComboBox.insertItems(1, self.bands.keys())
        self.fModeComboBox.insertItems(1, self.modes['AFU'].keys())

        self.prop: dict = {
            '': '',
            'AS': self.tr('Aircraft Scatter'),
            'AUE': self.tr('Aurora-E'),
            'AUR': self.tr('Aurora'),
            'BS': self.tr('Back scatter'),
            'ECH': self.tr('EchoLink'),
            'EME': self.tr('Earth-Moon-Earth'),
            'ES': self.tr('Sporadic E'),
            'F2': self.tr('F2 Reflection'),
            'FAI': self.tr('Field Aligned Irregularities'),
            'GWAVE': self.tr('Ground Wave'),
            'INTERNET': self.tr('Internet-assisted'),
            'ION': self.tr('Ionoscatter'),
            'IRL': self.tr('IRLP'),
            'LOS': self.tr('Line of Sight'),
            'MS': self.tr('Meteor scatter'),
            'RPT': self.tr('Repeater or Transponder'),
            'RS': self.tr('Rain scatter'),
            'SAT': self.tr('Satellite'),
            'TEP': self.tr('Trans-equatorial'),
            'TR': self.tr('Tropospheric ducting'),
        }

        self.ascii_replace: dict = {}
        try:
            with open(self.searchFile(f'data:i18n/ascii_replace_{QtCore.QLocale.system().name()[:2]}.json'),
                      encoding='utf-8') as arf:
                self.ascii_replace = json.load(arf)
                self.log.debug(f'Loaded ascii_replace from "{arf.name}"')
        except Exception:
            self.log.debug(f'Found no ascii_replace_xx.json for "{print(QtCore.QLocale.system().name()[:2])}"')

        self.__headers__ = (
            self.tr('QSO'),
            self.tr('Date/Time start'),
            self.tr('Date/Time end'),
            self.tr('Own call sign'),
            self.tr('Call sign'),
            self.tr('Name'),
            self.tr('QTH'),
            self.tr('Locator'),
            self.tr('RST sent'),
            self.tr('RST rcvd'),
            self.tr('Band'),
            self.tr('Mode'),
            self.tr('Submode'),
            self.tr('Frequency'),
            self.tr('Channel'),
            self.tr('Power'),
            self.tr('Propagation'),
            self.tr('Own Name'),
            self.tr('Own QTH'),
            self.tr('Own Locator'),
            self.tr('Radio'),
            self.tr('Antenna'),
            self.tr('Notes'),
            self.tr('Comment'),
            self.tr('Distance'),
            self.tr('QSL via'),
            self.tr('QSL path'),
            self.tr('QSL message'),
            self.tr('QSL sent'),
            self.tr('QSL rcvd'),
            self.tr('eQSL sent'),
            self.tr('eQSL rcvd'),
            self.tr('LoTW sent'),
            self.tr('LoTW rcvd'),
            self.tr('HamQTH'),
            self.tr('Contest'),
            self.tr('Tx QSO ID'),
            self.tr('Rx QSO ID'),
            self.tr('Rx data'),
        )

        self.__header_map__ = dict(zip(self.__sql_cols__, self.__headers__))

        self.settings_form = Settings(self, self.settings, self.hamlib_status, self.__headers__, self.log)

        # QSOForm
        self.qso_form = QSOForm(self, self, self.bands, self.modes, self.prop, self.settings, self.settings_form,
                                self.cb_channels, self.hamlib_error, self.log)
        self.qsoDockWidget.setWidget(self.qso_form)
        self.qsoDockWidget.visibilityChanged.connect(self.qso_form.startTimers)
        self.qsoDockWidget.visibilityChanged.connect(self.qso_form.clear)

        if int(self.settings.value('ui/qso_dock_float', 0)):
            self.qsoDockWidget.setFloating(True)
        else:
            qso_dock_area = self.int2dock_area(int(self.settings.value('ui/qso_dock_area',
                                                                       QtCore.Qt.DockWidgetArea.RightDockWidgetArea.value)))
            self.addDockWidget(qso_dock_area,
                               self.qsoDockWidget)
        self.qsoDockWidget.setVisible(bool(int(self.settings.value('ui/show_qso', 0))))

        self.keep_logging = False

        # Database
        self.__db_con__ = QtSql.QSqlDatabase.addDatabase('QSQLITE', 'main')

        if file:
            self.log.info(f'Opening database from commandline {file}...')
            self.connectDB(file)
        elif self.settings.value('lastDatabase', None):
            if os.path.isfile(self.settings.value('lastDatabase', None)):
                self.log.info(f'Opening last database {self.settings.value("lastDatabase", None)}...')
                self.connectDB(self.settings.value('lastDatabase', None))
            else:
                self.log.warning(f'Opening last database {self.settings.value("lastDatabase", None)} failed!')

        self.watchAppSelect = AppSelect(self, f'{self.tr(__prog_name__)} - {self.tr("Watch application log")}',
                                        self.settings)
        self.watchTimer = QtCore.QTimer(self)
        self.watchTimer.timeout.connect(self.watchFile)
        self.watchPos = 0
        self.watchFileName = ''

        self.lotw = LoTW(self.log)

        self.settings_form.settingsStored.connect(self.qso_form.refreshQTHList)
        self.settings_form.settingsStored.connect(self.qso_form.refreshRadioList)
        self.settings_form.settingsStored.connect(self.qso_form.refreshAntennaList)

    @staticmethod
    def int2dock_area(value: int) -> QtCore.Qt.DockWidgetArea:
        dock_area = QtCore.Qt.DockWidgetArea.NoDockWidgetArea
        match value:
            case 1:
                dock_area = QtCore.Qt.DockWidgetArea.LeftDockWidgetArea
            case 2:
                dock_area = QtCore.Qt.DockWidgetArea.RightDockWidgetArea
            case 4:
                dock_area = QtCore.Qt.DockWidgetArea.TopDockWidgetArea
            case 8:
                dock_area = QtCore.Qt.DockWidgetArea.BottomDockWidgetArea

        return dock_area

    def filterWidgetResize(self):
        if self.filterDockWidget.isFloating():
            self.filterDockWidget.resize(10, 10)

    def showSettings(self):
        if self.settings_form.exec():
            self.refreshTableView()

    def selectDB(self):
        res = QtWidgets.QFileDialog.getSaveFileName(
            self,
            self.tr('Select file'),
            self.settings.value('lastDatabase', None),
            self.tr('QSO-Log (*.qlog);;All Files (*.*)'),
            options=QtWidgets.QFileDialog.Option.DontConfirmOverwrite)

        if res[0]:
            self.log.info(f'Selected database {res[0]}')
            self.connectDB(res[0])

    def checkDB(self, db_file):
        # Check database for missing cols
        res = self.__db_con__.exec('SELECT GROUP_CONCAT(NAME,",") as columns FROM PRAGMA_TABLE_INFO("qsos")')
        res.next()
        db_cols = res.value('columns')
        if not db_cols:
            QtWidgets.QMessageBox.critical(self, self.tr('Database error'),
                                           self.tr('Checking database failed. Content is not accessable.'))
            self.close()
            return False

        db_cols_l = db_cols.split(',')
        missing_cols = False
        for col in self.__sql_cols__:
            if col not in db_cols_l:
                missing_cols = True
                break

        if missing_cols:
            path, db_name = os.path.split(db_file)
            bck_name = os.path.join(path, datetime.date.today().strftime('%Y-%m-%d') + ' ' + db_name)

            QtWidgets.QMessageBox.warning(self, self.tr('Database structure out-dated'),
                                          self.tr('The database structure is out-dated and needs a conversion\n\n'
                                                  'A backup will be generated:') + f'\n"{bck_name}"',
                                          )

            # Create backup
            self.__db_con__.close()
            try:
                os.rename(db_file, bck_name)
            except FileExistsError:
                self.log.error('A database backup could not be created. The file already exists.')
                QtWidgets.QMessageBox.critical(self, self.tr('Database backup error'),
                                               self.tr('A database backup could not be created.\n'
                                                       'The file already exists.'))
                self.close()
                return False

            # Open new DB
            self.__db_con__.setDatabaseName(db_file)
            if self.__db_con__.lastError().text():
                raise DatabaseOpenException(self.__db_con__.lastError().text())
            self.__db_con__.open()
            self.__db_con__.exec(self.__db_create_stmnt__)
            if self.__db_con__.lastError().text():
                raise DatabaseOpenException(self.__db_con__.lastError().text())

            # Open backup
            db_con_bck = QtSql.QSqlDatabase.addDatabase('QSQLITE', 'backup')
            db_con_bck.setDatabaseName(bck_name)
            if db_con_bck.lastError().text():
                raise DatabaseOpenException(db_con_bck.lastError().text())
            db_con_bck.open()
            self.__db_con__.exec(self.__db_create_stmnt__)
            if self.__db_con__.lastError().text():
                raise DatabaseOpenException(self.__db_con__.lastError().text())

            q_read = db_con_bck.exec(f'SELECT {db_cols} FROM qsos')
            if q_read.lastError().text():
                raise Exception(q_read.lastError().text())

            insert_stmnt = f'INSERT INTO qsos ({db_cols}) ' \
                           'VALUES (' + ",".join(["?"] * len(db_cols_l)) + ')'

            while q_read.next():
                row = []
                for i in range(len(db_cols_l)):
                    row.append(q_read.value(i))

                q_write = QtSql.QSqlQuery(self.__db_con__)
                q_write.prepare(insert_stmnt)
                for i, val in enumerate(row):
                    q_write.bindValue(i, val)
                q_write.exec()
                if q_write.lastError().text():
                    raise Exception(q_write.lastError().text())

            self.__db_con__.commit()
            db_con_bck.close()

            QtWidgets.QMessageBox.information(self, self.tr('Database conversion'),
                                              self.tr('Database conversion finished')
                                              )

        return True

    def connectDB(self, db_file):
        db_file = os.path.abspath(db_file)
        try:
            if self.__db_con__.isOpen():
                self.__db_con__.close()

            self.__db_con__.setDatabaseName(db_file)
            self.__db_con__.open()
            self.__db_con__.exec(self.__db_create_stmnt__)
            self.__db_con__.exec(self.__db_create_idx_stmnt__)

            if self.__db_con__.lastError().text():
                raise DatabaseOpenException(self.__db_con__.lastError().text())

            if not self.checkDB(db_file):
                return

            model = TranslatedTableModel(self, self.__db_con__,
                                         status_cols=tuple(range(self.__sql_cols__.index('qsl_sent'),
                                                                 self.__sql_cols__.index('hamqth') + 1)),
                                         prop_col=self.__sql_cols__.index('propagation'),
                                         prop_tr=self.prop)
            model.setTable('qsos')
            self.QSOTableView.setModel(model)

            for c in self.__sql_cols__:
                model.setHeaderData(self.__sql_cols__.index(c),
                                    QtCore.Qt.Orientation.Horizontal,
                                    self.__header_map__[c])

            self.refreshTableView()

            self.log.info(f'Opened database {db_file}')
            self.settings.setValue('lastDatabase', db_file)
            self.setWindowTitle(__prog_name__ + ' - ' + db_file)
        except DatabaseOpenException as exc:
            self.log.exception(exc)
            if db_file == self.settings.value('lastDatabase', None):
                self.settings.setValue('lastDatabase', None)

            QtWidgets.QMessageBox.critical(
                self,
                f'{__prog_name__} - {self.tr("Error")}',
                str(exc))

    def refreshTableView(self, sort: bool = True):
        self.setFilter()

        hidden_cols = self.settings.value('ui/hidden_cols', '').split(',')
        for i in range(len(self.__headers__)):
            if str(i + 1) in hidden_cols:
                self.QSOTableView.hideColumn(i)
            else:
                self.QSOTableView.showColumn(i)

        if sort and self.settings.value('ui/sort_col', self.tr('Date/Time start')) in self.__headers__:
            sort_order = QtCore.Qt.SortOrder.AscendingOrder
            if self.settings.value('ui/sort_order', 'ASC') == 'DSC':
                sort_order = QtCore.Qt.SortOrder.DescendingOrder

            self.QSOTableView.sortByColumn(self.__headers__.index(self.settings.value('ui/sort_col',
                                                                                      self.tr('Date/Time start'))),
                                           sort_order)

        self.QSOTableView.resizeColumnsToContents()

    def getQueryStr(self):
        view_filter = self.getFilter()
        if view_filter:
            return f"SELECT * FROM qsos WHERE {view_filter}"
        else:
            return "SELECT * FROM qsos"

    def getFilter(self):
        if self.__table_filter__:
            return self.__table_filter__
        else:
            recent_filter = self.settings.value('ui/recent_qsos', self.tr('Show all'))
            if recent_filter == self.tr('Last week'):
                return "DATE(date_time) > DATE('now', '-7 days')"
            elif recent_filter == self.tr('Last month'):
                return "DATE(date_time) > DATE('now', '-31 days')"
            elif recent_filter == self.tr('Last half year'):
                return "DATE(date_time) > DATE('now', '-183 days')"
            elif recent_filter == self.tr('Last year'):
                return "DATE(date_time) > DATE('now', '-365 days')"
            else:
                return ""

    def setFilter(self):
        if self.QSOTableView.model():
            self.QSOTableView.model().setFilter(self.getFilter())

    def setTableFilter(self):
        filter_set = []

        if self.fDateFromLineEdit.text():
            if check_format(REGEX_DATE, self.fDateFromLineEdit.text()):
                filter_set.append(f"DATE(date_time) >= DATE('{self.fDateFromLineEdit.text()}')")
                self.fDateFromLineEdit.setPalette(ColorPalettes.PaletteDefault)
            else:
                self.fDateFromLineEdit.setPalette(ColorPalettes.PaletteFaulty)
        else:
            self.fDateFromLineEdit.setPalette(ColorPalettes.PaletteDefault)

        if self.fDateToLineEdit.text():
            if check_format(REGEX_DATE, self.fDateToLineEdit.text()):
                filter_set.append(f"DATE(date_time) <= DATE('{self.fDateToLineEdit.text()}')")
                self.fDateToLineEdit.setPalette(ColorPalettes.PaletteDefault)
            else:
                self.fDateToLineEdit.setPalette(ColorPalettes.PaletteFaulty)
        else:
            self.fDateToLineEdit.setPalette(ColorPalettes.PaletteDefault)

        if self.fCallsignLineEdit.text():
            filter_set.append(f'call_sign LIKE "%{self.fCallsignLineEdit.text()}%"')
        if self.fBandComboBox.currentText():
            filter_set.append(f'band = "{self.fBandComboBox.currentText()}"')
        if self.fModeComboBox.currentText():
            filter_set.append(f'mode = "{self.fModeComboBox.currentText()}"')

        self.__table_filter__ = ' AND '.join(filter_set)

        self.setFilter()

    def resetTableFilter(self):
        self.__table_filter__ = ''
        self.setFilter()

        self.fDateFromLineEdit.clear()
        self.fDateToLineEdit.clear()
        self.fCallsignLineEdit.clear()
        self.fBandComboBox.setCurrentIndex(0)
        self.fModeComboBox.setCurrentIndex(0)

    def ctrlHamlib(self, start):
        self.settings_form.ctrlRigctld(start)

    def logQSO(self):
        self.qso_form.clear()
        self.qso_form.setChangeMode(False)
        self.qso_form.reset()
        self.qsoDockWidget.setVisible(True)
        self.qso_form.callSignLineEdit.setFocus()

    def fetchQSO(self):
        self.log.info('Logging QSO...')
        query = QtSql.QSqlQuery(self.__db_con__)
        query.prepare(self.__db_insert_stmnt__)
        for i, val in enumerate(self.qso_form.values):
            query.bindValue(i, val)
        query.exec()
        if query.lastError().text():
            raise Exception(query.lastError().text())

        self.__db_con__.commit()
        self.refreshTableView(sort=False)

        self.hamlib_error.setText('')  # TODO: Why???

    def deleteQSO(self):
        res = QtWidgets.QMessageBox.question(self, self.tr('Delete QSO'),
                                             self.tr('Do you really want to delete the selected QSO(s)?'),
                                             defaultButton=QtWidgets.QMessageBox.StandardButton.No)

        if res == QtWidgets.QMessageBox.StandardButton.Yes:
            done_ids = []

            for i in self.QSOTableView.selectedIndexes():
                qso_id = self.QSOTableView.model().data(i.siblingAtColumn(0))

                if qso_id in done_ids or qso_id is None:
                    continue
                done_ids.append(qso_id)

                self.log.info(f'Deleting QSO #{qso_id}...')
                query = QtSql.QSqlQuery(self.__db_con__)
                query.prepare('DELETE FROM qsos where id == ?')
                query.bindValue(0, qso_id)
                query.exec()

                if query.lastError().text():
                    raise Exception(query.lastError().text())

            self.__db_con__.commit()
            self.refreshTableView(sort=False)

    def changeQSO(self):
        self.qso_form.clear()
        self.qsoDockWidget.setVisible(True)
        self.qso_form.setChangeMode()

        i = self.QSOTableView.selectedIndexes().pop(0)
        qso_id = self.QSOTableView.model().data(i.siblingAtColumn(0))

        query = self.__db_con__.exec(f'SELECT * FROM qsos WHERE id = {qso_id}')
        if query.lastError().text():
            raise Exception(query.lastError().text())

        values = []
        while query.next():
            for col in range(len(self.__sql_cols__)):
                values.append(query.value(col))
            break
        self.qso_form.values = dict(zip(self.__sql_cols__, values))

    def updateQSO(self, qso_id: int):
        self.log.info(f'Changing QSO {qso_id}...')
        values = self.qso_form.values
        values += (qso_id,)

        query = QtSql.QSqlQuery(self.__db_con__)
        query.prepare(self.__db_update_stmnt__)

        for col, val in enumerate(values):
            query.bindValue(col, val)
        query.exec()
        if query.lastError().text():
            raise Exception(query.lastError().text())

        self.__db_con__.commit()
        self.refreshTableView(sort=False)
        self.qso_form.setChangeMode(False)

    def clearQSOForm(self):
        self.qso_form.clear()
        self.qso_form.setChangeMode(False)

    def export(self):
        exp_formats = {
            self.tr('ADIF 3 (*.adx *.adi *.adif)'): self.exportADIF,
            self.tr('CSV-File (*.csv)'): self.exportCSV,
        }

        if OPTION_OPENPYXL:
            exp_formats[self.tr('Excel-File (*.xlsx)')] = self.exportExcel

        res = QtWidgets.QFileDialog.getSaveFileName(
            self,
            self.tr('Select export file'),
            self.settings.value('lastExportDir', os.path.abspath(os.curdir)),
            ';;'.join(exp_formats.keys()))

        if res[0]:
            try:
                exp_formats[res[1]](res[0])
            except Exception as exc:
                self.log.exception(exc)

            self.settings.setValue('lastExportDir', os.path.abspath(os.path.dirname(res[0])))

    def exportCSV(self, file):
        self.log.info('Exporting to CSV...')

        with open(file, 'w', newline='', encoding='utf-8') as cf:
            writer = csv.writer(cf)

            # Write header
            writer.writerow(self.__headers__)

            # Write content
            query_str = self.getQueryStr() if self.settings.value('imp_exp/only_recent',
                                                                  0) else self.__db_select_stmnt__
            query = self.__db_con__.exec(query_str)

            if query.lastError().text():
                raise Exception(query.lastError().text())

            while query.next():
                row = []
                for i in range(len(self.__sql_cols__)):
                    row.append(query.value(i))
                writer.writerow(row)

    def exportExcel(self, file):
        self.log.info('Exporting to XLSX...')
        xl_wb = openpyxl.Workbook()
        xl_wb.properties.title = self.tr('Exported QSO log')
        xl_wb.properties.description = f'{__prog_name__} {__version__}'
        xl_wb.properties.creator = os.getlogin()

        xl_ws = xl_wb.active
        xl_ws.title = 'QSOs'
        xl_ws.freeze_panes = 'A2'

        col_widths = []

        # Write header
        column = 1
        for h in self.__headers__:
            cell = xl_ws.cell(column=column, row=1, value=h)
            col_widths.append(len(h))  # Initialise width approximation
            cell.font = Font(bold=True)
            column += 1

        # Write content
        query_str = self.getQueryStr() if self.settings.value('imp_exp/only_recent', 0) else self.__db_select_stmnt__
        query = self.__db_con__.exec(query_str)
        row = 2
        while query.next():
            for col in range(len(self.__headers__)):
                val = query.value(col)
                xl_ws.cell(column=col + 1, row=row, value=val)
                val_len = len(str(val))
                if col_widths[col] < val_len:
                    col_widths[col] = val_len
            row += 1

        # Set auto filter
        xl_ws.auto_filter.ref = f'A1:{openpyxl.utils.get_column_letter(len(self.__headers__))}1'

        # Fit size to content width approximation
        for c, w in zip(range(1, len(col_widths) + 1), col_widths):
            # Add 5 due to Excel filter drop down
            xl_ws.column_dimensions[openpyxl.utils.get_column_letter(c)].width = w + 5

        # Finally save
        try:
            xl_wb.save(file)
            self.log.info(f'Saved "{file}"')
        except OSError as e:
            self.log.critical(e)
            QtWidgets.QMessageBox.critical(
                self,
                f'{__prog_name__} - {self.tr("Error")}',
                str(e))

    def replaceNonASCII(self, text: str) -> str:
        non_ascii = find_non_ascii(text)

        for na in non_ascii:
            if na:
                if na in self.ascii_replace:
                    text = text.replace(na, self.ascii_replace[na])
                else:
                    text = text.replace(na, '_')

        return text

    def exportADIF(self, file):
        self.log.info('Exporting to ADIF...')

        query_str = self.getQueryStr() if self.settings.value('imp_exp/only_recent', 0) else self.__db_select_stmnt__
        is_adx: bool = os.path.splitext(file)[-1] == '.adx'
        doc = self._build_adif_export_(query_str, is_adx)
        try:
            if is_adx:
                adx.dump(file, doc)
            else:
                adi.dump(file, doc, 'ADIF Export by DragonLog')

            self.log.info(f'Saved "{file}"')
        except Exception as exc:
            self.log.exception(exc)

    def _build_adif_export_(self, query_str, is_adx=False, include_id=False):
        doc = {
            'HEADER':
                {
                    'ADIF_VER': '3.1.4',
                    'PROGRAMID': __prog_name__,
                    'PROGRAMVERSION': __version__,
                    'CREATED_TIMESTAMP': QtCore.QDateTime.currentDateTimeUtc().toString('yyyyMMdd HHmmss')
                },
            'RECORDS': None,
        }
        records = []

        query = self.__db_con__.exec(query_str)
        if query.lastError().text():
            raise Exception(query.lastError().text())
        while query.next():
            band = query.value(self.__sql_cols__.index('band'))

            if band == '11m' and not self.settings.value('station_cb/cb_exp_adif', 0):
                continue

            qso_date, qso_time = query.value(self.__sql_cols__.index('date_time')).split()

            record = {'QSO_DATE': qso_date.replace('-', ''),
                      'TIME_ON': qso_time.replace(':', ''),
                      'APP': []}

            if include_id and query.value(self.__sql_cols__.index('id')):
                if is_adx:
                    record['APP'].append({'@PROGRAMID': 'DRAGONLOG',
                                          '@FIELDNAME': 'QSOID',
                                          '@TYPE': 'N',
                                          '$': query.value(self.__sql_cols__.index('id'))})
                else:
                    record['APP_DRAGONLOG_QSOID'] = query.value(self.__sql_cols__.index('id'))
            if query.value(self.__sql_cols__.index('date_time_off')):
                qso_date_off, qso_time_off = query.value(self.__sql_cols__.index('date_time_off')).split()
                record['QSO_DATE_OFF'] = qso_date_off.replace('-', '')
                record['TIME_OFF'] = qso_time_off.replace(':', '')

            if query.value(self.__sql_cols__.index('call_sign')):
                if band == '11m' and is_adx:
                    record['APP'].append({'@PROGRAMID': 'DRAGONLOG',
                                          '@FIELDNAME': 'CBCALL',
                                          '@TYPE': 'I',
                                          '$': query.value(self.__sql_cols__.index('call_sign'))})
                else:
                    record['CALL'] = self.replaceNonASCII(query.value(self.__sql_cols__.index('call_sign')))
            if query.value(self.__sql_cols__.index('name')):
                record['NAME'] = self.replaceNonASCII(query.value(self.__sql_cols__.index('name')))
                record['NAME_INTL'] = query.value(self.__sql_cols__.index('name'))
            if query.value(self.__sql_cols__.index('qth')):
                record['QTH'] = self.replaceNonASCII(query.value(self.__sql_cols__.index('qth')))
                record['QTH_INTL'] = query.value(self.__sql_cols__.index('qth'))
            if query.value(self.__sql_cols__.index('locator')):
                record['GRIDSQUARE'] = query.value(self.__sql_cols__.index('locator'))
            if query.value(self.__sql_cols__.index('rst_sent')):
                record['RST_SENT'] = query.value(self.__sql_cols__.index('rst_sent'))
            if query.value(self.__sql_cols__.index('rst_rcvd')):
                record['RST_RCVD'] = query.value(self.__sql_cols__.index('rst_rcvd'))
            if band:
                if band == '11m':
                    if is_adx:
                        record['APP'].append({'@PROGRAMID': 'DRAGONLOG',
                                              '@FIELDNAME': 'CBQSO',
                                              '@TYPE': 'B',
                                              '$': 'Y'})
                        if query.value(self.__sql_cols__.index("channel")):
                            record['APP'].append({'@PROGRAMID': 'DRAGONLOG',
                                                  '@FIELDNAME': 'CBCHANNEL',
                                                  '@TYPE': 'N',
                                                  '$': str(query.value(self.__sql_cols__.index("channel")))})
                    else:
                        record['BAND'] = band.upper()
                        record['APP_DRAGONLOG_CBQSO'] = 'Y'
                        if query.value(self.__sql_cols__.index("channel")):
                            record['APP_DRAGONLOG_CBCHANNEL'] = query.value(self.__sql_cols__.index("channel"))
                else:
                    record['BAND'] = band.upper()
            if query.value(self.__sql_cols__.index('mode')):
                record['MODE'] = query.value(self.__sql_cols__.index('mode'))
            if query.value(self.__sql_cols__.index("freq")):
                record['FREQ'] = f'{query.value(self.__sql_cols__.index("freq")) / 1000:0.3f}'
            if query.value(self.__sql_cols__.index('power')):
                record['TX_PWR'] = query.value(self.__sql_cols__.index('power'))
            if query.value(self.__sql_cols__.index('own_callsign')):
                if band == '11m' and is_adx:
                    record['APP'].append({'@PROGRAMID': 'DRAGONLOG',
                                          '@FIELDNAME': 'CBOWNCALL',
                                          '@TYPE': 'I',
                                          '$': query.value(self.__sql_cols__.index('own_callsign'))})
                else:
                    record['STATION_CALLSIGN'] = self.replaceNonASCII(
                        query.value(self.__sql_cols__.index('own_callsign')))
            if query.value(self.__sql_cols__.index('own_name')):
                record['MY_NAME'] = self.replaceNonASCII(query.value(self.__sql_cols__.index('own_name')))
                record['MY_NAME_INTL'] = query.value(self.__sql_cols__.index('own_name'))
            if query.value(self.__sql_cols__.index('own_qth')):
                record['MY_CITY'] = self.replaceNonASCII(query.value(self.__sql_cols__.index('own_qth')))
                record['MY_CITY_INTL'] = query.value(self.__sql_cols__.index('own_qth'))
            if query.value(self.__sql_cols__.index('own_locator')):
                record['MY_GRIDSQUARE'] = query.value(self.__sql_cols__.index('own_locator'))
            if query.value(self.__sql_cols__.index('radio')):
                record['MY_RIG'] = self.replaceNonASCII(query.value(self.__sql_cols__.index('radio')))
                record['MY_RIG_INTL'] = query.value(self.__sql_cols__.index('radio'))
            if query.value(self.__sql_cols__.index('antenna')):
                record['MY_ANTENNA'] = self.replaceNonASCII(query.value(self.__sql_cols__.index('antenna')))
                record['MY_ANTENNA_INTL'] = query.value(self.__sql_cols__.index('antenna'))
            if query.value(self.__sql_cols__.index('dist')):
                record['DISTANCE'] = query.value(self.__sql_cols__.index('dist'))
            if query.value(self.__sql_cols__.index('remarks')) and bool(
                    self.settings.value('imp_exp/own_notes_adif', 0)):
                remarks = query.value(self.__sql_cols__.index('remarks'))
                if platform.system() == 'Linux':
                    remarks = remarks.replace('\n', '\r\n')
                record['NOTES'] = self.replaceNonASCII(remarks)
                record['NOTES_INTL'] = remarks
            if query.value(self.__sql_cols__.index('comments')):
                comment = query.value(self.__sql_cols__.index('comments'))
                record['COMMENT'] = self.replaceNonASCII(comment)
                record['COMMENT_INTL'] = comment
            if query.value(self.__sql_cols__.index('qsl_via')):
                record['QSL_VIA'] = query.value(self.__sql_cols__.index('qsl_via'))
            if query.value(self.__sql_cols__.index('qsl_path')):
                record['QSL_SENT_VIA'] = query.value(self.__sql_cols__.index('qsl_path'))
            if query.value(self.__sql_cols__.index('qsl_msg')):
                qsl_msg = query.value(self.__sql_cols__.index('qsl_msg'))
                if platform.system() == 'Linux':
                    qsl_msg = qsl_msg.replace('\n', '\r\n')
                record['QSLMSG'] = self.replaceNonASCII(qsl_msg)
                record['QSLMSG_INTL'] = qsl_msg
            if query.value(self.__sql_cols__.index('qsl_sent')):
                record['QSL_SENT'] = query.value(self.__sql_cols__.index('qsl_sent'))
            if query.value(self.__sql_cols__.index('qsl_rcvd')):
                record['QSL_RCVD'] = query.value(self.__sql_cols__.index('qsl_rcvd'))
            if query.value(self.__sql_cols__.index('eqsl_sent')):
                record['EQSL_QSL_SENT'] = query.value(self.__sql_cols__.index('eqsl_sent'))
            if query.value(self.__sql_cols__.index('eqsl_rcvd')):
                record['EQSL_QSL_RCVD'] = query.value(self.__sql_cols__.index('eqsl_rcvd'))
            if query.value(self.__sql_cols__.index('lotw_sent')):
                record['LOTW_QSL_SENT'] = query.value(self.__sql_cols__.index('lotw_sent'))
            if query.value(self.__sql_cols__.index('lotw_rcvd')):
                record['LOTW_QSL_RCVD'] = query.value(self.__sql_cols__.index('lotw_rcvd'))
            if query.value(self.__sql_cols__.index('hamqth')):
                record['HAMQTH_QSO_UPLOAD_STATUS'] = query.value(self.__sql_cols__.index('hamqth'))
            if query.value(self.__sql_cols__.index('contest_id')):
                record['CONTEST_ID'] = query.value(self.__sql_cols__.index('contest_id'))
            if query.value(self.__sql_cols__.index('ctx_qso_id')):
                record['STX'] = query.value(self.__sql_cols__.index('ctx_qso_id'))
            if query.value(self.__sql_cols__.index('crx_qso_id')):
                record['SRX'] = query.value(self.__sql_cols__.index('crx_qso_id'))
            if query.value(self.__sql_cols__.index('crx_data')):
                record['SRX_STRING'] = query.value(self.__sql_cols__.index('crx_data'))

            if not record['APP']:
                record.pop('APP')

            records.append(record)
        doc['RECORDS'] = records
        return doc

    def lotwUpload(self):
        self.log.info('Signing and uploading to LoTW...')
        if platform.system() == 'Windows':
            stationf_path = os.path.expanduser('~/AppData/Roaming/TrustedQSL/station_data')
        elif platform.system() == 'Linux':
            stationf_path = os.path.expanduser('~/.tqsl/station_data')
        else:
            self.log.warning(f'System "{platform.system()}" is currently not supported to upload to LoTW')
            return

        if not os.path.isfile(stationf_path):
            QtWidgets.QMessageBox.warning(self, self.tr('LoTW ADIF upload'),
                                          self.tr('Missing station configuration in TQSL'))
            return

        try:
            with open(stationf_path) as st_f:
                station_xml = st_f.read()

            station_def = xmltodict.parse(station_xml)

            stations = {}
            for st in station_def['StationDataFile']['StationData']:
                stations[f"{st['CALL']} - {st['@name']}"] = {'name': st['@name'],
                                                             'locator': st['GRIDSQUARE']}
        except Exception as exc:
            self.log.exception(exc)
            return

        station, ok = QtWidgets.QInputDialog.getItem(self, self.tr('LoTW ADIF upload'),
                                                     self.tr('Select station'),
                                                     stations)
        if not ok:
            return

        self.log.info(f'Selected station "{station}"')
        locator = stations[station]['locator'].upper()
        doc = self._build_adif_export_(f"SELECT * FROM qsos "
                                       f"WHERE band != '11m' AND upper(own_locator) LIKE '{locator}%'"
                                       f"AND (lotw_sent != 'Y' OR lotw_sent is NULL)",
                                       include_id=True)
        if len(doc['RECORDS']) < 1:
            QtWidgets.QMessageBox.warning(self, self.tr('LoTW ADIF upload'),
                                          self.tr('No records for location') + f': "{locator}"')
            return

        passwd, ok = '', False
        if self.settings.value('lotw/cert_needs_pwd', 0):
            passwd, ok = QtWidgets.QInputDialog.getText(self, self.tr('LoTW ADIF upload'),
                                                        self.tr('TQSL signature password'),
                                                        echo=QtWidgets.QLineEdit.EchoMode.PasswordEchoOnEdit)
            if not ok:
                return

        try:
            if self.lotw.upload_log(stations[station]['name'], doc, passwd if ok else ''):
                for rec in doc['RECORDS']:
                    update_stmnt = "UPDATE qsos SET lotw_sent='Y', lotw_rcvd='R' WHERE id = ?"

                    self.log.debug(f"Changing LoTW status for QSO {rec['APP_DRAGONLOG_QSOID']}...")
                    query = QtSql.QSqlQuery(self.__db_con__)
                    query.prepare(update_stmnt)
                    query.bindValue(0, rec['APP_DRAGONLOG_QSOID'])
                    query.exec()
                    if query.lastError().text():
                        raise Exception(query.lastError().text())

                self.__db_con__.commit()
                self.refreshTableView()
        except LoTWADIFFieldException as exc:
            QtWidgets.QMessageBox.critical(self, self.tr('LoTW ADIF upload'),
                                           self.tr('A field is missing for upload') + f':\n"{exc.args[0]}"')
        except LoTWCommunicationException:
            QtWidgets.QMessageBox.critical(self, self.tr('LoTW ADIF upload'),
                                           self.tr('Connection error or network unreachable'))
        except LoTWRequestException:
            QtWidgets.QMessageBox.critical(self, self.tr('LoTW ADIF upload'),
                                           self.tr('Server rejected log'))

    def logImport(self):
        imp_formats = {
            self.tr('ADIF 3 (*.adx *.adi *.adif)'): self.logImportADIF,
            self.tr('CSV-File (*.csv)'): self.logImportCSV,
        }

        if OPTION_OPENPYXL:
            imp_formats[self.tr('Excel-File (*.xlsx)')] = self.logImportExcel

        res = QtWidgets.QFileDialog.getOpenFileName(
            self,
            self.tr('Select import file'),
            self.settings.value('lastImportDir', os.path.abspath(os.curdir)),
            ';;'.join(imp_formats.keys())
        )

        if res[0]:
            imp_formats[res[1]](res[0])

            self.settings.setValue('lastImportDir', os.path.dirname(res[0]))

    def logImportExcel(self, file):
        self.log.info('Importing from XLSX...')

        xl_wb = openpyxl.load_workbook(file, read_only=True, data_only=True)
        xl_ws = xl_wb.active

        lines = 0

        for ln, row in enumerate(xl_ws.iter_rows(), 1):
            if ln == 1:  # Skip header
                continue

            row = list(row)

            if not len(row) >= len(self.__sql_cols__):
                self.log.warning(f'XLSX import, row {ln} has too few columns.\nSkipped row.')
                QtWidgets.QMessageBox.warning(
                    self,
                    self.tr('Log import XLSX'),
                    f'Row {ln} has too few columns.\nSkipped row.'
                )
                continue

            if not row[1].value or not row[4].value:
                self.log.warning(f'XLSX import, QSO date/time or callsign missing in row {ln}.\nSkipped row.')
                QtWidgets.QMessageBox.warning(
                    self,
                    self.tr('Log import XLSX'),
                    f'QSO date/time or callsign missing in row {ln}.\nSkipped row.'
                )
                continue

            if self.findQSO(row[1].value, row[4].value):
                self.log.info(
                    f'XLSX import, QSO row {ln} already exists for {row[1].value} and {row[4].value}. Skipping row.')
                continue

            query = QtSql.QSqlQuery(self.__db_con__)
            query.prepare(self.__db_insert_stmnt__)

            for i, cell in enumerate(row[1:]):
                query.bindValue(i, cell.value)
            query.exec()
            if query.lastError().text():
                QtWidgets.QMessageBox.warning(
                    self,
                    self.tr('Log import XLSX'),
                    f'Row {ln} import error ("{query.lastError().text()}").\nSkipped row.'
                )
            else:
                lines += 1

        self.__db_con__.commit()
        self.refreshTableView()
        self.log.info(f'Imported {lines} QSOs from "{file}"')

    def logImportCSV(self, file):
        self.log.info('Importing from CSV...')

        with open(file, newline='', encoding='utf-8') as cf:
            reader = csv.reader(cf)
            lines = 0

            for ln, row in enumerate(reader, 1):
                if ln == 1:  # Skip header
                    continue

                if not len(row) >= len(self.__sql_cols__):
                    self.log.warning(f'CSV import, row {ln} has too few columns.\nSkipped row.')
                    QtWidgets.QMessageBox.warning(
                        self,
                        self.tr('Log import CSV'),
                        f'Row {ln} has too few columns.\nSkipped row.'
                    )

                if not row[1] or not row[4]:
                    self.log.warning(f'CSV import, QSO date/time or callsign missing in row {ln}.\nSkipped row.')
                    QtWidgets.QMessageBox.warning(
                        self,
                        self.tr('Log import CSV'),
                        f'QSO date/time or callsign missing in row {ln}.\nSkipped row.'
                    )
                    continue

                if self.findQSO(row[1], row[4]):
                    self.log.info(
                        f'CSV import, QSO row {ln} already exists for {row[1]} and {row[4]}. Skipping row.')
                    continue

                query = QtSql.QSqlQuery(self.__db_con__)
                query.prepare(self.__db_insert_stmnt__)

                for i, val in enumerate(row[1:]):
                    query.bindValue(i, val)
                query.exec()
                if query.lastError().text():
                    QtWidgets.QMessageBox.warning(
                        self,
                        self.tr('Log import CSV'),
                        f'Row {ln} import error ("{query.lastError().text()}").\nSkipped row.'
                    )
                else:
                    lines += 1

        self.__db_con__.commit()
        self.refreshTableView()
        self.log.info(f'Imported {lines} QSOs from "{file}"')

    def logImportADIF(self, file):
        self.log.info('Importing from ADIF...')

        is_adx: bool = os.path.splitext(file)[-1] == '.adx'

        if is_adx:
            records: list = adx.load(file)['RECORDS']
        else:
            records: list = adi.load(file)['RECORDS']

        imported = 0
        for i, r in enumerate(records, 1):
            if 'QSO_DATE' not in r or 'TIME_ON' not in r:
                self.log.warning(f'ADIF import, QSO date/time missing in record {i}.\nSkipped record.')
                QtWidgets.QMessageBox.warning(
                    self,
                    self.tr('Log import ADIF'),
                    f'QSO date/time missing in record {i}.\nSkipped record.'
                )
                continue

            if 'CALL' not in r:
                self.log.warning(f'ADIF import, callsign missing in record {i}.\nSkipped record.')
                QtWidgets.QMessageBox.warning(
                    self,
                    self.tr('Log import ADIF'),
                    f'Callsign missing in record {i}.\nSkipped record.'
                )
                continue

            adi_time = r['TIME_ON']
            adi_date = r['QSO_DATE']
            time = f'{adi_time[:2]}:{adi_time[2:4]}' if len(
                adi_time) == 4 else f'{adi_time[:2]}:{adi_time[2:4]}:{adi_time[4:6]}'
            timestamp = f'{adi_date[:4]}-{adi_date[4:6]}-{adi_date[6:8]} {time}'

            if self.findQSO(timestamp, r['CALL']):
                self.log.info(f'ADIF import, QSO {i} already exists for {timestamp} and {r["CALL"]}. Skipping record.')
                continue

            query = QtSql.QSqlQuery(self.__db_con__)
            query.prepare(self.__db_insert_stmnt__)

            for j, val in enumerate(self._build_adif_import_(r)):
                query.bindValue(j, val)
            query.exec()
            if query.lastError().text():
                QtWidgets.QMessageBox.warning(
                    self,
                    self.tr('Log import ADIF'),
                    f'Record {i} import error ("{query.lastError().text()}").\nSkipped record.'
                )
            else:
                imported += 1

        self.__db_con__.commit()
        self.refreshTableView()

        self.log.info(f'Imported {imported} QSOs from "{file}"')

    def _build_adif_import_(self, r, use_cfg_id=False, use_cfg_station=False):
        values = [''] * (len(self.__sql_cols__) - 1)
        date = r['QSO_DATE']
        timex = r['TIME_ON']
        time = f'{timex[:2]}:{timex[2:4]}' if len(timex) == 4 else f'{timex[:2]}:{timex[2:4]}:{timex[4:6]}'
        values[0] = f'{date[:4]}-{date[4:6]}-{date[6:8]} {time}'
        if 'TIME_OFF' in r:
            date_off = r['QSO_DATE_OFF'] if 'QSO_DATE_OFF' in r else date  # Fallback
            timex_off = r['TIME_OFF']
            time_off = f'{timex_off[:2]}:{timex_off[2:4]}' if len(
                timex_off) == 4 else f'{timex_off[:2]}:{timex_off[2:4]}:{timex_off[4:6]}'
            values[1] = f'{date_off[:4]}-{date_off[4:6]}-{date_off[6:8]} {time_off}'
        else:
            values[1] = values[0]

        if use_cfg_id:
            values[self.__sql_cols__.index('own_callsign') - 1] = self.settings.value('station/callSign', '')
            values[self.__sql_cols__.index('own_name') - 1] = self.settings.value('station/name', '')

        if use_cfg_station:
            values[self.__sql_cols__.index('radio') - 1] = self.settings.value('station/radio', '')
            values[self.__sql_cols__.index('antenna') - 1] = self.settings.value('station/antenna', '')
            values[self.__sql_cols__.index('own_qth') - 1] = self.settings.value('station/QTH', '')
            values[self.__sql_cols__.index('own_locator') - 1] = self.settings.value('station/own_locator', '')

        values[self.__sql_cols__.index('channel') - 1] = '-'

        submode_eval = False

        for p in r:
            match p:
                case 'QSO_DATE' | 'TIME_ON' | 'QSO_DATE_OFF' | 'TIME_OFF' | 'APP_DRAGONLOG_CBQSO':
                    continue
                case 'BAND':
                    values[self.__adx_cols__.index(p)] = r[p].lower()
                case 'FREQ':
                    freq = r[p].replace(',', '.')  # Workaround for wrong export from fldigi
                    values[self.__adx_cols__.index(p)] = str(float(freq) * 1000)
                case 'MODE':
                    if r[p] in self.modes['AFU'] or r[p] in self.modes['CB']:  # If it is a main mode
                        values[self.__adx_cols__.index(p)] = r[p]
                    else:  # Workaround for wrong mode export from fldigi
                        for m in self.modes['AFU']:
                            if r[p] in self.modes['AFU'][m]:
                                values[self.__adx_cols__.index(p)] = m
                                values[self.__adx_cols__.index('SUBMODE')] = r[p]
                                submode_eval = True
                                break
                case 'SUBMODE':
                    if not submode_eval:  # Set only if not already evaluated from mode
                        values[self.__adx_cols__.index(p)] = r[p]
                case 'APP':  # Only for ADX as ADI App fields are recognised the standard way
                    for af in r[p]:
                        af_param = f'APP_{af["@PROGRAMID"].upper()}_{af["@FIELDNAME"].upper()}'
                        if af_param in self.__adx_cols__:
                            values[self.__adx_cols__.index(af_param)] = af['$']
                        elif af_param == 'APP_DRAGONLOG_CBCALL':
                            values[self.__adx_cols__.index('CALL')] = af['$']
                        elif af_param == 'APP_DRAGONLOG_CBOWNCALL':
                            values[self.__adx_cols__.index('STATION_CALLSIGN')] = af['$']
                        elif af_param == 'APP_DRAGONLOG_CBQSO' and af['$'] == 'Y':
                            values[self.__adx_cols__.index('BAND')] = '11m'
                case 'OPERATOR':
                    if not 'STATION_CALLSIGN' in r or not r['STATION_CALLSIGN']:
                        values[self.__adx_cols__.index('STATION_CALLSIGN')] = r[p]
                case 'GUEST_OP':
                    if (not 'STATION_CALLSIGN' in r or not r['STATION_CALLSIGN']) and \
                            (not 'OPERATOR' in r or not r['OPERATOR']):
                        values[self.__adx_cols__.index('STATION_CALLSIGN')] = r[p]
                case p if p in self.__adx_cols__:
                    values[self.__adx_cols__.index(p)] = r[p]
                case p if p + '_INTL' not in r:  # Take non *_INTL only if no suiting *_INTL are in import
                    if p + '_INTL' in self.__adx_cols__:
                        values[self.__adx_cols__.index(p + '_INTL')] = r[p]

        return values

    def watchFile(self):
        with open(self.watchFileName, encoding='ASCII') as adi_f:
            adi_str = adi_f.read()

        added = False

        for i, rec in enumerate(adi.loadi(adi_str, self.watchPos)):
            if i == 0:
                continue

            self.watchPos += 1

            if 'QSO_DATE' not in rec or 'TIME_ON' not in rec or 'CALL' not in rec:
                self.log.warning(
                    f'QSO date, time or call missing in record #{self.watchPos + 1} from watched file. Skipped.')
                continue

            adi_time = rec['TIME_ON']
            adi_date = rec['QSO_DATE']
            time = f'{adi_time[:2]}:{adi_time[2:4]}' if len(
                adi_time) == 4 else f'{adi_time[:2]}:{adi_time[2:4]}:{adi_time[4:6]}'
            timestamp = f'{adi_date[:4]}-{adi_date[4:6]}-{adi_date[6:8]} {time}'

            if not self.findQSO(timestamp, rec['CALL']):
                self.log.info(f'Adding QSO #{i} from "{self.watchFileName}" to logbook...')

                query = QtSql.QSqlQuery(self.__db_con__)
                query.prepare(self.__db_insert_stmnt__)

                for j, val in enumerate(self._build_adif_import_(rec,
                                                                 bool(self.settings.value('imp_exp/use_id_watch',
                                                                                          0)),
                                                                 bool(self.settings.value(
                                                                     'imp_exp/use_station_watch', 0)))):
                    query.bindValue(j, val)
                query.exec()
                if query.lastError().text():
                    self.log.error(
                        f'Record #{self.watchPos + 1} import error from watched file ("{query.lastError().text()}").'
                        'Skipped.')

                self.__db_con__.commit()
                added = True

        if added:
            self.refreshTableView()

    def findQSO(self, timestamp, call):
        query = self.__db_con__.exec(f'SELECT date_time, call_sign from qsos '
                                     f'where date_time="{timestamp}" and call_sign="{call}"')
        if query.lastError().text():
            raise Exception(query.lastError().text())

        return query.next()

    def workedBefore(self, call):
        query = self.__db_con__.exec(f'SELECT call_sign from qsos '
                                     f'where call_sign LIKE"%{call}%"')
        if query.lastError().text():
            raise Exception(query.lastError().text())

        worked = []
        while query.next():
            call = query.value(0)
            if not call in worked:
                worked.append(call)

        return worked

    def ctrlWatching(self, start):
        if start:
            app_res = self.watchAppSelect.exec()
            if app_res:
                res = QtWidgets.QFileDialog.getOpenFileName(
                    self,
                    self.tr('Select file to watch'),
                    app_res[1],
                    self.tr('ADIF 3 (*.adi *.adif)')
                )

                if res[0]:
                    if app_res[0] == 'Other':
                        self.settings.setValue('lastWatchFile', res[0])
                    else:
                        self.settings.setValue(f'lastWatchFile{app_res[0]}', res[0])
                    self.watchFileName = res[0]
                    self.watchPos = 0
                    self.watchFile()  # Read file once before looping
                    self.watchTimer.start(2000)
                    self.watch_status.setText(self.tr('Watching file') + f': {os.path.basename(res[0])}')
                    self.actionWatch_file_for_QSOs.setChecked(True)
                    self.actionWatch_file_for_QSOs_TB.setChecked(True)
                    return
        else:
            self.watchTimer.stop()
            self.watch_status.setText(self.tr('Watching file') + ': ' + self.tr('inactiv'))

        self.actionWatch_file_for_QSOs.setChecked(False)
        self.actionWatch_file_for_QSOs_TB.setChecked(False)

    # noinspection PyPep8Naming
    def showHelp(self):
        if not self.help_dialog:
            with open(self.searchFile('help:README.md')) as hf:
                help_text = hf.read()

            self.help_dialog = QtWidgets.QDialog(self)
            self.help_dialog.setWindowTitle(f'{self.tr(__prog_name__)} - {self.tr("Help")}')
            self.help_dialog.resize(500, 500)
            verticalLayout = QtWidgets.QVBoxLayout(self.help_dialog)
            scrollArea = QtWidgets.QScrollArea(self.help_dialog)
            scrollArea.setWidgetResizable(True)
            scrollAreaWidgetContents = QtWidgets.QWidget()
            verticalLayout_2 = QtWidgets.QVBoxLayout(scrollAreaWidgetContents)
            helpLabel = QtWidgets.QLabel(scrollAreaWidgetContents)
            helpLabel.setTextFormat(QtCore.Qt.TextFormat.MarkdownText)
            helpLabel.setWordWrap(True)
            helpLabel.setOpenExternalLinks(True)
            verticalLayout_2.addWidget(helpLabel)
            scrollArea.setWidget(scrollAreaWidgetContents)
            verticalLayout.addWidget(scrollArea)
            horizontalLayout = QtWidgets.QHBoxLayout()
            horizontalSpacer = QtWidgets.QSpacerItem(40, 20,
                                                     QtWidgets.QSizePolicy.Policy.Expanding,
                                                     QtWidgets.QSizePolicy.Policy.Minimum)
            horizontalLayout.addItem(horizontalSpacer)
            pushButton = QtWidgets.QPushButton(self.help_dialog)
            pushButton.setText(self.tr('Ok'))
            horizontalLayout.addWidget(pushButton)
            verticalLayout.addLayout(horizontalLayout)
            # noinspection PyUnresolvedReferences
            pushButton.clicked.connect(self.help_dialog.accept)

            helpLabel.setText(help_text)

        self.help_dialog.show()

    @property
    def programName(self):
        return __prog_name__

    @property
    def programVersion(self):
        return __version__

    def showAbout(self):
        cr = sys.copyright.replace('\n\n', '\n')

        op_txt = f'\n\nOpenPyXL {openpyxl.__version__}: Copyright (c) 2010 openpyxl' if OPTION_OPENPYXL else ''

        QtWidgets.QMessageBox.about(
            self,
            f'{__prog_name__} - {self.tr("About")}',
            f'{self.tr("Version")}: {__version__}\n'
            f'{self.tr("Author")}: {__author_name__} <{__author_email__}>\n{__copyright__}'
            f'\n\nPython {sys.version.split()[0]}: {cr}' +
            op_txt +
            '\nmaidenhead: Copyright (c) 2018 Michael Hirsch, Ph.D.' +
            f'\nPyADIF-File {adif_file.__version_str__}: {adif_file.__copyright__}' +
            '\n\nIcons: Crystal Project, Copyright (c) 2006-2007 Everaldo Coelho'
            '\nDragon icon by Icons8 https://icons8.com'
        )

    def showAboutQt(self):
        QtWidgets.QMessageBox.aboutQt(self, __prog_name__ + ' - ' + self.tr('About Qt'))

    def closeEvent(self, e):
        self.log.info(f'Quiting {__prog_name__}...')
        self.__db_con__.close()

        self.settings.setValue('ui/show_log', int(self.logDockWidget.isVisible()))
        self.settings.setValue('ui/log_dock_area', self.dockWidgetArea(self.logDockWidget).value)
        self.settings.setValue('ui/log_dock_float', int(self.logDockWidget.isFloating()))

        self.settings.setValue('ui/show_filter', int(self.filterDockWidget.isVisible()))
        self.settings.setValue('ui/filter_dock_area', self.dockWidgetArea(self.filterDockWidget).value)
        self.settings.setValue('ui/filter_dock_float', int(self.filterDockWidget.isFloating()))

        self.settings.setValue('ui/show_qso', int(self.qsoDockWidget.isVisible()))
        self.settings.setValue('ui/qso_dock_area', self.dockWidgetArea(self.qsoDockWidget).value)
        self.settings.setValue('ui/qso_dock_float', int(self.qsoDockWidget.isFloating()))

        self.settings_form.ctrlRigctld(False)
        e.accept()


def main():
    app = QtWidgets.QApplication(sys.argv)
    app_path = os.path.dirname(__file__)

    css = '''QToolBox::tab {
        background: #b0c4de;
        border-radius: 2px;
        color: black;
    }'''
    app.setStyleSheet(css)

    translator = QtCore.QTranslator(app)
    translator.load(os.path.abspath(app_path + '/data/i18n/DragonLog_' + QtCore.QLocale.system().name()))
    app.installTranslator(translator)

    file = None
    args = app.arguments()
    if len(args) > 1:
        file = args[1]
        if not (os.path.isfile(file) and os.path.splitext(file)[-1] in ('.qlog', '.sqlite')):
            file = None

    QtCore.QDir.addSearchPath('icons', app_path + '/icons')
    QtCore.QDir.addSearchPath('data', app_path + '/data')
    QtCore.QDir.addSearchPath('help', app_path + '/data')

    dl = DragonLog(file, app_path)
    dl.show()

    sys.exit(app.exec())


# Get old behaviour on printing a traceback on exceptions
sys._excepthook = sys.excepthook


def except_hook(cls, exception, traceback):
    sys._excepthook(cls, exception, traceback)
    sys.exit(1)


sys.excepthook = except_hook

if __name__ == '__main__':
    main()
