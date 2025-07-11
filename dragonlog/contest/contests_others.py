# DragonLog (c) 2025 by Andreas Schawo is licensed under CC BY-SA 4.0.
# To view a copy of this license, visit http://creativecommons.org/licenses/by-sa/4.0/
"""Contains other contests"""

from .base import (ContestLogCBR, CBRRecord, Address, BandStatistics, BAND_FROM_CBR, ExchangeData,
                   CategoryMode, CategoryBand, CategoryPower, CategoryOperator, CategoryAssisted, CategoryTransmitter)
from dragonlog.cty import CountryData, Country, CountryCodeNotFoundException


class IARUHFWorldChampionshipContest(ContestLogCBR):
    contest_name = 'IARU HF World Championship'
    contest_year = '2025'
    contest_update = '2025-07-08'
    contest_exch_fmt = 'ITU-Zone'

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

        self.cty: CountryData | None = params.get('cty', None)
        if not self.cty or type(self.cty) is not CountryData:
            self.cty = None
            self.log.error('Error with cty data')

        try:
            self.own_cty_data: Country = self.cty.country(callsign)
        except CountryCodeNotFoundException:
            self.log.error(f'Country data could not be found for your callsign "{callsign}"')
            self.own_cty_data: Country = Country(*([''] * 9))

        self.__multis_band__: dict[str, set] = dict(zip(self.valid_bands_list()[1:],
                                                        [set() for _ in range(len(self.valid_bands_list()[1:]))]))
        self.__multis2_band__: dict[str, set] = dict(zip(self.valid_bands_list()[1:],
                                                         [set() for _ in range(len(self.valid_bands_list()[1:]))]))

    def build_record(self, adif_rec) -> CBRRecord:
        adif_rec['STX_STRING'] = self.own_cty_data.itu
        rec = super().build_record(adif_rec)
        return rec

    def process_points(self, rec: CBRRecord):
        try:
            band = BAND_FROM_CBR[rec.band]
            if band not in self.__stats__:
                self.error(f'Wrong band "{band}" for contest')
                return

            call_cty = self.cty.country(rec.call)
            qso_point = 1
            self.__rated__ += 1

            if rec.rcvd_exch.strip().isdigit():
                self.__multis__.add(rec.rcvd_exch.strip())
                self.__multis_band__[band].add(rec.rcvd_exch.strip())

                if rec.rcvd_exch.strip() != self.own_cty_data.itu:
                    qso_point = 3
                    if call_cty.continent != self.own_cty_data.continent:
                        qso_point = 5
            else:
                self.__multis2__.add(rec.rcvd_exch.strip().upper())
                self.__multis2_band__[band].add(rec.rcvd_exch.strip().upper())

            self.__points__ += qso_point

            # fill stats
            self.__stats__[band].qsos += 1
            self.__stats__[band].rated += 1
            self.__stats__[band].points += qso_point
            self.__stats__[band].multis = len(self.__multis_band__[band])
            self.__stats__[band].multis2 = len(self.__multis2_band__[band])

            self.__header__['CLAIMED-SCORE'] = str(self.claimed_points)
        except Exception:
            self.exception()

    @property
    def statistics(self) -> dict[str, BandStatistics]:
        qsos = 0
        rated = 0
        points = 0
        multis = 0
        multis2 = 0
        for b in self.__stats__:
            self.__stats__[b].summary = self.__stats__[b].points * (
                    self.__stats__[b].multis + self.__stats__[b].multis2)
            qsos += self.__stats__[b].qsos
            rated += self.__stats__[b].rated
            points += self.__stats__[b].points
            multis += self.__stats__[b].multis
            multis2 += self.__stats__[b].multis2

        self.__stats__['Total'] = BandStatistics(qsos, rated, points, multis, multis2,
                                                 points * (multis + multis2))

        return self.__stats__

    @property
    def file_name(self) -> str:
        return f'{self.__contest_date__}_{self.__header__["CALLSIGN"]}-IARU_HF_Championship.cbr'

    @classmethod
    def valid_modes(cls) -> tuple[CategoryMode, ...]:
        return CategoryMode.MIXED, CategoryMode.CW, CategoryMode.SSB

    @classmethod
    def valid_bands(cls) -> tuple[CategoryBand, ...]:
        return (CategoryBand.B_ALL, CategoryBand.B_10M, CategoryBand.B_15M, CategoryBand.B_20M,
                CategoryBand.B_40M, CategoryBand.B_80M, CategoryBand.B_160M)

    @classmethod
    def is_single_day(cls) -> bool:
        return False

    @classmethod
    def valid_power(cls) -> tuple[CategoryPower, ...]:
        return CategoryPower.HIGH, CategoryPower.LOW, CategoryPower.QRP

    @classmethod
    def valid_operator(cls) -> tuple[CategoryOperator, ...]:
        return CategoryOperator.SINGLE, CategoryOperator.CHECKLOG

    @staticmethod
    def extract_exchange(exchange: str) -> ExchangeData | None:
        if exchange:
            return ExchangeData(itu_zone=exchange.strip())
        else:
            return None

    @staticmethod
    def prepare_exchange(exchange: ExchangeData):
        return f'{exchange.itu_zone}'
