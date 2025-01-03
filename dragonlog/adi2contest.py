import os
from enum import Enum, auto
import logging
from dataclasses import dataclass
from typing import Type

from .RegEx import *

import openpyxl
from openpyxl.worksheet.worksheet import Worksheet
from openpyxl.styles import Font

# noinspection SpellCheckingInspection
MODE_MAP_CBR = {
    'CW': 'CW',
    'SSB': 'PH',
    'FM': 'FM',
    'RTTY': 'RY',
    'FT8': 'DG',
    'MFSK': 'DG',
}

BAND_MAP_CBR = {
    '160m': '1800',
    '80m': '3500',
    '40m': '7000',
    '20m': '14000',
    '15m': '21000',
    '10m': '28000',
    '6m': '50',
    '4m': '70',
    '2m': '144',
    # '': '222',
    '70cm': '432',
    # '': '902',
    '23cm': '1.2G',
    # '': '2.3G',
    # '': '3.4G',
    # '': '5.7G',
    # '': '10G',
    # '': '24G',
    # '': '47G',
    # '': '75G',
    # '': '122G',
    # '': '134G',
    # '': '241G',
    # '': 'LIGHT',
}

BAND_FROM_CBR = dict(zip(BAND_MAP_CBR.values(), BAND_MAP_CBR.keys()))


@dataclass
class CBRRecord:
    band: str
    mode: str
    date: str
    time: str
    own_call: str
    sent_rst: str
    sent_exch: str
    call: str
    rcvd_rst: str
    rcvd_exch: str
    tx: str


class CategoryBand(Enum):
    B_ALL = auto()
    B_160M = auto()
    B_80M = auto()
    B_40M = auto()
    B_20M = auto()
    B_15M = auto()
    B_10M = auto()
    B_6M = auto()
    B_4M = auto()
    B_2M = auto()
    B_432 = auto()
    B_70CM = auto()
    B_23CM = auto()


class CategoryOperator(Enum):
    SINGLE_OP = auto()
    MULTI_OP = auto()
    CHECKLOG = auto()


class CategoryMode(Enum):
    CW = auto()
    SSB = auto()
    RTTY = auto()
    MIXED = auto()
    DIGI = auto()
    FM = auto()


class CategoryPower(Enum):
    LOW = auto()
    HIGH = auto()
    QRP = auto()
    A = auto()
    B = auto()
    C = auto()


class CategoryAssisted(Enum):
    ASSISTED = auto()
    NON_ASSISTED = auto()


class CategoryTransmitter(Enum):
    ONE = auto()
    TWO = auto()
    LIMITED = auto()
    UNLIMITED = auto()
    SWL = auto()


