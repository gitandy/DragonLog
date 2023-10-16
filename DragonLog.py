import os
import csv
import sys
import json
import math
import string
import socket
import datetime
import subprocess
from xml.etree.ElementTree import ElementTree

from PyQt6 import QtCore, QtWidgets, QtSql
import openpyxl
from openpyxl.styles import Font
import maidenhead
import xmlschema

import DragonLog_MainWindow_ui
import DragonLog_QSOForm_ui
import DragonLog_Settings_ui

__prog_name__ = 'DragonLog'
__prog_desc__ = 'Log QSO for Ham radio'
__author_name__ = 'Andreas Schawo'
__author_email__ = 'andreas@schawo.de'
__copyright__ = 'Copyright 2023 by Andreas Schawo,licensed under CC BY-SA 4.0'

import __version__ as version

__version__ = version.__version__
if version.__branch__:
    __version__ += '-' + version.__branch__
if version.__unclean__:
    __version__ += '-unclean'


class DatabaseOpenException(Exception):
    pass


class DatabaseWriteException(Exception):
    pass


class Settings(QtWidgets.QDialog, DragonLog_Settings_ui.Ui_Dialog):
    def __init__(self, parent, settings: QtCore.QSettings, rig_status: QtWidgets.QLabel):
        super().__init__(parent)
        self.setupUi(self)

        self.settings = settings
        self.rig_ids = None
        self.rigs = None
        self.rigctld_path = None
        self.rigctld = None
        self.rig_caps = []
        self.rig_status = rig_status

        if self.settings.value('cat/lasthamlibdir', None):
            self.init_hamlib(self.settings.value('cat/lasthamlibdir', None))

        self.checkHamlibTimer = QtCore.QTimer(self)
        self.checkHamlibTimer.timeout.connect(self.checkRigctld)

    def calcLocator(self):
        self.locatorLineEdit.setText(maidenhead.to_maiden(self.latitudeDoubleSpinBox.value(),
                                                          self.longitudeDoubleSpinBox.value(),
                                                          4))

    def checkRigctld(self):
        if self.rigctld and self.rigctld.poll():
            print('rigctld died unexpectedly')
            self.ctrlRigctldPushButton.setText(self.tr('Start'))
            self.rig_caps = []
            self.checkHamlibTimer.stop()
            self.rig_status.setText(self.tr('Hamlib') + ': ' + self.tr('inactiv'))

    def isRigctldActive(self):
        return self.ctrlRigctldPushButton.isChecked()

    @staticmethod
    def __is_exe__(path):
        return os.path.isfile(path) and os.access(path, os.X_OK)

    def chooseHamlibPath(self):
        hl_dir = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            self.tr('Choose hamlib directory'),
            self.settings.value('cat/lasthamlibdir', None)
        )

        self.init_hamlib(hl_dir)

    def init_hamlib(self, hl_dir):
        if hl_dir:
            rigctld_path = os.path.join(hl_dir, 'bin/rigctld.exe')
            if self.__is_exe__(rigctld_path):
                res = subprocess.run([rigctld_path, '-l'], capture_output=True)
                stdout = str(res.stdout, sys.getdefaultencoding()).replace('\r', '')
                if res.returncode != 0 or not stdout:
                    self.checkHamlibLabel.setText(self.tr('Error executing rigctld'))
                    self.settings.setValue('cat/lasthamlibdir', '')
                    self.hamlibPathLineEdit.setText('')

                first = True
                rig_pos = 0
                mfr_pos = 0
                model_pos = 0
                end_pos = 0
                self.rigs = {}
                self.rig_ids = {}
                for rig in stdout.split('\n'):
                    if first:
                        first = False
                        rig_pos = rig.index('Rig #')
                        mfr_pos = rig.index('Mfg')
                        model_pos = rig.index('Model')
                        end_pos = rig.index('Version')
                        continue
                    elif not rig.strip():  # Empty line
                        continue

                    rig_id = rig[rig_pos:mfr_pos - 1].strip()
                    mfr_name = rig[mfr_pos:model_pos - 1].strip()
                    model_name = rig[model_pos:end_pos - 1].strip()

                    self.rig_ids[f'{mfr_name}/{model_name}'] = rig_id
                    if mfr_name in self.rigs:
                        self.rigs[mfr_name].append(model_name)
                    else:
                        self.rigs[mfr_name] = [model_name]

                self.manufacturerComboBox.clear()
                self.manufacturerComboBox.insertItems(0, self.rigs.keys())
                if self.settings.value('cat/rigMfr', None):
                    self.manufacturerComboBox.setCurrentText(self.settings.value('cat/rigMfr'))
                else:
                    self.manufacturerComboBox.setCurrentIndex(0)

                self.settings.setValue('cat/lasthamlibdir', hl_dir)
                self.hamlibPathLineEdit.setText(hl_dir)
                self.checkHamlibLabel.setText('')
                self.rigctld_path = rigctld_path
            else:
                self.checkHamlibLabel.setText(self.tr('Directory does not contain the hamlib executable'))
                self.settings.setValue('cat/lasthamlibdir', '')
                self.hamlibPathLineEdit.setText('')

    def mfrChanged(self, mfr):
        self.modelComboBox.clear()
        self.modelComboBox.insertItems(0, self.rigs[mfr])

        if self.settings.value('cat/rigModel', None):
            self.modelComboBox.setCurrentText(self.settings.value('cat/rigModel'))

    def collectRigCaps(self, rig_id):
        res = subprocess.run([self.rigctld_path, f'--model={rig_id}', '-u'], capture_output=True)
        stdout = str(res.stdout, sys.getdefaultencoding()).replace('\r', '')
        self.rig_caps = []
        for ln in stdout.split('\n'):
            if ln.startswith('Can '):
                cap, able = ln.split(':')
                if able.strip() == 'Y':
                    self.rig_caps.append(cap[4:])

    def ctrlRigctld(self, start):
        if start:
            rig_id = self.rig_ids[self.manufacturerComboBox.currentText() + '/' + self.modelComboBox.currentText()]

            self.collectRigCaps(rig_id)

            self.rigctld = subprocess.Popen([self.rigctld_path,
                                             f'--model={rig_id}',
                                             f'--rig-file={self.catInterfaceLineEdit.text().strip()}',
                                             f'--serial-speed={self.catBaudComboBox.currentText()}',
                                             '--listen-addr=127.0.0.1'])
            if self.rigctld.poll():
                self.checkHamlibRunLabel.setText(self.tr('rigctld did not start properly'))
                self.ctrlRigctldPushButton.setChecked(False)
                self.rig_status.setText(self.tr('Hamlib') + ': ' + self.tr('inactiv'))
            else:
                self.checkHamlibRunLabel.setText('')
                self.ctrlRigctldPushButton.setText(self.tr('Stop'))
                print(f'rigctld is running with pid #{self.rigctld.pid} and arguments {self.rigctld.args}')
                self.checkHamlibTimer.start(1000)
                self.rig_status.setText(self.tr('Hamlib') + ': ' + self.tr('activ'))
        else:
            self.checkHamlibTimer.stop()
            if not self.rigctld.poll():
                os.kill(self.rigctld.pid, 9)
                print('Killed rigctld')
            self.ctrlRigctldPushButton.setText(self.tr('Start'))
            self.rig_status.setText(self.tr('Hamlib') + ': ' + self.tr('inactiv'))
            self.rig_caps = []

    def exec(self):
        # TODO: Load other settings here too
        print('Loading settings...')
        self.catInterfaceLineEdit.setText(self.settings.value('cat/interface', ''))
        self.catBaudComboBox.setCurrentText(self.settings.value('cat/baud', ''))
        return super().exec()

    def accept(self):
        # TODO: Store other settings here too
        print('Saving Settings...')
        self.settings.setValue('cat/interface', self.catInterfaceLineEdit.text())
        self.settings.setValue('cat/baud', self.catBaudComboBox.currentText())
        self.settings.setValue('cat/rigMfr', self.manufacturerComboBox.currentText())
        self.settings.setValue('cat/rigModel', self.modelComboBox.currentText())
        super().accept()


