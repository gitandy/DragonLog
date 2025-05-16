# DragonLog (c) 2025 by Andreas Schawo is licensed under CC BY-SA 4.0.
# To view a copy of this license, visit http://creativecommons.org/licenses/by-sa/4.0/
"""A local callbook for ham radio callsigna and associated data"""

import logging
import sys
import csv
import json
import sqlite3
import datetime
from dataclasses import dataclass, fields, astuple, asdict

from dragonlog.RegEx import check_call


def get_cur_dt() -> str:
    """Get current date/time independant of Python version"""
    if sys.version_info[0] == 3 and sys.version_info[1] < 11:
        # noinspection PyDeprecation
        return datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    return datetime.datetime.now(datetime.UTC).strftime('%Y-%m-%d %H:%M:%S')


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


# Register the adapter and converter
sqlite3.register_adapter(LocalCallbookData, adapt_callbook_data)
sqlite3.register_converter('CALLBOOKDATA', convert_callbook_data)


class LocalCallbookExportError(Exception):
    pass


class LocalCallbookImportError(Exception):
    pass


class LocalCallbookDatabaseError(Exception):
    pass


class LocalCallbook:
    __db_create_stmnt__ = '''CREATE TABLE IF NOT EXISTS "callbook" (
                                "callsign"  TEXT PRIMARY KEY NOT NULL,
                                "recorded"  NUMERIC NOT NULL,
                                "data" CALLBOOKDATA NOT NULL
                             );'''

    __db_create_idx_stmnt__ = '''CREATE INDEX IF NOT EXISTS "callsign" ON "callbook" (
                                    "callsign"
                                 )'''

    __db_create_view_stmnt__ = '''CREATE VIEW IF NOT EXISTS callbook_entries AS 
                                     SELECT COUNT(callsign) as entries FROM callbook'''

    def __init__(self, db_filename: str, logger=None):
        self.log = logging.getLogger(type(self).__name__)
        if logger:
            self.log.setLevel(logger.loglevel)
            self.log.addHandler(logger)
        self.log.debug('Initialising...')

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
            self.log.debug('Initialising database...')
            self.__db__.execute(self.__db_create_stmnt__)
            self.__db__.execute(self.__db_create_idx_stmnt__)

        self.__db__.execute(self.__db_create_view_stmnt__)

    @property
    def callbook_entries(self) -> int:
        """The number of entries in th callbook"""
        cur = self.__db__.execute('SELECT * FROM callbook_entries')
        return cur.fetchone()[0]

    @property
    def path(self) -> str:
        """The path to the database"""
        return self.__db_path__

    @property
    def is_new(self) -> bool:
        """The database is new and may need some callbook entries"""
        return self.__new_db__

    def import_from_csv(self, filename: str):
        self.log.info(f'Importing from CSV "{filename}"...')

        try:
            with open(filename, encoding='utf-8') as cf:
                reader = csv.DictReader(cf)
                for row in reader:
                    data = []
                    for f in fields(LocalCallbookData):
                        data.append(row.get(f, ''))
                    self.add_entry(row['callsign'],
                                   LocalCallbookData(*data))
        except KeyError as exc:
            raise LocalCallbookImportError(str(exc))
        except OSError as exc:
            raise LocalCallbookImportError(str(exc))

    def export_to_csv(self, filename: str):
        self.log.info(f'Exporting to CSV "{filename}"...')

        try:
            with open(filename, 'w', newline='', encoding='utf-8') as cf:
                writer = csv.writer(cf)
                # Write header
                writer.writerow(['callsign', 'recorded'] + [f.name for f in fields(LocalCallbookData)])

                cur = self.__db__.execute('SELECT * FROM callbook '
                                          'ORDER BY callsign')
                row: tuple[str, str, LocalCallbookData]
                for row in cur.fetchall():
                    writer.writerow(row[:2] + astuple(row[2]))
        except OSError as exc:
            raise LocalCallbookExportError(str(exc))

    def add_entry(self, callsign: str, data: LocalCallbookData, no_commit=False):
        """Stores a set of callbook data for a callsign
        if an entry allready exists the existing data is used to fill gaps in the newly provided data
        :param callsign: the callsing to search for
        :param data: the callbook date to store
        """
        callsign = callsign.upper()
        old_data = self.lookup(callsign)
        if old_data:
            # Try to fill missing fields with known data
            old_data = asdict(old_data[1])
            data_dict = asdict(data)
            for f in data_dict:
                if not data_dict[f]:
                    data_dict[f] = old_data[f]
            data = LocalCallbookData(**data_dict)

            # Update data set
            self.log.info(f'Updating {callsign}...')
            self.__db__.execute('UPDATE callbook SET recorded=?, data=? '
                                'WHERE callsign=?',
                                (get_cur_dt(), data, callsign))
        else:
            self.log.info(f'Adding {callsign}...')
            self.__db__.execute('INSERT INTO callbook(callsign, recorded, data) VALUES(?,?,?)',
                                (callsign, get_cur_dt(), data))

        if no_commit:
            return

        self.__db__.commit()

    def lookup(self, callsign: str, any_fix=False) -> tuple[str, LocalCallbookData] | None:
        """Searches for data for a callsign
        :param callsign: the callsing to search for
        :param any_fix: search for callsign with any prefix/suffix on no result
        """
        callsign = callsign.upper()
        cur = self.__db__.execute('SELECT callsign, data FROM callbook '
                                  'WHERE callsign=? '
                                  'ORDER BY recorded DESC',
                                  (callsign,))

        res = cur.fetchone()
        if not res and any_fix:
            _, callsign, _ = check_call(callsign)
            self.log.debug(f'Searching for any suffix for {callsign}...')
            cur = self.__db__.execute('SELECT callsign, data FROM callbook '
                                      'WHERE callsign LIKE ? or callsign LIKE ? or callsign LIKE ? '
                                      'ORDER BY recorded DESC',
                                      (f'{callsign}/%', f'%/{callsign}', f'%/{callsign}/%'))
            res = cur.fetchone()

        return res

    def close(self):
        self.log.info('Reducing and optimising database...')
        self.__db__.execute('VACUUM;')
        self.__db__.execute('PRAGMA optimize;')
        self.log.info('Closing database...')
        self.__db__.close()


__all__ = [LocalCallbook, LocalCallbookData, LocalCallbookExportError, LocalCallbookImportError]
