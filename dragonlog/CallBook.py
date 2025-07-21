# DragonLog (c) 2023 by Andreas Schawo is licensed under CC BY-SA 4.0.
# To view a copy of this license, visit http://creativecommons.org/licenses/by-sa/4.0/

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

import requests
import xmltodict
from adif_file import adi

from .Logger import Logger


class CallBookType(Enum):
    HamQTH = 'HamQTH.com'
    QRZCQ = 'QRZCQ.com'
    QRZ = 'QRZ.com'


@dataclass
class CallBookData:
    callsign: str
    nickname: str
    locator: str
    qth: str
    qsl_via: str
    qsl_bureau: bool
    qsl_direct: bool
    qsl_eqsl: bool
    qsl_lotw: bool
    darc_dok: str


class CommunicationException(Exception):
    pass


class RequestException(Exception):
    pass


class LoginException(Exception):
    pass


class SessionExpiredException(Exception):
    pass


class QSORejectedException(Exception):
    pass


class MissingADIFFieldException(Exception):
    pass


class CallsignNotFoundException(Exception):
    pass


class AbstractCallBook(ABC):
    """Standardised interface to access diffrent callbook services

    :param logger: the application log
    :param prog_name: the calling programs name"""

    def __init__(self, logger: Logger, prog_name: str):
        self.__program_str__ = prog_name
        self.__session__: str = ''

        self.log = logging.getLogger(type(self).__name__)
        self.log.setLevel(logger.loglevel)
        self.log.addHandler(logger)
        self.log.debug('Initialising...')

    @property
    @abstractmethod
    def required_fields(self) -> tuple:
        """A list of required fields to create a logbook entry"""
        pass

    @property
    @abstractmethod
    def __url__(self) -> str:
        pass

    def _get_(self, params: dict) -> dict:
        r = requests.get(self.__url__, params=params)

        if r.status_code == 200:
            return xmltodict.parse(r.text)
        else:
            raise CommunicationException(f'{self.callbook_type.name} error: HTTP-Error {r.status_code}')

    @property
    @abstractmethod
    def callbook_type(self) -> CallBookType:
        """The type of the callbook"""
        pass

    @abstractmethod
    def __login__(self, username: str, password: str) -> str:
        pass

    def login(self, username: str, password: str):
        """Login and retreive a session key
        :param username: the username used with this service
        :param password: the password used with this service"""
        if not username or not password:
            raise LoginException('Username or password missing')

        self.__session__ = self.__login__(username, password)

    @property
    def is_loggedin(self) -> bool:
        """Check if already logged in"""
        return bool(self.__session__)

    @abstractmethod
    def __get_dataset__(self, callsign: str):
        pass

    def get_dataset(self, callsign: str) -> CallBookData:
        """Perform a data search for a callsign search
        :param callsign: the callsign to be searched for
        :return: the callbook data set"""
        try:
            return self.__get_dataset__(callsign)
        except SessionExpiredException as exc:
            self.__session__ = ''
            raise exc

    @property
    @abstractmethod
    def has_logbook(self) -> bool:
        """Is a logbook available for this service"""
        pass

    @abstractmethod
    def __upload_log__(self, username: str, password: str, adif: str):
        pass

    def upload_log(self, username: str, password: str, adif_data: dict):
        """Upload logbook data
        :param username: the username used with this service
        :param password: the password used with this service
        :param adif_data: the data to be converted to ADI and uploaded"""

        if not username or not password:
            raise LoginException('Username or password missing')

        for field in self.required_fields:
            if field not in adif_data['RECORDS'][0]:
                raise MissingADIFFieldException(field)

        adif_data = adif_data.copy()
        adif_data['RECORDS'] = [adif_data['RECORDS'][0]]

        self.__upload_log__(username, password, adi.dumps(adif_data, 'ADIF Export by DragonLog'))


