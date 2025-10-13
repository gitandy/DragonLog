# DragonLog (c) 2025 by Andreas Schawo is licensed under CC BY-SA 4.0.
# To view a copy of this license, visit http://creativecommons.org/licenses/by-sa/4.0/
"""Contains contests from DARC Distrikt K"""

import os

OPTION_OPENPYXL = False
try:
    # noinspection PyUnresolvedReferences
    import openpyxl
    # noinspection PyUnresolvedReferences
    from openpyxl.worksheet.worksheet import Worksheet
    # noinspection PyUnresolvedReferences
    from openpyxl.styles import Font

    OPTION_OPENPYXL = True
except ImportError:
    pass


class OpenPyXLUnavailableException(Exception):
    pass


from .base import (ContestLogCBR, CBRRecord, Address, BandStatistics, BAND_MAP_CBR, BAND_FROM_CBR,
                   CategoryMode, CategoryBand, CategoryPower, CategoryOperator, CategoryAssisted, CategoryTransmitter,
                   ExchangeData)


class RLPMultis:
    __DOKS_RANGE__ = [f'K{i:02d}' for i in range(1, 57)]
    DOKS = [d for d in __DOKS_RANGE__ if d not in ('K20', 'K22', 'K23', 'K35', 'K37', 'K49', 'K51')]
    DISTRICT_DOKS = ('AJWK', 'DVK', 'RP', 'YLK')
    DISTRICT_SPECIAL = ('DA0RP', 'DF0RLP', 'DF0RPJ', 'DK0RLP',
                        'DK0YLK', 'DL0K', 'DL0RP', 'DL0YLK', 'DM0K')
    VFDB_DOKS = ('Z11', 'Z22', 'Z74', 'Z77')


