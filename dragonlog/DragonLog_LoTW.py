import os.path
import tempfile

import requests
from adif_file import adi


class LoTWCommunicationException(Exception):
    pass


class LoTWRequestException(Exception):
    pass


class LoTWLoginException(Exception):
    pass


class LoTWUserCallMatchException(Exception):
    pass


class LoTWQSODuplicateException(Exception):
    pass


class LoTWADIFFieldException(Exception):
    pass


class LoTW:
    required_fields = ('QSO_DATE', 'TIME_ON', 'CALL', 'MODE', 'BAND')
    fields = required_fields + ('FREQ', 'QSLMSG', 'RST_SENT', 'MY_GRIDSQUARE', 'STATION_CALLSIGN')

    def upload_log(self, password: str, doc: dict) -> bool:
        self._check_fields_(doc)

        # Export to tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            print(tmp_dir)
            tmp_file = os.path.join(tmp_dir, 'lotw_export.adi')
            adi.dump(tmp_file ,doc, 'ADIF Export by DragonLog')

            # Sign and Upload with TQSL

    def _check_fields_(self, doc: dict):
        for i, record in enumerate(doc['RECORDS']):
            for field in self.required_fields:
                if field not in record:
                    raise LoTWADIFFieldException(f'{field} in record #{i+1}')

    def check_inbox(self, username: str, password: str, record: dict) -> str:
        self._check_fields_(record)

        params = {
            'username': username,
            'password': password,
            'qso_callsing': record['CALL'],
            'qso_startdate': f"{record['QSO_DATE'][:4]}-{record['QSO_DATE'][4:6]}-{record['QSO_DATE'][6:8]}",
            'qso_starttime': f"{record['TIME_ON'][:2]}:{record['TIME_ON'][2:4]}:{record['TIME_ON'][4:6]}",
            'qso_band': record['BAND'],
            'qso_mode': record['MODE'],
        }

        r = requests.get('https://lotw.arrl.org/lotwuser/lotwreport.adi', params=params)

        if r.status_code == 200:
            if '<EOH>' in r.text:
                for qso in adi.loadi(r.text):
                    print(qso)
            else:
                raise LoTWRequestException(r.text.strip())
        else:
            raise LoTWCommunicationException(f'LoTW error: HTTP-Error {r.status_code}')