class HamQTHCallBook(AbstractCallBook):
    def __init__(self, logger: Logger, prog_name: str):
        super().__init__(logger, prog_name)

    @property
    def required_fields(self) -> tuple:
        return 'QSO_DATE', 'TIME_ON', 'CALL', 'MODE', 'BAND', 'RST_SENT', 'RST_RCVD'

    @property
    def __url__(self):
        return 'https://www.hamqth.com/xml.php'

    @property
    def callbook_type(self) -> CallBookType:
        return CallBookType.HamQTH

    def __login__(self, username: str, password: str) -> str:
        if not username or not password:
            raise LoginException('Username or password missing')

        try:
            res = self._get_({'u': username, 'p': password})
        except CommunicationException as exc:
            raise LoginException(str(exc))

        match res:
            case {'HamQTH': {'session': {'error': error}}}:
                raise LoginException(f"HamQTH error: {error}")
            case {'HamQTH': {'session': {'session_id': session_id}}}:
                return session_id
            case _:
                raise LoginException(f'HamQTH error: Unknown data format {res}')

    def __get_dataset__(self, callsign: str) -> CallBookData | None:
        try:
            self.log.debug(f'Searching {callsign}...')
            res = self._get_({'id': self.__session__,
                              'prg': self.__program_str__,
                              'callsign': callsign})
        except CommunicationException as exc:
            raise RequestException(str(exc))

        match res:
            case {'HamQTH': {'session': {'error': error}}}:
                if error == 'Session does not exist or expired':
                    raise SessionExpiredException('HamQTH')
                elif error == 'Callsign not found':
                    raise CallsignNotFoundException(callsign)
                else:
                    raise RequestException(f"HamQTH error: {error}")
            case {'HamQTH': {'search': data}}:
                if data:
                    return CallBookData(
                        callsign,
                        data.get('nick', ''),
                        data.get('grid', ''),
                        data.get('qth', ''),
                        data.get('qsl_via', ''),
                        data.get('qsl', '') == 'Y',
                        data.get('qsldirect', '') == 'Y',
                        data.get('eqsl', '') == 'Y',
                        data.get('lotw', '') == 'Y',
                        data.get('dok', ''),
                    )
                else:
                    return None
            case _:
                raise RequestException(f'HamQTH error: Unknown data format {res}')

    @property
    def has_logbook(self) -> bool:
        return True

    def __upload_log__(self, username: str, password: str, adif: str):
        if not username or not password:
            raise LoginException('Username or password missing')

        data = {
            'u': username,
            'p': password,
            'adif': adif,
            'prg': self.__program_str__,
            'cmd': 'insert'
        }

        r = requests.post('https://www.hamqth.com/qso_realtime.php', data=data)

        if r.status_code == 200:
            return
        elif r.status_code == 400:
            raise QSORejectedException(r.text)
        elif r.status_code == 403:
            raise LoginException(r.text)
        else:
            self.log.debug(f'HamQTH communication error #{r.status_code} "{r.text}"')
            raise CommunicationException(f'HamQTH error: HTTP-Error {r.status_code}')