class ContestLog:
    contest_name = 'Contest'
    contest_year = '2025'
    contest_update = '2024-12-16'

    REGEX_TIME = re.compile(r'(([0-1][0-9])|(2[0-3]))([0-5][0-9])([0-5][0-9])?')
    REGEX_DATE = re.compile(r'([1-9][0-9]{3})((0[1-9])|(1[0-2]))((0[1-9])|([1-2][0-9])|(3[0-2]))')

    def __init__(self, callsign, name, club, address, email, locator,
                 band: CategoryBand, mode: CategoryMode,
                 pwr: CategoryPower = CategoryPower.HIGH,
                 cat_operator: CategoryOperator = CategoryOperator.SINGLE_OP,
                 assisted: CategoryAssisted = CategoryAssisted.NON_ASSISTED,
                 tx: CategoryTransmitter = CategoryTransmitter.ONE,
                 operators: list[str] = None, specific='', skip_id=False, skip_warn=False, logger=None):

        self.log = logging.getLogger(type(self).__name__)
        if logger:
            self.log.setLevel(logger.loglevel)
            self.log.addHandler(logger)
        self.log.debug('Initialising...')

        self.__header__ = {
            'CONTEST': '',  # Class
            'CALLSIGN': '',
            'CATEGORY-OPERATOR': '',
            'CATEGORY-BAND': '',
            'CATEGORY-MODE': '',
            'CATEGORY-POWER': '',
            'CATEGORY-ASSISTED': '',
            'CATEGORY-TRANSMITTER': '',
            'SPECIFIC': '',
            'CLAIMED-SCORE': '',  # Class
            'CREATED-BY': '',  # Modul
            'OPERATORS': '',
            'NAME': '',
            'CLUB': '',
            'ADDRESS': '',
            'EMAIL': '',
            'GRID-LOCATOR': '',
        }
        self.__init_header__(callsign, name, club, address, email, locator,
                             band, mode, pwr, cat_operator, assisted, tx, operators, specific)

        self.__qso_id__: int = 0

        self.__errors__: int = 0
        self.__warnings__: int = 0
        self.__infos__: int = 0

        self.__qsos__: list[CBRRecord] = []

        self.__rated__: int = 0
        self.__points__: int = 0

        self.__skip_id__ = skip_id
        self.__skip_warn__ = skip_warn

        self.__contest_date__ = ''

        self.__out_file__ = None

    def __init_header__(self, callsign, name, club, address, email, locator,
                        band: CategoryBand, mode: CategoryMode,
                        pwr: CategoryPower = CategoryPower.HIGH,
                        cat_operator: CategoryOperator = CategoryOperator.SINGLE_OP,
                        assisted: CategoryAssisted = CategoryAssisted.NON_ASSISTED,
                        tx: CategoryTransmitter = CategoryTransmitter.ONE,
                        operators: list[str] = None, specific=''):

        if not check_format(REGEX_CALL, callsign):
            self.log.error(f'Callsign "{callsign}" does not match call format')
        if not check_format(REGEX_LOCATOR, locator):
            self.log.error(f'Locator "{locator}" does not match locator format')

        self.__header__['CONTEST'] = self.contest_name
        self.__header__['CREATED-BY'] = 'ContestLog v0.1'
        self.__header__['CALLSIGN'] = callsign
        self.__header__['NAME'] = name
        self.__header__['CLUB'] = club
        self.__header__['ADDRESS'] = address
        self.__header__['EMAIL'] = email
        self.__header__['GRID-LOCATOR'] = locator
        self.__header__['OPERATORS'] = ' '.join(operators) if operators else callsign
        self.__header__['CATEGORY-OPERATOR'] = cat_operator.name.replace('_', '-')
        self.__header__['CATEGORY-BAND'] = band.name[2:]
        self.__header__['CATEGORY-MODE'] = mode.name
        self.__header__['CATEGORY-POWER'] = pwr.name
        self.__header__['CATEGORY-ASSISTED'] = assisted.name.replace('_', '-')
        self.__header__['CATEGORY-TRANSMITTER'] = tx.name
        self.__header__['SPECIFIC'] = specific

    @property
    def infos(self):
        return self.__infos__

    @property
    def warnings(self):
        return self.__warnings__

    @property
    def errors(self):
        return self.__errors__

    def info(self, txt):
        self.__infos__ += 1
        self.log.info(f'QSO #{self.__qso_id__}: {txt}')

    def warning(self, txt):
        self.__warnings__ += 1
        self.log.warning(f'QSO #{self.__qso_id__}: {txt}')

    def error(self, txt):
        self.__errors__ += 1
        self.log.error(f'QSO #{self.__qso_id__}: {txt}')

    def exception(self, txt='Exception'):
        self.__errors__ += 1
        self.log.exception(f'QSO #{self.__qso_id__}: {txt}')

    def set_created_by(self, program_name: str):
        self.__header__['CREATED-BY'] = program_name

    def check_band(self, adif_rec: dict[str, str]) -> bool:
        if (adif_rec['BAND'].upper() != self.__header__['CATEGORY-BAND'] and
                BAND_MAP_CBR[adif_rec['BAND'].lower()] != self.__header__['CATEGORY-BAND'].lower()):
            self.log.warning(f'QSO #{self.__qso_id__} band "{adif_rec["BAND"].upper()}" does not match with '
                             f'contest band "{self.__header__["CATEGORY-BAND"]}"')
            if self.__skip_warn__:
                return False
        return True

    def append(self, adif_rec: dict[str, str]):
        self.__qso_id__ = adif_rec['APP_DRAGONLOG_QSOID']
        try:
            if self.__skip_id__:
                if 'CONTEST_ID' not in adif_rec:
                    self.error('Contest ID missing. Skipping.')
                    return
                if adif_rec['CONTEST_ID'] != self.__header__['CONTEST']:
                    self.warning(f'Contest ID "{adif_rec["CONTEST_ID"]}" does not match '
                                 f'"{self.__header__["CONTEST"]}". Skipping.')
                    return

            if self.__header__['CATEGORY-BAND'] != 'ALL' and not self.check_band(adif_rec):
                return

            if self.__header__['CATEGORY-MODE'] != 'MIXED' and adif_rec['MODE'].upper() != self.__header__[
                'CATEGORY-MODE']:
                self.warning(f'Mode "{adif_rec["MODE"].upper()}" does not match with '
                             f'contest mode "{self.__header__["CATEGORY-MODE"]}"')
                if self.__skip_warn__:
                    return

            if not check_format(REGEX_CALL, adif_rec['CALL']):
                self.warning(f'Call "{adif_rec["CALL"]}" does not match call format')
                if self.__skip_warn__:
                    return

            if not check_format(REGEX_RSTFIELD, adif_rec['RST_RCVD']):
                self.warning(
                    f'Rreceived RST "{adif_rec["RST_RCVD"]}" does not match RST format')
                if self.__skip_warn__:
                    return

            if not check_format(REGEX_RSTFIELD, adif_rec['RST_SENT']):
                self.warning(f'Sent RST "{adif_rec["RST_SENT"]}" does not match RST format')
                if self.__skip_warn__:
                    return

            if not check_format(self.REGEX_DATE, adif_rec['QSO_DATE']):
                self.warning(f'Date "{adif_rec["QSO_DATE"]}" does not match date format')
                if self.__skip_warn__:
                    return

            if not check_format(self.REGEX_TIME, adif_rec['TIME_ON']):
                self.warning(f'Time "{adif_rec["TIME_ON"]}" does not match time format')
                if self.__skip_warn__:
                    return

            rec = self.build_record(adif_rec)

            if rec:
                self.process_points(rec)
                self.__qsos__.append(rec)

                self.__header__['CLAIMED-SCORE'] = self.claimed_points

                self.log.debug(self.statistics())
        except KeyError as exc:
            self.error(f'Could not be processed. Field {exc} is missing')

    def build_record(self, adif_rec) -> CBRRecord:
        """Build the QSO info
        May be overridden"""
        self.log.debug(adif_rec)

        date = f'{adif_rec["QSO_DATE"][:4]}-{adif_rec["QSO_DATE"][4:6]}-{adif_rec["QSO_DATE"][6:8]}'
        if not self.__contest_date__:
            self.__contest_date__ = date

        return CBRRecord(BAND_MAP_CBR[adif_rec['BAND'].lower()],
                         MODE_MAP_CBR[adif_rec['MODE']],
                         date,
                         adif_rec['TIME_ON'][:4],
                         adif_rec['STATION_CALLSIGN'],
                         adif_rec['RST_SENT'],
                         adif_rec['STX_STRING'].upper() if 'STX_STRING' in adif_rec else adif_rec['STX'],
                         adif_rec['CALL'],
                         adif_rec['RST_RCVD'],
                         adif_rec['SRX_STRING'].upper() if 'SRX_STRING' in adif_rec else adif_rec['SRX'],
                         '0'
                         )

    def add_soapbox(self, txt: str):
        self.__header__['SOAPBOX'] = str(txt)

    def open_file(self, path: str = os.path.curdir):
        self.__out_file__ = open(os.path.join(path, self.file_name), 'w')

    def write_records(self):
        if self.__out_file__:
            for row in self.serialize_cbr():
                self.__out_file__.write(row)
                self.__out_file__.write('\n')

    def close_file(self):
        if self.__out_file__:
            self.__out_file__.close()

    @property
    def points(self) -> int:
        """Basic QSO points"""
        return self.__points__

    @property
    def claimed_points(self) -> int:
        """Points with some kind of multiplicator
        Should be overwritten"""
        return self.points

    @property
    def qsos(self) -> int:
        """Number of QSOs"""
        return len(self.__qsos__)

    @property
    def rated(self) -> int:
        """Number of QSOs rated with points"""
        return self.__rated__

    def process_points(self, rec: CBRRecord):
        """Place for calculating points and decision for rating a QSO
        Should be overwritten"""
        self.__points__ += 1
        self.__rated__ += 1

    def statistics(self) -> str:
        """Returns a statistic over the QSOs"""
        return f'QSOs: {self.qsos}, Rated: {self.rated}, Claimed points: {self.points}'

    def serialize_cbr(self):
        yield 'START-OF-LOG: 3.0'

        for k in self.__header__:
            if k in ('ADDRESS', 'SOAPBOX') and self.__header__[k]:
                for l in self.__header__[k].split('\n'):
                    yield f'{k}: {l}'
            elif self.__header__[k]:
                yield f'{k}: {self.__header__[k]}'

        yield ''  # Dived between header and records

        for r in self.__qsos__:
            yield (f'QSO: {r.band.rjust(5)} {r.mode} {r.date} {r.time} '
                   f'{r.own_call.ljust(13)} {r.sent_rst.rjust(3)} {r.sent_exch.ljust(6)} '
                   f'{r.call.ljust(13)} {r.rcvd_rst.rjust(3)} {r.rcvd_exch.ljust(6)} {r.tx}')

        yield 'END-OF-LOG:'

    @property
    def file_name(self) -> str:
        return f'{self.__contest_date__}_{self.__header__["CALLSIGN"]}-{self.__header__["CATEGORY-BAND"]}.cbr'

    @classmethod
    def valid_bands(cls) -> tuple[CategoryBand, ...]:
        return CategoryBand.B_ALL,

    @classmethod
    def valid_bands_list(cls) -> list[str]:
        return [b.name[2:] for b in cls.valid_bands()]

    @classmethod
    def valid_modes(cls) -> tuple[CategoryMode, ...]:
        return CategoryMode.MIXED,

    @classmethod
    def valid_modes_list(cls) -> list[str]:
        return [m.name for m in cls.valid_modes()]

    @classmethod
    def valid_power(cls) -> tuple[CategoryPower, ...]:
        return CategoryPower.HIGH, CategoryPower.LOW, CategoryPower.QRP

    @classmethod
    def valid_power_list(cls) -> list[str]:
        return [p.name for p in cls.valid_power()]

    @classmethod
    def descr_specific(cls) -> str:
        return 'Specific'

    @classmethod
    def is_single_day(cls) -> bool:
        return True


