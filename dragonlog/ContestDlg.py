import logging

from PyQt6 import QtWidgets, QtCore

from . import ContestDlg_ui
from .Logger import Logger
from .adi2contest import *
from . import ColorPalettes


class ContestDialog(QtWidgets.QDialog, ContestDlg_ui.Ui_ContestDialog):
    def __init__(self, parent, dragonlog, settings: QtCore.QSettings, logger: Logger, contests: list):
        super().__init__(parent)
        self.dragonlog = dragonlog
        self.setupUi(self)

        self.log = logging.getLogger('ContestDialog')
        self.log.addHandler(logger)
        self.log.setLevel(logger.loglevel)
        self.logger = logger
        self.log.debug('Initialising...')

        self.contest = None
        self.contestComboBox.insertItems(0, [CONTEST_NAMES[c] for c in contests])

        self.__validation__: dict[str, bool] = {}

        dt = QtCore.QDateTime.currentDateTimeUtc()
        self.fromDateEdit.setDate(dt.date())
        self.toDateEdit.setDate(dt.date())

        self.__settings__ = settings

        locator = ''
        if check_qth(settings.value('station/qth_loc', '')):
            _, locator = check_qth(settings.value('station/qth_loc', ''))

        self.callLineEdit.setText(self.__settings__.value('contest/call', settings.value('station/callSign', '')))
        self.callChanged(self.callLineEdit.text())
        self.locatorLineEdit.setText(self.__settings__.value('contest/locator', locator))
        self.locatorChanged(self.locatorLineEdit.text())
        self.nameLineEdit.setText(self.__settings__.value('contest/name', settings.value('station/name', '')))
        self.nameChanged(self.nameLineEdit.text())
        self.emailLineEdit.setText(self.__settings__.value('contest/email', ''))
        self.emailChanged(self.emailLineEdit.text())
        self.streetLineEdit.setText(self.__settings__.value('contest/street', ''))
        self.streetChanged(self.streetLineEdit.text())
        self.cityLineEdit.setText(self.__settings__.value('contest/city', ''))
        self.cityChanged(self.cityLineEdit.text())
        self.specificLineEdit.setText(self.__settings__.value('contest/specific', ''))
        self.specificChanged(self.specificLineEdit.text())
        self.clubLineEdit.setText(self.__settings__.value('contest/club', ''))
        self.clubChanged(self.clubLineEdit.text())

        self.exportPathLineEdit.setText(self.__settings__.value('contest/last_export_dir', os.path.abspath(os.curdir)))

    def contestChanged(self, contest: str):
        self.contest = CONTESTS[CONTEST_IDS[contest]]

        self.bandComboBox.clear()
        self.bandComboBox.insertItems(0, self.contest.valid_bands_list())

        self.toDateEdit.setEnabled(not self.contest.is_single_day())

        self.specificLabel.setText(self.contest.descr_specific())

        self.modeComboBox.clear()
        self.modeComboBox.insertItems(0, self.contest.valid_modes_list())

        self.powerComboBox.clear()
        self.powerComboBox.insertItems(0, self.contest.valid_power_list())

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
        if not txt.strip():
            self.streetLineEdit.setPalette(ColorPalettes.PaletteRequired)
            self.__validation__['street'] = False
        elif find_non_ascii(txt):
            self.streetLineEdit.setPalette(ColorPalettes.PaletteFaulty)
            self.__validation__['street'] = True
        else:
            self.streetLineEdit.setPalette(ColorPalettes.PaletteOk)
            self.__validation__['street'] = True

        self.checkRequired()

    def cityChanged(self, txt):
        if not txt.strip():
            self.cityLineEdit.setPalette(ColorPalettes.PaletteRequired)
            self.__validation__['city'] = False
        elif find_non_ascii(txt):
            self.cityLineEdit.setPalette(ColorPalettes.PaletteFaulty)
            self.__validation__['city'] = True
        else:
            self.cityLineEdit.setPalette(ColorPalettes.PaletteOk)
            self.__validation__['city'] = True

        self.checkRequired()

    def specificChanged(self, txt):
        if not txt.strip():
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

    def accept(self):
        self.log.info(f'Exporting "{self.contestComboBox.currentText()}" from {self.fromDateEdit.text()}...')

        doc = self.dragonlog._build_adif_export_(f"SELECT * FROM qsos WHERE "
                                                 f"contest_id = '{CONTEST_IDS[self.contestComboBox.currentText()]}' AND "
                                                 f"DATE(date_time) >= DATE('{self.fromDateEdit.text()}') AND "
                                                 f"DATE(date_time) <= DATE('{self.toDateEdit.text()}') "
                                                 "ORDER BY date_time",
                                                 include_id=True)

        contest: ContestLog = self.contest(self.callLineEdit.text(),
                                           self.nameLineEdit.text(),
                                           self.clubLineEdit.text(),
                                           f'{self.streetLineEdit.text()}\n{self.cityLineEdit.text()}',
                                           self.emailLineEdit.text(),
                                           self.locatorLineEdit.text(),
                                           CategoryBand['B_' + self.bandComboBox.currentText()],
                                           CategoryMode[self.modeComboBox.currentText()],
                                           specific=self.specificLineEdit.text(),
                                           logger=self.logger)
        contest.set_created_by(f'{self.dragonlog.programName} {self.dragonlog.programVersion}')

        if self.soapPlainTextEdit.toPlainText().strip():
            contest.add_soapbox(self.soapPlainTextEdit.toPlainText().strip())

        if doc['RECORDS']:
            try:
                for rec in doc['RECORDS']:
                    contest.append(rec)

                self.log.info(f'Contest statistics < {contest.statistics()} >')
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
                                                          'Export will be written anyway. Please check the application log before sending!')
                                                      )

                QtWidgets.QMessageBox.information(self, self.tr('Contest Export'),
                                                  self.tr('Contest data written to') + f' {contest.file_name}\n' +
                                                  self.tr('Claimed points') + f': {contest.claimed_points}\n\n' +
                                                  self.tr('Please check the file patiently before sending!')
                                                  )
            except Exception as exc:
                self.log.exception(exc)
        else:
            QtWidgets.QMessageBox.warning(self, self.tr('Contest Export'),
                                          self.tr('No contest data found for export') +
                                          f'\n"{self.contestComboBox.currentText()}" from {self.fromDateEdit.text()}')

        self.__settings__.setValue('contest/call', self.callLineEdit.text())
        self.__settings__.setValue('contest/locator', self.locatorLineEdit.text())
        self.__settings__.setValue('contest/name', self.nameLineEdit.text())
        self.__settings__.setValue('contest/email', self.emailLineEdit.text())
        self.__settings__.setValue('contest/street', self.streetLineEdit.text())
        self.__settings__.setValue('contest/city', self.cityLineEdit.text())
        self.__settings__.setValue('contest/specific', self.specificLineEdit.text())
        self.__settings__.setValue('contest/club', self.clubLineEdit.text())

        super().accept()