class RLPFALZAWLog(ContestLogCBR):
    contest_name = 'RLP Aktivitätswoche'
    contest_year = '2025'
    contest_update = '2025-01-05'
    contest_exch_fmt = 'DOK'

    def __init__(self, callsign: str, name: str, club: str, address: Address, email: str, locator: str,
                 band: type[CategoryBand], mode: type[CategoryMode],
                 pwr: type[CategoryPower] = CategoryPower.HIGH,
                 cat_operator: type[CategoryOperator] = CategoryOperator.SINGLE_OP,
                 assisted: type[CategoryAssisted] = CategoryAssisted.NON_ASSISTED,
                 tx: type[CategoryTransmitter] = CategoryTransmitter.ONE,
                 operators: list[str] = None, specific: str = '', skip_id: bool = False,
                 skip_warn: bool = False, logger=None, cty=None):
        super().__init__(callsign, name, club, address, email, locator,
                         band, mode, pwr, cat_operator,
                         assisted, tx, operators, specific, skip_id, skip_warn, logger, cty)

        self.__header__['CONTEST'] = 'RLP Aktivitaetswoche'

        self.__dok__ = specific

        self.__district_calls__: set[str] = set()

        self.__qsos_band__: list[str] = []  # QSO index: date, call, band
        self.__qsos_mode__: list[str] = []  # QSO index: date, call, mode

    @classmethod
    def is_single_day(cls) -> bool:
        return False

    def build_record(self, adif_rec) -> CBRRecord:
        adif_rec['STX_STRING'] = self.__dok__.upper()
        rec = super().build_record(adif_rec)
        return rec

    @property
    def district_calls(self) -> int:
        return len(self.__district_calls__)

    @property
    def multis(self) -> int:
        return (len(self.__multis__) if self.__multis__ else 1) + self.district_calls

    @property
    def claimed_points(self) -> int:
        return self.points * self.multis

    def process_points(self, rec: CBRRecord):
        try:
            rated = 1
            qso_point = 1
            if rec.mode == 'CW':
                qso_point = 3
            elif rec.mode == 'PH':
                qso_point = 2

            if rec.band == BAND_MAP_CBR['23cm']:
                qso_point *= 2

            if rec.rcvd_exch == self.__dok__:
                qso_point = 0
                rated = 0
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
                        self.__multis__.add(rec.rcvd_exch)
                        if rec.call in RLPMultis.DISTRICT_SPECIAL:
                            self.__district_calls__.add(rec.call)
                    else:
                        self.warning(f'DOK not counted as multi "{rec.rcvd_exch.upper()}"')
                else:
                    qso_point = 0
                    self.info(f'QSO with {rec.call} not rated: band or mode twice at same day "{rec.date}"')

            self.__points__ += qso_point

            if BAND_FROM_CBR[rec.band] in self.__stats__:
                self.__stats__[BAND_FROM_CBR[rec.band]].qsos += 1
                self.__stats__[BAND_FROM_CBR[rec.band]].rated += rated
                self.__stats__[BAND_FROM_CBR[rec.band]].points += qso_point
            else:
                self.__stats__[BAND_FROM_CBR[rec.band]] = BandStatistics(1, rated, qso_point, 1, 0, 1)

            self.__header__['CLAIMED-SCORE'] = str(self.claimed_points)
        except Exception:
            self.exception()

    @property
    def file_name(self) -> str:
        return f'{self.__contest_date__}_{self.__header__["CALLSIGN"]}-{self.__header__["SPECIFIC"]}.cbr'

    @classmethod
    def valid_modes(cls) -> tuple[CategoryMode, ...]:
        return CategoryMode.SSB, CategoryMode.MIXED, CategoryMode.CW, CategoryMode.FM

    @classmethod
    def valid_bands(cls) -> tuple[CategoryBand, ...]:
        return (CategoryBand.B_ALL, CategoryBand.B_160M, CategoryBand.B_80M,
                CategoryBand.B_40M, CategoryBand.B_20M, CategoryBand.B_15M,
                CategoryBand.B_10M, CategoryBand.B_6M, CategoryBand.B_4M,
                CategoryBand.B_2M, CategoryBand.B_70CM, CategoryBand.B_23CM)

    @classmethod
    def descr_specific(cls) -> str:
        return 'DOK'

    @classmethod
    def needs_specific(cls) -> bool:
        return True

    @staticmethod
    def extract_exchange(exchange: str) -> ExchangeData | None:
        if exchange:
            return ExchangeData(darc_dok=exchange.strip())
        else:
            return None

    @staticmethod
    def prepare_exchange(exchange: ExchangeData):
        return f'{exchange.darc_dok}'


