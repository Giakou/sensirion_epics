#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for basic SCD41 functionality
"""
import time
import sensirion_epics.sensirion.scd.scd4x as scd4x
import sensirion_epics.utils.log_utils as log_utils

if __name__ == '__main__':
    logger = log_utils.get_logger('INFO')

    # Create SCD41 object
    mysensor = scd4x.SCD41(bus_intf=1)

    with mysensor.i2c_daq():
        # Perform a self test to check that sensor is okay
        mysensor.self_test()
        # Check S/N
        logger.info(f'serial number = {mysensor.sn}')
        t_old = time.time()
        while True:
            if time.time() - t_old > 5:
                # Take single measurement
                mysensor.single_shot()
                # Fetch data when ready
                mysensor.fetch()
                logger.info(f'CO2 concentration = {mysensor.co2} ppm')
                logger.info(f'Temperature = {mysensor.t} °C')
                logger.info(f'Relative Humidity = {mysensor.rh}%')
                logger.info(f'Dew Point = {mysensor.dp} °C')
                t_old = time.time()
