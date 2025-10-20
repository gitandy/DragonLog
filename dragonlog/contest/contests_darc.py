# DragonLog (c) 2025 by Andreas Schawo is licensed under CC BY-SA 4.0.
# To view a copy of this license, visit http://creativecommons.org/licenses/by-sa/4.0/
"""Contains main DARC contests"""

from .base import (ContestLogCBR, ContestLogEDI, CBRRecord, Address, BandStatistics, BAND_FROM_CBR, ExchangeData,
                   CategoryMode, CategoryBand, CategoryPower, CategoryOperator, CategoryAssisted, CategoryTransmitter)


class DARCUKWFruehlingsContest(ContestLogEDI):
    contest_name = 'DARC UKW Frühlingswettbewerb'
    contest_year = '2025'
    contest_update = '2025-04-07'

    @classmethod
    def valid_modes(cls) -> tuple[CategoryMode, ...]:
        return CategoryMode.SSB, CategoryMode.CW, CategoryMode.FM

    @classmethod
    def valid_bands(cls) -> tuple[CategoryBand, ...]:
        return (CategoryBand.B_2M, CategoryBand.B_70CM, CategoryBand.B_23CM, CategoryBand.B_13CM,
                CategoryBand.B_9CM, CategoryBand.B_6CM, CategoryBand.B_3CM, CategoryBand.B_1_25CM,
                CategoryBand.B_6MM, CategoryBand.B_4MM, CategoryBand.B_2_5MM, CategoryBand.B_2MM, CategoryBand.B_1MM)

    @classmethod
    def descr_specific(cls) -> str:
        return 'DOK'

    @classmethod
    def valid_operator(cls) -> tuple[CategoryOperator, ...]:
        return CategoryOperator.SINGLE_OP, CategoryOperator.MULTI_OP, CategoryOperator.TRAINEE, CategoryOperator.CHECKLOG


class DARCUKWSommerFDContest(ContestLogEDI):
    contest_name = 'DARC UKW-Sommer-Fieldday'
    contest_year = '2025'
    contest_update = '2025-08-02'

    @classmethod
    def valid_modes(cls) -> tuple[CategoryMode, ...]:
        return CategoryMode.SSB, CategoryMode.CW, CategoryMode.FM

    @classmethod
    def valid_bands(cls) -> tuple[CategoryBand, ...]:
        return (CategoryBand.B_2M, CategoryBand.B_70CM,
                CategoryBand.B_23CM, CategoryBand.B_13CM, CategoryBand.B_9CM, CategoryBand.B_6CM)

    @classmethod
    def valid_operator(cls) -> tuple[CategoryOperator, ...]:
        return CategoryOperator.SINGLE_OP, CategoryOperator.TRAINEE, CategoryOperator.CHECKLOG


class DARCUKWContest(ContestLogEDI):
    contest_name = 'DARC UKW-Wettbewerb'
    contest_year = '2025'
    contest_update = '2025-04-07'

    @classmethod
    def valid_modes(cls) -> tuple[CategoryMode, ...]:
        return CategoryMode.SSB, CategoryMode.CW, CategoryMode.FM

    @classmethod
    def valid_bands(cls) -> tuple[CategoryBand, ...]:
        return (CategoryBand.B_2M, CategoryBand.B_70CM, CategoryBand.B_23CM, CategoryBand.B_13CM,
                CategoryBand.B_9CM, CategoryBand.B_6CM, CategoryBand.B_3CM, CategoryBand.B_1_25CM,
                CategoryBand.B_6MM, CategoryBand.B_4MM, CategoryBand.B_2_5MM, CategoryBand.B_2MM, CategoryBand.B_1MM)

    @classmethod
    def descr_specific(cls) -> str:
        return 'DOK'

    @classmethod
    def is_single_day(cls) -> bool:
        return False

    @classmethod
    def valid_power(cls) -> tuple[CategoryPower, ...]:
        return CategoryPower.NONE, CategoryPower.LOW

    @classmethod
    def valid_operator(cls) -> tuple[CategoryOperator, ...]:
        return CategoryOperator.SINGLE_OP, CategoryOperator.MULTI_OP, CategoryOperator.TRAINEE, CategoryOperator.CHECKLOG


