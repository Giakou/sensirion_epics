#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for basic SCD4x functionality
"""

import sensirion_epics.sensirion.scd.scd4x as scd4x
import sensirion_epics.utils.log_utils as log_utils

if __name__ == '__main__':
    logger = log_utils.get_logger('INFO')

    # Create SCD4x object
    mysensor = scd4x.SCD4x(bus_intf=1)

    with mysensor.i2c_daq():
        # Perform a self test to check that sensor is okay
        mysensor.self_test()
        # Check S/N
        logger.info(f'serial number = {mysensor.sn}')
        # Start periodic measurement with 30 seconds measurement interval
        mysensor.periodic_low_pwr()
        while True:
            # Fetch data when ready
            mysensor.fetch()
            logger.info(f'CO2 concentration = {mysensor.co2} ppm')
            logger.info(f'Temperature = {mysensor.t} °C')
            logger.info(f'Relative Humidity = {mysensor.rh}%')
            logger.info(f'Dew Point = {mysensor.dp} °C')