class QSOForm(QtWidgets.QDialog, DragonLog_QSOForm_ui.Ui_QSOFormDialog):
    # TODO: Colour rows with AFU call differently

    def __init__(self, parent, bands: dict, modes: dict, settings: QtCore.QSettings, settings_form: Settings,
                 cb_channels: dict):
        super().__init__(parent)
        self.setupUi(self)

        self.default_title = self.windowTitle()
        self.lastpos = None
        self.bands = bands
        self.modes = modes
        self.settings = settings
        self.settings_form = settings_form

        self.cb_channels = cb_channels
        self.channelComboBox.insertItems(0, ['-'] + list(cb_channels.keys()))

        self.bandComboBox.insertItems(0, bands.keys())

        self.stationChanged(True)
        self.identityChanged(True)

        self.rig_modes = {'USB': 'SSB',
                          'LSB': 'SSB',
                          'CW': 'CW',
                          'CWR': 'CW',
                          'RTTY': 'RTTY',
                          'RTTYR': 'RTTY',
                          'AM': 'AM',
                          'FM': 'FM',
                          'WFM': 'FM',
                          }

        self.refreshTimer = QtCore.QTimer(self)
        self.refreshTimer.timeout.connect(self.refreshRigData)

    # noinspection PyBroadException
    def refreshRigData(self):
        if self.settings_form.isRigctldActive():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(('127.0.0.1', 4532))

                s.sendall(b'\\get_freq\n')
                freq_s = s.recv(1024).decode('utf-8')
                try:
                    freq = float(freq_s) / 1000
                    for b in self.bands:
                        if freq < self.bands[b][1]:
                            if freq > self.bands[b][0]:
                                self.bandComboBox.setCurrentText(b)
                                self.freqDoubleSpinBox.setValue(freq)
                            break
                except Exception:
                    pass

                s.sendall(b'\\get_mode\n')
                mode_s = s.recv(1024).decode('utf-8').strip()
                try:
                    mode, passband = [v.strip() for v in mode_s.split('\n')]
                    if mode in self.rig_modes:
                        self.modeComboBox.setCurrentText(self.rig_modes[mode])
                except Exception:
                    pass

                if 'get power2mW' in self.settings_form.rig_caps:
                    s.sendall(b'\\power2mW\n')
                    pwr_s = s.recv(1024).decode('utf-8')
                    try:
                        pwr = int(float(pwr_s)*1000+.9)
                        self.powerSpinBox.setValue(pwr)
                    except Exception:
                        pass
                else:
                    self.powerSpinBox.setValue(0)
        else:
            self.refreshTimer.stop()

    def clear(self):
        self.callSignLineEdit.clear()
        self.nameLineEdit.clear()
        self.QTHLineEdit.clear()
        self.locatorLineEdit.clear()
        self.RSTSentLineEdit.setText('59')
        self.RSTRcvdLineEdit.setText('59')
        self.remarksTextEdit.clear()
        self.powerSpinBox.setValue(0)

        if bool(self.settings.value('station_cb/cb_by_default', 0)):
            self.bandComboBox.setCurrentText('11m')

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
        self.freqDoubleSpinBox.setMinimum(self.bands[band][0] - self.bands[band][2])
        self.freqDoubleSpinBox.setValue(self.bands[band][0] - self.bands[band][2])
        self.freqDoubleSpinBox.setMaximum(self.bands[band][1])
        self.freqDoubleSpinBox.setSingleStep(self.bands[band][2])

        self.modeComboBox.clear()
        if band == '11m':
            self.powerSpinBox.setMaximum(12)
            self.channelComboBox.setVisible(True)
            self.channelLabel.setVisible(True)
            self.freqDoubleSpinBox.setEnabled(False)
            self.channelComboBox.setCurrentIndex(-1)
            self.channelComboBox.setCurrentIndex(0)

            if self.stationGroupBox.isChecked():
                self.radioLineEdit.setText(self.settings.value('station_cb/radio', ''))
                self.antennaLineEdit.setText(self.settings.value('station_cb/antenna', ''))

            if self.identityGroupBox.isChecked():
                self.ownCallSignLineEdit.setText(self.settings.value('station_cb/callSign', ''))
        else:
            self.modeComboBox.insertItems(0, self.modes['AFU'].keys())
            self.modeComboBox.setCurrentIndex(0)
            self.powerSpinBox.setMaximum(1000)
            self.channelComboBox.setVisible(False)
            self.channelLabel.setVisible(False)
            self.freqDoubleSpinBox.setEnabled(True)

            if self.stationGroupBox.isChecked():
                self.radioLineEdit.setText(self.settings.value('station/radio', ''))
                self.antennaLineEdit.setText(self.settings.value('station/antenna', ''))

            if self.identityGroupBox.isChecked():
                self.ownCallSignLineEdit.setText(self.settings.value('station/callSign', ''))

    def stationChanged(self, checked):
        if checked:
            self.ownQTHLineEdit.setText(self.settings.value('station/QTH', ''))
            self.ownLocatorLineEdit.setText(self.settings.value('station/locator', ''))

            if self.bandComboBox.currentText() == '11m':
                self.radioLineEdit.setText(self.settings.value('station_cb/radio', ''))
                self.antennaLineEdit.setText(self.settings.value('station_cb/antenna', ''))
            else:
                self.radioLineEdit.setText(self.settings.value('station/radio', ''))
                self.antennaLineEdit.setText(self.settings.value('station/antenna', ''))

    def identityChanged(self, checked):
        if checked:
            self.ownNameLineEdit.setText(self.settings.value('station/name', ''))

            if self.bandComboBox.currentText() == '11m':
                self.ownCallSignLineEdit.setText(self.settings.value('station_cb/callSign', ''))
            else:
                self.ownCallSignLineEdit.setText(self.settings.value('station/callSign', ''))

    def channelChanged(self, ch):
        if ch and ch != '-':
            self.freqDoubleSpinBox.setValue(self.cb_channels[ch]['freq'])
            self.modeComboBox.clear()
            self.modeComboBox.insertItems(0, self.cb_channels[ch]['modes'])
            self.modeComboBox.setCurrentIndex(0)
        else:
            self.freqDoubleSpinBox.setValue(self.bands['11m'][0] - self.bands['11m'][2])

    def exec(self) -> int:
        if self.lastpos:
            self.move(self.lastpos)

        self.callSignLineEdit.setFocus()

        if self.settings_form.isRigctldActive():
            self.refreshTimer.start(500)

        return super().exec()

    def hideEvent(self, e):
        self.lastpos = self.pos()
        self.refreshTimer.stop()
        e.accept()