class RLPFALZABUKWLog(ContestLogCBR):
    contest_name = 'RLP Aktivitätsabend UKW'
    contest_year = '2025'
    contest_update = '2025-05-08'
    contest_exch_fmt = 'DOK,Locator'

    def __init__(self, callsign: str, name: str, club: str, address: Address, email: str, locator: str,
                 band: type[CategoryBand], mode: type[CategoryMode],
                 pwr: type[CategoryPower] = CategoryPower.HIGH,
                 cat_operator: type[CategoryOperator] = CategoryOperator.SINGLE_OP,
                 assisted: type[CategoryAssisted] = CategoryAssisted.NON_ASSISTED,
                 tx: type[CategoryTransmitter] = CategoryTransmitter.ONE,
                 operators: list[str] = None, specific: str = '', skip_id: bool = False,
                 skip_warn: bool = False, logger=None, cty=None):
        super().__init__(callsign, name, club, address, email, locator,
                         band, mode, pwr, cat_operator,
                         assisted, tx, operators, specific, skip_id, skip_warn, logger, cty)

        self.__header__['CONTEST'] = 'RLP Aktivitaetsabend UKW'

        self.__dok__ = specific

        self.__district_calls__: set[str] = set()

    def build_record(self, adif_rec) -> CBRRecord:
        adif_rec['STX_STRING'] = f'{self.__dok__.upper()} {self.__header__["GRID-LOCATOR"].upper()}'
        rec = super().build_record(adif_rec)
        return rec

    @property
    def district_calls(self) -> int:
        return len(self.__district_calls__)

    @property
    def multis(self) -> int:
        return (len(self.__multis__) if self.__multis__ else 1) + self.district_calls

    def process_points(self, rec: CBRRecord):
        # noinspection PyBroadException
        try:
            qso_point = 1
            rated = 1
            if rec.mode == 'CW':
                qso_point = 3
            elif rec.mode == 'PH':
                qso_point = 2

            if ' ' in rec.rcvd_exch:
                rcvd_dok, rcvd_loc = rec.rcvd_exch.split(' ', maxsplit=1)
            else:
                self.warning(f'Received DOK or locator missing "{rec.rcvd_exch}"')
                return

            if len(rcvd_loc) != 6:
                self.warning(
                    f'Received locator does not have 6 characters "{rcvd_loc}"')
            if len(rcvd_loc) >= 4:
                self.__multis2__.add(rcvd_loc[:4])

            if rcvd_dok == self.__dok__:
                qso_point = 0
                rated = 0
                self.info(f'QSO with {rec.call} not rated: same DOK "{rcvd_dok}"')
            else:
                self.__rated__ += 1
                if any((rcvd_dok in RLPMultis.DOKS,
                        rcvd_dok in RLPMultis.DISTRICT_DOKS + RLPMultis.VFDB_DOKS,
                        rcvd_dok == 'NM')):
                    self.__multis__.add(rcvd_dok)
                    if rec.call in RLPMultis.DISTRICT_SPECIAL:
                        self.__district_calls__.add(rec.call)
                else:
                    self.info(f'DOK not counted as multi "{rcvd_dok}"')

            self.__points__ += qso_point

            if BAND_FROM_CBR[rec.band] in self.__stats__:
                self.__stats__[BAND_FROM_CBR[rec.band]].qsos += 1
                self.__stats__[BAND_FROM_CBR[rec.band]].rated += rated
                self.__stats__[BAND_FROM_CBR[rec.band]].points += qso_point
                self.__stats__[BAND_FROM_CBR[rec.band]].multis = self.multis + self.district_calls
                self.__stats__[BAND_FROM_CBR[rec.band]].multis2 = self.multis2
            else:
                self.__stats__[BAND_FROM_CBR[rec.band]] = BandStatistics(1, rated, qso_point, 1, 1, 1)

            self.__header__['CLAIMED-SCORE'] = str(self.claimed_points)
        except Exception:
            self.exception()

    def _serialize_cbr_rec_(self):
        """Serialize the single QSOs for CBR with justified fields for DOK and locator"""
        for r in self.__qsos__:
            dok, loc = r.sent_exch.split(' ', maxsplit=1)
            r_dok, r_loc = r.rcvd_exch.split(' ', maxsplit=1)
            yield (f'QSO: {r.band.rjust(5)} {r.mode} {r.date} {r.time} '
                   f'{r.own_call.ljust(13)} {r.sent_rst.rjust(3)} {dok.ljust(6)} {loc.ljust(6)} '
                   f'{r.call.ljust(13)} {r.rcvd_rst.rjust(3)} {r_dok.ljust(6)} {r_loc.ljust(6)} {r.tx}')

    @property
    def file_name(self) -> str:
        return f'{self.__contest_date__}_{self.__header__["CALLSIGN"]}-{self.__header__["SPECIFIC"]}-{self.__header__["CATEGORY-BAND"]}.cbr'

    @classmethod
    def valid_power(cls) -> tuple[CategoryPower, ...]:
        return CategoryPower.NONE,

    @classmethod
    def valid_modes(cls) -> tuple[CategoryMode, ...]:
        return CategoryMode.SSB, CategoryMode.MIXED, CategoryMode.CW

    @classmethod
    def valid_bands(cls) -> tuple[CategoryBand, ...]:
        return CategoryBand.B_2M, CategoryBand.B_70CM

    @classmethod
    def descr_specific(cls) -> str:
        return 'DOK'

    @classmethod
    def needs_specific(cls) -> bool:
        return True

    @staticmethod
    def extract_exchange(exchange: str) -> ExchangeData | None:
        exchange = exchange.upper().strip().replace(',', ' ').replace('_', ' ')
        if ' ' in exchange:
            r_dok, r_loc = exchange.split(' ', maxsplit=1)
            return ExchangeData(locator=r_loc.strip(), darc_dok=r_dok.strip())
        else:
            return None

    @staticmethod
    def prepare_exchange(exchange: ExchangeData):
        return f'{exchange.darc_dok},{exchange.locator}'


