import json

from dragonlog import cty

EXTRA = {
    'Sov Mil Order of Malta': '',  # unclear
    'Spratly Islands': '',  # politically unclear
    'Agalega and St. Brandon': 'mu',
    'Rodriguez Island': 'mu',
    'Annobon Island': '',  # unclear
    'Conway Reef': 'fj',
    'Rotuma Island': 'fj',
    'Kingdom of Eswatini': 'sz',
    'Bouvet': 'bv',
    'Peter 1 Island': '',  # politically unclear
    'ITU HQ': 'itu',
    'United Nations HQ': 'un',
    'Vienna Intl Ctr': '',
    'Timor - Leste': 'tl',
    'West Malaysia': 'my',
    'East Malaysia': 'my',
    'Dem. Rep. of the Congo': 'cd',
    'Scarborough Reef': '',  # politically unclear
    'Pratas Island': 'tw',
    'The Gambia': 'gm',
    'San Felix and San Ambrosio': 'cl',
    'Easter Island': 'cl',
    'Juan Fernandez Islands': 'cl',
    'Madeira Islands': 'pt',
    'Azores': 'pt',
    'Sable Island': 'ca',
    'St. Paul Island': 'us-ak',
    'Fed. Rep. of Germany': 'de',
    'North Cook Islands': 'ck',
    'South Cook Islands': 'ck',
    'Bosnia-Herzegovina': 'ba',
    'Balearic Islands': 'es',
    'Canary Islands': 'es',
    'Ceuta and Melilla': 'es',
    'St. Barthelemy': 'bl',
    'Chesterfield Islands': '',
    'Austral Islands': '',
    'Clipperton Island': '',
    'Marquesas Islands': '',
    'Reunion Island': '',
    'Glorioso Islands': '',
    'Juan de Nova and Europa': '',
    'Tromelin Island': '',
    'Crozet Island': '',
    'Kerguelen Islands': '',
    'Amsterdam and St. Paul Is.': '',
    'Wallis and Futuna Islands': '',
    'Shetland Islands': '',
    'Temotu Province': 'sb',
    'Galapagos Islands': 'ec',
    'San Andres and Providencia': 'co',
    'Malpelo Island': 'co',
    'Republic of Korea': 'kr',
    'Vatican City': 'va',
    'African Italy': 'it',
    'Sardinia': 'it',
    'Sicily': 'it',
    'St. Vincent': 'vc',
    'Minami Torishima': 'jp',
    'Ogasawara': 'jp',
    'Svalbard': 'no',
    'Bear Island': 'no',
    'Jan Mayen': 'no',
    'Guantanamo Bay': '',  # unclear
    'Mariana Islands': 'mp',
    'Baker and Howland Islands': '',
    'Johnston Island': '',
    'Midway Island': '',
    'Palmyra and Jarvis Islands': '',
    'Kure Island': '',
    'Swains Island': '',
    'Wake Island': '',
    'Navassa Island': '',
    'US Virgin Islands': 'vi',
    'Desecheo Island': 'pr',
    'Aland Islands': 'ax',
    'Market Reef': '',  # Sweden and Finland
    'Czech Republic': 'cz',
    'Slovak Republic': 'sk',
    'DPR of Korea': 'kp',
    'Curacao': 'cw',
    'Bonaire': 'nl',
    'Saba and St. Eustatius': 'nl',
    'Fernando de Noronha': 'br',
    'St. Peter and St. Paul': 'br',
    'Trindade and Martim Vaz': 'br',
    'Franz Josef Land': 'ru',
    'Sao Tome and Principe': 'st',
    'Mount Athos': 'gr',
    'Dodecanese': 'gr',
    'Crete': 'gr',
    'Western Kiribati': 'ki',
    'Central Kiribati': 'ki',
    'Eastern Kiribati': 'ki',
    'Banaba Island': 'ki',
    'Asiatic Turkey': 'tr',
    'European Turkey': 'tr',
    'Cocos Island': 'cc',
    'Corsica': 'fr',
    'Cote d\'Ivoire': 'ci',
    'European Russia': 'ru',
    'Kaliningrad': 'ru',
    'Asiatic Russia': 'ru',
    'Brunei Darussalam': 'bn',
    'Heard Island': 'hm',
    'Macquarie Island': '',
    'Lord Howe Island': '',
    'Mellish Reef': '',
    'Willis Island': '',
    'Pitcairn Island': 'pn',
    'Ducie Island': '',
    'South Georgia Island': '',
    'South Shetland Islands': '',
    'South Orkney Islands': '',
    'South Sandwich Islands': '',
    'Chagos Islands': 'mu',
    'Andaman and Nicobar Is.': 'in',
    'Lakshadweep Islands': 'in',
    'Revillagigedo': 'mx',
    'Macao': 'mo',
    'Aves Island': '',  # politically unclear
    'Republic of Kosovo': 'xk',
    'Republic of South Sudan': 'ss',
    'UK Base Areas on Cyprus': '',  # unclear
    'St. Helena': 'sh',
    'Ascension Island': 'sh',
    'Tristan da Cunha and Gough Islands': 'sh',
    'Tokelau Islands': 'tk',
    'Chatham Islands': 'nz',
    'Kermadec Islands': 'nz',
    'N.Z. Subantarctic Is.': 'nz',
    'Pr. Edward and Marion Is.': 'za',
}


def main():
    with open('../dragonlog/icons/flags/codes.json') as cc_f:
        codes: dict = json.load(cc_f)

    country_map: dict = dict(zip(codes.values(), codes.keys()))

    cty_d = cty.CountryData('../dragonlog/data/cty/cty.csv')

    matches = 0
    extra_matches = 0
    non_matches = 0
    for c in cty_d.countries:
        if c in EXTRA and EXTRA[c]:
            country_map[c] = EXTRA[c]
            extra_matches +=1
        elif c.replace('&', 'and').replace('St. ', 'Saint ') not in country_map:
            print(f"'{c.replace('&', 'and')}': '',")
            non_matches += 1
        else:
            matches +=1

    print('\n==============')
    print(f'Matches found: {matches}')
    print(f'Extra matches: {extra_matches}')
    print(f'Non matching : {non_matches}')
    print(f'Matched      : {(matches+extra_matches)/(matches+extra_matches+non_matches)*100:.1f}%')

    with open('../dragonlog/icons/flags/flags_map.json', 'w') as fm_f:
        json.dump(country_map, fm_f, indent=2)


if __name__ == '__main__':
    main()
