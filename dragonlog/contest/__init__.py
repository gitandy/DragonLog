# DragonLog (c) 2025 by Andreas Schawo is licensed under CC BY-SA 4.0.
# To view a copy of this license, visit http://creativecommons.org/licenses/by-sa/4.0/

from .base import ContestLog
from .contests_darc import DARCUKWContest, DARCUKWFruehlingsContest, DARCOsterContest
from .contests_darc_rlp import RLPFALZAWLog, RLPFALZABKWLog, RLPFALZABUKWLog, K32KurzUKWLog
from .contests_darc_others import L33EinsteigerContest

CONTESTS: dict[str, type[ContestLog]] = {
    'DARC-UKW': DARCUKWContest,
    'DARC-UKW-FRUEHLING': DARCUKWFruehlingsContest,
    'DARC-KW-OSTERN': DARCOsterContest,
    'RL-PFALZ-AW': RLPFALZAWLog,
    'RL-PFALZ-AB.UKW': RLPFALZABUKWLog,
    'RL-PFALZ-AB.KW': RLPFALZABKWLog,
    'K32-KURZ-UKW': K32KurzUKWLog,
    'L33-EINSTEIGER': L33EinsteigerContest,
}

CONTEST_NAMES = dict(zip(CONTESTS.keys(), [c.contest_name for c in CONTESTS.values()]))
CONTEST_IDS = dict(zip([c.contest_name for c in CONTESTS.values()], CONTESTS.keys()))