class RLPFALZABKWLog(ContestLogCBR):
    contest_name = 'RLP Aktivitätsabend KW'
    contest_year = '2025'
    contest_update = '2025-05-08'
    contest_exch_fmt = 'DOK'

    def __init__(self, callsign: str, name: str, club: str, address: Address, email: str, locator: str,
                 band: type[CategoryBand], mode: type[CategoryMode],
                 pwr: type[CategoryPower] = CategoryPower.HIGH,
                 cat_operator: type[CategoryOperator] = CategoryOperator.SINGLE_OP,
                 assisted: type[CategoryAssisted] = CategoryAssisted.NON_ASSISTED,
                 tx: type[CategoryTransmitter] = CategoryTransmitter.ONE,
                 operators: list[str] = None, specific: str = '', skip_id: bool = False,
                 skip_warn: bool = False, logger=None, cty=None):
        super().__init__(callsign, name, club, address, email, locator,
                         band, mode, pwr, cat_operator,
                         assisted, tx, operators, specific, skip_id, skip_warn, logger, cty)

        self.__header__['CONTEST'] = 'RLP Aktivitaetsabend KW'

        self.__dok__ = specific

        self.__district_calls__: set[str] = set()

    def build_record(self, adif_rec) -> CBRRecord:
        adif_rec['STX_STRING'] = self.__dok__.upper()
        rec = super().build_record(adif_rec)
        return rec

    @property
    def district_calls(self) -> int:
        return len(self.__district_calls__)

    @property
    def multis(self) -> int:
        return (len(self.__multis__) if self.__multis__ else 1) + self.district_calls

    def process_points(self, rec: CBRRecord):
        # noinspection PyBroadException
        try:
            qso_point = 1
            rated = 1
            if rec.mode == 'CW':
                qso_point = 3
            elif rec.mode == 'PH':
                qso_point = 2

            if rec.rcvd_exch == self.__dok__:
                qso_point = 0
                rated = 0
                self.info(f'QSO with {rec.call} not rated: same DOK "{rec.rcvd_exch.upper()}"')
            else:
                self.__rated__ += 1
                if any((rec.rcvd_exch.upper() in RLPMultis.DOKS,
                        rec.rcvd_exch.upper() in RLPMultis.DISTRICT_DOKS + RLPMultis.VFDB_DOKS,
                        rec.rcvd_exch.upper() == 'NM')):
                    self.__multis__.add(rec.rcvd_exch)
                    if rec.call in RLPMultis.DISTRICT_SPECIAL:
                        self.__district_calls__.add(rec.call)
                else:
                    self.info(f'DOK not counted as multi "{rec.rcvd_exch.upper()}"')

            self.__points__ += qso_point

            if BAND_FROM_CBR[rec.band] in self.__stats__:
                self.__stats__[BAND_FROM_CBR[rec.band]].qsos += 1
                self.__stats__[BAND_FROM_CBR[rec.band]].rated += rated
                self.__stats__[BAND_FROM_CBR[rec.band]].points += qso_point
            else:
                self.__stats__[BAND_FROM_CBR[rec.band]] = BandStatistics(1, rated, qso_point, 1, 0, qso_point)

            self.__header__['CLAIMED-SCORE'] = str(self.claimed_points)
        except Exception:
            self.exception()

    @property
    def file_name(self) -> str:
        return f'{self.__contest_date__}_{self.__header__["CALLSIGN"]}-{self.__header__["SPECIFIC"]}-{self.__header__["CATEGORY-BAND"]}.cbr'

    @classmethod
    def valid_power(cls) -> tuple[CategoryPower, ...]:
        return CategoryPower.NONE,

    @classmethod
    def valid_modes(cls) -> tuple[CategoryMode, ...]:
        return CategoryMode.SSB, CategoryMode.MIXED, CategoryMode.CW

    @classmethod
    def valid_bands(cls) -> tuple[CategoryBand, ...]:
        return CategoryBand.B_80M, CategoryBand.B_10M

    @classmethod
    def descr_specific(cls) -> str:
        return 'DOK'

    @classmethod
    def needs_specific(cls) -> bool:
        return True

    @staticmethod
    def extract_exchange(exchange: str) -> ExchangeData | None:
        if exchange:
            return ExchangeData(darc_dok=exchange.strip())
        else:
            return None

    @staticmethod
    def prepare_exchange(exchange: ExchangeData):
        return f'{exchange.darc_dok}'


