import re
import os.path
import logging
import platform
import tempfile
import subprocess

import requests
from adif_file import adi
from PyQt6 import QtCore

from .Logger import Logger


class LoTWCommunicationException(Exception):
    pass


class LoTWRequestException(Exception):
    pass


class LoTWLoginException(Exception):
    pass


class LoTWNoRecordException(Exception):
    pass


class LoTWADIFFieldException(Exception):
    pass


class LoTW:
    required_fields = ('QSO_DATE', 'TIME_ON', 'CALL', 'MODE', 'BAND')
    fields = required_fields + ('FREQ', 'QSLMSG', 'RST_SENT', 'MY_GRIDSQUARE', 'STATION_CALLSIGN')
    REGEX_RECORDS = re.compile(r'(?:.*?<[eE][oO][hH]>)?\n*(.*?<[eE][oO][rR]>).*?', re.DOTALL)

    def __init__(self, logger: Logger):
        self.log = logging.getLogger('LoTW')
        self.log.addHandler(logger)
        self.log.setLevel(logger.loglevel)
        self.logger = logger
        self.log.debug('Initialising...')

    def upload_log(self, station: str, doc: dict, password: str = '') -> bool:
        self._check_fields_(doc)

        # Export to tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_file = os.path.join(tmp_dir, 'DragonLog_Export.adi')
            adi.dump(tmp_file, doc, 'ADIF Export by DragonLog')

            if platform.system() == 'Windows':
                tqsl_path = 'C:/Program Files (x86)/TrustedQSL/tqsl.exe'
            else:
                tqsl_path = 'tqsl'

            cmd = [tqsl_path,
                   '-d',  # Supress date range dialog
                   '-u',  # Directly upload
                   '-a', 'all',  # Sign all including already sent
                   '-f', 'ignore',  # Ignore QTH information
                   '-x',  # Batch mode
                   '-l', station,
                   tmp_file]
            if password:
                cmd.append('-p')
                cmd.append(password)

            res = subprocess.run(cmd, capture_output=True)
            match res.returncode:
                case 0:
                    self.log.debug('TQSL exited with success')
                    return True
                case 1:  # Will it be possible?
                    self.log.debug('TQSL canceled by user')
                case 2:
                    self.log.warning('Log rejected by LoTW')
                    raise LoTWRequestException
                case 3 | 4 | 5:
                    self.log.error(f'Local or server error: {res.returncode}')
                case 6 | 7:  # Should not occur on tempfile
                    self.log.error(f'Error for read/write on input/output file: {res.returncode}')
                case 8:  # Should never occur
                    self.log.warning('TQSL no QSOs were processed')
                case 9:
                    self.log.warning('TQSL some QSOs were already uploaded')
                    return True
                case 10:  # Should not occur due to tested syntax
                    self.log.error('TQSL command syntax error')
                case 11:
                    self.log.warning('LoTW Connection error or network unreachable')
                    raise LoTWCommunicationException()

        return False

    def _check_fields_(self, doc: dict):
        for i, record in enumerate(doc['RECORDS']):
            for field in self.required_fields:
                if field not in record:
                    raise LoTWADIFFieldException(f'{field} in record #{i + 1}')

    def check_inbox(self, username: str, password: str, record: dict) -> bool:
        self._check_fields_({'RECORDS': [record]})
        self.log.debug(f"Checking inbox for {record['CALL']} on {record['QSO_DATE']}")

        if not username or not password:
            raise LoTWLoginException('Missing username or password')

        qso_dt = QtCore.QDateTime.fromString(
            f"{record['QSO_DATE'][:4]}-{record['QSO_DATE'][4:6]}-{record['QSO_DATE'][6:8]} "
            f"{record['TIME_ON'][:2]}:{record['TIME_ON'][2:4]}",
            'yyyy-MM-dd hh:mm')
        start_dt = qso_dt.addSecs(-600)
        end_dt = qso_dt.addSecs(600)

        self.log.debug(f"Filter QSOs between {start_dt.toString('yyyy-MM-dd hh:mm')} and "
                       f"{end_dt.toString('yyyy-MM-dd hh:mm')}")

        params = {
            'login': username,
            'password': password,
            'qso_query': '1',
            'qso_callsing': record['CALL'],
            'qso_startdate': start_dt.date().toString('yyyy-MM-dd'),
            'qso_starttime': start_dt.time().toString('hh:mm'),
            'qso_enddate': end_dt.date().toString('yyyy-MM-dd'),
            'qso_endtime': end_dt.time().toString('hh:mm'),
            'qso_band': record['BAND'],
            'qso_mode': record['MODE'],
        }

        r = requests.get('https://lotw.arrl.org/lotwuser/lotwreport.adi', params=params)
        if r.status_code == 200:
            if r.text.strip().endswith('<APP_LoTW_EOF>'):
                records = re.findall(self.REGEX_RECORDS, r.text)
                if len(records) > 1:
                    raise LoTWRequestException('Too much search results')
                elif len(records) == 0:
                    raise LoTWNoRecordException('No search results')

                try:
                    doc = adi.loads(records[0].strip())

                    if doc['RECORDS'][0]['QSL_RCVD'] == 'Y':
                        return True
                    else:
                        return False
                except adi.TagDefinitionException as exc:
                    raise LoTWRequestException(exc)
            else:
                raise LoTWLoginException()
        else:
            raise LoTWCommunicationException(f'LoTW error: HTTP-Error {r.status_code}')
