import csv
import json


def build_modes(src, dst):
    modes = {
        'AFU': {},
        'CB': {
            'FM': [],
            'AM': [],
            'SSB': ['LSB', 'USB'],
        }
    }

    with open(src, newline='') as bcf:
        print('Reading modes...')
        cr = csv.reader(bcf, delimiter='\t')

        skipped = False
        for m in cr:
            # Skip header
            if not skipped:
                skipped = True
                continue

            smodes = m[1].replace(' ', '').split(',') if m[1].strip() else []
            modes['AFU'][m[0].strip()] = smodes

    with open(dst, 'w') as bjf:
        print('Writing modes...')
        json.dump(modes, bjf, indent=2)


if __name__ == '__main__':
    build_modes('modes.csv', '../modes.json')
