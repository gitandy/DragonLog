import os
import csv
import string
import sys
import json
import math

from PyQt6 import QtCore, QtWidgets, QtGui, QtSql
import openpyxl
from openpyxl.styles import Font
import maidenhead

import DragonLog_MainWindow_ui
import DragonLog_QSOForm_ui
import DragonLog_Settings_ui

__prog_name__ = 'DragonLog'
__prog_desc__ = 'Log QSO for Ham radio'
__author_name__ = 'Andreas Schawo'
__author_email__ = 'andreas@schawo.de'
__copyright__ = 'Copyright (c) 2023, Andreas Schawo'

__version__ = 'v0.1'


class DatabaseOpenException(Exception):
    pass


class DatabaseWriteException(Exception):
    pass


class QSOForm(QtWidgets.QDialog, DragonLog_QSOForm_ui.Ui_QSOFormDialog):
    # TODO: Colour rows with AFU call differently

    def __init__(self, parent, bands: dict, modes: dict, settings: QtCore.QSettings):
        super().__init__(parent)
        self.setupUi(self)

        self.default_title = self.windowTitle()
        self.lastpos = None
        self.bands = bands
        self.modes = modes
        self.settings = settings

        self.modeComboBox.insertItems(0, modes['AFU'])
        self.bandComboBox.insertItems(0, bands.keys())

        self.stationChanged(True)
        self.identityChanged(True)

    def clear(self):
        self.callSignLineEdit.clear()
        self.nameLineEdit.clear()
        self.QTHLineEdit.clear()
        self.locatorLineEdit.clear()
        self.RSTSentLineEdit.setText('59')
        self.RSTRcvdLineEdit.setText('59')
        self.remarksTextEdit.clear()

        if self.bandComboBox.currentIndex() < 0:
            self.bandComboBox.setCurrentIndex(0)
        if self.modeComboBox.currentIndex() < 0:
            self.modeComboBox.setCurrentIndex(0)

    def reset(self):
        self.autoDateCheckBox.setEnabled(True)
        self.stationGroupBox.setCheckable(True)
        self.identityGroupBox.setCheckable(True)
        self.autoDateCheckBox.setChecked(True)
        self.stationGroupBox.setChecked(True)
        self.identityGroupBox.setChecked(True)

        self.setWindowTitle(self.default_title)

    def bandChanged(self, band: str):
        self.freqSpinBox.setValue(int((self.bands[band][0] + self.bands[band][1]) / 2))
        self.freqSpinBox.setMinimum(int(self.bands[band][0]))
        self.freqSpinBox.setMaximum(int(self.bands[band][1]))
        self.freqSpinBox.setSingleStep(self.bands[band][2])

        self.modeComboBox.clear()
        if band == '11 m':
            self.modeComboBox.insertItems(0, self.modes['CB'])
            self.powerSpinBox.setMaximum(12)

            if self.stationGroupBox.isChecked():
                self.radioLineEdit.setText(self.settings.value('station_cb/radio', ''))
                self.antennaLineEdit.setText(self.settings.value('station_cb/antenna', ''))

            if self.identityGroupBox.isChecked():
                self.ownCallSignLineEdit.setText(self.settings.value('station_cb/callSign', ''))
        else:
            self.modeComboBox.insertItems(0, self.modes['AFU'])
            self.powerSpinBox.setMaximum(1000)

            if self.stationGroupBox.isChecked():
                self.radioLineEdit.setText(self.settings.value('station/radio', ''))
                self.antennaLineEdit.setText(self.settings.value('station/antenna', ''))

            if self.identityGroupBox.isChecked():
                self.ownCallSignLineEdit.setText(self.settings.value('station/callSign', ''))

    def stationChanged(self, checked):
        if checked:
            self.ownQTHLineEdit.setText(self.settings.value('station/QTH', ''))
            self.ownLocatorLineEdit.setText(self.settings.value('station/locator', ''))

            if self.bandComboBox.currentText() == '11 m':
                self.radioLineEdit.setText(self.settings.value('station_cb/radio', ''))
                self.antennaLineEdit.setText(self.settings.value('station_cb/antenna', ''))
            else:
                self.radioLineEdit.setText(self.settings.value('station/radio', ''))
                self.antennaLineEdit.setText(self.settings.value('station/antenna', ''))

    def identityChanged(self, checked):
        if checked:
            self.ownNameLineEdit.setText(self.settings.value('station/name', ''))

            if self.bandComboBox.currentText() == '11 m':
                self.ownCallSignLineEdit.setText(self.settings.value('station_cb/callSign', ''))
            else:
                self.ownCallSignLineEdit.setText(self.settings.value('station/callSign', ''))

    def exec(self) -> int:
        if self.lastpos:
            self.move(self.lastpos)

        self.callSignLineEdit.setFocus()

        return super().exec()

    def hideEvent(self, e):
        self.lastpos = self.pos()
        e.accept()