class RLPMultis:
    DOKS_RANGE = [f'K{i:02d}' for i in range(1, 57)]
    DOKS = [d for d in DOKS_RANGE if d not in ('K20', 'K22', 'K23', 'K35', 'K37', 'K49', 'K51')]
    DISTRICT_DOKS = ('AJWK', 'DVK', 'RP', 'YLK')
    DISTRICT_SPECIAL = ('DA0RP', 'DF0RLP', 'DF0RPJ', 'DK0RLP',
                        'DK0YLK', 'DL0K', 'DL0RP', 'DL0YLK', 'DM0K')
    VFDB_DOKS = ('Z11', 'Z22', 'Z74', 'Z77')


class RLPFALZAWLog(ContestLog):
    contest_name = 'RLP Aktivitätswoche'
    contest_year = '2025'
    contest_update = '2024-11-02'

    def __init__(self, callsign, name, club, address, email, locator,
                 band: CategoryBand, mode: CategoryMode,
                 pwr: CategoryPower = CategoryPower.HIGH,
                 cat_operator: CategoryOperator = CategoryOperator.SINGLE_OP,
                 assisted: CategoryAssisted = CategoryAssisted.NON_ASSISTED,
                 tx: CategoryTransmitter = CategoryTransmitter.ONE,
                 operators: list[str] = None, specific='', skip_id=False, skip_warn=False, logger=None):
        super().__init__(callsign, name, club, address, email, locator,
                         band, mode, pwr, cat_operator,
                         assisted, tx, operators, specific, skip_id, skip_warn, logger)

        self.__header__['CONTEST'] = 'RLP Aktivitaetswoche'

        self.__dok__ = specific

        self.__multis__: list[str] = []
        self.__district_calls__: list[str] = []

        self.__points_per_band__:dict[str, int] = {}

        self.__qsos_band__: list[str] = []  # QSO index: date, call, band
        self.__qsos_mode__: list[str] = []  # QSO index: date, call, mode

    @classmethod
    def is_single_day(cls) -> bool:
        return False

    def statistics(self) -> str:
        common_stats = (f'QSOs: {self.qsos}, Rated: {self.rated}, Points: {self.points}, '
                f'Multis: {self.multis}, Extra Multis: {self.district_calls}, '
                f'Claimed points: {self.claimed_points}')
        band_stats = [f'{b:>5s} {self.__points_per_band__[b]:>5d} points' for b in self.__points_per_band__]
        return common_stats + '\nStatistics per band:\n' + '\n'.join(band_stats)

    def build_record(self, adif_rec) -> CBRRecord:
        adif_rec['STX_STRING'] = self.__dok__.upper()
        rec = super().build_record(adif_rec)
        return rec

    @property
    def multis(self) -> int:
        return len(self.__multis__)

    @property
    def district_calls(self) -> int:
        return len(self.__district_calls__)

    @property
    def claimed_points(self) -> int:
        return self.points * (self.multis + self.district_calls)

    def process_points(self, rec: CBRRecord):
        try:
            qso_point = 1
            if rec.mode == 'CW':
                qso_point = 3
            elif rec.mode == 'PH':
                qso_point = 2

            if rec.band == BAND_MAP_CBR['23cm']:
                qso_point *= 2

            if rec.rcvd_exch == self.__dok__:
                qso_point = 0
                self.info(f'QSO with {rec.call} not rated: same DOK "{rec.rcvd_exch.upper()}"')
            else:
                qso_band = rec.date + rec.call + rec.band
                qso_mode = rec.date + rec.call + rec.mode

                if qso_band not in self.__qsos_band__ and qso_mode not in self.__qsos_mode__:
                    self.__qsos_band__.append(qso_band)
                    self.__qsos_mode__.append(qso_mode)
                    self.__rated__ += 1
                    if any((rec.rcvd_exch.upper() in RLPMultis.DOKS,
                            rec.rcvd_exch.upper() in RLPMultis.DISTRICT_DOKS + RLPMultis.VFDB_DOKS,
                            rec.rcvd_exch.upper() == 'NM')):
                        if rec.rcvd_exch not in self.__multis__:
                            self.__multis__.append(rec.rcvd_exch)
                        if (rec.call in RLPMultis.DISTRICT_SPECIAL and
                                rec.call not in self.__district_calls__):
                            self.__district_calls__.append(rec.call)
                    else:
                        self.warning(f'DOK not counted as multi "{rec.rcvd_exch.upper()}"')
                else:
                    qso_point = 0
                    self.info(f'QSO with {rec.call} not rated: band or mode twice at same day "{rec.date}"')

            self.__points__ += qso_point

            if BAND_FROM_CBR[rec.band] in self.__points_per_band__:
                self.__points_per_band__[BAND_FROM_CBR[rec.band]] += qso_point
            else:
                self.__points_per_band__[BAND_FROM_CBR[rec.band]] = qso_point

            self.__header__['CLAIMED-SCORE'] = self.claimed_points
        except Exception:
            self.exception()

    @property
    def file_name(self) -> str:
        return f'{self.__contest_date__}_{self.__header__["CALLSIGN"]}-{self.__header__["SPECIFIC"]}.cbr'

    @classmethod
    def valid_modes(cls) -> tuple[CategoryMode, ...]:
        return CategoryMode.MIXED, CategoryMode.CW, CategoryMode.SSB, CategoryMode.FM

    @classmethod
    def valid_bands(cls) -> tuple[CategoryBand, ...]:
        return (CategoryBand.B_ALL, CategoryBand.B_23CM, CategoryBand.B_432,
                CategoryBand.B_2M, CategoryBand.B_4M, CategoryBand.B_6M,
                CategoryBand.B_10M, CategoryBand.B_15M, CategoryBand.B_20M,
                CategoryBand.B_40M, CategoryBand.B_80M, CategoryBand.B_160M)

    @classmethod
    def descr_specific(cls) -> str:
        return 'DOK'