class K32KurzUKWLog(ContestLogCBR):
    contest_name = 'K32 FM-Kurzaktivität'
    contest_year = '2025'
    contest_update = '2025-05-05'
    contest_exch_fmt = 'DOK,Class'

    def __init__(self, callsign: str, name: str, club: str, address: Address, email: str, locator: str,
                 band: type[CategoryBand], mode: type[CategoryMode],
                 pwr: type[CategoryPower] = CategoryPower.HIGH,
                 cat_operator: type[CategoryOperator] = CategoryOperator.SINGLE_OP,
                 assisted: type[CategoryAssisted] = CategoryAssisted.NON_ASSISTED,
                 tx: type[CategoryTransmitter] = CategoryTransmitter.ONE,
                 operators: list[str] = None, specific: str = '', skip_id: bool = False,
                 skip_warn: bool = False, logger=None, cty=None):
        super().__init__(callsign, name, club, address, email, locator,
                         band, mode, pwr, cat_operator,
                         assisted, tx, operators, specific, skip_id, skip_warn, logger, cty)

        self.__dok__ = specific

        self.__xl_wb__ = None
        self.__out_path__ = ''

    def check_band(self, adif_rec: dict[str, str]) -> bool:
        if adif_rec['BAND'].lower() not in ('2m', '70cm'):
            self.warning(f'Band "{adif_rec["BAND"].lower()}" does not match with '
                         f'contest bands 2m / 70cm ')
            if self.__skip_warn__:
                return False
        return True

    def open_file(self, path: str = os.path.curdir):
        if not OPTION_OPENPYXL:
            raise OpenPyXLUnavailableException

        self.__out_path__ = path

        templ_path = os.path.join(os.path.split(__file__)[0], 'data/Logvorlage_V1_FM_K32.xlsx')
        self.__xl_wb__ = openpyxl.open(templ_path)
        self.__xl_wb__.properties.title = self.contest_name
        self.__xl_wb__.properties.description = self.__header__['CREATED-BY']
        self.__xl_wb__.properties.creator = self.__header__['NAME']

        xl_ws: Worksheet = self.__xl_wb__['Log']

        xl_ws['B4'] = self.__header__['GRID-LOCATOR']

        xl_ws['D2'] = self.__header__['CALLSIGN']
        xl_ws['D3'] = self.__header__['SPECIFIC']
        xl_ws['D4'] = self.__header__['NAME']
        xl_ws['D5'] = self.__header__['EMAIL']

        xl_ws['D7'] = self.__header__['CATEGORY-POWER']

    def build_record(self, adif_rec) -> CBRRecord | None:
        if self.__header__['CATEGORY-BAND'] in ('all', adif_rec['BAND'].lower()):
            adif_rec['STX_STRING'] = f'{self.__dok__.upper()},{self.__header__["CATEGORY-POWER"]}'
            rec = super().build_record(adif_rec)
            return rec
        else:
            return None

    def write_records(self):
        if self.__xl_wb__:
            xl_ws: Worksheet = self.__xl_wb__['Log']

            date = ''
            row = 10
            for rec in self.__qsos__:
                xl_ws[f'A{row}'] = 2 if rec.band == '144' else 70
                xl_ws[f'B{row}'] = f'{rec.time[:2]}:{rec.time[2:]}'
                xl_ws[f'C{row}'] = rec.call

                dok, pwr = '?', '?'
                if ',' in rec.rcvd_exch:
                    dok, pwr = rec.rcvd_exch.split(',', maxsplit=1)
                elif ' ' in rec.rcvd_exch:
                    dok, pwr = rec.rcvd_exch.split(' ', maxsplit=1)
                xl_ws[f'D{row}'] = dok.strip().upper()
                xl_ws[f'E{row}'] = pwr.strip().upper()

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

    def process_points(self, rec: CBRRecord):
        if ' ' in rec.rcvd_exch:
            r_dok, r_pwr = rec.rcvd_exch.split(' ', maxsplit=1)
            r_dok = r_dok.strip()
            r_pwr = r_pwr.strip()
        else:
            self.warning(f'Received DOK or power class missing "{rec.rcvd_exch.upper()}"')
            return

        # noinspection PyBroadException
        try:
            qso_point = 2
            if r_pwr == self.__header__['CATEGORY-POWER'] and r_pwr == CategoryPower.A.name:
                qso_point = 3
            elif r_pwr != self.__header__['CATEGORY-POWER'] and r_pwr in (CategoryPower.A.name, CategoryPower.B.name):
                qso_point = 3
            elif r_pwr == self.__header__['CATEGORY-POWER'] and r_pwr == CategoryPower.C.name:
                qso_point = 1

            self.__rated__ += 1
            self.__multis__.add(r_dok)
            if self.__header__['SPECIFIC'] != 'K32' and r_dok == 'K32':
                self.__multis__.add('K32extra')
            self.__points__ += qso_point

            if BAND_FROM_CBR[rec.band] in self.__stats__:
                self.__stats__[BAND_FROM_CBR[rec.band]].qsos += 1
                self.__stats__[BAND_FROM_CBR[rec.band]].rated += 1
                self.__stats__[BAND_FROM_CBR[rec.band]].points += qso_point
                self.__stats__[BAND_FROM_CBR[rec.band]].multis = self.multis
            else:
                self.__stats__[BAND_FROM_CBR[rec.band]] = BandStatistics(1, 1, qso_point, 1, 0, 1)

            self.__header__['CLAIMED-SCORE'] = str(self.claimed_points)
        except Exception:
            self.exception()

    @property
    def file_name(self) -> str:
        return f'{self.__contest_date__}_K32_KURZ_UKW_{self.__header__["CALLSIGN"]}.xlsx'

    @classmethod
    def valid_modes(cls) -> tuple[CategoryMode, ...]:
        return CategoryMode.FM,

    @classmethod
    def valid_bands(cls) -> tuple[CategoryBand, ...]:
        return CategoryBand.B_ALL, CategoryBand.B_2M, CategoryBand.B_70CM

    @classmethod
    def valid_power(cls) -> tuple[CategoryPower, ...]:
        return CategoryPower.A, CategoryPower.B, CategoryPower.C

    @classmethod
    def descr_specific(cls) -> str:
        return 'DOK'

    @classmethod
    def needs_specific(cls) -> bool:
        return True

    @staticmethod
    def extract_exchange(exchange: str) -> ExchangeData | None:
        exchange = exchange.upper().strip().replace(',', ' ').replace('_', ' ')
        if ' ' in exchange:
            r_dok, r_pwr = exchange.split(' ', maxsplit=1)
            return ExchangeData(power=r_pwr.strip(), darc_dok=r_dok.strip())
        else:
            return None

    @staticmethod
    def prepare_exchange(exchange: ExchangeData):
        return f'{exchange.darc_dok},{exchange.power}'
