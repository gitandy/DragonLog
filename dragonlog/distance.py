# DragonLog (c) 2023-2024 by Andreas Schawo is licensed under CC BY-SA 4.0.
# To view a copy of this license, visit http://creativecommons.org/licenses/by-sa/4.0/

import math

import maidenhead


def distance(pos1: str, pos2: str) -> int:
    """Calculate distance between two maidenhead locators

    :param pos1: first maidenhead locator
    :param pos2: second maidenhead locator
    :return: distance in km
    """

    if not type(pos1) is str or not type(pos2) is str or len(pos1)%2 != 0 or len(pos2)%2 != 0:
        raise Exception('Maidenhead locators must be strings of 2-8 chars')

    try:
        pos1 = maidenhead.to_location(pos1, True)
        pos2 = maidenhead.to_location(pos2, True)

        mlat = math.radians(pos1[0])
        mlon = math.radians(pos1[1])
        plat = math.radians(pos2[0])
        plon = math.radians(pos2[1])

        return int(6371.01 * math.acos(
            math.sin(mlat) * math.sin(plat) + math.cos(mlat) * math.cos(plat) * math.cos(mlon - plon)))
    except ValueError as exc:
        raise Exception(exc)
