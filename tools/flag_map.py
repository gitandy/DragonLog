import json

from dragonlog import cty

EXTRA = {
    'Sov Mil Order of Malta': '',
    'Spratly Islands': '',
    'Agalega and St. Brandon': '',
    'Rodriguez Island': '',
    'Annobon Island': '',
    'Conway Reef': '',
    'Rotuma Island': '',
    'Kingdom of Eswatini': '',
    'Bouvet': 'bv',
    'Peter 1 Island': '',
    'ITU HQ': '',
    'United Nations HQ': 'un',
    'Vienna Intl Ctr': '',
    'Timor - Leste': '',
    'West Malaysia': 'my',
    'East Malaysia': 'my',
    'Dem. Rep. of the Congo': 'cd',
    'Trinidad and Tobago': '',
    'Scarborough Reef': '',
    'Pratas Island': '',
    'The Gambia': 'gm',
    'San Felix and San Ambrosio': '',
    'Easter Island': '',
    'Juan Fernandez Islands': '',
    'Madeira Islands': 'pt',
    'Azores': 'pt',
    'Sable Island': '',
    'St. Paul Island': '',
    'Fed. Rep. of Germany': 'de',
    'North Cook Islands': 'ck',
    'South Cook Islands': 'ck',
    'Bosnia-Herzegovina': 'ba',
    'Balearic Islands': 'es',
    'Canary Islands': 'es',
    'Ceuta and Melilla': '',
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
    'Temotu Province': '',
    'Galapagos Islands': '',
    'San Andres and Providencia': '',
    'Malpelo Island': '',
    'Republic of Korea': 'kr',
    'Vatican City': 'va',
    'African Italy': 'it',
    'Sardinia': 'it',
    'Sicily': 'it',
    'St. Vincent': 'vc',
    'Minami Torishima': '',
    'Ogasawara': '',
    'Svalbard': '',
    'Bear Island': '',
    'Jan Mayen': '',
    'Guantanamo Bay': '',
    'Mariana Islands': '',
    'Baker and Howland Islands': '',
    'Johnston Island': '',
    'Midway Island': '',
    'Palmyra and Jarvis Islands': '',
    'Kure Island': '',
    'Swains Island': '',
    'Wake Island': '',
    'Navassa Island': '',
    'US Virgin Islands': 'vi',
    'Desecheo Island': '',
    'Aland Islands': 'ax',
    'Market Reef': '',
    'Czech Republic': 'cz',
    'Slovak Republic': 'sk',
    'DPR of Korea': 'kp',
    'Curacao': 'cw',
    'Bonaire': '',
    'Saba and St. Eustatius': '',
    'Fernando de Noronha': '',
    'St. Peter and St. Paul': '',
    'Trindade and Martim Vaz': '',
    'Franz Josef Land': '',
    'Sao Tome and Principe': 'st',
    'Mount Athos': '',
    'Dodecanese': '',
    'Crete': 'gr',
    'Western Kiribati': 'ki',
    'Central Kiribati': 'ki',
    'Eastern Kiribati': 'ki',
    'Banaba Island': '',
    'Asiatic Turkey': 'tr',
    'European Turkey': 'tr',
    'Cocos Island': 'cc',
    'Corsica': 'fr',
    'Cote d\'Ivoire': 'ci',
    'European Russia': 'ru',
    'Kaliningrad': 'ru',
    'Asiatic Russia': 'ru',
    'Antigua and Barbuda': '',
    'Brunei Darussalam': '',
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
    'Chagos Islands': '',
    'Andaman and Nicobar Is.': '',
    'Lakshadweep Islands': '',
    'Revillagigedo': '',
    'Macao': 'mo',
    'Aves Island': '',
    'Republic of Kosovo': 'xk',
    'Republic of South Sudan': 'ss',
    'UK Base Areas on Cyprus': '',
    'St. Helena': 'sh',
    'Ascension Island': '',
    'Tristan da Cunha and Gough Islands': 'sh',
    'Tokelau Islands': '',
    'Chatham Islands': '',
    'Kermadec Islands': '',
    'N.Z. Subantarctic Is.': '',
    'Pr. Edward and Marion Is.': '',
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
