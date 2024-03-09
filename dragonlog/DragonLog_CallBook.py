from dataclasses import dataclass
from enum import Enum, auto

import requests
import xmltodict


class CallBookType(Enum):
    HamQTH = auto()

@dataclass
class CallBookData:
    callsign: str
    nickname: str
    locator: str
    qth: str


class CommunicationException(Exception):
    pass

class RequestException(Exception):
    pass

class LoginException(Exception):
    pass

class SessionExpiredException(Exception):
    pass

class CallBook:
    def __init__(self, callbook_type: CallBookType, program: str):
        self.__callbook_type__ = callbook_type
        self.__program_str__ = program
        self.__session__: str = ''

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

    def _hamqth_request_(self, params: dict):
        r = requests.get('https://www.hamqth.com/xml.php', params=params)

        if r.status_code == 200:
            return xmltodict.parse(r.text)
        else:
            raise CommunicationException(f'HamQTH error: HTTP-Error {r.status_code}')

    def _hamqth_login_(self, username: str, password: str) -> str:
        try:
            res = self._hamqth_request_({'u': username, 'p': password})
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
            res = self._hamqth_request_({'id': self.__session__,
                                         'prg': self.__program_str__,
                                         'callsign': callsign})
        except CommunicationException as exc:
            raise RequestException(str(exc))

        match res:
            case {'HamQTH': {'session': {'error': error}}}:
                if error == 'Session does not exist or expired':
                    raise SessionExpiredException('HamQTH')
                else:
                    raise RequestException(f"HamQTH error: {error}")
            case {'HamQTH': {'search': data}}:
                if data:
                    return CallBookData(
                        callsign,
                        data['nick'] if 'nick' in data else '',
                        data['grid'] if 'grid' in data else '',
                        data['qth'] if 'qth' in data else '',
                    )
            case _:
                raise RequestException(f'HamQTH error: Unknown data format {res}')