class DARCOsterContest(ContestLogCBR):
    contest_name = 'DARC-Ostercontest'
    contest_year = '2025'
    contest_update = '2025-04-13'
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

        self.__band_multis__: dict[str, set[str]] = {}

    def build_record(self, adif_rec) -> CBRRecord:
        adif_rec['STX_STRING'] = self.__header__['SPECIFIC'].upper()
        rec = super().build_record(adif_rec)
        return rec

    def process_points(self, rec: CBRRecord):
        try:
            qso_point = 1

            self.__rated__ += 1
            band = BAND_FROM_CBR[rec.band]
            if band not in self.__band_multis__:
                self.__band_multis__[band] = set()

            if rec.rcvd_exch.upper() != 'NM':
                multi = 'DOK_' + rec.mode + rec.rcvd_exch.upper()
                if multi not in self.__band_multis__[band]:
                    self.__multis__.add(multi)
                self.__band_multis__[band].add(multi)
            else:
                self.info(f'DOK not counted as multi "{rec.rcvd_exch.upper()}"')

            if self.cty:
                pfx = self.cty.prefix(rec.call)
                if pfx:
                    multi = 'PFX_' + rec.mode + pfx  # Todo: store as multi2
                    if multi not in self.__band_multis__[band]:
                        self.__multis__.add(multi)
                    self.__band_multis__[band].add(multi)
            else:
                self.log.warning('Could not process prefix due to missing cty data')

            self.__points__ += qso_point

            if band in self.__stats__:
                self.__stats__[band].qsos += 1
                self.__stats__[band].rated += 1
                self.__stats__[band].points += qso_point
                self.__stats__[band].multis = len(self.__band_multis__[band])
            else:  # Todo: should already be initialised
                self.__stats__[band] = BandStatistics(1, 1, 1, len(self.__band_multis__[band]), 0, qso_point)

            self.__header__['CLAIMED-SCORE'] = str(self.claimed_points)
        except Exception:
            self.exception()

    @property
    def statistics(self) -> dict[str, BandStatistics]:
        qsos = 0
        rated = 0
        points = 0
        multis = 0
        claimed = 0
        for b in self.__stats__:
            self.__stats__[b].summary = self.__stats__[b].points * self.__stats__[b].multis
            qsos += self.__stats__[b].qsos
            rated += self.__stats__[b].rated
            points += self.__stats__[b].points
            multis += self.__stats__[b].multis
            claimed += self.__stats__[b].summary

        self.__stats__['Total'] = BandStatistics(qsos, rated, points, multis, 0, claimed)

        return self.__stats__

    @property
    def file_name(self) -> str:
        return f'{self.__contest_date__}_{self.__header__["CALLSIGN"]}-{self.__header__["SPECIFIC"]}-{self.__header__["CATEGORY-BAND"]}.cbr'

    @classmethod
    def valid_modes(cls) -> tuple[CategoryMode, ...]:
        return CategoryMode.SSB, CategoryMode.MIXED, CategoryMode.CW

    @classmethod
    def valid_bands(cls) -> tuple[CategoryBand, ...]:
        return CategoryBand.B_ALL, CategoryBand.B_80M, CategoryBand.B_40M

    @classmethod
    def descr_specific(cls) -> str:
        return 'DOK'

    @classmethod
    def needs_specific(cls) -> bool:
        return True

    @classmethod
    def valid_power(cls) -> tuple[CategoryPower, ...]:
        return CategoryPower.HIGH, CategoryPower.LOW

    @classmethod
    def valid_operator(cls) -> tuple[CategoryOperator, ...]:
        return CategoryOperator.SINGLE_OP, CategoryOperator.CHECKLOG

    @staticmethod
    def extract_exchange(exchange: str) -> ExchangeData | None:
        if exchange:
            return ExchangeData(darc_dok=exchange.strip())
        else:
            return None

    @staticmethod
    def prepare_exchange(exchange: ExchangeData):
        return f'{exchange.darc_dok}'


class DARCXMASContest(ContestLogCBR):
    contest_name = 'DARC Weihnachtscontest'
    contest_year = '2025'
    contest_update = '2025-08-29'
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

        self.__band_multis__: dict[str, set[str]] = {'80m': set(), '40m': set()}
        self.__band_multis2__: dict[str, set[str]] = {'80m': set(), '40m': set()}

    @classmethod
    def valid_modes(cls) -> tuple[CategoryMode, ...]:
        return CategoryMode.MIXED, CategoryMode.SSB, CategoryMode.CW

    @classmethod
    def valid_bands(cls) -> tuple[CategoryBand, ...]:
        return CategoryBand.B_ALL, CategoryBand.B_80M, CategoryBand.B_40M

    @classmethod
    def descr_specific(cls) -> str:
        return 'DOK'

    def process_points(self, rec: CBRRecord):
        # noinspection PyBroadException
        try:
            qso_point = 1

            self.__rated__ += 1
            band = BAND_FROM_CBR[rec.band]

            if rec.rcvd_exch.upper() != 'NM':
                self.__multis__.add(rec.rcvd_exch.upper())
                self.__band_multis__[band].add(rec.rcvd_exch.upper())
            else:
                self.info(f'DOK not counted as multi "{rec.rcvd_exch.upper()}"')

            if self.cty:
                pfx = self.cty.prefix(rec.call)
                if pfx:
                    self.__multis2__.add(pfx)
                    self.__band_multis2__[band].add(pfx)
            else:
                self.log.warning('Could not process prefix due to missing cty data')

            self.__points__ += qso_point

            self.__stats__[band].qsos += 1
            self.__stats__[band].rated += 1
            self.__stats__[band].points += qso_point
            self.__stats__[band].multis = len(self.__band_multis__[band])
            self.__stats__[band].multis2 = len(self.__band_multis2__[band])

            self.__header__['CLAIMED-SCORE'] = str(self.claimed_points)
        except Exception:
            self.exception()


