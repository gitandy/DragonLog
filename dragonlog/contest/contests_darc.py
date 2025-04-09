# DragonLog (c) 2025 by Andreas Schawo is licensed under CC BY-SA 4.0.
# To view a copy of this license, visit http://creativecommons.org/licenses/by-sa/4.0/

from .base import ContestLogEDI, CategoryMode, CategoryBand, CategoryPower, CategoryOperator

class DARCUKWFruehlingsContest(ContestLogEDI):
    contest_name = 'DARC UKW Frühlingswettbewerb'
    contest_year = '2025'
    contest_update = '2025-04-07'

    @classmethod
    def valid_modes(cls) -> tuple[CategoryMode, ...]:
        return CategoryMode.FM, CategoryMode.SSB, CategoryMode.CW

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
        return CategoryOperator.SINGLE, CategoryOperator.MULTI, CategoryOperator.TRAINEE, CategoryOperator.CHECKLOG


class DARCUKWContest(ContestLogEDI):
    contest_name = 'DARC UKW-Wettbewerb'
    contest_year = '2025'
    contest_update = '2025-04-07'

    @classmethod
    def valid_modes(cls) -> tuple[CategoryMode, ...]:
        return CategoryMode.FM, CategoryMode.SSB, CategoryMode.CW

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
        return CategoryOperator.SINGLE, CategoryOperator.MULTI, CategoryOperator.TRAINEE, CategoryOperator.CHECKLOG
