import os
import subprocess
import sys
import platform

import maidenhead
from PyQt6 import QtWidgets, QtCore

import DragonLog_Settings_ui


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

    def calcLocator(self):
        self.locatorLineEdit.setText(maidenhead.to_maiden(self.latitudeDoubleSpinBox.value(),
                                                          self.longitudeDoubleSpinBox.value(),
                                                          4))

    def checkRigctld(self):
        if self.rigctld and self.rigctld.poll():
            print('rigctld died unexpectedly')
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
            self.manufacturerComboBox.insertItems(0, self.rigs.keys())
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
            if self.rigctld and not self.rigctld.poll():
                os.kill(self.rigctld.pid, 9)
                print('Killed rigctld')
            self.ctrlRigctldPushButton.setText(self.tr('Start'))
            self.rig_status.setText(self.tr('Hamlib') + ': ' + self.tr('inactiv'))
            self.rig_caps = []

    def exec(self):
        print('Loading settings...')
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

        return super().exec()

    def accept(self):
        print('Saving Settings...')
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

        super().accept()