class DARCCWAContest(DARCXMASContest):
    contest_name = 'DARC CW Ausbildungscontest'
    contest_year = '2025'
    contest_update = '2025-08-29'
    contest_exch_fmt = 'DOK'

    @classmethod
    def valid_modes(cls) -> tuple[CategoryMode, ...]:
        return CategoryMode.CW,

    @classmethod
    def valid_bands(cls) -> tuple[CategoryBand, ...]:
        return CategoryBand.B_80M,


class DARCWAGContest(ContestLogCBR):
    contest_name = 'DARC Worked All Germany Contest'
    contest_year = '2025'
    contest_update = '2025-10-15'
    contest_exch_fmt = 'DOK or Number'

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

        self.__multis_band__: dict[str, set] = dict(zip(self.valid_bands_list()[1:],
                                                        [set() for _ in range(len(self.valid_bands_list()[1:]))]))

    def build_record(self, adif_rec) -> CBRRecord:
        if self.own_cty_data.code.startswith('DL'):  # Use DOK as sent exchange
            adif_rec['STX_STRING'] = self.__header__['SPECIFIC'].upper()
        rec = super().build_record(adif_rec)
        return rec

    def process_points(self, rec: CBRRecord):
        try:
            band = BAND_FROM_CBR[rec.band]
            if band not in self.__stats__:
                self.error(f'Wrong band "{band}" for contest')
                return

            qso_point = 1
            if not self.own_cty_data.code.startswith('DL'):
                if rec.rcvd_exch.strip()[0].isalpha():  # german caller
                    qso_point = 3
                    self.__rated__ += 1
                    self.__multis__.add(rec.rcvd_exch.strip()[0])
                    self.__multis_band__[band].add(rec.rcvd_exch.strip()[0])
                else:  # non german caller
                    self.warning('QSO with non-german stations is not rated')
                    qso_point = 0
            else:  # german station
                self.__rated__ += 1
                call_cty = self.cty.country(rec.call)
                if rec.rcvd_exch.strip()[0].isalpha():  # german caller
                    self.__multis__.add(call_cty.code)
                    self.__multis_band__[band].add(call_cty.code)
                else:  # non german caller
                    if call_cty.continent != 'EU':
                        qso_point = 5
                    else:
                        qso_point = 3
                    self.__multis__.add(call_cty.code)
                    self.__multis_band__[band].add(call_cty.code)

            self.__points__ += qso_point

            # fill stats
            self.__stats__[band].qsos += 1
            self.__stats__[band].rated += 1 if qso_point else 0
            self.__stats__[band].points += qso_point
            self.__stats__[band].multis = len(self.__multis_band__[band])

            self.__header__['CLAIMED-SCORE'] = str(self.claimed_points)
        except Exception:
            self.exception()

    @classmethod
    def valid_modes(cls) -> tuple[CategoryMode, ...]:
        return CategoryMode.SSB, CategoryMode.MIXED, CategoryMode.CW

    @classmethod
    def valid_bands(cls) -> tuple[CategoryBand, ...]:
        return (CategoryBand.B_ALL, CategoryBand.B_80M, CategoryBand.B_40M,
                CategoryBand.B_20M, CategoryBand.B_15M, CategoryBand.B_10M)

    @classmethod
    def descr_specific(cls) -> str:
        return 'DOK'

    @classmethod
    def needs_specific(cls) -> bool:
        return True

    @classmethod
    def valid_operator(cls) -> tuple[CategoryOperator, ...]:
        return (CategoryOperator.SINGLE_OP, CategoryOperator.MULTI_OP,
                CategoryOperator.CHECKLOG, CategoryOperator.TRAINEE)

    @staticmethod
    def extract_exchange(exchange: str) -> ExchangeData | None:
        if type(exchange) is str and exchange.strip() and exchange.strip()[0].isalpha():
            return ExchangeData(darc_dok=exchange.strip())
        else:
            return None

    @staticmethod
    def prepare_exchange(exchange: ExchangeData):
        return f'{exchange.darc_dok}'

    @classmethod
    def is_single_day(cls) -> bool:
        """If the contest is on a single day"""
        return False