class Settings(QtWidgets.QDialog, DragonLog_Settings_ui.Ui_Dialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setupUi(self)

    def calcLocator(self):
        self.locatorLineEdit.setText(maidenhead.to_maiden(self.latitudeDoubleSpinBox.value(),
                                                          self.longitudeDoubleSpinBox.value(),
                                                          4))


class DragonLog(QtWidgets.QMainWindow, DragonLog_MainWindow_ui.Ui_MainWindow):
    __sql_cols__ = ('id', 'date_time', 'own_callsign', 'call_sign', 'name', 'qth', 'locator', 'rst_sent', 'rst_rcvd',
                    'band', 'mode', 'freq', 'power', 'own_qth', 'own_locator', 'radio', 'antenna', 'remarks', 'dist')

    __db_create_stmnt__ = '''CREATE TABLE IF NOT EXISTS "qsos" (
                            "id"    INTEGER PRIMARY KEY NOT NULL,
                            "date_time"   NUMERIC,
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
                            "power"  REAL,
                            "own_qth"   TEXT,
                            "own_locator" TEXT,
                            "radio"   TEXT,
                            "antenna"   TEXT,
                            "remarks"   TEXT,
                            "dist" INTEGER
                        );'''

    __db_insert_stmnt__ = 'INSERT INTO qsos (' + ",".join(__sql_cols__[1:]) + ') ' \
                                                                              'VALUES (' + ",".join(
        ["?"] * (len(__sql_cols__) - 1)) + ')'
    __db_update_stmnt__ = 'UPDATE qsos SET ' + "=?,".join(__sql_cols__[1:]) + '=? ' \
                                                                              'WHERE id = ?'
    __db_select_stmnt__ = f'SELECT * FROM qsos'

    @staticmethod
    def calc_distance(mh_pos1: str, mh_pos2: str):
        if mh_pos1 and mh_pos2:
            pos1 = maidenhead.to_location(mh_pos1, True)
            pos2 = maidenhead.to_location(mh_pos2, True)

            mlat = math.radians(pos1[0])
            mlon = math.radians(pos1[1])
            plat = math.radians(pos2[0])
            plon = math.radians(pos2[1])

            return int(6371.01 * math.acos(
                math.sin(mlat) * math.sin(plat) + math.cos(mlat) * math.cos(plat) * math.cos(mlon - plon)))
        else:
            return 0

    def __init__(self, file=None, app_path='.'):
        super().__init__()

        print(f'Starting {__prog_name__}...')

        self.setupUi(self)

        self.app_path = app_path
        self.help_dialog = None

        self.settings = QtCore.QSettings(self.tr(__prog_name__))
        self.lastDatabase = None
        self.lastImportDir = None
        self.lastExportDir = None
        self.loadSettings()

        with open(os.path.join(app_path, 'bands.json')) as bj:
            self.bands: dict = json.load(bj)
        with open(os.path.join(app_path, 'modes.json')) as mj:
            self.modes: dict = json.load(mj)
        self.qso_form = QSOForm(self, self.bands, self.modes, self.settings)
        self.keep_logging = False

        self.settings_form = Settings(self)

        self.__headers__ = (
            self.tr('QSO'),
            self.tr('Date/Time'),
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
            self.tr('Power'),
            self.tr('Own QTH'),
            self.tr('Own Locator'),
            self.tr('Radio'),
            self.tr('Antenna'),
            self.tr('Remarks'),
            self.tr('Distance'),
        )

        self.__header_map__ = dict(zip(self.__sql_cols__, self.__headers__))

        self.__db_con__ = QtSql.QSqlDatabase.addDatabase('QSQLITE', 'main')

        if file:
            print(f'Opening database from commandline {file}...')
            self.connectDB(file)
        elif self.lastDatabase:
            print(f'Opening last database {self.lastDatabase}...')
            self.connectDB(self.lastDatabase)

    def loadSettings(self):
        self.lastDatabase = self.settings.value('lastDatabase', None)
        self.lastExportDir = self.settings.value('lastExportDir', os.path.abspath(os.curdir))
        self.lastImportDir = self.settings.value('lastImportDir', os.path.abspath(os.curdir))

    def storeSettings(self):
        if self.lastDatabase:
            self.settings.setValue('lastDatabase', os.path.abspath(self.lastDatabase))
        else:
            self.settings.setValue('lastDatabase', None)
        self.settings.setValue('lastExportDir', os.path.abspath(self.lastExportDir))
        self.settings.setValue('lastImportDir', os.path.abspath(self.lastImportDir))

    def showSettings(self):
        self.settings_form.callsignLineEdit.setText(self.settings.value('station/callSign', ''))
        self.settings_form.QTHLineEdit.setText(self.settings.value('station/QTH', ''))
        self.settings_form.locatorLineEdit.setText(self.settings.value('station/locator', ''))
        self.settings_form.radioLineEdit.setText(self.settings.value('station/radio', ''))
        self.settings_form.antennaLineEdit.setText(self.settings.value('station/antenna', ''))

        self.settings_form.callsignCBLineEdit.setText(self.settings.value('station_cb/callSign', ''))
        self.settings_form.radioCBLineEdit.setText(self.settings.value('station_cb/radio', ''))
        self.settings_form.antennaCBLineEdit.setText(self.settings.value('station_cb/antenna', ''))

        if self.settings_form.exec():
            self.settings.setValue('station/callSign', self.settings_form.callsignLineEdit.text())
            self.settings.setValue('station/QTH', self.settings_form.QTHLineEdit.text())
            self.settings.setValue('station/locator', self.settings_form.locatorLineEdit.text())
            self.settings.setValue('station/radio', self.settings_form.radioLineEdit.text())
            self.settings.setValue('station/antenna', self.settings_form.antennaLineEdit.text())

            self.settings.setValue('station_cb/callSign', self.settings_form.callsignCBLineEdit.text())
            self.settings.setValue('station_cb/radio', self.settings_form.radioCBLineEdit.text())
            self.settings.setValue('station_cb/antenna', self.settings_form.antennaCBLineEdit.text())

            print('Changed settings')
        else:
            print('Settings aborted')

    def selectDB(self):
        res = QtWidgets.QFileDialog.getSaveFileName(
            self,
            self.tr('Select file'),
            self.lastDatabase,
            self.tr('QSO-Log (*.qlog);;All Files (*.*)'),
            options=QtWidgets.QFileDialog.Option.DontConfirmOverwrite)

        if res[0]:
            print(f'Selected database {res[0]}')
            self.connectDB(res[0])

    def connectDB(self, db_file):
        try:
            if self.__db_con__.isOpen():
                self.__db_con__.close()

            self.__db_con__.setDatabaseName(db_file)
            if self.__db_con__.lastError().text():
                raise DatabaseOpenException(self.__db_con__.lastError().text())

            self.__db_con__.open()

            # TODO: Check table structure and warn/fix

            self.__db_con__.exec(self.__db_create_stmnt__)
            if self.__db_con__.lastError().text():
                raise DatabaseOpenException(self.__db_con__.lastError().text())

            model = QtSql.QSqlTableModel(self, self.__db_con__)
            model.setTable('qsos')

            for c in self.__sql_cols__:
                model.setHeaderData(self.__sql_cols__.index(c),
                                    QtCore.Qt.Orientation.Horizontal,
                                    self.__header_map__[c])

            self.QSOTableView.setModel(model)
            self.QSOTableView.hideColumn(self.__sql_cols__.index('freq'))
            self.QSOTableView.hideColumn(self.__sql_cols__.index('power'))
            self.QSOTableView.hideColumn(self.__sql_cols__.index('own_qth'))
            self.QSOTableView.hideColumn(self.__sql_cols__.index('own_locator'))
            self.QSOTableView.hideColumn(self.__sql_cols__.index('radio'))
            self.QSOTableView.hideColumn(self.__sql_cols__.index('antenna'))
            self.QSOTableView.hideColumn(self.__sql_cols__.index('remarks'))
            self.QSOTableView.sortByColumn(1, QtCore.Qt.SortOrder.AscendingOrder)
            self.QSOTableView.resizeColumnsToContents()

            print(f'Opened database {db_file}')
            self.lastDatabase = db_file
            self.setWindowTitle(__prog_name__ + ' - ' + db_file)
        except DatabaseOpenException as exc:
            if db_file == self.lastDatabase:
                self.lastDatabase = None
                self.storeSettings()

            QtWidgets.QMessageBox.critical(
                self,
                f'{__prog_name__} - {self.tr("Error")}',
                str(exc))

    def logQSO(self):
        self.qso_form.clear()
        if not self.keep_logging:
            self.qso_form.reset()

        dt = QtCore.QDateTime.currentDateTimeUtc()
        self.qso_form.dateEdit.setDate(dt.date())
        self.qso_form.timeEdit.setTime(dt.time())

        if self.qso_form.exec():
            print('Logging QSO...')

            if self.qso_form.autoDateCheckBox.isChecked():
                date_time = QtCore.QDateTime.currentDateTimeUtc().toString('yyyy-MM-dd HH:mm:ss')
            else:
                date_time = self.qso_form.dateEdit.text() + ' ' + self.qso_form.timeEdit.text()

            values = (
                date_time,
                self.qso_form.ownCallSignLineEdit.text(),
                self.qso_form.callSignLineEdit.text(),
                self.qso_form.nameLineEdit.text(),
                self.qso_form.QTHLineEdit.text(),
                self.qso_form.locatorLineEdit.text(),
                self.qso_form.RSTSentLineEdit.text(),
                self.qso_form.RSTRcvdLineEdit.text(),
                self.qso_form.bandComboBox.currentText(),
                self.qso_form.modeComboBox.currentText(),
                self.qso_form.freqSpinBox.value(),
                self.qso_form.powerSpinBox.value(),
                self.qso_form.ownQTHLineEdit.text(),
                self.qso_form.ownLocatorLineEdit.text(),
                self.qso_form.radioLineEdit.text(),
                self.qso_form.antennaLineEdit.text(),
                self.qso_form.remarksTextEdit.toPlainText().strip(),
                self.calc_distance(self.qso_form.locatorLineEdit.text(), self.qso_form.ownLocatorLineEdit.text())
            )

            query = QtSql.QSqlQuery(self.__db_con__)
            query.prepare(self.__db_insert_stmnt__)
            for i, val in enumerate(values):
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

                print(f'Deleting QSO "{qso_id}"...')
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

        for i in self.QSOTableView.selectedIndexes():
            qso_id = self.QSOTableView.model().data(i.siblingAtColumn(0))

            if qso_id in done_ids or qso_id is None:
                continue
            done_ids.append(qso_id)

            self.qso_form.autoDateCheckBox.setChecked(False)
            self.qso_form.stationGroupBox.setChecked(False)
            self.qso_form.identityGroupBox.setChecked(False)
            self.qso_form.autoDateCheckBox.setEnabled(False)
            self.qso_form.stationGroupBox.setCheckable(False)
            self.qso_form.identityGroupBox.setCheckable(False)

            date, time = self.QSOTableView.model().data(i.siblingAtColumn(self.__sql_cols__.index('date_time'))).split()
            self.qso_form.dateEdit.setDate(QtCore.QDate.fromString(date, 'yyyy-MM-dd'))
            self.qso_form.timeEdit.setTime(QtCore.QTime.fromString(time))
            self.qso_form.ownCallSignLineEdit.setText(self.QSOTableView.model().data(i.siblingAtColumn(
                self.__sql_cols__.index('own_callsign'))))
            self.qso_form.callSignLineEdit.setText(self.QSOTableView.model().data(i.siblingAtColumn(
                self.__sql_cols__.index('call_sign'))))
            self.qso_form.nameLineEdit.setText(self.QSOTableView.model().data(i.siblingAtColumn(
                self.__sql_cols__.index('name'))))
            self.qso_form.QTHLineEdit.setText(self.QSOTableView.model().data(i.siblingAtColumn(
                self.__sql_cols__.index('qth'))))
            self.qso_form.locatorLineEdit.setText(self.QSOTableView.model().data(i.siblingAtColumn(
                self.__sql_cols__.index('locator'))))
            self.qso_form.RSTSentLineEdit.setText(self.QSOTableView.model().data(i.siblingAtColumn(
                self.__sql_cols__.index('rst_sent'))))
            self.qso_form.RSTRcvdLineEdit.setText(self.QSOTableView.model().data(i.siblingAtColumn(
                self.__sql_cols__.index('rst_rcvd'))))
            self.qso_form.bandComboBox.setCurrentText(self.QSOTableView.model().data(i.siblingAtColumn(
                self.__sql_cols__.index('band'))))
            self.qso_form.modeComboBox.setCurrentText(self.QSOTableView.model().data(i.siblingAtColumn(
                self.__sql_cols__.index('mode'))))
            self.qso_form.freqSpinBox.setValue(int(self.QSOTableView.model().data(i.siblingAtColumn(
                self.__sql_cols__.index('freq')))))
            self.qso_form.powerSpinBox.setValue(int(self.QSOTableView.model().data(i.siblingAtColumn(
                self.__sql_cols__.index('power')))))
            self.qso_form.ownQTHLineEdit.setText(self.QSOTableView.model().data(i.siblingAtColumn(
                self.__sql_cols__.index('own_qth'))))
            self.qso_form.ownLocatorLineEdit.setText(self.QSOTableView.model().data(i.siblingAtColumn(
                self.__sql_cols__.index('own_locator'))))
            self.qso_form.radioLineEdit.setText(self.QSOTableView.model().data(i.siblingAtColumn(
                self.__sql_cols__.index('radio'))))
            self.qso_form.antennaLineEdit.setText(self.QSOTableView.model().data(i.siblingAtColumn(
                self.__sql_cols__.index('antenna'))))
            self.qso_form.remarksTextEdit.setText(self.QSOTableView.model().data(i.siblingAtColumn(
                self.__sql_cols__.index('remarks'))))

            self.qso_form.setWindowTitle(self.tr('Change QSO') + f' #{qso_id}')

            if self.qso_form.exec():
                print(f'Changing QSO {qso_id}...')

                values = (
                    self.qso_form.dateEdit.text() + ' ' + self.qso_form.timeEdit.text(),
                    self.qso_form.ownCallSignLineEdit.text(),
                    self.qso_form.callSignLineEdit.text(),
                    self.qso_form.nameLineEdit.text(),
                    self.qso_form.QTHLineEdit.text(),
                    self.qso_form.locatorLineEdit.text(),
                    self.qso_form.RSTSentLineEdit.text(),
                    self.qso_form.RSTRcvdLineEdit.text(),
                    self.qso_form.bandComboBox.currentText(),
                    self.qso_form.modeComboBox.currentText(),
                    self.qso_form.freqSpinBox.value(),
                    self.qso_form.powerSpinBox.value(),
                    self.qso_form.ownQTHLineEdit.text(),
                    self.qso_form.ownLocatorLineEdit.text(),
                    self.qso_form.radioLineEdit.text(),
                    self.qso_form.antennaLineEdit.text(),
                    self.qso_form.remarksTextEdit.toPlainText().strip(),
                    self.calc_distance(self.qso_form.locatorLineEdit.text(), self.qso_form.ownLocatorLineEdit.text()),
                    qso_id,
                )

                query = QtSql.QSqlQuery(self.__db_con__)
                query.prepare(self.__db_update_stmnt__)

                for col, val in enumerate(values):
                    query.bindValue(col, val)
                query.exec()
                if query.lastError().text():
                    raise Exception(query.lastError().text())

                self.__db_con__.commit()

                self.QSOTableView.model().select()
                self.QSOTableView.resizeColumnsToContents()
            else:
                print(f'Changing QSO(s) aborted')
                break

    def export(self):
        res = QtWidgets.QFileDialog.getSaveFileName(
            self,
            self.tr('Select export file'),
            self.lastExportDir,
            self.tr('Excel-File (*.xlsx);;CSV-File (*.csv);;ADIF 3.0 (*.adi)'))

        if res[0]:
            if res[1] == 'Excel-File (*.xlsx)':
                self.exportExcel(res[0])
            elif res[1] == 'CSV-File (*.csv)':
                self.exportCSV(res[0])
            elif res[1] == 'ADIF 3.0 (*.adi)':
                self.exportADI(res[0])

            self.lastExportDir = os.path.dirname(res[0])

    def exportCSV(self, file):
        print('Exporting to CSV...')

        with open(file, 'w', newline='') as cf:
            writer = csv.writer(cf, delimiter=';', dialect=csv.excel)

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

        # Write header
        column = 1
        for h in self.__headers__:
            cell = xl_ws.cell(column=column, row=1, value=h)
            cell.font = Font(bold=True)
            column += 1

        # Write content
        query = self.__db_con__.exec(self.__db_select_stmnt__)
        row = 2
        while query.next():
            for col in range(len(self.__headers__)):
                xl_ws.cell(column=col + 1, row=row, value=query.value(col))
            row += 1

        # Set auto filter
        xl_ws.auto_filter.ref = f'A1:{string.ascii_uppercase[len(self.__headers__) - 1]}1'

        # Fit size to content is not available so set fixed approximations
        col_widths = (10, 20, 15, 15, 25, 25, 15, 10, 10, 10, 10, 15, 10, 25, 15, 25, 25, 40, 10)
        for c, w in zip(string.ascii_uppercase[:len(col_widths)], col_widths):
            xl_ws.column_dimensions[c].width = w

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
    def _adif_tag_(ttype, content):
        if content:
            return f'<{ttype}:{len(str(content))}>{content} '

        return ''

    def exportADI(self, file):
        print('Exporting to ADI...')

        with open(file, 'w', newline='\n') as af:
            # Write header
            header = f'ADIF Export by DragonLog\n' \
                     f'<ADIF_VER:5>3.1.4 <PROGRAMID:{len(__prog_name__)}>{__prog_name__} ' \
                     f'<PROGRAMVERSION:{len(__version__)}>{__version__}\n' \
                     f'<eoh>\n\n'
            af.write(header)

            # Write content
            query = self.__db_con__.exec(self.__db_select_stmnt__)
            if query.lastError().text():
                raise Exception(query.lastError().text())

            while query.next():
                qso_date, qso_time = query.value(self.__sql_cols__.index('date_time')).split()

                af.write(self._adif_tag_('qso_date', qso_date.replace('-', '')))
                af.write(self._adif_tag_('time_on', qso_time.replace(':', '')[:4]))
                af.write(self._adif_tag_('call', query.value(self.__sql_cols__.index('call_sign'))))
                af.write(self._adif_tag_('name', query.value(self.__sql_cols__.index('name'))))
                af.write(self._adif_tag_('qth', query.value(self.__sql_cols__.index('qth'))))
                af.write(self._adif_tag_('gridsquare', query.value(self.__sql_cols__.index('locator'))))
                af.write('\n')  # Insert a linebreak for readability
                af.write(self._adif_tag_('rst_sent', query.value(self.__sql_cols__.index('rst_sent'))))
                af.write(self._adif_tag_('rst_rcvd', query.value(self.__sql_cols__.index('rst_rcvd'))))
                af.write(self._adif_tag_('band', query.value(self.__sql_cols__.index('band')).replace(' ', '').upper()))
                af.write(self._adif_tag_('mode', query.value(self.__sql_cols__.index('mode'))))
                af.write(self._adif_tag_('freq', f'{query.value(self.__sql_cols__.index("freq")) / 1000:0.3f}'))
                af.write(self._adif_tag_('tx_pwr', query.value(self.__sql_cols__.index('power'))))
                af.write('\n')  # Insert a linebreak for readability
                af.write(self._adif_tag_('station_callsign', query.value(self.__sql_cols__.index('own_callsign'))))
                af.write(self._adif_tag_('my_gridsquare', query.value(self.__sql_cols__.index('own_locator'))))
                af.write(self._adif_tag_('my_rig', query.value(self.__sql_cols__.index('radio'))))
                af.write(self._adif_tag_('my_antenna', query.value(self.__sql_cols__.index('antenna'))))
                af.write(self._adif_tag_('distance', query.value(self.__sql_cols__.index('dist'))))
                af.write('\n')  # Insert a linebreak for readability
                af.write(self._adif_tag_('notes',
                                         query.value(self.__sql_cols__.index('remarks')).replace('\n', '\r\n')))

                af.write('<eor>\n\n')  # Insert end of row

    # noinspection PyPep8Naming
    def showHelp(self):
        if not self.help_dialog:
            with open(os.path.join(self.app_path, 'README.md')) as hf:
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

    def showAbout(self):
        cr = sys.copyright.replace('\n\n', '\n')

        QtWidgets.QMessageBox.about(
            self,
            f'{__prog_name__} - {self.tr("About")}',
            f'{self.tr("Version")}: {__version__}\n' +
            f'{self.tr("Author")}: {__author_name__} <{__author_email__}>\n{__copyright__}' +
            f'\n\nPython {sys.version.split()[0]}: {cr}' +
            '\n\nIcons: Crystal Project, Copyright (c) 2006-2007 Everaldo Coelho' +
            '\nDragon icon by Icons8 https://icons8.com'
        )

    def showAboutQt(self):
        QtWidgets.QMessageBox.aboutQt(self, __prog_name__ + ' - ' + self.tr('About Qt'))

    def closeEvent(self, e):
        print(f'Quiting {__prog_name__}...')
        self.storeSettings()
        self.__db_con__.close()
        e.accept()


def main():
    app = QtWidgets.QApplication(sys.argv)
    translator = QtCore.QTranslator(app)
    translator.load(os.path.abspath(os.path.dirname(sys.argv[0])) + '/DragonLog_' + QtCore.QLocale.system().name())
    app.installTranslator(translator)

    file = None
    args = app.arguments()
    if len(args) > 1:
        file = args[1]
        if not (os.path.isfile(file) and os.path.splitext(file)[-1] in ('.qlog', '.sqlite')):
            file = None

    app_path = os.path.dirname(args[0])

    QtCore.QDir.addSearchPath('icons', app_path + '/icons')

    dl = DragonLog(file, app_path)
    dl.show()

    sys.exit(app.exec())


# Get old behaviour on printing a traceback on exceptions
def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)


if __name__ == '__main__':
    sys.excepthook = except_hook

    main()
