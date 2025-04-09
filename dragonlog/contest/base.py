# DragonLog (c) 2023-2025 by Andreas Schawo is licensed under CC BY-SA 4.0.
# To view a copy of this license, visit http://creativecommons.org/licenses/by-sa/4.0/

import os
import re
import typing
from enum import Enum, auto
import logging
from dataclasses import dataclass

from dragonlog.RegEx import check_format, REGEX_CALL, REGEX_LOCATOR, REGEX_RSTFIELD
from dragonlog.distance import distance

# noinspection SpellCheckingInspection
MODE_MAP_CBR = {
    'CW': 'CW',
    'SSB': 'PH',
    'FM': 'FM',
    'RTTY': 'RY',
    'FT8': 'DG',
    'MFSK': 'DG',
}

MODE_MAP_EDI = {
    'UNKNOWN': 0,
    'SSB': 1,
    'PH': 1,
    'CW': 2,
    'SSB-CW': 3,
    'CB-SSB': 4,
    'AM': 5,
    'FM': 6,
    'RTTY ': 7,
    'RY': 7,
    'SSTV': 8,
    'ATV': 9,
}

BAND_MAP_CBR = {
    'all': 'ALL',
    '160m': '1800',
    '80m': '3500',
    '40m': '7000',
    '20m': '14000',
    '15m': '21000',
    '10m': '28000',
    '6m': '50',
    '4m': '70',
    '2m': '144',
    '1.25m': '222',
    '70cm': '432',
    '33cm': '902',
    '23cm': '1.2G',
    '13cm': '2.3G',
    '9cm': '3.4G',
    '6cm': '5.7G',
    '3cm': '10G',
    '1.25cm': '24G',
    '6mm': '47G',
    '4mm': '75G',
    '2.5mm': '122G',
    '2mm': '134G',
    '1mm': '241G',
    # 'submm': 'LIGHT',
}

