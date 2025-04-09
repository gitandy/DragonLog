# DragonLog (c) 2025 by Andreas Schawo is licensed under CC BY-SA 4.0.
# To view a copy of this license, visit http://creativecommons.org/licenses/by-sa/4.0/

from .base import ContestLogEDI, CategoryMode, CategoryBand


class L33EinsteigerContest(ContestLogEDI):
    contest_name = 'L33 Einsteiger-Contest'
    contest_year = '2025'
    contest_update = '2025-04-06'

    @classmethod
    def valid_modes(cls) -> tuple[CategoryMode, ...]:
        return CategoryMode.FM,

    @classmethod
    def valid_bands(cls) -> tuple[CategoryBand, ...]:
        return CategoryBand.B_2M,

    @classmethod
    def descr_specific(cls) -> str:
        return 'DOK'
