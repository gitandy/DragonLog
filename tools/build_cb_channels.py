import csv
import json


def build_cb_channels(src, dst):
    channels = {}

    with open(src, newline='') as bcf:
        print('Reading channels...')
        cr = csv.reader(bcf, delimiter=';')

        skipped = False
        for c in cr:
            # Skip header
            if not skipped:
                skipped = True
                continue

            modes = c[2].replace(' ', '').split(',')
            channels[c[0]] = {'freq': int(c[1]),
                              'modes': modes}

    with open(dst, 'w') as bjf:
        print('Writing channels...')
        json.dump(channels, bjf, indent=2)


if __name__ == '__main__':
    build_cb_channels('cb_channels.csv', '../data/cb_channels.json')