class DragonLog(QtWidgets.QMainWindow, DragonLog_MainWindow_ui.Ui_MainWindow):
    __sql_cols__ = ('id', 'date_time', 'own_callsign', 'call_sign', 'name', 'qth', 'locator', 'rst_sent', 'rst_rcvd',
                    'band', 'mode', 'freq', 'channel', 'power', 'own_qth', 'own_locator', 'radio', 'antenna', 'remarks',
                    'dist')

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
                            "channel"  INTEGER,
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
        self.hamlib_status = QtWidgets.QLabel(self.tr('Hamlib') + ': ' + self.tr('inactiv'))
        self.statusBar().addPermanentWidget(self.hamlib_status)

        with open(self.searchFile('data:bands.json')) as bj:
            self.bands: dict = json.load(bj)
        with open(self.searchFile('data:modes.json')) as mj:
            self.modes: dict = json.load(mj)
        with open(self.searchFile('data:cb_channels.json')) as cj:
            self.cb_channels: dict = json.load(cj)

        self.settings_form = Settings(self, self.settings, self.hamlib_status)

        self.qso_form = QSOForm(self, self.bands, self.modes, self.settings, self.settings_form, self.cb_channels)
        self.keep_logging = False

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
            self.tr('Channel'),
            self.tr('Power'),
            self.tr('Own QTH'),
            self.tr('Own Locator'),
            self.tr('Radio'),
            self.tr('Antenna'),
            self.tr('Remarks'),
            self.tr('Distance'),
        )

        self.__header_map__ = dict(zip(self.__sql_cols__, self.__headers__))

        self.adx_export_schema = xmlschema.XMLSchema(self.searchFile('data:adif/adx314.xsd'))
        self.adx_import_schema = xmlschema.XMLSchema(self.searchFile('data:adif/adx314generic.xsd'))

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

    def showSettings(self):
        self.settings_form.callsignLineEdit.setText(self.settings.value('station/callSign', ''))
        self.settings_form.QTHLineEdit.setText(self.settings.value('station/QTH', ''))
        self.settings_form.locatorLineEdit.setText(self.settings.value('station/locator', ''))
        self.settings_form.radioLineEdit.setText(self.settings.value('station/radio', ''))
        self.settings_form.antennaLineEdit.setText(self.settings.value('station/antenna', ''))

        self.settings_form.callsignCBLineEdit.setText(self.settings.value('station_cb/callSign', ''))
        self.settings_form.radioCBLineEdit.setText(self.settings.value('station_cb/radio', ''))
        self.settings_form.antennaCBLineEdit.setText(self.settings.value('station_cb/antenna', ''))
        self.settings_form.cbDefaultCheckBox.setChecked(bool(self.settings.value('station_cb/cb_by_default', 0)))

        if self.settings_form.exec():
            self.settings.setValue('station/callSign', self.settings_form.callsignLineEdit.text())
            self.settings.setValue('station/QTH', self.settings_form.QTHLineEdit.text())
            self.settings.setValue('station/locator', self.settings_form.locatorLineEdit.text())
            self.settings.setValue('station/radio', self.settings_form.radioLineEdit.text())
            self.settings.setValue('station/antenna', self.settings_form.antennaLineEdit.text())

            self.settings.setValue('station_cb/callSign', self.settings_form.callsignCBLineEdit.text())
            self.settings.setValue('station_cb/radio', self.settings_form.radioCBLineEdit.text())
            self.settings.setValue('station_cb/antenna', self.settings_form.antennaCBLineEdit.text())
            self.settings.setValue('station_cb/cb_by_default', int(self.settings_form.cbDefaultCheckBox.isChecked()))

            print('Changed settings')
        else:
            print('Settings aborted')

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
            os.rename(db_file, bck_name)

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
            if self.__db_con__.lastError().text():
                raise DatabaseOpenException(self.__db_con__.lastError().text())

            self.checkDB(db_file)

            model = QtSql.QSqlTableModel(self, self.__db_con__)
            model.setTable('qsos')

            for c in self.__sql_cols__:
                model.setHeaderData(self.__sql_cols__.index(c),
                                    QtCore.Qt.Orientation.Horizontal,
                                    self.__header_map__[c])

            self.QSOTableView.setModel(model)
            self.QSOTableView.hideColumn(self.__sql_cols__.index('own_qth'))
            self.QSOTableView.hideColumn(self.__sql_cols__.index('own_locator'))
            self.QSOTableView.hideColumn(self.__sql_cols__.index('radio'))
            self.QSOTableView.hideColumn(self.__sql_cols__.index('antenna'))
            self.QSOTableView.hideColumn(self.__sql_cols__.index('remarks'))
            self.QSOTableView.sortByColumn(1, QtCore.Qt.SortOrder.AscendingOrder)
            self.QSOTableView.resizeColumnsToContents()

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

            band = self.qso_form.bandComboBox.currentText()

            values = (
                date_time,
                self.qso_form.ownCallSignLineEdit.text(),
                self.qso_form.callSignLineEdit.text(),
                self.qso_form.nameLineEdit.text(),
                self.qso_form.QTHLineEdit.text(),
                self.qso_form.locatorLineEdit.text(),
                self.qso_form.RSTSentLineEdit.text(),
                self.qso_form.RSTRcvdLineEdit.text(),
                band,
                self.qso_form.modeComboBox.currentText(),
                self.qso_form.freqDoubleSpinBox.value() if self.qso_form.freqDoubleSpinBox.value() >= self.bands[band][
                    0] else '',
                self.qso_form.channelComboBox.currentText() if band == '11m' else '-',
                self.qso_form.powerSpinBox.value() if self.qso_form.powerSpinBox.value() > 0 else '',
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

            band = self.QSOTableView.model().data(i.siblingAtColumn(self.__sql_cols__.index('band')))
            self.qso_form.bandComboBox.setCurrentText(band)

            self.qso_form.modeComboBox.setCurrentText(self.QSOTableView.model().data(i.siblingAtColumn(
                self.__sql_cols__.index('mode'))))

            try:
                freq = float(self.QSOTableView.model().data(i.siblingAtColumn(self.__sql_cols__.index('freq'))))
            except ValueError:
                freq = self.bands[band][0] - self.bands[band][2]
            self.qso_form.freqDoubleSpinBox.setValue(freq)

            if band == '11m':
                self.qso_form.channelComboBox.setCurrentIndex(-1)
                channel = self.QSOTableView.model().data(i.siblingAtColumn(self.__sql_cols__.index('channel')))
                self.qso_form.channelComboBox.setCurrentText(str(channel) if channel else '-')
            else:
                self.qso_form.channelComboBox.setCurrentIndex(-1)

            try:
                power = int(self.QSOTableView.model().data(i.siblingAtColumn(
                    self.__sql_cols__.index('power'))))
            except ValueError:
                power = 0
            self.qso_form.powerSpinBox.setValue(power)
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

                band = self.qso_form.bandComboBox.currentText()

                values = (
                    self.qso_form.dateEdit.text() + ' ' + self.qso_form.timeEdit.text(),
                    self.qso_form.ownCallSignLineEdit.text(),
                    self.qso_form.callSignLineEdit.text(),
                    self.qso_form.nameLineEdit.text(),
                    self.qso_form.QTHLineEdit.text(),
                    self.qso_form.locatorLineEdit.text(),
                    self.qso_form.RSTSentLineEdit.text(),
                    self.qso_form.RSTRcvdLineEdit.text(),
                    band,
                    self.qso_form.modeComboBox.currentText(),
                    self.qso_form.freqDoubleSpinBox.value() if self.qso_form.freqDoubleSpinBox.value() >=
                                                               self.bands[band][0] else '',
                    self.qso_form.channelComboBox.currentText() if band == '11m' else '-',
                    self.qso_form.powerSpinBox.value() if self.qso_form.powerSpinBox.value() > 0 else '',
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
            else:
                print(f'Changing QSO(s) aborted')
                break

        self.__db_con__.commit()
        self.QSOTableView.model().select()
        self.QSOTableView.resizeColumnsToContents()

    def export(self):
        res = QtWidgets.QFileDialog.getSaveFileName(
            self,
            self.tr('Select export file'),
            self.settings.value('lastExportDir', os.path.abspath(os.curdir)),
            self.tr('Excel-File (*.xlsx)') + ';;' +
            self.tr('CSV-File (*.csv)') + ';;' +
            self.tr('ADIF 3 (*.adi *.adx)'))

        if res[0]:
            if res[1] == self.tr('Excel-File (*.xlsx)'):
                self.exportExcel(res[0])
            elif res[1] == self.tr('CSV-File (*.csv)'):
                self.exportCSV(res[0])
            elif res[1] == self.tr('ADIF 3 (*.adi *.adx)'):
                if os.path.splitext(res[0])[-1] == '.adx':
                    self.exportADX(res[0])
                else:
                    self.exportADI(res[0])

            self.settings.setValue('lastExportDir', os.path.abspath(os.path.dirname(res[0])))

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
            return f'<{ttype.upper()}:{len(str(content))}>{content} '

        return ''

    def exportADI(self, file):
        print('Exporting to ADI...')

        with open(file, 'w', newline='\n') as af:
            # Write header
            header = 'ADIF Export by DragonLog\n' + \
                     self._adif_tag_('ADIF_VER', '3.1.4') + \
                     self._adif_tag_('PROGRAMID', __prog_name__) + \
                     self._adif_tag_('PROGRAMVERSION', __version__) + \
                     '\n<eoh>\n\n'

            af.write(header)

            # Write content
            query = self.__db_con__.exec(self.__db_select_stmnt__)
            if query.lastError().text():
                raise Exception(query.lastError().text())

            while query.next():
                band = query.value(self.__sql_cols__.index('band'))

                if band == '11m':
                    continue

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
                af.write(self._adif_tag_('band', band.upper()))
                af.write(self._adif_tag_('mode', query.value(self.__sql_cols__.index('mode'))))
                freq = query.value(self.__sql_cols__.index("freq"))
                af.write(self._adif_tag_('freq', f'{freq / 1000:0.3f}' if freq else ''))
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

    def exportADX(self, file):
        print('Exporting to ADX...')

        doc = {
            'HEADER':
                {
                    'ADIF_VER': '3.1.4',
                    'PROGRAMID': __prog_name__,
                    'PROGRAMVERSION': __version__
                },
            'RECORDS': {'RECORD': []},
        }

        query = self.__db_con__.exec(self.__db_select_stmnt__)
        if query.lastError().text():
            raise Exception(query.lastError().text())

        while query.next():
            band = query.value(self.__sql_cols__.index('band'))

            if band == '11m':
                continue

            qso_date, qso_time = query.value(self.__sql_cols__.index('date_time')).split()

            record = {'QSO_DATE': qso_date.replace('-', ''),
                      'TIME_ON': qso_time.replace(':', '')[:4]}

            if query.value(self.__sql_cols__.index('call_sign')):
                record['CALL'] = query.value(self.__sql_cols__.index('call_sign'))
            if query.value(self.__sql_cols__.index('name')):
                record['NAME'] = query.value(self.__sql_cols__.index('name'))
            if query.value(self.__sql_cols__.index('qth')):
                record['QTH'] = query.value(self.__sql_cols__.index('qth'))
            if query.value(self.__sql_cols__.index('locator')):
                record['GRIDSQUARE'] = query.value(self.__sql_cols__.index('locator'))
            if query.value(self.__sql_cols__.index('rst_sent')):
                record['RST_SENT'] = query.value(self.__sql_cols__.index('rst_sent'))
            if query.value(self.__sql_cols__.index('rst_rcvd')):
                record['RST_RCVD'] = query.value(self.__sql_cols__.index('rst_rcvd'))
            if band:
                record['BAND'] = band.upper()
            if query.value(self.__sql_cols__.index('mode')):
                record['MODE'] = query.value(self.__sql_cols__.index('mode'))
            if query.value(self.__sql_cols__.index("freq")):
                record['FREQ'] = f'{query.value(self.__sql_cols__.index("freq")) / 1000:0.3f}'
            if query.value(self.__sql_cols__.index('power')):
                record['TX_PWR'] = query.value(self.__sql_cols__.index('power'))
            if query.value(self.__sql_cols__.index('own_callsign')):
                record['STATION_CALLSIGN'] = query.value(self.__sql_cols__.index('own_callsign'))
            if query.value(self.__sql_cols__.index('own_locator')):
                record['MY_GRIDSQUARE'] = query.value(self.__sql_cols__.index('own_locator'))
            if query.value(self.__sql_cols__.index('radio')):
                record['MY_RIG'] = query.value(self.__sql_cols__.index('radio'))
            if query.value(self.__sql_cols__.index('antenna')):
                record['MY_ANTENNA'] = query.value(self.__sql_cols__.index('antenna'))
            if query.value(self.__sql_cols__.index('dist')):
                record['DISTANCE'] = query.value(self.__sql_cols__.index('dist'))
            if query.value(self.__sql_cols__.index('remarks')):
                record['NOTES'] = query.value(self.__sql_cols__.index('remarks')).replace('\n', '\r\n')

            doc['RECORDS']['RECORD'].append(record)

        ElementTree(self.adx_export_schema.encode(doc)).write(file, xml_declaration=True, encoding='utf-8')

    def logImport(self):
        res = QtWidgets.QFileDialog.getOpenFileName(
            self,
            self.tr('Select import file'),
            self.settings.value('lastImportDir', os.path.abspath(os.curdir)),
            # self.tr('Excel-File (*.xlsx)') + ';;' +
            self.tr('CSV-File (*.csv)')  # + ';;' +
            # self.tr('ADIF 3 (*.adi)')
        )

        if res[0]:
            if res[1] == self.tr('Excel-File (*.xlsx)'):
                self.logImportExcel(res[0])
            elif res[1] == self.tr('CSV-File (*.csv)'):
                self.logImportCSV(res[0])
            elif res[1] == self.tr('ADIF 3.0 (*.adi)'):
                self.logImportADI(res[0])

            self.settings.setValue('lastImportDir', os.path.dirname(res[0]))

    def logImportCSV(self, file):
        print('Importing from CSV...')

        with open(file, newline='', encoding='utf-8') as cf:
            reader = csv.reader(cf, delimiter=';', dialect=csv.excel)

            ln = 0
            for row in reader:
                ln += 1
                if ln == 1:
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

    def showAbout(self):
        cr = sys.copyright.replace('\n\n', '\n')

        QtWidgets.QMessageBox.about(
            self,
            f'{__prog_name__} - {self.tr("About")}',
            f'{self.tr("Version")}: {__version__}\n'
            f'{self.tr("Author")}: {__author_name__} <{__author_email__}>\n{__copyright__}'
            f'\n\nPython {sys.version.split()[0]}: {cr}'
            f'\n\nOpenPyXL {openpyxl.__version__}: Copyright (c) 2010 openpyxl'
            '\nmaidenhead: Copyright (c) 2018 Michael Hirsch, Ph.D.' +
            f'\nxmlschema {xmlschema.__version__}: Copyright (c), 2016-2022, '
            f'SISSA (Scuola Internazionale Superiore di Studi Avanzati)'
            '\n\nIcons: Crystal Project, Copyright (c) 2006-2007 Everaldo Coelho'
            '\nDragon icon by Icons8 https://icons8.com'
        )

    def showAboutQt(self):
        QtWidgets.QMessageBox.aboutQt(self, __prog_name__ + ' - ' + self.tr('About Qt'))

    def closeEvent(self, e):
        print(f'Quiting {__prog_name__}...')
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
    QtCore.QDir.addSearchPath('data', app_path + '/data')

    dl = DragonLog(file, app_path)
    dl.show()

    sys.exit(app.exec())


# Get old behaviour on printing a traceback on exceptions
def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)


if __name__ == '__main__':
    sys.excepthook = except_hook

    main()
