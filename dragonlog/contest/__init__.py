# DragonLog (c) 2025 by Andreas Schawo is licensed under CC BY-SA 4.0.
# To view a copy of this license, visit http://creativecommons.org/licenses/by-sa/4.0/

from .base import ContestLog, ExchangeData, ContestLogCBR, ContestLogEDI
from .contests_darc import (DARCUKWContest, DARCUKWFruehlingsContest, DARCOsterContest, DARCUKWSommerFDContest,
                            DARCXMASContest, DARCCWAContest, DARCWAGContest)
from .contests_darc_rlp import RLPFALZAWLog, RLPFALZABKWLog, RLPFALZABUKWLog, K32KurzUKWLog
from .contests_darc_others import L33EinsteigerContest
from .contests_others import IARUHFWorldChampionshipContest, RussianDistrictAwardContest

CONTESTS: dict[str, type[ContestLog]] = {
    'DARC-WAG': DARCWAGContest,
    'DARC-UKW': DARCUKWContest,
    'DARC-UKW-FRUEHLING': DARCUKWFruehlingsContest,
    'DARC-UKW-SOMMERFD': DARCUKWSommerFDContest,
    'DARC-KW-OSTERN': DARCOsterContest,
    'DARC-XMAS': DARCXMASContest,
    'DARC-CWA': DARCCWAContest,
    'RL-PFALZ-AW': RLPFALZAWLog,
    'RL-PFALZ-AB.UKW': RLPFALZABUKWLog,
    'RL-PFALZ-AB.KW': RLPFALZABKWLog,
    'K32-KURZ-UKW': K32KurzUKWLog,
    'L33-EINSTEIGER': L33EinsteigerContest,
    'IARU-HF': IARUHFWorldChampionshipContest,
    'RDAC': RussianDistrictAwardContest,
    # Insert other contests above
    'KW-UNIVERSAL': ContestLogCBR,
    'UKW-UNIVERSAL': ContestLogEDI,
}

CONTEST_NAMES = dict(zip(CONTESTS.keys(), [c.contest_name for c in CONTESTS.values()]))
CONTEST_IDS = dict(zip([c.contest_name for c in CONTESTS.values()], CONTESTS.keys()))


def build_contest_list() -> str:
    """Build a contest list as Markdown"""

    text = '''
Available Contests
==================

The table shows all available contests with the last date the contest definition was updated.

The *Year* column shows the year the contest definition is targeted to. 
If it does not show the current year you should check for a program update.

The *Internal ID* is the ID which is imported or exported in ADIF format. 

The *Exch format* is the format you must use to type in the received exchange. 
If a separator is you can also use a blank or underscore instead of a comma.
The sent exchange is handled automatically.

| Contest name | Internal ID | Year | Updated | Exch format |
|--------------|-------------|------|---------|-------------|
'''

    for c in CONTESTS:
        cntst: type[ContestLog] = CONTESTS[c]
        text += f'| {cntst.contest_name} | {c} | ***{cntst.contest_year}*** | {cntst.contest_update} | {cntst.contest_exch_fmt} |\n'

    return text
