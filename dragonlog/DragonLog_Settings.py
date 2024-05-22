import os
import sys
import typing
import logging
import platform
import subprocess

import maidenhead
from PyQt6 import QtWidgets, QtCore, QtGui
import keyring

from . import DragonLog_Settings_ui
from .Logger import Logger
from .RegEx import REGEX_CALL, REGEX_LOCATOR, check_format
from .CallBook import CallBookType
from .ListEdit import ListEdit

# Fix problems with importing win32 in frozen executable
if getattr(sys, 'frozen', False):
    # noinspection PyUnresolvedReferences
    import win32timezone
    from keyring.backends import Windows

    keyring.set_keyring(Windows.WinVaultKeyring())


class Settings(QtWidgets.QDialog, DragonLog_Settings_ui.Ui_Dialog):
    callbookChanged = QtCore.pyqtSignal(str)
    rigctldStatusChanged = QtCore.pyqtSignal(bool)
    settingsStored = QtCore.pyqtSignal()

    def __init__(self, parent, settings: QtCore.QSettings, rig_status: QtWidgets.QLabel, cols: typing.Iterable,
                 logger: Logger):
        super().__init__(parent)
        self.setupUi(self)

        self.log = logging.getLogger('Settings')
        self.log.addHandler(logger)
        self.log.setLevel(logger.loglevel)
        self.logger = logger
        self.log.debug('Initialising...')

        self.rigsListEdit = ListEdit(self.listingsWidget, self.tr('Radios'))
        self.listingsWidget.layout().addWidget(self.rigsListEdit, 0, 0, 1, 1)
        self.rigsListEdit.listChanged.connect(self.refreshRigsComboBox)
        self.antsListEdit = ListEdit(self.listingsWidget, self.tr('Antennas'))
        self.listingsWidget.layout().addWidget(self.antsListEdit, 0, 1, 1, 1)
        self.antsListEdit.listChanged.connect(self.refreshAntsComboBox)

        self.settings = settings
        self.rig_ids = None
        self.rigs = None
        self.rigctld_path = None
        self.rigctld = None
        self.rig_caps = []
        self.rig_status = rig_status

        self.rigctl_startupinfo = None
        if platform.system() == 'Windows':
            self.rigctl_startupinfo = subprocess.STARTUPINFO()
            self.rigctl_startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            if self.settings.value('cat/rigctldPath', None):
                if self.__is_exe__(self.settings.value('cat/rigctldPath')):
                    self.init_hamlib(self.settings.value('cat/rigctldPath'))
                else:
                    self.settings.setValue('cat/rigctldPath', '')
                    self.hamlibPathLineEdit.setText('')
        else:
            self.rigctldPathLabel.setVisible(False)
            self.hamlibPathLineEdit.setVisible(False)
            self.hamlibPathToolButton.setVisible(False)
            self.checkHamlibLabel.setVisible(False)
            self.init_hamlib('rigctld')

        self.checkHamlibTimer = QtCore.QTimer(self)
        self.checkHamlibTimer.timeout.connect(self.checkRigctld)

        self.palette_default = QtGui.QPalette()
        self.palette_default.setColor(QtGui.QPalette.ColorGroup.Active, QtGui.QPalette.ColorRole.Base,
                                      QtGui.QColor(255, 255, 255))
        self.palette_ok = QtGui.QPalette()
        self.palette_ok.setColor(QtGui.QPalette.ColorGroup.Active, QtGui.QPalette.ColorRole.Base,
                                 QtGui.QColor(204, 255, 204))
        self.palette_empty = QtGui.QPalette()
        self.palette_empty.setColor(QtGui.QPalette.ColorGroup.Active, QtGui.QPalette.ColorRole.Base,
                                    QtGui.QColor(255, 255, 204))
        self.palette_faulty = QtGui.QPalette()
        self.palette_faulty.setColor(QtGui.QPalette.ColorGroup.Active, QtGui.QPalette.ColorRole.Base,
                                     QtGui.QColor(255, 204, 204))

        self.columns = cols
        self.sortComboBox.insertItems(0, cols)

        self.callbooks = dict([(cbt.value, cbt.name) for cbt in set(CallBookType)])
        self.callbookComboBox.insertItems(0, self.callbooks.keys())

    def refreshRigsComboBox(self):
        self.radioComboBox.clear()
        self.radioComboBox.insertItems(0, self.rigsListEdit.items())
        self.radioComboBox.setCurrentText(self.settings.value('station/radio', ''))

    def refreshAntsComboBox(self):
        self.antennaComboBox.clear()
        self.antennaComboBox.insertItems(0, self.antsListEdit.items())
        self.antennaComboBox.setCurrentText(self.settings.value('station/antenna', ''))

    def calcLocator(self):
        self.locatorLineEdit.setText(maidenhead.to_maiden(self.latitudeDoubleSpinBox.value(),
                                                          self.longitudeDoubleSpinBox.value(),
                                                          4))

    def checkRigctld(self):
        if self.rigctld and self.rigctld.poll():
            self.log.error('rigctld died unexpectedly')
            self.ctrlRigctldPushButton.setText(self.tr('Start'))
            self.ctrlRigctldPushButton.setChecked(False)
            self.rig_caps = []
            self.checkHamlibTimer.stop()
            self.rig_status.setText(self.tr('Hamlib') + ': ' + self.tr('inactiv'))

    def isRigctldActive(self):
        return self.rigctld and not self.rigctld.poll()

    @staticmethod
    def __is_exe__(path):
        return os.path.isfile(path) and os.access(path, os.X_OK)

    def chooseHamlibPath(self):
        rigctld_path = QtWidgets.QFileDialog.getOpenFileName(
            self,
            self.tr('Choose hamlib rigctld executable'),
            self.settings.value('cat/rigctldPath', None),
            'rigctld.exe (rigctld.exe)'
        )

        if self.__is_exe__(rigctld_path[0]):
            self.init_hamlib(rigctld_path[0])
        else:
            self.checkHamlibLabel.setText(self.tr('Selected file is not the executable'))

    def init_hamlib(self, rigctld_path):
        if rigctld_path:
            try:
                res = subprocess.run([rigctld_path, '-l'], capture_output=True)
                stdout = str(res.stdout, sys.getdefaultencoding()).replace('\r', '')
                if res.returncode != 0 or not stdout:
                    self.log.error(f'Error executing rigctld: {res.returncode}')
                    self.checkHamlibLabel.setText(self.tr('Error executing rigctld'))
                    self.settings.setValue('cat/rigctldPath', '')
                    self.hamlibPathLineEdit.setText('')
                    return
                self.log.debug('Executed rigctld to list rigs')
            except FileNotFoundError:
                self.log.info('rigctld is not available')
                self.checkHamlibLabel.setText(self.tr('rigctld is not available'))
                self.settings.setValue('cat/rigctldPath', '')
                self.hamlibPathLineEdit.setText('')
                return

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
            self.manufacturerComboBox.insertItems(0, sorted(self.rigs.keys()))
            if self.settings.value('cat/rigMfr', None):
                self.manufacturerComboBox.setCurrentText(self.settings.value('cat/rigMfr'))
            else:
                self.manufacturerComboBox.setCurrentIndex(0)

            self.settings.setValue('cat/rigctldPath', rigctld_path)
            self.hamlibPathLineEdit.setText(rigctld_path)
            self.checkHamlibLabel.setText('')
            self.rigctld_path = rigctld_path

    def mfrChanged(self, mfr):
        self.modelComboBox.clear()

        if mfr in self.rigs:
            self.modelComboBox.insertItems(0, sorted(self.rigs[mfr]))

        if self.settings.value('cat/rigModel', None):
            self.modelComboBox.setCurrentText(self.settings.value('cat/rigModel'))

    def collectRigCaps(self, rig_id):
        res = subprocess.run([self.rigctld_path, f'--model={rig_id}', '-u'],
                             capture_output=True,
                             startupinfo=self.rigctl_startupinfo)
        stdout = str(res.stdout, sys.getdefaultencoding()).replace('\r', '')
        self.rig_caps = []
        for ln in stdout.split('\n'):
            if ln.startswith('Can '):
                cap, able = ln.split(':')
                if able.strip() == 'Y':
                    self.rig_caps.append(cap[4:].lower())

    # noinspection PyUnresolvedReferences
    def ctrlRigctld(self, start):
        if start:
            if not self.rigctld_path:
                self.log.warning('rigctld is not available')
                self.ctrlRigctldPushButton.setChecked(False)
                self.parent().actionStart_hamlib_TB.setChecked(False)
                self.parent().actionStart_hamlib_TB.setText(self.tr('Start hamlib'))
                return

            if not self.rigctld:
                rig_mfr = self.settings.value('cat/rigMfr')
                rig_model = self.settings.value('cat/rigModel')
                rig_if = self.settings.value("cat/interface")
                rig_speed = self.settings.value("cat/baud")
                if not rig_mfr or not rig_model or not rig_if or not rig_speed:
                    QtWidgets.QMessageBox.critical(self, self.tr('CAT settings error'),
                                                   self.tr('CAT configuration was never saved '
                                                           'or a parameter is missing'))
                    self.ctrlRigctldPushButton.setChecked(False)
                    self.parent().actionStart_hamlib_TB.setChecked(False)
                    self.parent().actionStart_hamlib_TB.setText(self.tr('Start hamlib'))
                    return

                rig_id = self.rig_ids[f'{rig_mfr}/{rig_model}']

                self.collectRigCaps(rig_id)

                self.rigctld = subprocess.Popen([self.rigctld_path,
                                                 f'--model={rig_id}',
                                                 f'--rig-file={rig_if}',
                                                 f'--serial-speed={rig_speed}',
                                                 '--listen-addr=127.0.0.1'],
                                                startupinfo=self.rigctl_startupinfo)

                if self.rigctld.poll():
                    self.checkHamlibRunLabel.setText(self.tr('rigctld did not start properly'))
                    self.ctrlRigctldPushButton.setChecked(False)
                    self.parent().actionStart_hamlib_TB.setChecked(False)
                    self.parent().actionStart_hamlib_TB.setText(self.tr('Start hamlib'))
                    self.rig_status.setText(self.tr('Hamlib') + ': ' + self.tr('inactiv'))
                else:
                    self.checkHamlibRunLabel.setText('')
                    self.ctrlRigctldPushButton.setChecked(True)
                    self.ctrlRigctldPushButton.setText(self.tr('Stop'))
                    self.parent().actionStart_hamlib_TB.setChecked(True)
                    self.parent().actionStart_hamlib_TB.setText(self.tr('Stop hamlib'))
                    self.log.info(f'rigctld is running with pid #{self.rigctld.pid} and arguments {self.rigctld.args}')
                    self.checkHamlibTimer.start(1000)
                    self.rig_status.setText(self.tr('Hamlib') + ': ' + self.tr('activ'))
                    self.rigctldStatusChanged.emit(True)
        else:
            self.checkHamlibTimer.stop()
            if self.rigctld and not self.rigctld.poll():
                os.kill(self.rigctld.pid, 9)
                self.log.info('Killed rigctld')
            self.rigctld = None
            self.ctrlRigctldPushButton.setChecked(False)
            self.ctrlRigctldPushButton.setText(self.tr('Start'))
            self.parent().actionStart_hamlib_TB.setChecked(False)
            self.parent().actionStart_hamlib_TB.setText(self.tr('Start hamlib'))
            self.rig_status.setText(self.tr('Hamlib') + ': ' + self.tr('inactiv'))
            self.rig_caps = []
            self.rigctldStatusChanged.emit(False)

    def locatorChanged(self, txt):
        if not txt:
            self.locatorLineEdit.setPalette(self.palette_empty)
        elif check_format(REGEX_LOCATOR, txt):
            self.locatorLineEdit.setPalette(self.palette_ok)
        else:
            self.locatorLineEdit.setPalette(self.palette_faulty)

    def callSignChanged(self, txt):
        if not txt:
            self.callsignLineEdit.setPalette(self.palette_empty)
        elif check_format(REGEX_CALL, txt):
            self.callsignLineEdit.setPalette(self.palette_ok)
        else:
            self.callsignLineEdit.setPalette(self.palette_faulty)

    def callSignCBChanged(self, txt):
        if not txt:
            self.callsignCBLineEdit.setPalette(self.palette_empty)
        else:
            self.callsignCBLineEdit.setPalette(self.palette_ok)

    def hideCol(self):
        for item in self.colShowListWidget.selectedItems():
            self.colHideListWidget.insertItem(0, item.text())
            self.colShowListWidget.takeItem(self.colShowListWidget.row(item))

        self.colHideListWidget.sortItems()

    def showCol(self):
        for item in self.colHideListWidget.selectedItems():
            self.colShowListWidget.insertItem(0, item.text())
            self.colHideListWidget.takeItem(self.colHideListWidget.row(item))

        self.colShowListWidget.sortItems()

    def callbookSelected(self, service: str):
        """Slot (i.e. if callbookComboBox is changed)"""
        self.callbookUserLineEdit.setText(self.settings.value(f'callbook/{self.callbooks[service]}_user', ''))

    def exec(self):
        self.log.info('Loading settings...')
        self.catInterfaceLineEdit.setText(self.settings.value('cat/interface', ''))
        self.catBaudComboBox.setCurrentText(self.settings.value('cat/baud', ''))

        self.rigsListEdit.clear()
        self.rigsListEdit.setItems(self.settings.value('listings/rigs'))
        self.antsListEdit.clear()
        self.antsListEdit.setItems(self.settings.value('listings/antennas'))

        self.callsignLineEdit.setText(self.settings.value('station/callSign', ''))
        self.nameLineEdit.setText(self.settings.value('station/name', ''))
        self.QTHLineEdit.setText(self.settings.value('station/QTH', ''))
        self.locatorLineEdit.setText(self.settings.value('station/locator', ''))
        self.radioComboBox.setCurrentText(self.settings.value('station/radio', ''))
        self.antennaComboBox.setCurrentText(self.settings.value('station/antenna', ''))

        self.callsignCBLineEdit.setText(self.settings.value('station_cb/callSign', ''))
        self.radioCBLineEdit.setText(self.settings.value('station_cb/radio', ''))
        self.antennaCBLineEdit.setText(self.settings.value('station_cb/antenna', ''))
        self.cbDefaultCheckBox.setChecked(bool(self.settings.value('station_cb/cb_by_default', 0)))
        self.expCBQSOsCheckBox.setChecked(bool(self.settings.value('station_cb/cb_exp_adif', 0)))

        self.sortComboBox.setCurrentText(self.settings.value('ui/sort_col', self.tr('Date/Time start')))
        sort_order = self.settings.value('ui/sort_order', 'ASC')
        self.sortAscRadioButton.setChecked(sort_order == 'ASC')
        self.sortDscRadioButton.setChecked(sort_order == 'DSC')
        self.recentQSOsComboBox.setCurrentText(self.settings.value('ui/recent_qsos', self.tr('Show all')))
        self.colHideListWidget.clear()
        self.colShowListWidget.clear()
        h_cols = self.settings.value('ui/hidden_cols', '').split(',')
        for i, c in enumerate(self.columns, 1):
            if str(i) not in h_cols:
                self.colShowListWidget.addItem(f'{i:02d} - {c}')
            else:
                self.colHideListWidget.addItem(f'{i:02d} - {c}')
        self.colShowListWidget.sortItems()
        self.colHideListWidget.sortItems()
        self.logLevelComboBox.setCurrentText(str(self.settings.value('ui/log_level', 'Info')).capitalize())
        self.logToFileCheckBox.setChecked(bool(self.settings.setValue('ui/log_file', 0)))

        self.expOwnNotesADIFCheckBox.setChecked(bool(self.settings.value('imp_exp/own_notes_adif', 0)))
        self.expRecentOnlyCheckBox.setChecked(bool(self.settings.value('imp_exp/only_recent', 0)))
        self.useCfgIDWatchCheckBox.setChecked(bool(self.settings.value('imp_exp/use_id_watch', 0)))
        self.useCfgStationWatchCheckBox.setChecked(bool(self.settings.value('imp_exp/use_station_watch', 0)))

        self.callbookComboBox.setCurrentText(self.callbook_dname)
        self.callbookUserLineEdit.setText(self.settings.value(f'callbook/{self.callbook_id}_user', ''))

        self.eqslUserLineEdit.setText(self.settings.value('eqsl/username', ''))
        self.lotwUserLineEdit.setText(self.settings.value('lotw/username', ''))
        self.lotwCertPwdCheckBox.setChecked(bool(self.settings.value('lotw/cert_needs_pwd', 0)))

        return super().exec()

    @property
    def callbook_id(self) -> str:
        """The selected callbooks id"""
        return self.settings.value('callbook/service', 'HamQTH')

    @property
    def callbook_dname(self) -> str:
        """Returns the selected callbooks descriptive name"""
        return CallBookType[self.settings.value('callbook/service', 'HamQTH')].value

    def callbookPassword(self, callbook: CallBookType) -> str:
        """Get the password for the callbook
        :param callbook: the callbook service to get the password for
        :return: the password"""

        return keyring.get_password(callbook.value,
                                    self.settings.value(f'callbook/{callbook.name}_user', ''))

    def eqslPassword(self) -> str:
        """The password for the eQSL service"""
        return keyring.get_password('eqsl.cc',
                                    self.settings.value('eqsl/username', ''))

    def lotwPassword(self) -> str:
        """The password for the LoTW online service"""
        return keyring.get_password('lotw.arrl.org',
                                    self.settings.value('lotw/username', ''))

    def accept(self):
        self.log.info('Saving Settings...')
        self.settings.setValue('cat/interface', self.catInterfaceLineEdit.text())
        self.settings.setValue('cat/baud', self.catBaudComboBox.currentText())
        self.settings.setValue('cat/rigMfr', self.manufacturerComboBox.currentText())
        self.settings.setValue('cat/rigModel', self.modelComboBox.currentText())

        self.settings.setValue('station/callSign', self.callsignLineEdit.text())
        self.settings.setValue('station/name', self.nameLineEdit.text())
        self.settings.setValue('station/QTH', self.QTHLineEdit.text())
        self.settings.setValue('station/locator', self.locatorLineEdit.text())
        self.settings.setValue('station/radio', self.radioComboBox.currentText())
        self.settings.setValue('station/antenna', self.antennaComboBox.currentText())

        self.settings.setValue('listings/rigs', self.rigsListEdit.items())
        self.settings.setValue('listings/antennas', self.antsListEdit.items())

        self.settings.setValue('station_cb/callSign', self.callsignCBLineEdit.text())
        self.settings.setValue('station_cb/radio', self.radioCBLineEdit.text())
        self.settings.setValue('station_cb/antenna', self.antennaCBLineEdit.text())
        self.settings.setValue('station_cb/cb_by_default', int(self.cbDefaultCheckBox.isChecked()))
        self.settings.setValue('station_cb/cb_exp_adif', int(self.expCBQSOsCheckBox.isChecked()))

        self.settings.setValue('ui/sort_col', self.sortComboBox.currentText())
        self.settings.setValue('ui/sort_order', 'ASC' if self.sortAscRadioButton.isChecked() else 'DSC')
        self.settings.setValue('ui/recent_qsos', self.recentQSOsComboBox.currentText())
        self.settings.setValue('ui/hidden_cols',
                               ','.join([str(int(i.text().split('-')[0].strip())) for i in
                                         self.colHideListWidget.findItems('.*',
                                                                          QtCore.Qt.MatchFlag.MatchRegularExpression)]))
        self.settings.setValue('ui/log_level', self.logLevelComboBox.currentText().upper())
        self.settings.setValue('ui/log_file', int(self.logToFileCheckBox.isChecked()))

        self.settings.setValue('imp_exp/own_notes_adif', int(self.expOwnNotesADIFCheckBox.isChecked()))
        self.settings.setValue('imp_exp/only_recent', int(self.expRecentOnlyCheckBox.isChecked()))
        self.settings.setValue('imp_exp/use_id_watch', int(self.useCfgIDWatchCheckBox.isChecked()))
        self.settings.setValue('imp_exp/use_station_watch', int(self.useCfgStationWatchCheckBox.isChecked()))

        self.settings.setValue('callbook/service', self.callbooks[self.callbookComboBox.currentText()])
        self.settings.setValue(f'callbook/{self.callbook_id}_user', self.callbookUserLineEdit.text())
        if self.callbookUserLineEdit.text() and self.callbookPasswdLineEdit.text():
            keyring.set_password(self.callbookComboBox.currentText(),
                                 self.callbookUserLineEdit.text(),
                                 self.callbookPasswdLineEdit.text())
        self.callbookPasswdLineEdit.clear()
        self.callbookChanged.emit(self.callbooks[self.callbookComboBox.currentText()])

        self.settings.setValue('eqsl/username', self.eqslUserLineEdit.text())
        if self.eqslUserLineEdit.text() and self.eqslPasswdLineEdit.text():
            keyring.set_password('eqsl.cc',
                                 self.eqslUserLineEdit.text(),
                                 self.eqslPasswdLineEdit.text())
        self.eqslPasswdLineEdit.clear()

        self.settings.setValue('lotw/username', self.lotwUserLineEdit.text())
        if self.lotwUserLineEdit.text() and self.lotwPasswdLineEdit.text():
            keyring.set_password('lotw.arrl.org',
                                 self.lotwUserLineEdit.text(),
                                 self.lotwPasswdLineEdit.text())
        self.lotwPasswdLineEdit.clear()
        self.settings.value('lotw/cert_needs_pwd', int(self.lotwCertPwdCheckBox.isChecked()))

        self.settingsStored.emit()
        super().accept()
