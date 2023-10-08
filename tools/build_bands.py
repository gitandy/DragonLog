import csv
import json


def build_bands(src, dst):
    bands = {}

    with open(src, newline='') as bcf:
        print('Reading bands...')
        cr = csv.reader(bcf, delimiter='\t')

        skipped = False
        for b in cr:
            # Skip header
            if not skipped:
                skipped = True
                continue

            fb = float(b[1])*1000
            fe = float(b[2])*1000
            fs = 1 if fb < 1000 else 100

            bands[b[0].strip()] = [int(fb) if fb > 1000 else fb, int(fe) if fe > 1000 else fe, fs]

    bands['11m'] = [26565, 27405, 10]

    bands = dict(sorted(bands.items(), key=lambda item: item[1][0]))

    with open(dst, 'w') as bjf:
        print('Writing bands...')
        json.dump(bands, bjf, indent=2)


if __name__ == '__main__':
    build_bands('bands.csv', '../bands.json')