class RLPFALZABUKWLog(ContestLog):
    contest_name = 'RLP Aktivitätsabend UKW'
    contest_year = '2025'
    contest_update = '2024-12-16'

    def __init__(self, callsign, name, club, address, email, locator,
                 band: CategoryBand, mode: CategoryMode,
                 pwr: CategoryPower = CategoryPower.HIGH,
                 cat_operator: CategoryOperator = CategoryOperator.SINGLE_OP,
                 assisted: CategoryAssisted = CategoryAssisted.NON_ASSISTED,
                 tx: CategoryTransmitter = CategoryTransmitter.ONE,
                 operators: list[str] = None, specific='', skip_id=False, skip_warn=False, logger=None):
        super().__init__(callsign, name, club, address, email, locator,
                         band, mode, pwr, cat_operator,
                         assisted, tx, operators, specific, skip_id, skip_warn, logger)

        self.__header__['CONTEST'] = 'RLP Aktivitaetsabend UKW'

        self.__dok__ = specific

        self.__multis__ = []
        self.__district_calls__ = []

    def statistics(self) -> str:
        return (f'QSOs: {self.qsos}, Rated: {self.rated}, Points: {self.points}, '
                f'Multis: {self.multis}, Extra Multis: {self.district_calls}, '
                f'Claimed points: {self.claimed_points}')

    def build_record(self, adif_rec) -> CBRRecord:
        adif_rec['STX_STRING'] = f'{self.__dok__.upper()} {self.__header__["GRID-LOCATOR"].upper()}'
        rec = super().build_record(adif_rec)
        return rec

    @property
    def multis(self) -> int:
        return len(self.__multis__)

    @property
    def district_calls(self) -> int:
        return len(self.__district_calls__)

    @property
    def claimed_points(self) -> int:
        return self.points * (self.multis + self.district_calls)

    def process_points(self, rec: CBRRecord):
        try:
            qso_point = 1
            if rec.mode == 'CW':
                qso_point = 3
            elif rec.mode == 'PH':
                qso_point = 2

            rcvd_exch = rec.rcvd_exch.strip().upper().split(' ', maxsplit=1)
            if len(rcvd_exch) < 2:
                self.warning(
                    f'Received DOK or locator missing "{rec.rcvd_exch.upper()}"')
            else:
                if len(rcvd_exch[1]) != 6:
                    self.warning(
                        f'Received locator does not have 6 characters "{rcvd_exch[1]}"')
            rcvd_dok = rcvd_exch[0]

            if rcvd_dok == self.__dok__:
                qso_point = 0
            else:
                self.__rated__ += 1
                if any((rcvd_dok in RLPMultis.DOKS,
                        rcvd_dok in RLPMultis.DISTRICT_DOKS + RLPMultis.VFDB_DOKS,
                        rcvd_dok == 'NM')):
                    if rcvd_dok not in self.__multis__:
                        self.__multis__.append(rcvd_dok)
                    if (rec.call in RLPMultis.DISTRICT_SPECIAL and
                            rec.call not in self.__district_calls__):
                        self.__district_calls__.append(rec.call)
                else:
                    self.info(f'DOK not counted as multi "{rcvd_dok}"')

            self.__points__ += qso_point

            self.__header__['CLAIMED-SCORE'] = self.claimed_points
        except Exception:
            self.exception()

    @property
    def file_name(self) -> str:
        return f'{self.__contest_date__}_{self.__header__["CALLSIGN"]}-{self.__header__["SPECIFIC"]}-{self.__header__["CATEGORY-BAND"]}.cbr'

    @classmethod
    def valid_modes(cls) -> tuple[CategoryMode, ...]:
        return CategoryMode.MIXED, CategoryMode.CW, CategoryMode.SSB

    @classmethod
    def valid_bands(cls) -> tuple[CategoryBand, ...]:
        return CategoryBand.B_432, CategoryBand.B_2M

    @classmethod
    def descr_specific(cls) -> str:
        return 'DOK'


