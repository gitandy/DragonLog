# DragonLog (c) 2025 by Andreas Schawo is licensed under CC BY-SA 4.0.
# To view a copy of this license, visit http://creativecommons.org/licenses/by-sa/4.0/
"""A local callbook for ham radio callsigns and associated data and contest call history"""

import logging
import sys
import csv
import json
import sqlite3
import datetime
from collections import namedtuple
from dataclasses import dataclass, fields, astuple, asdict
from enum import Enum, auto

from dragonlog.RegEx import check_call


def get_cur_dt() -> str:
    """Get current date/time independant of Python version"""
    if sys.version_info[0] == 3 and sys.version_info[1] < 11:
        # noinspection PyDeprecation
        return datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    return datetime.datetime.now(datetime.UTC).strftime('%Y-%m-%d %H:%M:%S')


# Local Callbook
@dataclass
class LocalCallbookData:
    """Callbook entry for a callsign"""
    name: str = ''
    locator: str = ''
    qth: str = ''
    qsl_via: str = ''
    qsl_bureau: str = 'N'
    qsl_direct: str = 'N'
    qsl_eqsl: str = 'N'
    qsl_lotw: str = 'N'
    darc_dok: str = ''


def adapt_callbook_data(cbd: LocalCallbookData) -> str:
    return json.dumps(asdict(cbd))


def convert_callbook_data(data: bytes) -> LocalCallbookData:
    data = json.loads(data.decode('utf8'))
    return LocalCallbookData(**data)


sqlite3.register_adapter(LocalCallbookData, adapt_callbook_data)
sqlite3.register_converter('CALLBOOKDATA', convert_callbook_data)


# Call history
@dataclass
class CallHistoryData:
    """Represents history data for a callsign"""
    locator: str = ''
    power_class: str = ''
    darc_dok: str = ''
    itu_zone: str = ''
    rda_number: str = ''


def adapt_history_data(chd: CallHistoryData) -> str:
    return json.dumps(asdict(chd))


def convert_history_data(data: bytes) -> CallHistoryData:
    data = json.loads(data.decode('utf8'))
    return CallHistoryData(**data)


sqlite3.register_adapter(CallHistoryData, adapt_history_data)
sqlite3.register_converter('CALLHISTORYDATA', convert_history_data)


class LocalCallbookExportError(Exception):
    pass


class LocalCallbookImportError(Exception):
    pass


class LocalCallbookDatabaseError(Exception):
    pass


class UpdateMode(Enum):
    Complement = auto()
    Overwrite = auto()
    Substitute = auto()


LocalCallbookResult = namedtuple('LocalCallbookResult',
                                 ('callsign', 'callbook_data'))

CallHistoryResult = namedtuple('CallHistoryResult',
                               ('contest', 'callsign', 'history_data', 'callbook_data'))


