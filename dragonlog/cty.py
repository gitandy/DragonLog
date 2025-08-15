# DragonLog © 2023-2024 by Andreas Schawo is licensed under CC BY-SA 4.0.
# To view a copy of this license, visit http://creativecommons.org/licenses/by-sa/4.0/

import re
import csv
from collections import namedtuple
from collections.abc import Generator

Country = namedtuple('Country', ('code', 'name', 'dxcc',
                                 'continent', 'cq', 'itu',
                                 'lat', 'lon', 'time_off'))


class CountryCodeNotFoundException(Exception):
    pass


class CountryNotFoundException(Exception):
    pass


class CountryData:
    """Loads country data from a cty CSV file
    Provides search for prefix, country code and country data by a given callsign"""

    # noinspection RegExpRedundantEscape
    RE_OVERRIDES = re.compile(r'([A-Z0-9/=]+)(?:\((\d+)\))?(?:\[(\d+)\])?.*')

    def __init__(self, cty_file):
        self.__countries__: dict[str, Country] = {}
        self.__prefixes__ = {}
        self.__pfx_list__ = []
        self.__calls__ = {}
        self.__data_ver__ = ''

        self.__load__(cty_file)

    def __load__(self, cty_file: str):
        """Loads the cty data file and builds the internal data structure
        :param cty_file: the cty data in CSV format"""

        with (open(cty_file) as cty_f):
            cty = csv.reader(cty_f, delimiter=',')
            for row in cty:
                row[0] = row[0].replace('*', '')
                self.__countries__[row[0]] = Country(*row[:-1])

                for pfx in row[9][:-1].split():
                    data = {'cty_code': row[0]}

                    pfx_parts = re.findall(self.RE_OVERRIDES, pfx)[0]
                    pfx, cq_or, itu_or = pfx_parts
                    if cq_or:
                        data['cq_or'] = cq_or[0]
                    if itu_or:
                        data['itu_or'] = itu_or[0]

                    if pfx.startswith('='):
                        if row[0] == 'VE' and pfx.startswith('=VER'):
                            self.__data_ver__ = pfx[1:]
                            continue
                        if not pfx[1:] in self.__calls__:
                            # Callsign can be doubled, only the first is correct
                            self.__calls__[pfx[1:]] = data
                    else:
                        self.__prefixes__[pfx] = data

        self.__pfx_list__ = sorted(self.__prefixes__)

    @property
    def version(self) -> str:
        """Get the version of the data file"""

        return self.__data_ver__

    def prefix(self, call: str) -> str:
        """Get the prefix of a callsign
        :param call: the callsign (upper or lowercase)
        :return: the prefix"""

        part = ''
        i = 0
        pfx = ''
        for d in call.upper():
            part += d
            try:
                i = self.__pfx_list__.index(part, i)
                pfx = self.__pfx_list__[i]
            except ValueError:
                continue
        return pfx

    def cty_code(self, call) -> dict:
        """Get the country code for a callsign
        :param call: the callsign (upper or lowercase)
        :return: the country code"""

        if call in self.__calls__:
            return self.__calls__[call.upper()]
        elif self.prefix(call.upper()):
            return self.__prefixes__[self.prefix(call.upper())]
        else:
            raise CountryCodeNotFoundException(f'for "{call}"')

    def country(self, call: str) -> Country:
        """Get the country data from a callsign
        :param call: the callsign (upper or lowercase)
        :return: the country data"""

        data = self.cty_code(call)
        if data:
            cty_code = data['cty_code']
            cty_data = self.__countries__[cty_code]
            if 'cq_or' in data:
                cty_data = cty_data._replace(cq=data['cq_or'])
            if 'itu_or' in data:
                cty_data = cty_data._replace(itu=data['itu_or'])

            return cty_data
        else:
            raise CountryNotFoundException(f'for "{call}"')

    @property
    def countries(self) -> Generator:
        for c in self.__countries__.values():
            yield c.name


def main():
    cty = CountryData('data/cty/cty.csv')
    print(cty.version)
    print(cty.country('VERSION'))


if __name__ == '__main__':
    main()