class QRZCQCallBook(AbstractCallBook):
    def __init__(self, logger: Logger, prog_name: str):
        super().__init__(logger, prog_name)

    @property
    def required_fields(self) -> tuple:
        raise NotImplementedError('QRZCQ.com API for uploading is currently not stable')

    @property
    def __url__(self):
        return 'https://ssl.qrzcq.com/xml'

    @property
    def callbook_type(self) -> CallBookType:
        return CallBookType.QRZCQ

    def __login__(self, username: str, password: str) -> str:
        if not username or not password:
            raise LoginException('Username or password missing')

        try:
            res = self._get_({'username': username,
                              'password': password,
                              'agent': self.__program_str__})
        except CommunicationException as exc:
            raise LoginException(str(exc))

        match res:
            case {'QRZCQDatabase': {'Session': {'Error': error}}}:
                raise LoginException(f"QRZCQ error: {error}")
            case {'QRZCQDatabase': {'Session': {'Key': session_id}}}:
                return session_id
            case _:
                raise LoginException(f'QRZCQ error: Unknown data format {res}')

    def __get_dataset__(self, callsign: str) -> CallBookData | None:
        try:
            self.log.debug(f'Searching {callsign}...')
            res = self._get_({'s': self.__session__,
                              'callsign': callsign,
                              'agent': self.__program_str__})
        except CommunicationException as exc:
            raise RequestException(str(exc))

        match res:
            case {'QRZCQDatabase': {'Session': {'Error': error}}}:
                if error == 'Session does not exist or expired':
                    raise SessionExpiredException('QRZCQ')
                elif error.startswith('Not found') or error.startswith('Callsign Empty'):
                    raise CallsignNotFoundException(callsign)
                else:
                    raise RequestException(f"QRZCQ error: {error}")
            case {'QRZCQDatabase': {'Callsign': data}}:
                if data:
                    return CallBookData(
                        callsign,
                        data.get('name', ''),
                        data.get('locator', ''),
                        data.get('qth', ''),
                        data.get('manager', ''),
                        data.get('bqsl', '') == '1',
                        data.get('mqsl', '') == '1',
                        data.get('eqsl', '') == '1',
                        data.get('lotw', '') == '1',
                        data.get('dok', ''),
                    )
                else:
                    return None
            case _:
                raise RequestException(f'QRZCQ error: Unknown data format {res}')

    @property
    def has_logbook(self) -> bool:
        return False

    def __upload_log__(self, username: str, password: str, adif: str):
        raise NotImplementedError('QRZCQ.com API for uploading is currently not stable')


class QRZCallBook(AbstractCallBook):
    def __init__(self, logger: Logger, prog_name: str):
        super().__init__(logger, prog_name)

    @property
    def required_fields(self) -> tuple:
        raise NotImplementedError('QRZ.com API for uploading is not available')

    @property
    def __url__(self):
        return 'https://xmldata.qrz.com/xml/1.34/'

    @property
    def callbook_type(self) -> CallBookType:
        return CallBookType.QRZ

    def __login__(self, username: str, password: str) -> str:
        if not username or not password:
            raise LoginException('Username or password missing')

        try:
            res = self._get_({'username': username,
                              'password': password,
                              'agent': self.__program_str__})
        except CommunicationException as exc:
            raise LoginException(str(exc))

        match res:
            case {'QRZDatabase': {'Session': {'Error': error}}}:
                raise LoginException(f"QRZ error: {error}")
            case {'QRZDatabase': {'Session': {'Key': session_id}}}:
                return session_id
            case _:
                raise LoginException(f'QRZ error: Unknown data format {res}')

    def __get_dataset__(self, callsign: str) -> CallBookData | None:
        try:
            self.log.debug(f'Searching {callsign}...')
            res = self._get_({'s': self.__session__,
                              'callsign': callsign,
                              # 'agent': self.__program_str__
                              })
        except CommunicationException as exc:
            raise RequestException(str(exc))

        match res:
            case {'QRZDatabase': {'Session': {'Error': error}}}:
                if error == 'Session does not exist or expired':
                    raise SessionExpiredException('QRZ')
                elif error.startswith('Not found') or error.startswith('Callsign Empty'):
                    raise CallsignNotFoundException(callsign)
                else:
                    raise RequestException(f"QRZ error: {error}")
            case {'QRZDatabase': {'Callsign': data}}:
                if data:
                    return CallBookData(
                        callsign,
                        data.get('name_fmt', data.get('fname', '')),
                        data.get('grid', ''),
                        data.get('addr2', ''),
                        data.get('qslmgr', ''),
                        False,  # not available
                        data.get('mqsl', '') == '1',
                        data.get('eqsl', '') == '1',
                        data.get('lotw', '') == '1',
                        '',  # not available
                    )
                else:
                    return None
            case _:
                raise RequestException(f'QRZ error: Unknown data format {res}')

    @property
    def has_logbook(self) -> bool:
        return False

    def __upload_log__(self, username: str, password: str, adif: str):
        raise NotImplementedError('QRZ.com API for uploading is not available')