class RLPFALZABKWLog(ContestLog):
    contest_name = 'RLP Aktivitätsabend KW'
    contest_year = '2025'
    contest_update = '2024-12-16'

    def __init__(self, callsign, name, club, address, email, locator,
                 band: CategoryBand, mode: CategoryMode,
                 pwr: CategoryPower = CategoryPower.HIGH,
                 cat_operator: CategoryOperator = CategoryOperator.SINGLE_OP,
                 assisted: CategoryAssisted = CategoryAssisted.NON_ASSISTED,
                 tx: CategoryTransmitter = CategoryTransmitter.ONE,
                 operators: list[str] = None, specific='', skip_id=False, skip_warn=False, logger=None):
        super().__init__(callsign, name, club, address, email, locator,
                         band, mode, pwr, cat_operator,
                         assisted, tx, operators, specific, skip_id, skip_warn, logger)

        self.__header__['CONTEST'] = 'RLP Aktivitaetsabend KW'

        self.__dok__ = specific

        self.__multis__ = []
        self.__district_calls__ = []

    def statistics(self) -> str:
        return (f'QSOs: {self.qsos}, Rated: {self.rated}, Points: {self.points}, '
                f'Multis: {self.multis}, Extra Multis: {self.district_calls}, '
                f'Claimed points: {self.claimed_points}')

    def build_record(self, adif_rec) -> CBRRecord:
        adif_rec['STX_STRING'] = self.__dok__.upper()
        rec = super().build_record(adif_rec)
        return rec

    @property
    def multis(self) -> int:
        return len(self.__multis__)

    @property
    def district_calls(self) -> int:
        return len(self.__district_calls__)

    @property
    def claimed_points(self) -> int:
        return self.points * (self.multis + self.district_calls)

    def process_points(self, rec: CBRRecord):
        try:
            qso_point = 1
            if rec.mode == 'CW':
                qso_point = 3
            elif rec.mode == 'PH':
                qso_point = 2

            if rec.rcvd_exch == self.__dok__:
                qso_point = 0
            else:
                self.__rated__ += 1
                if any((rec.rcvd_exch.upper() in RLPMultis.DOKS,
                        rec.rcvd_exch.upper() in RLPMultis.DISTRICT_DOKS + RLPMultis.VFDB_DOKS,
                        rec.rcvd_exch.upper() == 'NM')):
                    if rec.rcvd_exch not in self.__multis__:
                        self.__multis__.append(rec.rcvd_exch)
                    if (rec.call in RLPMultis.DISTRICT_SPECIAL and
                            rec.call not in self.__district_calls__):
                        self.__district_calls__.append(rec.call)
                else:
                    self.info(f'DOK not counted as multi "{rec.rcvd_exch.upper()}"')

            self.__points__ += qso_point

            self.__header__['CLAIMED-SCORE'] = self.claimed_points
        except Exception:
            self.exception()

    @property
    def file_name(self) -> str:
        return f'{self.__contest_date__}_{self.__header__["CALLSIGN"]}-{self.__header__["SPECIFIC"]}-{self.__header__["CATEGORY-BAND"]}.cbr'

    @classmethod
    def valid_modes(cls) -> tuple[CategoryMode, ...]:
        return CategoryMode.MIXED, CategoryMode.CW, CategoryMode.SSB

    @classmethod
    def valid_bands(cls) -> tuple[CategoryBand, ...]:
        return CategoryBand.B_10M, CategoryBand.B_80M

    @classmethod
    def descr_specific(cls) -> str:
        return 'DOK'


