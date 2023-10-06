import math


def geo_dist(pos1, pos2):
    mlat = math.radians(pos1[0])
    mlon = math.radians(pos1[1])
    plat = math.radians(pos2[0])
    plon = math.radians(pos2[1])
    return 6371.01 * math.acos(math.sin(mlat)*math.sin(plat) + math.cos(mlat)*math.cos(plat)*math.cos(mlon - plon))
