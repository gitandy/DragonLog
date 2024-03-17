import os
import csv
import sys
import json
import datetime

from PyQt6 import QtCore, QtWidgets, QtSql, QtGui
import adif_file
from adif_file import adi, adx

OPTION_OPENPYXL = False
try:
    import openpyxl
    from openpyxl.styles import Font

    OPTION_OPENPYXL = True
except ImportError:
    pass

from . import DragonLog_MainWindow_ui
from .DragonLog_QSOForm import QSOForm
from .DragonLog_Settings import Settings
from .DragonLog_AppSelect import AppSelect

__prog_name__ = 'DragonLog'
__prog_desc__ = 'Log QSO for Ham radio'
__author_name__ = 'Andreas Schawo'
__author_email__ = 'andreas@schawo.de'
__copyright__ = 'Copyright 2023 by Andreas Schawo,licensed under CC BY-SA 4.0'

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
    def __init__(self, color_map, column):
        super(BackgroundBrushDelegate, self).__init__()

        self.color_map = color_map
        self.column = column

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


class DragonLog(QtWidgets.QMainWindow, DragonLog_MainWindow_ui.Ui_MainWindow):
    __sql_cols__ = ('id', 'date_time', 'date_time_off', 'own_callsign', 'call_sign', 'name', 'qth', 'locator',
                    'rst_sent', 'rst_rcvd', 'band', 'mode', 'freq', 'channel', 'power',
                    'own_name', 'own_qth', 'own_locator', 'radio', 'antenna',
                    'remarks', 'comments', 'dist',
                    'qsl_via', 'qsl_path', 'qsl_msg', 'qsl_sent', 'qsl_rcvd',
                    'eqsl_sent', 'eqsl_rcvd', 'hamqth')

    __adx_cols__ = (
        'QSO_DATE/TIME_ON', 'QSO_DATE/TIME_OFF', 'STATION_CALLSIGN', 'CALL', 'NAME_INTL', 'QTH_INTL', 'GRIDSQUARE',
        'RST_SENT', 'RST_RCVD', 'BAND', 'MODE', 'FREQ', 'APP_DRAGONLOG_CBCHANNEL', 'TX_PWR',
        'MY_NAME_INTL', 'MY_CITY_INTL', 'MY_GRIDSQUARE', 'MY_RIG_INTL', 'MY_ANTENNA_INTL',
        'NOTES_INTL', 'COMMENT_INTL',  'DISTANCE'
        'QSL_VIA', 'QSL_SENT_VIA', 'QSLMSG_INTL', 'QSL_SENT', 'QSL_RCVD',
        'EQSL_QSL_SENT', 'EQSL_QSL_RCVD', 'HAMQTH_QSO_UPLOAD_STATUS')

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
                            "freq"  REAL,
                            "channel"  INTEGER,
                            "power"  REAL,
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
                            "hamqth"   TEXT
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

        print(f'Starting {__prog_name__}...')

        self.setupUi(self)

        self.app_path = app_path
        self.help_dialog = None

        self.settings = QtCore.QSettings(self.tr(__prog_name__))

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
            self.tr('Frequency'),
            self.tr('Channel'),
            self.tr('Power'),
            self.tr('Own Name'),
            self.tr('Own QTH'),
            self.tr('Own Locator'),
            self.tr('Radio'),
            self.tr('Antenna'),
            self.tr('Notes'),
            self.tr('Comments'),
            self.tr('Distance'),
            self.tr('QSL via'),
            self.tr('QSL path'),
            self.tr('QSL message'),
            self.tr('QSL sent'),
            self.tr('QSL rcvd'),
            self.tr('eQSL sent'),
            self.tr('eQSL rcvd'),
            self.tr('HamQTH'),
        )

        self.__header_map__ = dict(zip(self.__sql_cols__, self.__headers__))

        self.settings_form = Settings(self, self.settings, self.hamlib_status, self.__headers__)

        self.qso_form = QSOForm(self, self.bands, self.modes, self.settings, self.settings_form,
                                self.cb_channels, self.hamlib_error)
        self.keep_logging = False

        self.__db_con__ = QtSql.QSqlDatabase.addDatabase('QSQLITE', 'main')

        if file:
            print(f'Opening database from commandline {file}...')
            self.connectDB(file)
        elif self.settings.value('lastDatabase', None):
            if os.path.isfile(self.settings.value('lastDatabase', None)):
                print(f'Opening last database {self.settings.value("lastDatabase", None)}...')
                self.connectDB(self.settings.value('lastDatabase', None))
            else:
                print(f'Opening last database {self.settings.value("lastDatabase", None)} failed!')

        self.watchAppSelect = AppSelect(self, f'{self.tr(__prog_name__)} - {self.tr("Watch application log")}',
                                        self.settings)
        self.watchTimer = QtCore.QTimer(self)
        self.watchTimer.timeout.connect(self.watchFile)
        self.watchPos = 0
        self.watchFileName = ''

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
            print(f'Selected database {res[0]}')
            self.connectDB(res[0])

    def checkDB(self, db_file):
        # Check database for missing cols
        res = self.__db_con__.exec('SELECT GROUP_CONCAT(NAME,",") as columns FROM PRAGMA_TABLE_INFO("qsos")')
        res.next()
        db_cols = res.value('columns')
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
            if self.__db_con__.lastError().text():
                raise DatabaseOpenException(self.__db_con__.lastError().text())
            self.__db_con__.open()
            self.__db_con__.exec(self.__db_create_stmnt__)
            self.__db_con__.exec(self.__db_create_idx_stmnt__)

            if self.__db_con__.lastError().text():
                raise DatabaseOpenException(self.__db_con__.lastError().text())

            if not self.checkDB(db_file):
                return

            model = QtSql.QSqlTableModel(self, self.__db_con__)
            model.setTable('qsos')

            for c in self.__sql_cols__:
                model.setHeaderData(self.__sql_cols__.index(c),
                                    QtCore.Qt.Orientation.Horizontal,
                                    self.__header_map__[c])

            self.QSOTableView.setModel(model)

            self.refreshTableView()

            print(f'Opened database {db_file}')
            self.settings.setValue('lastDatabase', db_file)
            self.setWindowTitle(__prog_name__ + ' - ' + db_file)
        except DatabaseOpenException as exc:
            if db_file == self.settings.value('lastDatabase', None):
                self.settings.setValue('lastDatabase', None)

            QtWidgets.QMessageBox.critical(
                self,
                f'{__prog_name__} - {self.tr("Error")}',
                str(exc))

    def refreshTableView(self):
        hidden_cols = self.settings.value('ui/hidden_cols', '').split(',')
        for i in range(len(self.__headers__)):
            if str(i+1) in hidden_cols:
                self.QSOTableView.hideColumn(i)
            else:
                self.QSOTableView.showColumn(i)

        if self.settings.value('ui/sort_col', self.tr('Date/Time start')) in self.__headers__:
            self.QSOTableView.sortByColumn(self.__headers__.index(self.settings.value('ui/sort_col',
                                                                                      self.tr('Date/Time start'))),
                                           QtCore.Qt.SortOrder.AscendingOrder)

        self.QSOTableView.resizeColumnsToContents()

    def ctrlHamlib(self, start):
        self.settings_form.ctrlRigctld(start)

    def logQSO(self):
        self.qso_form.clear()
        if not self.keep_logging:
            self.qso_form.reset()

        dt = QtCore.QDateTime.currentDateTimeUtc()
        self.qso_form.dateEdit.setDate(dt.date())
        self.qso_form.dateOnEdit.setDate(dt.date())
        self.qso_form.timeEdit.setTime(dt.time())
        self.qso_form.timeOnEdit.setTime(dt.time())

        if self.qso_form.exec():
            print('Logging QSO...')
            query = QtSql.QSqlQuery(self.__db_con__)
            query.prepare(self.__db_insert_stmnt__)
            for i, val in enumerate(self.qso_form.values):
                query.bindValue(i, val)
            query.exec()
            if query.lastError().text():
                raise Exception(query.lastError().text())

            self.__db_con__.commit()
            self.QSOTableView.model().select()
            self.QSOTableView.resizeColumnsToContents()
        else:
            print('Logging aborted')
            self.keep_logging = False

        self.hamlib_error.setText('')

    def logMultiQSOs(self):
        self.keep_logging = True

        self.qso_form.setWindowTitle(self.tr('Log multi QSOs'))

        while self.keep_logging:
            self.logQSO()

        self.qso_form.reset()  # To reset window title

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

                print(f'Deleting QSO #{qso_id}...')
                query = QtSql.QSqlQuery(self.__db_con__)
                query.prepare('DELETE FROM qsos where id == ?')
                query.bindValue(0, qso_id)
                query.exec()

                if query.lastError().text():
                    raise Exception(query.lastError().text())

            self.__db_con__.commit()
            self.QSOTableView.model().select()
            self.QSOTableView.resizeColumnsToContents()

    def changeQSO(self):
        done_ids = []
        self.qso_form.setChangeMode()

        for i in self.QSOTableView.selectedIndexes():
            qso_id = self.QSOTableView.model().data(i.siblingAtColumn(0))

            if qso_id in done_ids or qso_id is None:
                continue
            done_ids.append(qso_id)

            values = []
            for col in range(len(self.__sql_cols__)):
                values.append(self.QSOTableView.model().data(i.siblingAtColumn(col)))

            self.qso_form.clear()
            self.qso_form.setChangeMode()
            self.qso_form.values = dict(zip(self.__sql_cols__, values))

            self.qso_form.setWindowTitle(self.tr('Change QSO') + f' #{qso_id}')

            if self.qso_form.exec():
                print(f'Changing QSO {qso_id}...')
                values = self.qso_form.values
                values += (qso_id,)

                query = QtSql.QSqlQuery(self.__db_con__)
                query.prepare(self.__db_update_stmnt__)

                for col, val in enumerate(values):
                    query.bindValue(col, val)
                query.exec()
                if query.lastError().text():
                    raise Exception(query.lastError().text())
            else:
                print('Changing QSO(s) aborted')
                break

        self.__db_con__.commit()
        self.QSOTableView.model().select()
        self.QSOTableView.resizeColumnsToContents()
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
            exp_formats[res[1]](res[0])

            self.settings.setValue('lastExportDir', os.path.abspath(os.path.dirname(res[0])))

    def exportCSV(self, file):
        print('Exporting to CSV...')

        with open(file, 'w', newline='', encoding='utf-8') as cf:
            writer = csv.writer(cf)

            # Write header
            writer.writerow(self.__headers__)

            # Write content
            query = self.__db_con__.exec(self.__db_select_stmnt__)
            if query.lastError().text():
                raise Exception(query.lastError().text())

            while query.next():
                row = []
                for i in range(len(self.__sql_cols__)):
                    row.append(query.value(i))
                writer.writerow(row)

    def exportExcel(self, file):
        print('Exporting to Excel...')
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
        query = self.__db_con__.exec(self.__db_select_stmnt__)
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
        for c, w in zip(range(1, len(col_widths)+1), col_widths):
            # Add 5 due to Excel filter drop down
            xl_ws.column_dimensions[openpyxl.utils.get_column_letter(c)].width = w + 5

        # Finally save
        try:
            xl_wb.save(file)
            print(f'Saved "{file}"')
        except OSError as e:
            QtWidgets.QMessageBox.critical(
                self,
                f'{__prog_name__} - {self.tr("Error")}',
                str(e))

    @staticmethod
    def replaceUmlautsLigatures(text: str):
        text = text.replace('Ä', 'Ae')
        text = text.replace('Ö', 'Oe')
        text = text.replace('Ü', 'Ue')
        text = text.replace('ä', 'ae')
        text = text.replace('ö', 'oe')
        text = text.replace('ü', 'ue')
        text = text.replace('ß', 'ss')
        return text

    def exportADIF(self, file):
        print('Exporting to ADIF...')

        is_adx: bool = os.path.splitext(file)[-1] == '.adx'

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

        query = self.__db_con__.exec(self.__db_select_stmnt__)
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
                    record['CALL'] = self.replaceUmlautsLigatures(query.value(self.__sql_cols__.index('call_sign')))
            if query.value(self.__sql_cols__.index('name')):
                record['NAME'] = self.replaceUmlautsLigatures(query.value(self.__sql_cols__.index('name')))
                record['NAME_INTL'] = query.value(self.__sql_cols__.index('name'))
            if query.value(self.__sql_cols__.index('qth')):
                record['QTH'] = self.replaceUmlautsLigatures(query.value(self.__sql_cols__.index('qth')))
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
                    record['STATION_CALLSIGN'] = self.replaceUmlautsLigatures(
                        query.value(self.__sql_cols__.index('own_callsign')))
            if query.value(self.__sql_cols__.index('own_name')):
                record['MY_NAME'] = self.replaceUmlautsLigatures(query.value(self.__sql_cols__.index('own_name')))
                record['MY_NAME_INTL'] = query.value(self.__sql_cols__.index('own_name'))
            if query.value(self.__sql_cols__.index('own_qth')):
                record['MY_CITY'] = self.replaceUmlautsLigatures(query.value(self.__sql_cols__.index('own_qth')))
                record['MY_CITY_INTL'] = query.value(self.__sql_cols__.index('own_qth'))
            if query.value(self.__sql_cols__.index('own_locator')):
                record['MY_GRIDSQUARE'] = query.value(self.__sql_cols__.index('own_locator'))
            if query.value(self.__sql_cols__.index('radio')):
                record['MY_RIG'] = self.replaceUmlautsLigatures(query.value(self.__sql_cols__.index('radio')))
                record['MY_RIG_INTL'] = query.value(self.__sql_cols__.index('radio'))
            if query.value(self.__sql_cols__.index('antenna')):
                record['MY_ANTENNA'] = self.replaceUmlautsLigatures(query.value(self.__sql_cols__.index('antenna')))
                record['MY_ANTENNA_INTL'] = query.value(self.__sql_cols__.index('antenna'))
            if query.value(self.__sql_cols__.index('dist')):
                record['DISTANCE'] = query.value(self.__sql_cols__.index('dist'))
            if query.value(self.__sql_cols__.index('remarks')) and bool(self.settings.value('imp_exp/own_notes_adif', 0)):
                record['NOTES'] = self.replaceUmlautsLigatures(
                    query.value(self.__sql_cols__.index('remarks')).replace('\n', '\r\n'))
                record['NOTES_INTL'] = query.value(self.__sql_cols__.index('remarks')).replace('\n', '\r\n')
            if query.value(self.__sql_cols__.index('comments')):
                record['COMMENT'] = self.replaceUmlautsLigatures(
                    query.value(self.__sql_cols__.index('comments')).replace('\n', '\r\n'))
                record['COMMENT_INTL'] = query.value(self.__sql_cols__.index('comments')).replace('\n', '\r\n')
            if query.value(self.__sql_cols__.index('qsl_via')):
                record['QSL_VIA'] = query.value(self.__sql_cols__.index('qsl_via'))
            if query.value(self.__sql_cols__.index('qsl_path')):
                record['QSL_SENT_VIA'] = query.value(self.__sql_cols__.index('qsl_path'))
            if query.value(self.__sql_cols__.index('qsl_msg')):
                record['QSLMSG'] = self.replaceUmlautsLigatures(
                    query.value(self.__sql_cols__.index('qsl_msg')).replace('\n', '\r\n'))
                record['QSLMSG_INTL'] = query.value(self.__sql_cols__.index('qsl_msg')).replace('\n', '\r\n')
            if query.value(self.__sql_cols__.index('qsl_sent')):
                record['QSL_SENT'] = query.value(self.__sql_cols__.index('qsl_sent'))
            if query.value(self.__sql_cols__.index('qsl_rcvd')):
                record['QSL_RCVD'] = query.value(self.__sql_cols__.index('qsl_rcvd'))
            if query.value(self.__sql_cols__.index('eqsl_sent')):
                record['EQSL_QSL_SENT'] = query.value(self.__sql_cols__.index('eqsl_sent'))
            if query.value(self.__sql_cols__.index('eqsl_rcvd')):
                record['EQSL_QSL_RCVD'] = query.value(self.__sql_cols__.index('eqsl_rcvd'))
            if query.value(self.__sql_cols__.index('hamqth')):
                record['HAMQTH_QSO_UPLOAD_STATUS'] = query.value(self.__sql_cols__.index('hamqth'))

            if not record['APP']:
                record.pop('APP')

            records.append(record)

        doc['RECORDS'] = records
        if os.path.splitext(file)[-1] == '.adx':
            adx.dump(file, doc)
        else:
            adi.dump(file, doc, 'ADIF Export by DragonLog')

        print(f'Saved "{file}"')

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
        print('Importing from Excel...')

        xl_wb = openpyxl.load_workbook(file, read_only=True, data_only=True)
        xl_ws = xl_wb.active

        ln = 0
        for row in xl_ws.iter_rows():
            ln += 1
            if ln == 1:  # Skip header
                continue

            row = list(row)

            if len(row) >= len(self.__sql_cols__) and row[1].value:
                query = QtSql.QSqlQuery(self.__db_con__)
                query.prepare(self.__db_insert_stmnt__)

                for i, cell in enumerate(row[1:]):
                    query.bindValue(i, cell.value)
                query.exec()
                if query.lastError().text():
                    QtWidgets.QMessageBox.warning(
                        self,
                        self.tr('Log import Excel'),
                        f'Row {ln} import error ("{query.lastError().text()}").\nSkipped row.'
                    )
            else:
                QtWidgets.QMessageBox.warning(
                    self,
                    self.tr('Log import Excel'),
                    f'Row {ln} has too few columns.\nSkipped row.'
                )

        self.__db_con__.commit()
        self.QSOTableView.model().select()
        self.QSOTableView.resizeColumnsToContents()
        print(f'Imported {ln - 1} QSOs from "{file}"')

    def logImportCSV(self, file):
        print('Importing from CSV...')

        with open(file, newline='', encoding='utf-8') as cf:
            reader = csv.reader(cf)

            ln = 0
            for row in reader:
                ln += 1
                if ln == 1:  # Skip header
                    continue

                if len(row) >= len(self.__sql_cols__) and row[1]:
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
                    QtWidgets.QMessageBox.warning(
                        self,
                        self.tr('Log import CSV'),
                        f'Row {ln} has too few columns.\nSkipped row.'
                    )

        self.__db_con__.commit()
        self.QSOTableView.model().select()
        self.QSOTableView.resizeColumnsToContents()
        print(f'Imported {ln - 1} QSOs from "{file}"')

    def logImportADIF(self, file):
        print('Importing from ADIF...')

        is_adx: bool = os.path.splitext(file)[-1] == '.adx'

        if is_adx:
            records: list = adx.load(file)['RECORDS']
        else:
            records: list = adi.load(file)['RECORDS']

        imported = 0
        for i, r in enumerate(records, 1):
            if 'QSO_DATE' not in r or 'TIME_ON' not in r:
                QtWidgets.QMessageBox.warning(
                    self,
                    self.tr('Log import ADIF'),
                    f'QSO date/time missing in record {i}.\nSkipped record.'
                )
                continue

            query = QtSql.QSqlQuery(self.__db_con__)
            query.prepare(self.__db_insert_stmnt__)

            for j, val in enumerate(self._build_values_adiimport_(r)):
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
        self.QSOTableView.model().select()
        self.QSOTableView.resizeColumnsToContents()

        print(f'Imported {imported} QSOs from "{file}"')

    def _build_values_adiimport_(self, r, use_cfg_id=False, use_cfg_station=False):
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
                    if r[p] in self.modes['AFU'] or r[p] in self.modes['CB']:
                        values[self.__adx_cols__.index(p)] = r[p]
                    else:  # Workaround for wrong mode export from fldigi
                        # TODO: store in submode if Dragonlog supports submodes
                        for m in self.modes['AFU']:
                            if r[p] in self.modes['AFU'][m]:
                                values[self.__adx_cols__.index(p)] = m
                                break
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

            if 'QSO_DATE' not in rec or 'TIME_ON' not in rec or 'CALL' not  in rec:
                print(f'QSO date, time or call missing in record #{self.watchPos+1} from watched file. Skipped.')
                continue

            adi_time = rec['TIME_ON']
            adi_date = rec['QSO_DATE']
            time = f'{adi_time[:2]}:{adi_time[2:4]}' if len(
                adi_time) == 4 else f'{adi_time[:2]}:{adi_time[2:4]}:{adi_time[4:6]}'
            timestamp = f'{adi_date[:4]}-{adi_date[4:6]}-{adi_date[6:8]} {time}'

            if not self.findQSO(timestamp, rec['CALL']):
                print(f'Adding QSO #{i} from "{self.watchFileName}" to logbook...')

                query = QtSql.QSqlQuery(self.__db_con__)
                query.prepare(self.__db_insert_stmnt__)

                for j, val in enumerate(self._build_values_adiimport_(rec,
                                                                      bool(self.settings.value('imp_exp/use_id_watch', 0)),
                                                                      bool(self.settings.value('imp_exp/use_station_watch', 0)))):
                    query.bindValue(j, val)
                query.exec()
                if query.lastError().text():
                    print(f'Record #{self.watchPos+1} import error from watched file ("{query.lastError().text()}").'
                          'Skipped.')

                self.__db_con__.commit()
                added = True

        if added:
            self.QSOTableView.model().select()
            self.QSOTableView.resizeColumnsToContents()

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
        print(f'Quiting {__prog_name__}...')
        self.__db_con__.close()
        self.settings_form.ctrlRigctld(False)
        e.accept()


def main():
    app = QtWidgets.QApplication(sys.argv)
    app_path = os.path.dirname(__file__)

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
