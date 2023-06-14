#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Helper library for value conversion
"""

import math

# Magnus coefficients from
# https://sensirion.com/media/documents/8AB2AD38/61642ADD/Sensirion_AppNotes_Humidity_Sensors_Introduction_to_Relative_Humidit.pdf
MC = {
    'water': {
        'alpha': 6.112,  # in hPa
        'beta': 17.62,
        'lambda': 243.12  # in degrees Celsius
    },
    'ice': {
        'alpha': 6.112,  # in hPa
        'beta': 22.46,
        'lambda': 272.62  # in degrees Celsius
    }
}


def dew_point(t, rh):
    """Calculate dew point from temperature and relative humidity using Magnus formula. For more info:
    https://sensirion.com/media/documents/8AB2AD38/61642ADD/Sensirion_AppNotes_Humidity_Sensors_Introduction_to_Relative_Humidit.pdf"""

    t_range = 'water' if t >= 0 else 'ice'
    # Define some custom constants to make the Magnus formula more readable
    c1 = MC[t_range]['beta'] * t / (MC[t_range]['lambda'] + t)
    c2 = math.log(rh / 100.0)

    # Magnus formula for calculating the dew point
    dew_p = MC[t_range]['lambda'] * (c2 + c1) / (MC[t_range]['beta'] - c2 - c1)
    return round(dew_p, 2)
