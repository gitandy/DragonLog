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
    def __init__(self, logger: Logger, prog_name: str):
        self.__program_str__ = prog_name
        self.__session__: str = ''

        self.log = logging.getLogger('CallBook')
        self.log.setLevel(logger.loglevel)
        self.log.addHandler(logger)
        self.log.debug('Initialising...')

    @property
    @abstractmethod
    def required_fields(self) -> tuple:
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
        pass

    @abstractmethod
    def __login__(self, username: str, password: str) -> str:
        pass

    def login(self, username: str, password: str):
        self.__session__ = self.__login__(username, password)

    @property
    def is_loggedin(self) -> bool:
        return bool(self.__session__)

    @abstractmethod
    def __get_dataset__(self, callsign: str):
        pass

    def get_dataset(self, callsign: str) -> CallBookData:
        try:
            return self.__get_dataset__(callsign)
        except SessionExpiredException as exc:
            self.__session__ = ''
            raise exc

    @abstractmethod
    def __upload_log__(self, username: str, password: str, adif: str):
        pass

    def upload_log(self, username: str, password: str, adif_data: dict):
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

    def __get_dataset__(self, callsign: str) -> CallBookData:
        try:
            self.log.debug(f'Searching {callsign}')
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
                        data['nick'] if 'nick' in data else '',
                        data['grid'] if 'grid' in data else '',
                        data['qth'] if 'qth' in data else '',
                        data['qsl_via'] if 'qsl_via' in data else '',
                        'qsl' in data and data['qsl'] == 'Y',
                        'qsldirect' in data and data['qsldirect'] == 'Y',
                        'eqsl' in data and data['eqsl'] == 'Y',
                        'lotw' in data and data['lotw'] == 'Y',
                    )
            case _:
                raise RequestException(f'HamQTH error: Unknown data format {res}')

    def __upload_log__(self, username: str, password: str, adif: str):
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
        elif r.status_code in (400, 500):
            raise QSORejectedException(r.text)
        elif r.status_code == 403:
            raise LoginException(r.text)
        else:
            raise CommunicationException(f'HamQTH error: HTTP-Error {r.status_code}')