class LocalCallbook:
    __db_create_stmnt__ = '''CREATE TABLE IF NOT EXISTS "callbook" (
                                "callsign"  TEXT PRIMARY KEY NOT NULL,
                                "recorded"  NUMERIC NOT NULL,
                                "data" CALLBOOKDATA NOT NULL
                             );'''

    __db_create_view_stmnt_count__ = '''CREATE VIEW IF NOT EXISTS callbook_entries AS 
                                     SELECT COUNT(callsign) as entries FROM callbook'''

    __db_create_stmnt_hist__ = '''CREATE TABLE IF NOT EXISTS "history" (
                                "contest"    TEXT NOT NULL,
                                "callsign"  TEXT NOT NULL,
                                "recorded"  NUMERIC NOT NULL,
                                "data" CALLHISTORYDATA
                                );'''

    __db_create_idx_stmnt_hist__ = '''CREATE INDEX IF NOT EXISTS "call_history" ON "history" (
                                    "contest",
                                    "callsign"
                                );'''

    __db_create_view_stmnt_hist_count__ = '''CREATE VIEW IF NOT EXISTS history_entries AS 
                                     SELECT COUNT(contest) as entries, COUNT(DISTINCT contest) as contests FROM history;'''

    __db_create_view_stmnt_hist__ = '''CREATE VIEW IF NOT EXISTS history_callbook AS
                                    SELECT contest, history.callsign, history.recorded, history.data as history_data, 
                                           callbook.data as callbook_data FROM history 
                                    LEFT JOIN callbook 
                                    ON history.callsign == callbook.callsign;'''

    def __init__(self, db_filename: str, logger=None, csv_delimiter: str = ','):
        self.log = logging.getLogger(type(self).__name__)
        if logger:
            self.log.setLevel(logger.loglevel)
            self.log.addHandler(logger)
        self.log.debug('Initialising...')

        self.__csv_delimiter__ = csv_delimiter
        self.__new_db__ = False
        try:
            self.__db__ = sqlite3.connect(db_filename, detect_types=sqlite3.PARSE_DECLTYPES)
            self.log.info(f'Using callbook "{db_filename}"')
            self.__db_path__ = db_filename
            self._init_db_()
        except sqlite3.DatabaseError as exc:
            raise LocalCallbookDatabaseError(str(exc))

    def _init_db_(self):
        self.__db__.execute('PRAGMA user_version = 0xDF1A5C;')
        self.__db__.execute('PRAGMA application_id = 0xca1b004;')
        self.__db__.execute('PRAGMA temp_store = MEMORY;')
        self.__db__.execute('PRAGMA journal_mode = WAL;')
        self.__db__.execute('PRAGMA synchronous = NORMAL;')

        cur = self.__db__.execute('SELECT GROUP_CONCAT(NAME,",") as columns FROM PRAGMA_TABLE_INFO("callbook")')
        if not cur.fetchone()[0]:
            self.__new_db__ = True
            self.log.debug('Initialising table "callbook"...')
            self.__db__.execute(self.__db_create_stmnt__)
        self.__db__.execute(self.__db_create_view_stmnt_count__)

        cur = self.__db__.execute('SELECT GROUP_CONCAT(NAME,",") as columns FROM PRAGMA_TABLE_INFO("history")')
        if not cur.fetchone()[0]:
            self.__new_db__ = True
            self.log.debug('Initialising table "history"...')
            self.__db__.execute(self.__db_create_stmnt_hist__)
        self.__db__.execute(self.__db_create_idx_stmnt_hist__)
        self.__db__.execute(self.__db_create_view_stmnt_hist_count__)
        self.__db__.execute(self.__db_create_view_stmnt_hist__)

    @property
    def callbook_entries(self) -> int:
        """The number of entries in the callbook"""
        cur = self.__db__.execute('SELECT * FROM callbook_entries')
        return cur.fetchone()[0]

    @property
    def history_entries(self) -> tuple[int, int]:
        """The number of entries and contests in the history"""
        cur = self.__db__.execute('SELECT * FROM history_entries')
        return cur.fetchone()

    @property
    def path(self) -> str:
        """The path to the database"""
        return self.__db_path__

    @property
    def is_new(self) -> bool:
        """The database is new and may need some callbook entries"""
        return self.__new_db__

    def import_callbook(self, filename: str):
        self.log.info(f'Importing callbook from CSV "{filename}"...')
        try:
            with open(filename, encoding='utf-8') as cf:
                reader = csv.DictReader(cf, delimiter=self.__csv_delimiter__)
                d_fields = [f.name for f in fields(LocalCallbookData)]
                for hf in reader.fieldnames:
                    if hf not in ('callsign', 'recorded') and hf not in d_fields:
                        self.log.warning(f'Unsupported field "{hf}" in callbook import')
                for row in reader:
                    callsign = row.pop('callsign')
                    row.pop('recorded', None)
                    for f in tuple(row.keys()):
                        if not f in d_fields:
                            row.pop(f)
                    if row:
                        self.update_entry(callsign, LocalCallbookData(**row), UpdateMode.Substitute)
        except KeyError as exc:
            raise LocalCallbookImportError(f'Column {exc} is missing in callbook import') from None
        except OSError as exc:
            raise LocalCallbookImportError(str(exc)) from None

    def export_callbook(self, filename: str):
        self.log.info(f'Exporting to CSV "{filename}"...')
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as cf:
                writer = csv.writer(cf, delimiter=self.__csv_delimiter__)
                # Write header
                writer.writerow(['callsign', 'recorded'] + [f.name for f in fields(LocalCallbookData)])

                cur = self.__db__.execute('SELECT * FROM callbook '
                                          'ORDER BY callsign')
                row: tuple[str, str, LocalCallbookData]
                for row in cur.fetchall():
                    writer.writerow(row[:2] + astuple(row[2]))
        except OSError as exc:
            raise LocalCallbookExportError(str(exc)) from None

    def update_entry(self, callsign: str, data: LocalCallbookData, mode: UpdateMode = UpdateMode.Overwrite):
        """Stores or updates a set of callbook data for a callsign
        if an entry allready exists the existing data is used depending on the update mode
        :param callsign: the callsign to associate the data to
        :param data: the callbook date to store (existing data is complemented)
        :param mode: overwrite with new data, complement existing data, substitute completly with new data
        """
        callsign = callsign.upper()
        if mode != UpdateMode.Substitute:
            old_data = self.lookup(callsign)
            if old_data:
                old_data = asdict(old_data[1])
                data_dict = asdict(data)
                if mode == UpdateMode.Complement:
                    # Try to fill missing fields with new data
                    for f in old_data:
                        if not old_data[f]:
                            old_data[f] = data_dict[f]
                    data = LocalCallbookData(**old_data)
                else:
                    # Try to fill missing new fields with known data
                    for f in data_dict:
                        if not data_dict[f]:
                            data_dict[f] = old_data[f]
                    data = LocalCallbookData(**data_dict)

            self.log.info(f'Updating or adding {callsign}...')
            cur = self.__db__.execute('UPDATE callbook SET recorded=?, data=? '
                                      'WHERE callsign=?',
                                      (get_cur_dt(), data, callsign))
            if cur.rowcount < 1:
                self.__db__.execute('INSERT INTO callbook(callsign, recorded, data) VALUES(?,?,?)',
                                    (callsign, get_cur_dt(), data))
        else:
            self.log.info(f'Adding or replacing {callsign}...')
            self.__db__.execute('INSERT OR REPLACE INTO callbook(callsign, recorded, data) VALUES(?,?,?)',
                                (callsign, get_cur_dt(), data))

        self.__db__.commit()

    def import_history(self, filename: str):
        self.log.info(f'Importing history from CSV "{filename}"...')
        try:
            with open(filename, encoding='utf-8') as cf:
                reader = csv.DictReader(cf, delimiter=self.__csv_delimiter__)
                d_fields = [f.name for f in fields(CallHistoryData)]
                for hf in reader.fieldnames:
                    if hf not in ('contest', 'callsign', 'recorded') and hf not in d_fields:
                        self.log.warning(f'Unsupported field "{hf}" in history import')
                for row in reader:
                    contest = row.pop('contest')
                    callsign = row.pop('callsign')
                    row.pop('recorded', None)
                    for f in tuple(row.keys()):
                        if not f in d_fields:
                            row.pop(f)
                    if row:
                        self.update_history(contest, callsign, CallHistoryData(**row))
        except KeyError as exc:
            raise LocalCallbookImportError(f'Column {exc} is missing in history import') from None
        except OSError as exc:
            raise LocalCallbookImportError(str(exc)) from None

    def export_history(self, filename: str, contest: str = None):
        self.log.info(f'Exporting history to CSV "{filename}"...')
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as cf:
                writer = csv.writer(cf, delimiter=self.__csv_delimiter__)

                # Write header
                writer.writerow(['contest', 'callsign', 'recorded'] + [f.name for f in fields(CallHistoryData)])

                if contest:
                    cur = self.__db__.execute('SELECT * FROM history '
                                              'WHERE contest=? '
                                              'ORDER BY callsign', (contest,))
                else:
                    cur = self.__db__.execute('SELECT * FROM history '
                                              'ORDER BY contest, callsign')
                row: tuple[str, str, str, CallHistoryData]
                for row in cur.fetchall():
                    writer.writerow(row[:3] + astuple(row[3]))
        except OSError as exc:
            raise LocalCallbookExportError(str(exc))

    def update_history(self, contest: str, callsign: str, data: CallHistoryData):
        """Stores or updates a set of contest call history data
        Existing data sets are updated as whole
        :param contest: the contest to associate the data to
        :param callsign: the callsign to associate the data to
        :param data: the callbook date to store
        """
        callsign = callsign.upper()
        self.log.info(f'Inserting or updating {callsign} for {contest}...')
        cur = self.__db__.execute('UPDATE history SET recorded=?, data=? '
                                  'WHERE contest=? and callsign=?',
                                  (get_cur_dt(), data, contest, callsign))
        if cur.rowcount < 1:
            self.__db__.execute('INSERT INTO history(contest, callsign, recorded, data) '
                                'VALUES(?,?,?,?)',
                                (contest, callsign, get_cur_dt(), data))
        self.__db__.commit()

    def lookup(self, callsign: str, any_fix=False) -> LocalCallbookResult | None:
        """Searches for data for a callsign
        :param callsign: the callsing to search for
        :param any_fix: search for callsign with any prefix/suffix on no result
        :return: a tuple of callsign and data
        """
        callsign = callsign.upper()
        cur = self.__db__.execute('SELECT callsign, data FROM callbook '
                                  'WHERE callsign=? '
                                  'ORDER BY recorded DESC',
                                  (callsign,))

        res = cur.fetchone()
        if not res and any_fix:
            call_check = check_call(callsign)
            if call_check:
                callsign = call_check[1]
                self.log.debug(f'Searching for any suffix for {callsign}...')
                cur = self.__db__.execute('SELECT callsign, data FROM callbook '
                                          'WHERE callsign LIKE ? or callsign LIKE ? or callsign LIKE ? '
                                          'ORDER BY recorded DESC',
                                          (f'{callsign}/%', f'%/{callsign}', f'%/{callsign}/%'))
                res = cur.fetchone()

        return LocalCallbookResult(*res) if res else None

    def lookup_history(self, contest: str, callsign: str,
                       any_fix=False, any_contest=False) -> CallHistoryResult | None:
        """Searches for data for a callsign in a contest
        If any_suffix and any_contest are used together they are tried in that order
        :param contest: the contest to search for
        :param callsign: the callsing to search for
        :param any_fix: search for callsign with any prefix/suffix on no result
        :param any_contest: search for callsign in any contest on no result (returns latests result)
        :return: a tuple of contest, callsign, history data, callbook data (if available)
        """
        callsign = callsign.upper()
        cur = self.__db__.execute('SELECT contest, callsign, history_data, callbook_data FROM history_callbook '
                                  'WHERE contest=? and callsign=? '
                                  'ORDER BY recorded DESC',
                                  (contest, callsign))

        res = cur.fetchone()
        if not res and any_fix:
            self.log.debug('Searching history for any suffix...')
            cur = self.__db__.execute('SELECT contest, callsign, history_data, callbook_data FROM history_callbook '
                                      'WHERE contest=? and (callsign LIKE ? or callsign LIKE ? or callsign LIKE ?) '
                                      'ORDER BY recorded DESC',
                                      (contest, f'{callsign}/%', f'%/{callsign}', f'%/{callsign}/%'))
            res = cur.fetchone()

        if cur.rowcount < 1 and any_contest:
            self.log.debug('Searching history in any contest...')
            cur = self.__db__.execute('SELECT contest, callsign, history_data, callbook_data FROM history_callbook '
                                      'WHERE callsign=? '
                                      'ORDER BY recorded DESC',
                                      (callsign,))
            res = cur.fetchone()

        return CallHistoryResult(*res) if res else None

    def close(self):
        """Explicitly close the database after running a cleanup and optimisation"""
        self.log.info('Reducing and optimising database...')
        self.__db__.execute('VACUUM;')
        self.__db__.execute('PRAGMA optimize;')
        self.log.info('Closing database...')
        self.__db__.close()


__all__ = [LocalCallbook, LocalCallbookData, CallHistoryData,
           LocalCallbookExportError, LocalCallbookImportError, LocalCallbookDatabaseError]