class K32KurzUKWLog(ContestLog):
    contest_name = 'K32 FM-Kurzaktivität'
    contest_year = '2024'
    contest_update = '2024-10-16'

    def __init__(self, callsign, name, club, address, email, locator,
                 band: CategoryBand, mode: CategoryMode,
                 pwr: CategoryPower = CategoryPower.B,
                 cat_operator: CategoryOperator = CategoryOperator.SINGLE_OP,
                 assisted: CategoryAssisted = CategoryAssisted.NON_ASSISTED,
                 tx: CategoryTransmitter = CategoryTransmitter.ONE,
                 operators: list[str] = None, specific='', skip_id=False, skip_warn=False, logger=None):
        super().__init__(callsign, name, club, address, email, locator,
                         band, mode, pwr, cat_operator,
                         assisted, tx, operators, specific, skip_id, skip_warn, logger)

        self.__dok__ = specific

        self.__multis__ = []

        self.__xl_wb__: openpyxl.Workbook | None = None
        self.__out_path__ = ''

    def check_band(self, adif_rec: dict[str, str]) -> bool:
        if adif_rec['BAND'].lower() not in ('2m', '70cm'):
            self.warning(f'Band "{adif_rec["BAND"].lower()}" does not match with '
                         f'contest bands 2m / 70cm ')
            if self.__skip_warn__:
                return False
        return True

    def open_file(self, path: str = os.path.curdir):
        self.__out_path__ = path

        templ_path = os.path.join(os.path.split(__file__)[0], 'data/Logvorlage_V1_FM_K32.xlsx')
        self.__xl_wb__ = openpyxl.open(templ_path)
        self.__xl_wb__.properties.title = self.contest_name
        self.__xl_wb__.properties.description = self.__header__['CREATED-BY']
        self.__xl_wb__.properties.creator = self.__header__['NAME']

        xl_ws: Worksheet = self.__xl_wb__['Log']

        xl_ws['B3'] = self.__header__['CATEGORY-BAND'].lower()
        xl_ws['B4'] = self.__header__['GRID-LOCATOR']

        xl_ws['D1'] = self.__header__['SPECIFIC']
        xl_ws['D2'] = self.__header__['NAME']

        addr = self.__header__['ADDRESS'].split('\n', 1)
        xl_ws['D3'] = addr[0]
        xl_ws['D4'] = addr[1].replace('\n', ' ') if len(addr) > 1 else ''

        xl_ws['D5'] = self.__header__['EMAIL']

        xl_ws['B7'] = self.__header__['CALLSIGN']
        xl_ws['D7'] = self.__header__['CATEGORY-POWER']

    def statistics(self) -> str:
        return (f'QSOs: {self.qsos}, Rated: {self.rated}, Points: {self.points}, '
                f'Multis: {self.multis}, '
                f'Claimed points: {self.claimed_points}')

    def build_record(self, adif_rec) -> CBRRecord:
        if adif_rec['BAND'].upper() == self.__header__['CATEGORY-BAND']:
            adif_rec['STX_STRING'] = f'{self.__dok__.upper()},{self.__header__["CATEGORY-POWER"]}'
            rec = super().build_record(adif_rec)

            return rec

    def write_records(self):
        if self.__xl_wb__:
            xl_ws: Worksheet = self.__xl_wb__['Log']

            date = ''
            row = 10
            for rec in self.__qsos__:
                xl_ws[f'A{row}'] = f'{rec.time[:2]}:{rec.time[2:]}'
                xl_ws[f'B{row}'] = rec.call

                dok, pwr = rec.rcvd_exch.split(',')
                xl_ws[f'C{row}'] = dok.strip()
                xl_ws[f'D{row}'] = pwr.strip()

                date = rec.date
                row += 1

            xl_ws['B5'] = date
            row += 1
            ft = Font(bold=True)
            xl_ws[f'C{row}'].font = ft
            xl_ws[f'D{row}'].font = ft
            xl_ws[f'C{row}'] = 'vsl. Punkte'
            xl_ws[f'D{row}'] = self.claimed_points

    def close_file(self):
        if self.__xl_wb__:
            self.__xl_wb__.save(os.path.join(self.__out_path__, self.file_name))

    @property
    def multis(self) -> int:
        return len(self.__multis__)

    @property
    def claimed_points(self) -> int:
        return self.points * self.multis

    def process_points(self, rec: CBRRecord):
        try:
            r_dok, r_pwr = rec.rcvd_exch.split(',')
            r_dok = r_dok.strip()
            r_pwr = r_pwr.strip()
        except Exception:
            self.exception(
                f'Error on processing received exchange "{rec.rcvd_exch}" for {rec.call} at {rec.date} {rec.time}')

        try:
            qso_point = 2
            if r_pwr == self.__header__['CATEGORY-POWER'] and r_pwr == CategoryPower.A.name:
                qso_point = 3
            elif r_pwr == self.__header__['CATEGORY-POWER'] and r_pwr == CategoryPower.C.name:
                qso_point = 1

            self.__rated__ += 1

            if r_dok not in self.__multis__:
                self.__multis__.append(r_dok)

            self.__points__ += qso_point

            self.__header__['CLAIMED-SCORE'] = self.claimed_points
        except Exception:
            self.exception()

    @property
    def file_name(self) -> str:
        return f'{self.__contest_date__}_K32_KURZ_UKW_{self.__header__["CALLSIGN"]}_{self.__header__["CATEGORY-BAND"]}.xlsx'

    @classmethod
    def valid_modes(cls) -> tuple[CategoryMode, ...]:
        return CategoryMode.FM,

    @classmethod
    def valid_bands(cls) -> tuple[CategoryBand, ...]:
        return CategoryBand.B_2M, CategoryBand.B_70CM

    @classmethod
    def valid_power(cls) -> tuple[CategoryPower, ...]:
        return CategoryPower.A, CategoryPower.B, CategoryPower.C

    @classmethod
    def descr_specific(cls) -> str:
        return 'DOK'


CONTESTS: dict[str, Type[ContestLog]] = {
    'RL-PFALZ-AW': RLPFALZAWLog,
    'RL-PFALZ-AB.UKW': RLPFALZABUKWLog,
    'RL-PFALZ-AB.KW': RLPFALZABKWLog,
    'K32-KURZ-UKW': K32KurzUKWLog,
}

CONTEST_NAMES = dict(zip(CONTESTS.keys(), [c.contest_name for c in CONTESTS.values()]))
CONTEST_IDS = dict(zip([c.contest_name for c in CONTESTS.values()], CONTESTS.keys()))
