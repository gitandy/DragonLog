import sys
import string
import datetime

from adif_file import adx, adi


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


def main():
    rec_amount = 1000
    if len(sys.argv) > 1:
        try:
            rec_amount = int(sys.argv[1])
        except ValueError:
            pass

    doc = {
        'HEADER': {'ADIF_VER': '3.1.4',
                   'CREATED_TIMESTAMP': datetime.datetime.now(datetime.UTC).strftime('%Y%m%d %H%M%S'),
                   'PROGRAMID': 'Generate big test file',
                   'PROGRAMVERSION': '0.1'},
        'RECORDS': []
    }

    for i, call in enumerate(gen_call(rec_amount)):
        record = {'CALL': call,
                  'QSO_DATE': f'20231204',
                  'TIME_ON': '1100',
                  'TIME_OFF': '1105',
                  'NAME': f'Test OM #{i}',
                  'QTH': f'Test #{i}',
                  'NOTES': f'Test file #{i}',
                  'STATION_CALLSIGN': 'XX1XXX',
                  'GRIDSQUARE': 'JO33uu',
                  'RST_SENT': '59',
                  'RST_RCVD': '59',
                  'BAND': '10m',
                  'MODE': 'SSB',
                  'SUBMODE': 'USB',
                  'FREQ': 28400,
                  'TX_PWR': 50,
                  'MY_NAME': 'Paul',
                  'MY_CITY_INTL': 'Very large city name',
                  'MY_GRIDSQUARE': 'JO77zz',
                  }

        doc['RECORDS'].append(record)

    print(f'Generating testfile for {rec_amount} QSOs...')
    adi.dump(f'big_testfile_{rec_amount}.adi', doc)


if __name__ == '__main__':
    main()
