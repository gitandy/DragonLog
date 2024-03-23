import logging
from dataclasses import dataclass
from enum import Enum, auto

import requests
import xmltodict
from adif_file import adi

from .Logger import Logger


class CallBookType(Enum):
    HamQTH = auto()


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


class CallBook:
    def __init__(self, callbook_type: CallBookType, program: str, logger: Logger):
        self.__callbook_type__ = callbook_type
        self.__program_str__ = program
        self.__session__: str = ''

        self.log = logging.getLogger('CallBook')
        self.log.setLevel(logger.loglevel)
        self.log.addHandler(logger)
        self.log.debug('Initialising...')

    @property
    def callbook_type(self):
        return self.__callbook_type__

    def login(self, username: str, password: str):
        match self.__callbook_type__:
            case CallBookType.HamQTH:
                self.__session__ = self._hamqth_login_(username, password)

    @property
    def is_loggedin(self) -> bool:
        return bool(self.__session__)

    def get_dataset(self, callsign: str) -> CallBookData:
        try:
            match self.__callbook_type__:
                case CallBookType.HamQTH:
                    return self._hamqth_get_data_(callsign)
        except SessionExpiredException as exc:
            self.__session__ = ''
            raise exc

    @property
    def required_fields(self):
        match self.__callbook_type__:
            case CallBookType.HamQTH:
                return 'QSO_DATE', 'TIME_ON', 'CALL', 'MODE', 'BAND', 'RST_SENT', 'RST_RCVD'
            case _:
                return ()

    def upload_log(self, username: str, password: str, adif_data: dict):
        for field in self.required_fields:
            if field not in adif_data['RECORDS'][0]:
                raise MissingADIFFieldException(field)

        adif_data = adif_data.copy()
        adif_data['RECORDS'] = [adif_data['RECORDS'][0]]

        match self.__callbook_type__:
            case CallBookType.HamQTH:
                return self._hamqth_upload_(username, password, adi.dumps(adif_data, 'ADIF Export by DragonLog'))

    def _hamqth_get_(self, params: dict):
        r = requests.get('https://www.hamqth.com/xml.php', params=params)

        if r.status_code == 200:
            return xmltodict.parse(r.text)
        else:
            raise CommunicationException(f'HamQTH error: HTTP-Error {r.status_code}')

    def _hamqth_login_(self, username: str, password: str) -> str:
        try:
            res = self._hamqth_get_({'u': username, 'p': password})
        except CommunicationException as exc:
            raise LoginException(str(exc))

        match res:
            case {'HamQTH': {'session': {'error': error}}}:
                raise LoginException(f"HamQTH error: {error}")
            case {'HamQTH': {'session': {'session_id': session_id}}}:
                return session_id
            case _:
                raise LoginException(f'HamQTH error: Unknown data format {res}')

    def _hamqth_get_data_(self, callsign: str) -> CallBookData:
        try:
            self.log.debug(f'Searching {callsign}')
            res = self._hamqth_get_({'id': self.__session__,
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
                        data['qsl'] == 'Y' if 'qsl' in data else False,
                        data['qsldirect'] == 'Y' if 'qsldirect' in data else False,
                        data['eqsl'] == 'Y' if 'eqsl' in data else False,
                    )
            case _:
                raise RequestException(f'HamQTH error: Unknown data format {res}')

    def _hamqth_upload_(self, username: str, password: str, adif: str):
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