BAND_MAP_EDI = {
    '6m': '50 MHz',
    '4m': '70 MHz',
    '2m': '144 MHz',
    '70cm': '432 MHz',
    '23cm': '1.3 GHz',
    '13cm': '2.3 GHz',
    '9cm': '3.4 GHz',
    '6cm': '5.7 GHz',
    '3cm': '10 GHz',
    '1.25cm': '24 GHz',
    '6mm': '47 GHz',
    '4mm': '75 GHz',
    '2.5mm': '120 GHz',
    '2mm': '144 GHz',
    '1mm': '248 GHz',
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


@dataclass
class EDIRecord(CBRRecord):
    dist: int


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
    B_1_25M = auto()
    B_70CM = auto()
    B_23CM = auto()
    B_13CM = auto()
    B_9CM = auto()
    B_6CM = auto()
    B_3CM = auto()
    B_1_25CM = auto()
    B_6MM = auto()
    B_4MM = auto()
    B_2_5MM = auto()
    B_2MM = auto()
    B_1MM = auto()
    B_SUBMM = auto()


class CategoryOperator(Enum):
    SINGLE = auto()
    MULTI = auto()
    CHECKLOG = auto()
    TRAINEE = auto()


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
    NONE = auto()


class CategoryAssisted(Enum):
    ASSISTED = auto()
    NON_ASSISTED = auto()


class CategoryTransmitter(Enum):
    ONE = auto()
    TWO = auto()
    LIMITED = auto()
    UNLIMITED = auto()
    SWL = auto()


@dataclass
class Address:
    street: str
    zip: str
    city: str
    country: str


@dataclass
class BandStatistics:
    qsos: int = 0
    rated: int = 0
    points: int = 0
    multis: int = 1
    summary: int = 0

    def values(self) -> tuple:
        return tuple(self.__dict__.values())


class ContestLog:
    contest_name = 'Contest'
    contest_year = '2025'
    contest_update = '2024-12-16'

    REGEX_TIME = re.compile(r'(([0-1][0-9])|(2[0-3]))([0-5][0-9])([0-5][0-9])?')
    REGEX_DATE = re.compile(r'([1-9][0-9]{3})((0[1-9])|(1[0-2]))((0[1-9])|([1-2][0-9])|(3[0-2]))')

    def __init__(self, callsign: str, name: str, club: str, address: Address, email: str, locator: str,
                 band: type[CategoryBand], mode: type[CategoryMode],
                 pwr: type[CategoryPower] = CategoryPower.HIGH,
                 cat_operator: type[CategoryOperator] = CategoryOperator.SINGLE,
                 assisted: type[CategoryAssisted] = CategoryAssisted.NON_ASSISTED,
                 tx: type[CategoryTransmitter] = CategoryTransmitter.ONE,
                 operators: list[str] = None, specific: str = '', skip_id: bool = False,
                 skip_warn: bool = False, logger=None, **params):

        self.log = logging.getLogger(type(self).__name__)
        if logger:
            self.log.setLevel(logger.loglevel)
            self.log.addHandler(logger)
        self.log.debug('Initialising...')

        self.__header__: dict[str, str] = {
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
        self.__multis__: set[str] = set()

        self.__stats__: dict[str, BandStatistics] = {}

        self.__skip_id__ = skip_id
        self.__skip_warn__ = skip_warn

        self.__contest_date__ = ''

        self.__out_file__ = None

    def __init_header__(self, callsign, name, club, address: Address, email, locator,
                        band: type[CategoryBand], mode: type[CategoryMode],
                        pwr: type[CategoryPower] = CategoryPower.HIGH,
                        cat_operator: type[CategoryOperator] = CategoryOperator.SINGLE,
                        assisted: type[CategoryAssisted] = CategoryAssisted.NON_ASSISTED,
                        tx: type[CategoryTransmitter] = CategoryTransmitter.ONE,
                        operators: list[str] = None, specific: str = ''):

        if not check_format(REGEX_CALL, callsign):
            self.log.error(f'Callsign "{callsign}" does not match call format')
        if locator and not check_format(REGEX_LOCATOR, locator):
            self.log.warning(f'Locator "{locator}" does not match locator format')

        self.__header__['CONTEST'] = self.contest_name
        self.__header__['CREATED-BY'] = 'ContestLog v0.1'
        self.__header__['CALLSIGN'] = callsign
        self.__header__['NAME'] = name
        self.__header__['CLUB'] = club
        self.__header__['ADDRESS'] = address.street
        self.__header__['ADDRESS-POSTALCODE'] = address.zip
        self.__header__['ADDRESS-CITY'] = address.city
        self.__header__['ADDRESS-COUNTRY'] = address.country
        self.__header__['EMAIL'] = email
        self.__header__['GRID-LOCATOR'] = locator
        self.__header__['OPERATORS'] = ' '.join(operators) if operators else callsign
        self.__header__['CATEGORY-OPERATOR'] = cat_operator.name
        self.__header__['CATEGORY-BAND'] = band.name[2:].replace('_', '.')
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
        if (adif_rec['BAND'] != self.__header__['CATEGORY-BAND'] and
                BAND_MAP_CBR[adif_rec['BAND'].lower()] != self.__header__['CATEGORY-BAND'].lower()):
            self.log.warning(f'QSO #{self.__qso_id__} band "{adif_rec["BAND"]}" does not match with '
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

                self.__header__['CLAIMED-SCORE'] = str(self.claimed_points)

                self.log.debug(self.summary())
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
                         adif_rec['STX_STRING'].upper() if 'STX_STRING' in adif_rec else str(adif_rec['STX']),
                         adif_rec['CALL'],
                         adif_rec['RST_RCVD'],
                         adif_rec['SRX_STRING'].upper() if 'SRX_STRING' in adif_rec else str(adif_rec['SRX']),
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

    @property
    def multis(self) -> int:
        return len(self.__multis__) if self.__multis__ else 1

    def process_points(self, rec: CBRRecord):
        """Place for calculating points and decision for rating a QSO
        Should be overwritten"""
        self.__points__ += 1
        self.__rated__ += 1

        if BAND_FROM_CBR[rec.band] in self.__stats__:
            self.__stats__[BAND_FROM_CBR[rec.band]].qsos += 1
            self.__stats__[BAND_FROM_CBR[rec.band]].rated += 1
            self.__stats__[BAND_FROM_CBR[rec.band]].points += 1
        else:
            self.__stats__[BAND_FROM_CBR[rec.band]] = BandStatistics(1, 1, 1, 1, 1)

    def summary(self) -> str:
        """Returns a statistic over the QSOs"""
        return (f'QSOs: {self.qsos}, Rated: {self.rated}, '
                f'Points: {self.points}, Multis: {self.multis}, '
                f'Claimed points: {self.claimed_points}')

    @property
    def statistics(self) -> dict[str, BandStatistics]:
        for b in self.__stats__:
            self.__stats__[b].multis = self.multis
            self.__stats__[b].summary = self.__stats__[b].points * self.multis

        self.__stats__['Total'] = BandStatistics(self.qsos, self.rated, self.points, self.multis, self.claimed_points)

        return self.__stats__

    def serialize_cbr(self):
        # CBR format from http://wwrof.org/cabrillo/

        yield 'START-OF-LOG: 3.0'

        for k in self.__header__:
            if k in ('ADDRESS', 'SOAPBOX') and self.__header__[k]:
                for l in self.__header__[k].split('\n'):
                    yield f'{k}: {l}'
            elif k == 'CATEGORY-BAND':
                yield f'CATEGORY-BAND: {BAND_MAP_CBR[self.__header__[k].lower()]}'
            elif self.__header__[k]:
                yield f'{k}: {self.__header__[k]}'

        yield ''  # Divide between header and records

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
        return [b.name[2:].lower().replace('_', '.') for b in cls.valid_bands()]

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
    def valid_operator(cls) -> tuple[CategoryOperator, ...]:
        return CategoryOperator.SINGLE, CategoryOperator.MULTI, CategoryOperator.CHECKLOG

    @classmethod
    def valid_operator_list(cls) -> list[str]:
        return [o.name for o in cls.valid_operator()]

    @classmethod
    def descr_specific(cls) -> str:
        return 'Specific'

    @classmethod
    def needs_specific(cls) -> bool:
        return False

    @classmethod
    def is_single_day(cls) -> bool:
        return True


class ContestLogEDI(ContestLog):
    contest_name = 'ContestEDI'
    contest_year = '2025'
    contest_update = '2025-04-06'

    def __init__(self, callsign: str, name: str, club: str, address: Address, email: str, locator: str,
                 band: type[CategoryBand], mode: type[CategoryMode],
                 pwr: type[CategoryPower] = CategoryPower.HIGH,
                 cat_operator: type[CategoryOperator] = CategoryOperator.SINGLE,
                 assisted: type[CategoryAssisted] = CategoryAssisted.NON_ASSISTED,
                 tx: type[CategoryTransmitter] = CategoryTransmitter.ONE,
                 operators: list[str] = None, specific: str = '', skip_id: bool = False,
                 skip_warn: bool = False, logger=None, **params):
        super().__init__(callsign, name, club, address, email, locator,
                         band, mode, pwr, cat_operator,
                         assisted, tx, operators, specific, skip_id, skip_warn, logger)

        self.__qsos__: list[EDIRecord] = []

        self.__from_date__ = params.get('from_date', '2001-01-01')
        self.__to_date__ = params.get('to_date', '2001-01-01')
        self.__qth__ = params.get('qth', '<QTH>')
        self.__radio__ = params.get('radio', '<RADIO>')
        self.__power__ = params.get('pwr_watts', '<POWER_IN_WATTS>')
        self.__antenna__ = params.get('antenna', '<ANTENNA>')
        self.__ant_height_ground__ = params.get('ant_height_ground', '<ABOVE_GROUND>')
        self.__ant_height_sea__ = params.get('ant_height_sea', '<ABOVE_SEA>')

        self.__dok__ = specific

        self.__calls__ = []
        self.__locators__ = []
        self.__codxc__ = ['', '', 0]

        self.__edi_file__: typing.TextIO = None

    def check_band(self, adif_rec: dict[str, str]) -> bool:
        if adif_rec['BAND'] != self.__header__['CATEGORY-BAND']:
            self.warning(
                f'Band "{adif_rec["BAND"]}" does not match with contest band {self.__header__["CATEGORY-BAND"]}')
            if self.__skip_warn__:
                return False
        return True

    def open_file(self, path: str = os.path.curdir):
        # EDI-Format from http://www.ok2kkw.com/ediformat.htm
        self.__edi_file__ = open(os.path.join(path, self.file_name), 'w')

        self.__edi_file__.write('[REG1TEST;1]\n')
        self.__edi_file__.write(f'TName={self.contest_name}\n')
        self.__edi_file__.write(f'TDate={self.__from_date__.replace("-", "")};{self.__to_date__.replace("-", "")}\n')

        # Operator
        self.__edi_file__.write(f'PCall={self.__header__["CALLSIGN"]}\n')
        self.__edi_file__.write(f'PWWLo={self.__header__["GRID-LOCATOR"].upper()}\n')
        self.__edi_file__.write(f'PExch={self.__header__["GRID-LOCATOR"].upper()}\n')
        self.__edi_file__.write(f'PAdr1={self.__qth__}\n')
        self.__edi_file__.write('PAdr2=\n')
        self.__edi_file__.write(f'PSect={self.__header__["CATEGORY-OPERATOR"]}\n')
        self.__edi_file__.write(f'PBand={BAND_MAP_EDI[self.__header__["CATEGORY-BAND"].lower()]}\n')
        self.__edi_file__.write(f'PClub={self.__header__["SPECIFIC"]}\n')

        # Responsible
        self.__edi_file__.write(f'RName={self.__header__["NAME"]}\n')
        self.__edi_file__.write(f'RCall={self.__header__["CALLSIGN"]}\n')

        addr = self.__header__['ADDRESS'].split('\n', 1)
        addr_2 = addr[1].replace('\n', ' ') if len(addr) > 1 else ''
        self.__edi_file__.write(f'RAdr1={addr[0]}\n')
        self.__edi_file__.write(f'RAdr2={addr_2}\n')

        self.__edi_file__.write(f'RPoCo={self.__header__["ADDRESS-POSTALCODE"]}\n')
        self.__edi_file__.write(f'RCity={self.__header__["ADDRESS-CITY"]}\n')
        self.__edi_file__.write(f'RCoun={self.__header__["ADDRESS-COUNTRY"]}\n')
        self.__edi_file__.write('RPhon=\n')
        self.__edi_file__.write(f'RHBBS={self.__header__["EMAIL"]}\n')

        # Operators
        self.__edi_file__.write(f'MOpe1={self.__header__["OPERATORS"]}\n')
        self.__edi_file__.write('MOpe2=\n')

        # Station
        self.__edi_file__.write(f'STXEq={self.__radio__}\n')
        self.__edi_file__.write(f'SPowe={self.__power__}\n')
        self.__edi_file__.write(f'SRXEq={self.__radio__}\n')
        self.__edi_file__.write(f'SAnte={self.__antenna__}\n')
        self.__edi_file__.write(f'SAntH={self.__ant_height_ground__};{self.__ant_height_sea__}\n')

    def summary(self) -> str:
        return (f'QSOs: {self.qsos}, Rated: {self.rated}, Points: {self.points}, '
                f'Claimed points: {self.claimed_points}')

    def build_record(self, adif_rec) -> EDIRecord | None:
        self.log.debug(adif_rec)

        if self.__header__['CATEGORY-BAND'] in ('ALL', adif_rec['BAND'].upper()):
            date = f'{adif_rec["QSO_DATE"][:4]}-{adif_rec["QSO_DATE"][4:6]}-{adif_rec["QSO_DATE"][6:8]}'
            if not self.__contest_date__:
                self.__contest_date__ = date

            srx_string = adif_rec['SRX_STRING'].replace(' ', ',', 1)
            _, rloc = srx_string.split(',')

            dist = 0
            try:
                loc = self.__header__['GRID-LOCATOR']
                dist = distance(loc if loc else adif_rec['MY_GRIDSQUARE'], rloc)
            except Exception as exc:
                self.exception(str(exc))

            if dist > int(self.__codxc__[2]):
                self.__codxc__ = [adif_rec['CALL'], rloc, str(dist)]

            if rloc.upper() not in self.__locators__:
                self.__locators__.append(rloc.upper())

            return EDIRecord(BAND_MAP_CBR[adif_rec['BAND'].lower()],
                             MODE_MAP_CBR[adif_rec['MODE']],
                             date,
                             adif_rec['TIME_ON'][:4],
                             adif_rec['STATION_CALLSIGN'],
                             adif_rec['RST_SENT'],
                             f'{adif_rec["STX"]:03d}',
                             adif_rec['CALL'],
                             adif_rec['RST_RCVD'],
                             srx_string,
                             '0',
                             dist
                             )

    def write_records(self):
        if self.__edi_file__:
            # Contest info
            self.__edi_file__.write(f'CQSOs={len(self.__qsos__)};1\n')
            self.__edi_file__.write(f'CQSOP={self.claimed_points}\n')
            self.__edi_file__.write(f'CWWLs={len(self.__locators__)};0;1\n')
            self.__edi_file__.write('CWWLB=0\n')
            self.__edi_file__.write('CExcs=0;0;1\n')
            self.__edi_file__.write('CExcB=0\n')
            self.__edi_file__.write('CDXCs=0;0;1\n')
            self.__edi_file__.write('CDXCB=0\n')
            self.__edi_file__.write(f'CToSc={self.claimed_points}\n')
            self.__edi_file__.write(f'CODXC={";".join(self.__codxc__)}\n')

            # Remarks
            self.__edi_file__.write('[Remarks]\n')
            if 'SOAPBOX' in self.__header__ and self.__header__['SOAPBOX'].strip():
                self.__edi_file__.write(self.__header__['SOAPBOX'].strip() + '\n')

            # Records
            self.__edi_file__.write(f'[QSORecords;{len(self.__qsos__)}]\n')
            calls = []
            locators = []

            for rec in self.__qsos__:
                rnr, rloc = rec.rcvd_exch.split(',')

                dup = False
                if rec.call not in calls:
                    calls.append(rec.call)
                else:
                    dup = True

                lnew = True
                if rloc.upper() not in locators:
                    locators.append(rloc.upper())
                else:
                    lnew = False

                edi_fields = [rec.date[2:].replace('-', ''),  # Date
                              rec.time[:4],  # Time
                              rec.call,  # Call
                              str(MODE_MAP_EDI[rec.mode]),  # Mode
                              rec.sent_rst,  # sent RST
                              rec.sent_exch,  # sent Exch
                              rec.rcvd_rst,  # rcvd RST
                              rnr,  # rcvd QSO nr
                              '',  # recvd Exch
                              rloc.upper(),  # Locator
                              str(rec.dist) if not dup else '0',  # QSO Points
                              '',  # New exch
                              'N' if lnew else '',  # New locator
                              '',  # New DXCC
                              '' if not dup else 'D'  # Duplicate QSO
                              ]
                self.__edi_file__.write(';'.join(edi_fields) + '\n')

    def close_file(self):
        if self.__edi_file__:
            self.__edi_file__.close()

    @property
    def claimed_points(self) -> int:
        return self.points

    def process_points(self, rec: EDIRecord):
        # noinspection PyBroadException
        try:
            rated = 1
            points = rec.dist
            if rec.call in self.__calls__:
                self.info('Duplicate QSO will not be rated')
                rated = 0
                points = 0
            else:
                self.__calls__.append(rec.call)
                self.__rated__ += 1
                self.__points__ += rec.dist

            if BAND_FROM_CBR[rec.band] in self.__stats__:
                self.__stats__[BAND_FROM_CBR[rec.band]].qsos += 1
                self.__stats__[BAND_FROM_CBR[rec.band]].rated += rated
                self.__stats__[BAND_FROM_CBR[rec.band]].points += points
            else:
                self.__stats__[BAND_FROM_CBR[rec.band]] = BandStatistics(1, rated, points, 1, 1)
        except Exception:
            self.exception()

    @property
    def file_name(self) -> str:
        return f'{self.__contest_date__}_{self.__header__["CALLSIGN"]}_{self.contest_name.replace(" ", "-")}.edi'

    @classmethod
    def valid_modes(cls) -> tuple[CategoryMode, ...]:
        return CategoryMode.MIXED,

    @classmethod
    def valid_bands(cls) -> tuple[CategoryBand, ...]:
        return CategoryBand.B_ALL,

    @classmethod
    def valid_power(cls) -> tuple[CategoryPower, ...]:
        return CategoryPower.NONE,
