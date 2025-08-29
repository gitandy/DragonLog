# DragonLog (c) 2023-2025 by Andreas Schawo is licensed under CC BY-SA 4.0.
# To view a copy of this license, visit http://creativecommons.org/licenses/by-sa/4.0/

import os
import logging

from PyQt6 import QtWidgets, QtCore

from . import ContestDlg_ui
from .Logger import Logger
from .contest import CONTESTS, CONTEST_IDS, CONTEST_NAMES
from .contest.base import (ContestLog, ContestLogEDI, Address,
                           CategoryBand, CategoryMode, CategoryPower, CategoryOperator)
from . import ColorPalettes
from .RegEx import check_qth, check_format, find_non_ascii, REGEX_CALL, REGEX_LOCATOR, REGEX_EMAIL
from .cty import CountryData


class ContestDialog(QtWidgets.QDialog, ContestDlg_ui.Ui_ContestDialog):
    def __init__(self, parent, dragonlog, settings: QtCore.QSettings, logger: Logger, contests: list,
                 cty: CountryData):
        super().__init__(parent)
        self.dragonlog = dragonlog
        self.setupUi(self)

        self.log = logging.getLogger('ContestDialog')
        self.log.addHandler(logger)
        self.log.setLevel(logger.loglevel)
        self.logger = logger
        self.log.debug('Initialising...')

        self.__cty__ = cty

        self.__settings__ = settings

        self.contest: type[ContestLog] | None = None
        self.contestComboBox.insertItems(0, [CONTEST_NAMES[c] for c in contests])
        if CONTEST_IDS.get(self.__settings__.value('contest/id', ''), '') in contests:
            self.contestComboBox.setCurrentText(self.__settings__.value('contest/id', ''))

        self.__validation__: dict[str, bool] = {}

        cur_date = QtCore.QDateTime.currentDateTimeUtc().toString('yyyy-MM-dd')
        date_from = self.__settings__.value('contest/from_date', cur_date)
        self.fromDateEdit.setDate(QtCore.QDate.fromString(date_from, 'yyyy-MM-dd'))
        date_to = self.__settings__.value('contest/to_date', cur_date)
        self.toDateEdit.setDate(QtCore.QDate.fromString(date_to, 'yyyy-MM-dd'))

        city = ''
        locator = ''
        if check_qth(settings.value('station/qth_loc', '')):
            city, locator = check_qth(settings.value('station/qth_loc', ''))

        self.callLineEdit.setText(self.__settings__.value('contest/call', settings.value('station/callSign', '')))
        self.callChanged(self.callLineEdit.text())
        self.operatorsLineEdit.setText(self.callLineEdit.text())
        self.locatorLineEdit.setText(self.__settings__.value('contest/locator', locator))
        self.locatorChanged(self.locatorLineEdit.text())
        self.nameLineEdit.setText(self.__settings__.value('contest/name', settings.value('station/name', '')))
        self.nameChanged(self.nameLineEdit.text())
        self.emailLineEdit.setText(self.__settings__.value('contest/email', ''))
        self.emailChanged(self.emailLineEdit.text())
        self.streetLineEdit.setText(self.__settings__.value('contest/street', ''))
        self.streetChanged(self.streetLineEdit.text())
        self.zipLineEdit.setText(self.__settings__.value('contest/zip', ''))
        self.zipChanged(self.zipLineEdit.text())
        self.cityLineEdit.setText(self.__settings__.value('contest/city', ''))
        self.cityChanged(self.cityLineEdit.text())
        self.countryLineEdit.setText(self.__settings__.value('contest/country', ''))
        self.countryChanged(self.countryLineEdit.text())
        self.specificLineEdit.setText(self.__settings__.value('contest/specific', ''))
        self.specificChanged(self.specificLineEdit.text())
        self.clubLineEdit.setText(self.__settings__.value('contest/club', ''))
        self.clubChanged(self.clubLineEdit.text())

        self.qthLineEdit.setText(city)
        self.rigLineEdit.setText(self.__settings__.value('station/radio', ''))
        self.powerSpinBox.setValue(int(self.__settings__.value('contest_edi/power', 0)))
        self.antennaLineEdit.setText(self.__settings__.value('station/antenna', ''))
        self.antAboveGroundSpinBox.setValue(int(self.__settings__.value('contest_edi/ant_height_ground', -1)))
        self.antAboveSeaSpinBox.setValue(int(self.__settings__.value('contest_edi/ant_height_sea', -1)))

        self.exportPathLineEdit.setText(self.__settings__.value('contest/last_export_dir', os.path.abspath(os.curdir)))

    def contestChanged(self, contest: str):
        self.contest = CONTESTS[CONTEST_IDS[contest]]

        self.bandComboBox.clear()
        self.bandComboBox.insertItems(0, self.contest.valid_bands_list())

        self.toDateEdit.setEnabled(not self.contest.is_single_day())
        self.toDateEdit.setMinimumDate(self.fromDateEdit.date())
        self.toDateEdit.setDate(self.fromDateEdit.date())

        self.specificLabel.setText(self.contest.descr_specific())

        self.modeComboBox.clear()
        self.modeComboBox.insertItems(0, self.contest.valid_modes_list())

        self.powerComboBox.clear()
        self.powerComboBox.insertItems(0, self.contest.valid_power_list())

        self.opComboBox.clear()
        self.opComboBox.insertItems(0, self.contest.valid_operator_list())

        self.ediGroupBox.setEnabled(issubclass(self.contest, ContestLogEDI))

    def fromDateChanged(self, date: QtCore.QDate):
        if self.contest.is_single_day():
            self.toDateEdit.setMinimumDate(date)
            self.toDateEdit.setDate(date)
        else:
            self.toDateEdit.setMinimumDate(date.addDays(1))

    def choosePath(self):
        res = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            self.tr('Select export folder'),
            self.__settings__.value('contest/last_export_dir', os.path.abspath(os.curdir)))

        if res:
            self.exportPathLineEdit.setText(res)
            self.__settings__.setValue('contest/last_export_dir', res)

    def checkRequired(self):
        if all(self.__validation__.values()):
            self.exportPushButton.setEnabled(True)
        else:
            self.exportPushButton.setEnabled(False)

    def callChanged(self, txt):
        if not txt.strip():
            self.callLineEdit.setPalette(ColorPalettes.PaletteRequired)
            self.__validation__['call'] = False
        elif check_format(REGEX_CALL, txt):
            self.callLineEdit.setPalette(ColorPalettes.PaletteOk)
            self.__validation__['call'] = True
        else:
            self.callLineEdit.setPalette(ColorPalettes.PaletteFaulty)
            self.__validation__['call'] = True

        self.checkRequired()

    def locatorChanged(self, txt):
        if not txt.strip():
            self.locatorLineEdit.setPalette(ColorPalettes.PaletteRequired)
            self.__validation__['locator'] = False
        elif check_format(REGEX_LOCATOR, txt):
            self.locatorLineEdit.setPalette(ColorPalettes.PaletteOk)
            self.__validation__['locator'] = True
        else:
            self.locatorLineEdit.setPalette(ColorPalettes.PaletteFaulty)
            self.__validation__['locator'] = True

        self.checkRequired()

    def nameChanged(self, txt):
        if not txt.strip():
            self.nameLineEdit.setPalette(ColorPalettes.PaletteRequired)
            self.__validation__['name'] = False
        elif ' ' in txt.strip() and not find_non_ascii(txt):
            self.nameLineEdit.setPalette(ColorPalettes.PaletteOk)
            self.__validation__['name'] = True
        else:
            self.nameLineEdit.setPalette(ColorPalettes.PaletteFaulty)
            self.__validation__['name'] = True

        self.checkRequired()

    def emailChanged(self, txt):
        if not txt.strip():
            self.emailLineEdit.setPalette(ColorPalettes.PaletteRequired)
            self.__validation__['email'] = False
        elif check_format(REGEX_EMAIL, txt):
            self.emailLineEdit.setPalette(ColorPalettes.PaletteOk)
            self.__validation__['email'] = True
        else:
            self.emailLineEdit.setPalette(ColorPalettes.PaletteFaulty)
            self.__validation__['email'] = True

        self.checkRequired()

    def streetChanged(self, txt):
        if find_non_ascii(txt):
            self.streetLineEdit.setPalette(ColorPalettes.PaletteFaulty)
        else:
            self.streetLineEdit.setPalette(ColorPalettes.PaletteDefault)

    def zipChanged(self, txt):
        if find_non_ascii(txt):
            self.zipLineEdit.setPalette(ColorPalettes.PaletteFaulty)
        else:
            self.zipLineEdit.setPalette(ColorPalettes.PaletteDefault)

    def cityChanged(self, txt):
        if find_non_ascii(txt):
            self.cityLineEdit.setPalette(ColorPalettes.PaletteFaulty)
        else:
            self.cityLineEdit.setPalette(ColorPalettes.PaletteDefault)

    def countryChanged(self, txt):
        if find_non_ascii(txt):
            self.countryLineEdit.setPalette(ColorPalettes.PaletteFaulty)
        else:
            self.countryLineEdit.setPalette(ColorPalettes.PaletteDefault)

    def specificChanged(self, txt):
        if not txt.strip() and self.contest.needs_specific():
            self.specificLineEdit.setPalette(ColorPalettes.PaletteRequired)
            self.__validation__['specific'] = False
        elif find_non_ascii(txt):
            self.specificLineEdit.setPalette(ColorPalettes.PaletteFaulty)
            self.__validation__['specific'] = True
        else:
            self.specificLineEdit.setPalette(ColorPalettes.PaletteOk)
            self.__validation__['specific'] = True

        self.checkRequired()

    def clubChanged(self, txt):
        if not txt.strip():
            self.clubLineEdit.setPalette(ColorPalettes.PaletteRequired)
            self.__validation__['club'] = False
        elif find_non_ascii(txt):
            self.clubLineEdit.setPalette(ColorPalettes.PaletteFaulty)
            self.__validation__['club'] = True
        else:
            self.clubLineEdit.setPalette(ColorPalettes.PaletteOk)
            self.__validation__['club'] = True

        self.checkRequired()

    def operatorChanged(self, op_class):
        if op_class in ('MULTI', 'TRAINEE'):
            self.operatorsLineEdit.setEnabled(True)
        else:
            self.operatorsLineEdit.setEnabled(False)
        self.operatorsLineEdit.setText(self.callLineEdit.text())

    def accept(self):
        self.log.info(f'Exporting "{self.contestComboBox.currentText()}" from {self.fromDateEdit.text()}...')

        c_filter = f"""SELECT * FROM qsos WHERE 
    contest_id = '{CONTEST_IDS[self.contestComboBox.currentText()]}' AND 
    DATE(date_time) >= DATE('{self.fromDateEdit.text()}') AND
    DATE(date_time) <= DATE('{self.toDateEdit.text()}') """

        if self.bandComboBox.currentText() != 'all':
            c_filter += f"AND band == '{self.bandComboBox.currentText()}' "

        c_filter += 'ORDER BY date_time,id'

        # noinspection PyProtectedMember
        doc = self.dragonlog.build_adif_export(c_filter, include_id=True)

        addr = Address(
            self.streetLineEdit.text(),
            self.zipLineEdit.text(),
            self.cityLineEdit.text(),
            self.countryLineEdit.text()
        )

        # noinspection PyTypeChecker,PyCallingNonCallable
        contest: ContestLog = self.contest(self.__settings__.value('station/callSign', 'XX1XXX').upper(),
                                           self.nameLineEdit.text(),
                                           self.clubLineEdit.text(),
                                           addr,
                                           self.emailLineEdit.text(),
                                           self.locatorLineEdit.text(),
                                           CategoryBand.from_str(self.bandComboBox.currentText()),
                                           CategoryMode.from_str(self.modeComboBox.currentText()),
                                           CategoryPower.from_str(self.powerComboBox.currentText()),
                                           CategoryOperator.from_str(self.opComboBox.currentText()),
                                           operators=self.operatorsLineEdit.text().split(' '),
                                           specific=self.specificLineEdit.text(),
                                           logger=self.logger,
                                           cty=self.__cty__)
        contest.set_created_by(f'{self.dragonlog.programName} {self.dragonlog.programVersion}')
        if isinstance(contest, ContestLogEDI):
            contest.set_edi_data(from_date=self.fromDateEdit.text(),
                                 to_date=self.toDateEdit.text(),
                                 qth=self.qthLineEdit.text(),
                                 radio=self.rigLineEdit.text(),
                                 pwr_watts=self.powerSpinBox.value(),
                                 antenna=self.antennaLineEdit.text(),
                                 ant_height_ground=self.antAboveGroundSpinBox.value(),
                                 ant_height_sea=self.antAboveSeaSpinBox.value())

        if self.soapPlainTextEdit.toPlainText().strip():
            contest.add_soapbox(self.soapPlainTextEdit.toPlainText().strip())

        if doc['RECORDS']:
            try:
                for rec in doc['RECORDS']:
                    contest.append(rec)

                self.log.info(f'Contest statistics {contest.summary()}')
                contest.open_file(self.exportPathLineEdit.text())
                contest.write_records()
                contest.close_file()
                self.log.info(f'Records written to "{contest.file_name}"')

                if contest.errors or contest.warnings:
                    QtWidgets.QMessageBox.information(self, self.tr('Contest Export'),
                                                      self.tr('There were {} error(s) and {} warning(s) '
                                                              'when processing the contest data').format(contest.errors,
                                                                                                         contest.warnings) +
                                                      '\n\n' +
                                                      self.tr(
                                                          'Export will be written anyway. '
                                                          'Please check the application log before sending!')
                                                      )

                QtWidgets.QMessageBox.information(self, self.tr('Contest Export'),
                                                  self.tr('Contest data written to') + f' {contest.file_name}\n' +
                                                  self.tr('Claimed points') + f': {contest.claimed_points}\n\n' +
                                                  self.tr('Please check the file patiently before sending!')
                                                  )
            except Exception as exc:
                self.log.exception(exc)
                QtWidgets.QMessageBox.critical(self, self.tr('Contest Export'),
                                               self.tr(
                                                   'Error processing contest data.\n'
                                                   'Please check log for further information.'))
        else:
            QtWidgets.QMessageBox.warning(self, self.tr('Contest Export'),
                                          self.tr('No contest data found for export') +
                                          f'\n"{self.contestComboBox.currentText()}" from {self.fromDateEdit.text()}')

        self.__settings__.setValue('contest/id', self.contestComboBox.currentText())
        self.__settings__.setValue('contest/from_date', self.fromDateEdit.text())
        self.__settings__.setValue('contest/to_date', self.toDateEdit.text())
        self.__settings__.setValue('contest/call', self.callLineEdit.text())
        self.__settings__.setValue('contest/locator', self.locatorLineEdit.text())
        self.__settings__.setValue('contest/name', self.nameLineEdit.text())
        self.__settings__.setValue('contest/email', self.emailLineEdit.text())
        self.__settings__.setValue('contest/street', self.streetLineEdit.text())
        self.__settings__.setValue('contest/zip', self.zipLineEdit.text())
        self.__settings__.setValue('contest/city', self.cityLineEdit.text())
        self.__settings__.setValue('contest/country', self.countryLineEdit.text())
        self.__settings__.setValue('contest/specific', self.specificLineEdit.text())
        self.__settings__.setValue('contest/club', self.clubLineEdit.text())

        self.__settings__.setValue('contest_edi/power', self.powerSpinBox.value())
        self.__settings__.setValue('contest_edi/ant_height_ground', self.antAboveGroundSpinBox.value())
        self.__settings__.setValue('contest_edi/ant_height_sea', self.antAboveSeaSpinBox.value())

        super().accept()
