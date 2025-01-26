import os
import sys
import json
import random
import string
import datetime

from adif_file import adx, adi

with open('../dragonlog/data/bands.json') as bf:
    BANDS: dict = json.load(bf)
    BANDS.pop('11m')

with open('../dragonlog/data/modes.json') as mf:
    MODES = json.load(mf)['AFU']


def gen_call(calls=None, prefix='', suffix=''):
    gen_calls = 0
    for fpc in string.ascii_uppercase:
        for spc in string.ascii_uppercase:
            for nr in range(10):
                for fsc in string.ascii_uppercase:
                    for ssc in string.ascii_uppercase:
                        gen_calls += 1
                        if gen_calls > calls:
                            return
                        else:
                            yield f'{prefix}{fpc}{spc}{nr}{fsc}{ssc}{suffix}'


def get_random_int(start: int, stop: int) -> int:
    return int(random.random() * ((stop+1) - start) + start)


def get_rand_freq(band: str) -> float:
    start, stop, _ = BANDS[band]
    return get_random_int(start, stop) / 1000


def get_rand_rst() -> str:
    r = get_random_int(1, 5)
    s = get_random_int(1, 9)
    return f'{r}{s}'


def get_rand_loc() -> str:
    # A..R, 0..9, a..x
    l1 = string.ascii_uppercase[get_random_int(0, 17)]
    l2 = string.ascii_uppercase[get_random_int(0, 17)]
    l34 = f'{get_random_int(0, 99):02d}'
    l5 = string.ascii_lowercase[get_random_int(0, 24)]
    l6 = string.ascii_lowercase[get_random_int(0, 24)]
    return l1 + l2 + l34 + l5 + l6


def get_rand_suffix() -> str:
    suffixes = ('', '/M', '/P', '/T', '/AM', '/MM')
    return suffixes[get_random_int(0, len(suffixes)-1)]


def main():
    rec_amount = 1000
    adif_type = 'i'
    if len(sys.argv) > 1:
        try:
            rec_amount = int(sys.argv[1])
        except ValueError:
            pass

        if len(sys.argv) > 2 and sys.argv[2] == 'x':
            adif_type = 'x'

    doc = {
        'HEADER': {'ADIF_VER': '3.1.4',
                   'CREATED_TIMESTAMP': datetime.datetime.utcnow().strftime('%Y%m%d %H%M%S'),
                   'PROGRAMID': os.path.basename(sys.argv[0]),
                   'PROGRAMVERSION': '0.2'},
        'RECORDS': []
    }

    bands = list(BANDS.keys())
    modes = list(MODES.keys())

    for i, call in enumerate(gen_call(rec_amount)):
        rY = get_random_int(2018, 2024)
        rM = get_random_int(1, 12)
        rD = get_random_int(1, 28) if rM == 2 else get_random_int(1, 30)
        rh = get_random_int(0, 23)
        rm = get_random_int(0, 54)
        rb = bands[get_random_int(0, len(BANDS)-1)]
        rf = get_rand_freq(rb)

        record = {'CALL': call + get_rand_suffix(),
                  'QSO_DATE': f'{rY}{rM:02d}{rD:02d}',
                  'TIME_ON': f'{rh:02d}{rm:02d}',
                  'TIME_OFF': f'{rh:02d}{rm + 5:02d}',
                  'NAME': f'Test OM #{i}',
                  'QTH': f'Test #{i}',
                  'NOTES': f'Test file #{i}',
                  'STATION_CALLSIGN': 'XX1XXX',
                  'GRIDSQUARE': get_rand_loc(),
                  'RST_SENT': get_rand_rst(),
                  'RST_RCVD': get_rand_rst(),
                  'BAND': rb,
                  'MODE': modes[get_random_int(0, len(modes)-1)],
                  'SUBMODE': 'USB',
                  'FREQ': rf,
                  'TX_PWR': get_random_int(1, 100),
                  'MY_NAME': 'Paul Mustermann',
                  'MY_CITY': 'Very large city name',
                  'MY_GRIDSQUARE': 'JO77zz',
                  }

        doc['RECORDS'].append(record)

    print(f'Generating testfile for {rec_amount} QSOs...')
    if adif_type == 'i':
        adi.dump(f'big_testfile_{rec_amount}.adi', doc, comment=f'Big test file with {rec_amount} QSOs')
    else:
        adx.dump(f'big_testfile_{rec_amount}.adx', doc, False)

if __name__ == '__main__':
    main()
