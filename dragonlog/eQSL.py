import re
import logging

import requests
from adif_file import adi

from .Logger import Logger


class EQSLCommunicationException(Exception):
    pass


class EQSLRequestException(Exception):
    pass


class EQSLLoginException(Exception):
    pass


class EQSLUserCallMatchException(Exception):
    pass


class EQSLQSODuplicateException(Exception):
    pass


class EQSLADIFFieldException(Exception):
    pass


class EQSL:
    required_fields = ('QSO_DATE', 'TIME_ON', 'CALL', 'MODE', 'BAND')
    fields = required_fields + ('FREQ', 'QSLMSG', 'RST_SENT', 'MY_GRIDSQUARE', 'PROP_MODE', 'SUBMODE')
    image_pattern = re.compile(r'.*<img src="(.*)" alt="" />.*')
    upl_res_pattern = re.compile(r' *([EWCIR][a-z]*:.*)<BR>')

    def __init__(self, program: str, logger: Logger):
        self.__program_str__ = program

        self.log = logging.getLogger('EQSL')
        self.log.addHandler(logger)
        self.log.setLevel(logger.loglevel)
        self.logger = logger
        self.log.debug('Initialising...')

    def upload_log(self, username: str, password: str, record: dict) -> bool:
        if not username or not password:
            raise EQSLLoginException('Username or password missing')

        self._check_fields_(record)

        record = record.copy()

        for field in list(record.keys()):  # Create list object due to changes to dict below
            if not field in self.fields:
                record.pop(field)

        record['ADIF_VER'] = '3.1.4'
        record['PROGRAMID'] = self.__program_str__

        # Skip header and remove linebreaks
        data = adi.dumps({'RECORDS': [record]}).replace('\n', ' ')

        params = {
            'ADIFData': 'QSL-Upload ' + data,
            'EQSL_USER': username,
            'EQSL_PSWD': password,
        }

        try:
            r = requests.get('https://www.eQSL.cc/qslcard/importADIF.cfm', params=params)
        except requests.exceptions.ConnectionError:
            raise EQSLCommunicationException(f'eQSL is not reachable')

        if r.status_code == 200:
            for res in re.findall(self.upl_res_pattern, r.text):
                if 'Error' in res:
                    if ('No match on eQSL_User/eQSL_Pswd' in res or
                            'Multiple accounts match eQSL_User/eQSL_Pswd' in res):
                        raise EQSLUserCallMatchException(res)
                    elif 'Missing eQSL_User' in res or 'Missing eQSL_Pswd' in res:
                        raise EQSLLoginException(res)
                    elif 'Missing ADIFData parameter' in res:
                        raise EQSLADIFFieldException(res)
                    else:
                        raise EQSLRequestException(res)
                elif 'Warning' in res:
                    if 'Bad record: Duplicate' in res:
                        raise EQSLQSODuplicateException(res)
                    else:
                        raise EQSLADIFFieldException(res)
                elif 'Caution' in res:
                    self.log.warning(f'eQSL result: {res}')
                elif 'Information' in res:
                    self.log.info(f'eQSL result: {res}')
                elif 'Result' in res:
                    self.log.debug(f'eQSL result: {res}')

            return True
        else:
            raise EQSLCommunicationException(f'eQSL error: HTTP-Error {r.status_code}')

    def _check_fields_(self, record: dict):
        for field in self.required_fields:
            if field not in record:
                raise EQSLADIFFieldException(field)

    def check_inbox(self, username: str, password: str, record: dict) -> str:
        if not username or not password:
            raise EQSLLoginException('Username or password missing')

        self._check_fields_(record)

        params = {
            'Username': username,
            'Password': password,
            'CallsignFrom': record['CALL'],
            'QSOYear': record['QSO_DATE'][:4],
            'QSOMonth': record['QSO_DATE'][4:6],
            'QSODay': record['QSO_DATE'][6:],
            'QSOHour': record['TIME_ON'][:2],
            'QSOMinute': record['TIME_ON'][2:4],
            'QSOBand': record['BAND'],
            'QSOMode': record['MODE'],
        }

        try:
            r = requests.get('https://www.eQSL.cc/qslcard/GeteQSL.cfm', params=params)
        except requests.exceptions.ConnectionError:
            raise EQSLCommunicationException(f'eQSL is not reachable')

        if r.status_code == 200:
            if r.text.strip().startswith('Error'):
                if ('No match on Username/Password for that QSO Date/Time' in r.text or
                        'overlapping accounts for that QSO Date/Time' in r.text):
                    raise EQSLUserCallMatchException(r.text.strip())
                elif ('User is Regular member but must be at least Silver to download mass eQSLs.' in r.text or
                      'User is Bronze member but must be at least Silver to download mass eQSLs.' in r.text or
                      'Not Authorized to download mass eQSLs.' in r.text):
                    raise EQSLLoginException(r.text.strip())
                else:
                    raise EQSLRequestException(r.text.strip())
            elif 'Variable PASSWORD is undefined.' in r.text:
                raise EQSLLoginException('Variable PASSWORD is undefined')
            else:
                url_part = re.findall(self.image_pattern, r.text)
                if url_part:
                    return 'https://www.eQSL.cc' + url_part[0]
                else:
                    return ''
        else:
            self.log.debug(f'Status code: {r.status_code}')
            raise EQSLCommunicationException(f'eQSL error: HTTP-Error {r.status_code}')

    @staticmethod
    def receive_qsl_card(url: str) -> bytes:
        if url:
            r = requests.get(url)

            if r.status_code == 200:
                return r.content
            else:
                raise EQSLCommunicationException(f'eQSL error: HTTP-Error {r.status_code}')
        else:
            return b''
