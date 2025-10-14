# DragonLog (c) 2023-2025 by Andreas Schawo is licensed under CC BY-SA 4.0.
# To view a copy of this license, visit http://creativecommons.org/licenses/by-sa/4.0/

import os
import sys
import typing
import logging
import platform

from PyQt6 import QtWidgets, QtCore
import keyring

from . import DragonLog_Settings_ui
from .Logger import Logger
from .RegEx import REGEX_CALL, check_format
from .CallBook import CallBookType
from .ListEdit import ListEdit
from .SelectWidget import SelectWidget
from . import ColorPalettes
from .RigControl import RigControl, RigctldExecutionException, NoExecutableFoundException

# Fix problems with importing win32 in frozen executable
if getattr(sys, 'frozen', False):
    # noinspection PyUnresolvedReferences
    import win32timezone
    from keyring.backends import Windows

    keyring.set_keyring(Windows.WinVaultKeyring())


class Settings(QtWidgets.QDialog, DragonLog_Settings_ui.Ui_Dialog):
    callbookChanged = QtCore.pyqtSignal(str)
    settingsStored = QtCore.pyqtSignal()
    ctyDataChanged = QtCore.pyqtSignal(str)

    def __init__(self, parent, settings: QtCore.QSettings,
                 bands: typing.Iterable, modes: typing.Iterable, cols: typing.Iterable,
                 logger: Logger, rigctl: RigControl):
        super().__init__(parent)
        self.setupUi(self)

        self.log = logging.getLogger('Settings')
        self.log.addHandler(logger)
        self.log.setLevel(logger.loglevel)
        self.logger = logger
        self.log.debug('Initialising...')
        self.log.info(f'Using system key vault: {keyring.get_keyring().name}')

        self.qthsListEdit = ListEdit(self.listingsWidget, self.tr('QTHs & locators'))
        self.qthsListEdit.setToolTip(self.tr('Type in as: "City (Locator)", i.e. "Koblenz (JO30ti)"'))
        self.listingsWidget.layout().addWidget(self.qthsListEdit, 0, 0, 1, 2)
        self.qthsListEdit.listChanged.connect(self.refreshQTHsComboBox)
        self.rigsListEdit = ListEdit(self.listingsWidget, self.tr('Radios'))
        self.listingsWidget.layout().addWidget(self.rigsListEdit, 1, 0, 1, 1)
        self.rigsListEdit.listChanged.connect(self.refreshRigsComboBox)
        self.antsListEdit = ListEdit(self.listingsWidget, self.tr('Antennas'))
        self.listingsWidget.layout().addWidget(self.antsListEdit, 1, 1, 1, 1)
        self.antsListEdit.listChanged.connect(self.refreshAntsComboBox)

        self.bandsSelectWidget = SelectWidget(self.bandsGroupBox, bands,
                                              self.tr('Show bands'), self.tr('Hide bands'))
        self.bandsGroupBox.layout().addWidget(self.bandsSelectWidget)
        self.modesSelectWidget = SelectWidget(self.modesGroupBox, modes,
                                              self.tr('Show modes'), self.tr('Hide modes'))
        self.modesGroupBox.layout().addWidget(self.modesSelectWidget)
        self.columnsSelectWidget = SelectWidget(self.columnsGroupBox, cols,
                                                self.tr('Show columns'), self.tr('Hide columns'))
        self.columnsGroupBox.layout().addWidget(self.columnsSelectWidget)

        self.settings = settings

        self.rigctl = rigctl

        if platform.system() == 'Windows':
            if self.settings.value('cat/rigctldPath', None):
                if self.rigctl.__is_exe__(self.settings.value('cat/rigctldPath')):
                    self.hamlibPathLineEdit.setText(self.settings.value('cat/rigctldPath'))
                else:
                    self.settings.setValue('cat/rigctldPath', '')
                    self.hamlibPathLineEdit.setText('')
        else:
            self.rigctldPathLabel.setVisible(False)
            self.hamlibPathLineEdit.setVisible(False)
            self.hamlibPathToolButton.setVisible(False)
            self.checkHamlibLabel.setVisible(False)

        self.refreshMfrComboBox()

        self.columns = cols
        self.sortComboBox.insertItems(0, cols)

        self.callbooks = dict([(cbt.value, cbt.name) for cbt in set(CallBookType)])
        self.callbookComboBox.insertItems(0, self.callbooks.keys())

    def refreshMfrComboBox(self):
        self.manufacturerComboBox.clear()
        self.manufacturerComboBox.insertItems(0, sorted(self.rigctl.availableManufacturers))
        if self.settings.value('cat/rigMfr', None):
            self.manufacturerComboBox.setCurrentText(self.settings.value('cat/rigMfr'))
        else:
            self.manufacturerComboBox.setCurrentIndex(0)

    def refreshQTHsComboBox(self):
        self.qthComboBox.clear()
        self.qthComboBox.insertItems(0, self.qthsListEdit.items())
        self.qthComboBox.setCurrentText(self.settings.value('station/qth_loc', ''))

    def refreshRigsComboBox(self):
        self.radioComboBox.clear()
        self.radioComboBox.insertItems(0, self.rigsListEdit.items())
        self.radioComboBox.setCurrentText(self.settings.value('station/radio', ''))

    def refreshAntsComboBox(self):
        self.antennaComboBox.clear()
        self.antennaComboBox.insertItems(0, self.antsListEdit.items())
        self.antennaComboBox.setCurrentText(self.settings.value('station/antenna', ''))

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
            try:
                self.rigctl.init_hamlib(rigctld_path[0])
                self.settings.setValue('cat/rigctldPath', rigctld_path[0])
                self.checkHamlibLabel.setText('')
                self.hamlibPathLineEdit.setText(rigctld_path[0])
                self.refreshMfrComboBox()
            except RigctldExecutionException as exc:
                self.settings.setValue('cat/rigctldPath', '')
                self.checkHamlibLabel.setText(self.tr('Error executing rigctld'))
                self.hamlibPathLineEdit.setText('')
            except NoExecutableFoundException as exc:
                self.settings.setValue('cat/rigctldPath', '')
                self.checkHamlibLabel.setText(self.tr('rigctld is not available'))
        else:
            self.checkHamlibLabel.setText(self.tr('Selected file is not the executable'))

    def mfrChanged(self, mfr):
        self.modelComboBox.clear()

        if mfr in self.rigctl.availableManufacturers:
            self.modelComboBox.insertItems(0, sorted(self.rigctl.availableRigs(mfr)))

        if self.settings.value('cat/rigModel', None):
            self.modelComboBox.setCurrentText(self.settings.value('cat/rigModel'))

    def callSignChanged(self, txt):
        if not txt:
            self.callsignLineEdit.setPalette(ColorPalettes.PaletteEmpty)
        elif check_format(REGEX_CALL, txt):
            self.callsignLineEdit.setPalette(ColorPalettes.PaletteOk)
        else:
            self.callsignLineEdit.setPalette(ColorPalettes.PaletteFaulty)

    def callSignCBChanged(self, txt):
        if not txt:
            self.callsignCBLineEdit.setPalette(ColorPalettes.PaletteEmpty)
        else:
            self.callsignCBLineEdit.setPalette(ColorPalettes.PaletteOk)

    def callbookSelected(self, service: str):
        """Slot (i.e. if callbookComboBox is changed)"""
        self.callbookUserLineEdit.setText(self.settings.value(f'callbook/{self.callbooks[service]}_user', ''))

    def chooseCtyDataFile(self):
        cty_path = QtWidgets.QFileDialog.getOpenFileName(
            self,
            self.tr('Choose Country data file'),
            os.path.split(self.settings.value('dx_spots/cty_data', ''))[0],
            'Country data (*.csv)'
        )

        if os.path.isfile(cty_path[0]):
            self.ctyPathLineEdit.setText(cty_path[0])
            self.settings.setValue('dx_spots/cty_data', cty_path[0])
            self.ctyDataChanged.emit(cty_path[0])

    def exec(self):
        self.log.info('Loading settings...')
        self.catInterfaceLineEdit.setText(self.settings.value('cat/interface', ''))
        self.catBaudComboBox.setCurrentText(self.settings.value('cat/baud', ''))

        self.qthsListEdit.clear()
        self.qthsListEdit.setItems(self.settings.value('listings/qths'))
        self.rigsListEdit.clear()
        self.rigsListEdit.setItems(self.settings.value('listings/rigs'))
        self.antsListEdit.clear()
        self.antsListEdit.setItems(self.settings.value('listings/antennas'))

        self.callsignLineEdit.setText(self.settings.value('station/callSign', '').upper())
        self.nameLineEdit.setText(self.settings.value('station/name', ''))
        self.qthComboBox.setCurrentText(self.settings.value('station/qth_loc', ''))
        self.radioComboBox.setCurrentText(self.settings.value('station/radio', ''))
        self.antennaComboBox.setCurrentText(self.settings.value('station/antenna', ''))

        self.callsignCBLineEdit.setText(self.settings.value('station_cb/callSign', ''))
        self.radioCBLineEdit.setText(self.settings.value('station_cb/radio', ''))
        self.antennaCBLineEdit.setText(self.settings.value('station_cb/antenna', ''))
        self.cbDefaultCheckBox.setChecked(bool(int(self.settings.value('station_cb/cb_by_default', 0))))
        self.expCBQSOsCheckBox.setChecked(bool(int(self.settings.value('station_cb/cb_exp_adif', 0))))

        self.fontComboBox.setCurrentText(self.settings.value('ui/font', 'Inter SlashedZero'))
        self.fontSizeSpinBox.setValue(int(self.settings.value('ui/font_size', 9)))
        self.qfFontSizeSpinBox.setValue(int(self.settings.value('ui/form_font_size', 10)))
        self.ccFontSizeSpinBox.setValue(int(self.settings.value('ui/cc_font_size', 12)))
        self.sortComboBox.setCurrentText(self.settings.value('ui/sort_col', self.tr('Date/Time start')))
        sort_order = self.settings.value('ui/sort_order', 'ASC')
        self.sortAscRadioButton.setChecked(sort_order == 'ASC')
        self.sortDscRadioButton.setChecked(sort_order == 'DSC')
        self.recentQSOsComboBox.setCurrentText(self.settings.value('ui/recent_qsos', self.tr('Show all')))

        try:
            self.columnsSelectWidget.indexesDisabled = [int(c) for c in self.settings.value('ui/hidden_cols',
                                                                                            '1').split(',')]
        except ValueError:
            self.logger.exception(f'Reading "ui/hidden_cols": {self.settings.value("ui/hidden_cols", "")}')

        self.bandsSelectWidget.itemsEnabled = self.settings.value('ui/show_bands', self.bandsSelectWidget.items)
        self.modesSelectWidget.itemsEnabled = self.settings.value('ui/show_modes', self.modesSelectWidget.items)

        self.checkUpdatesCheckBox.setChecked(bool(int(self.settings.value('ui/check_updates', 1))))
        self.logLevelComboBox.setCurrentText(str(self.settings.value('ui/log_level', 'Info')).capitalize())
        self.logToFileCheckBox.setChecked(bool(int(self.settings.value('ui/log_file', 0))))

        dx_call = self.settings.value('dx_spots/call', '')
        self.dxCallLineEdit.setText(dx_call if dx_call else self.settings.value('station/callSign', ''))
        dx_addr = self.settings.value('dx_spots/address', '')
        self.dxAddrLineEdit.setText(dx_addr if dx_addr else 'hamqth.com')
        dx_port = int(self.settings.value('dx_spots/port', 7300)) if dx_addr else 7300
        self.dxPortSpinBox.setValue(dx_port if 0 < dx_port <= self.dxPortSpinBox.maximum() else 7300)
        self.ctyPathLineEdit.setText(self.settings.value('dx_spots/cty_data', ''))

        self.expOwnNotesADIFCheckBox.setChecked(bool(int(self.settings.value('imp_exp/own_notes_adif', 0))))
        self.expRecentOnlyCheckBox.setChecked(bool(int(self.settings.value('imp_exp/only_recent', 0))))
        self.csvDelimiterComboBox.setCurrentText(self.csv_delimiter)
        self.useCfgIDImportCheckBox.setChecked(bool(int(self.settings.value('imp_exp/use_id_adif', 0))))
        self.useCfgStationImportCheckBox.setChecked(bool(int(self.settings.value('imp_exp/use_station_adif', 0))))
        self.useCfgIDWatchCheckBox.setChecked(bool(int(self.settings.value('imp_exp/use_id_watch', 0))))
        self.useCfgStationWatchCheckBox.setChecked(bool(int(self.settings.value('imp_exp/use_station_watch', 0))))
        self.useCfgStationCCCheckBox.setChecked(bool(int(self.settings.value('imp_exp/use_station_hamcc', 0))))

        self.callbookComboBox.setCurrentText(self.callbook_dname)
        self.callbookUserLineEdit.setText(self.settings.value(f'callbook/{self.callbook_id}_user', ''))

        self.eqslUserLineEdit.setText(self.settings.value('eqsl/username', ''))
        self.useQSOCallCheckBox.setChecked(bool(int(self.settings.value('eqsl/use_qso_call', 0))))

        self.lotwUserLineEdit.setText(self.settings.value('lotw/username', ''))
        self.lotwCertPwdCheckBox.setChecked(bool(int(self.settings.value('lotw/cert_needs_pwd', 0))))

        return super().exec()

    @property
    def csv_delimiter(self) -> str:
        return self.settings.value('imp_exp/csv_delimiter', ';' if self.locale().decimalPoint() == ',' else ',')

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

        self.settings.setValue('station/callSign', self.callsignLineEdit.text().upper())
        self.settings.setValue('station/name', self.nameLineEdit.text())
        self.settings.setValue('station/qth_loc', self.qthComboBox.currentText())
        self.settings.setValue('station/radio', self.radioComboBox.currentText())
        self.settings.setValue('station/antenna', self.antennaComboBox.currentText())

        self.settings.setValue('listings/qths', self.qthsListEdit.items())
        self.settings.setValue('listings/rigs', self.rigsListEdit.items())
        self.settings.setValue('listings/antennas', self.antsListEdit.items())

        self.settings.setValue('station_cb/callSign', self.callsignCBLineEdit.text())
        self.settings.setValue('station_cb/radio', self.radioCBLineEdit.text())
        self.settings.setValue('station_cb/antenna', self.antennaCBLineEdit.text())
        self.settings.setValue('station_cb/cb_by_default', int(self.cbDefaultCheckBox.isChecked()))
        self.settings.setValue('station_cb/cb_exp_adif', int(self.expCBQSOsCheckBox.isChecked()))

        self.settings.setValue('ui/font', self.fontComboBox.currentText())
        self.settings.setValue('ui/font_size', self.fontSizeSpinBox.value())
        self.settings.setValue('ui/form_font_size', self.qfFontSizeSpinBox.value())
        self.settings.setValue('ui/cc_font_size', self.ccFontSizeSpinBox.value())
        self.settings.setValue('ui/sort_col', self.sortComboBox.currentText())
        self.settings.setValue('ui/sort_order', 'ASC' if self.sortAscRadioButton.isChecked() else 'DSC')
        self.settings.setValue('ui/recent_qsos', self.recentQSOsComboBox.currentText())
        self.settings.setValue('ui/hidden_cols',
                               ','.join([str(c) for c in self.columnsSelectWidget.indexesDisabled]))
        self.settings.setValue('ui/show_bands', self.bandsSelectWidget.itemsEnabled)
        self.settings.setValue('ui/show_modes', self.modesSelectWidget.itemsEnabled)
        self.settings.setValue('ui/check_updates', int(self.checkUpdatesCheckBox.isChecked()))

        self.settings.setValue('ui/log_level', self.logLevelComboBox.currentText().upper())
        self.settings.setValue('ui/log_file', int(self.logToFileCheckBox.isChecked()))

        self.settings.setValue('dx_spots/call', self.dxCallLineEdit.text())
        self.settings.setValue('dx_spots/address', self.dxAddrLineEdit.text())
        self.settings.setValue('dx_spots/port', self.dxPortSpinBox.value())
        self.settings.setValue('dx_spots/cty_data', self.ctyPathLineEdit.text())

        self.settings.setValue('imp_exp/own_notes_adif', int(self.expOwnNotesADIFCheckBox.isChecked()))
        self.settings.setValue('imp_exp/only_recent', int(self.expRecentOnlyCheckBox.isChecked()))
        self.settings.setValue('imp_exp/csv_delimiter', self.csvDelimiterComboBox.currentText())
        self.settings.setValue('imp_exp/use_id_adif', int(self.useCfgIDImportCheckBox.isChecked()))
        self.settings.setValue('imp_exp/use_station_adif', int(self.useCfgStationImportCheckBox.isChecked()))
        self.settings.setValue('imp_exp/use_id_watch', int(self.useCfgIDWatchCheckBox.isChecked()))
        self.settings.setValue('imp_exp/use_station_watch', int(self.useCfgStationWatchCheckBox.isChecked()))
        self.settings.setValue('imp_exp/use_station_hamcc', int(self.useCfgStationCCCheckBox.isChecked()))

        self.settings.setValue('callbook/service', self.callbooks[self.callbookComboBox.currentText()])
        self.settings.setValue(f'callbook/{self.callbook_id}_user', self.callbookUserLineEdit.text())
        if self.callbookUserLineEdit.text() and self.callbookPasswdLineEdit.text():
            keyring.set_password(self.callbookComboBox.currentText(),
                                 self.callbookUserLineEdit.text(),
                                 self.callbookPasswdLineEdit.text())
        self.callbookPasswdLineEdit.clear()
        self.callbookChanged.emit(self.callbooks[self.callbookComboBox.currentText()])

        self.settings.setValue('eqsl/username', self.eqslUserLineEdit.text())
        self.settings.setValue('eqsl/use_qso_call', int(self.useQSOCallCheckBox.isChecked()))
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
