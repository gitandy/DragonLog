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
from .DragonLog_RegEx import REGEX_CALL, REGEX_LOCATOR, check_format

# Fix problems with importing win32 in frozen executable
if getattr(sys, 'frozen', False):
    import win32timezone
    from keyring.backends import Windows

    keyring.set_keyring(Windows.WinVaultKeyring())


class Settings(QtWidgets.QDialog, DragonLog_Settings_ui.Ui_Dialog):
    def __init__(self, parent, settings: QtCore.QSettings, rig_status: QtWidgets.QLabel, cols: typing.Iterable,
                 logger: Logger):
        super().__init__(parent)
        self.setupUi(self)

        self.log = logging.getLogger('Settings')
        self.log.addHandler(logger)
        self.log.setLevel(logger.loglevel)
        self.logger = logger
        self.log.debug('Initialising...')

        self.settings = settings
        self.rig_ids = None
        self.rigs = None
        self.rigctld_path = None
        self.rigctld = None
        self.rig_caps = []
        self.rig_status = rig_status

        if platform.system() == 'Windows':
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
        return self.ctrlRigctldPushButton.isChecked()

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
            res = subprocess.run([rigctld_path, '-l'], capture_output=True)
            stdout = str(res.stdout, sys.getdefaultencoding()).replace('\r', '')
            if res.returncode != 0 or not stdout:
                self.checkHamlibLabel.setText(self.tr('Error executing rigctld'))
                self.settings.setValue('cat/rigctldPath', '')
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
        self.modelComboBox.insertItems(0, sorted(self.rigs[mfr]))

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
                    self.rig_caps.append(cap[4:].lower())

    def ctrlRigctld(self, start):
        if start:
            if not self.rigctld:
                # FIXME: read from settings not from UI (problem if UI was never initialised)
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

    def exec(self):
        self.log.info('Loading settings...')
        self.catInterfaceLineEdit.setText(self.settings.value('cat/interface', ''))
        self.catBaudComboBox.setCurrentText(self.settings.value('cat/baud', ''))

        self.callsignLineEdit.setText(self.settings.value('station/callSign', ''))
        self.nameLineEdit.setText(self.settings.value('station/name', ''))
        self.QTHLineEdit.setText(self.settings.value('station/QTH', ''))
        self.locatorLineEdit.setText(self.settings.value('station/locator', ''))
        self.radioLineEdit.setText(self.settings.value('station/radio', ''))
        self.antennaLineEdit.setText(self.settings.value('station/antenna', ''))

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

        self.callbookUserLineEdit.setText(self.settings.value('callbook/username', ''))
        self.eqslUserLineEdit.setText(self.settings.value('eqsl/username', ''))
        self.lotwUserLineEdit.setText(self.settings.value('lotw/username', ''))
        self.lotwCertPwdCheckBox.setChecked(bool(self.settings.value('lotw/cert_needs_pwd', 0)))

        return super().exec()

    def callbookPassword(self):
        return keyring.get_password('HamQTH.com',
                                    self.settings.value('callbook/username', ''))

    def eqslPassword(self):
        return keyring.get_password('eqsl.cc',
                                    self.settings.value('eqsl/username', ''))

    def lotwPassword(self):
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
        self.settings.setValue('station/radio', self.radioLineEdit.text())
        self.settings.setValue('station/antenna', self.antennaLineEdit.text())

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

        self.settings.setValue('callbook/username', self.callbookUserLineEdit.text())
        if self.callbookUserLineEdit.text() and self.callbookPasswdLineEdit.text():
            keyring.set_password('HamQTH.com',
                                 self.callbookUserLineEdit.text(),
                                 self.callbookPasswdLineEdit.text())
        self.callbookPasswdLineEdit.clear()

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

        super().accept()
