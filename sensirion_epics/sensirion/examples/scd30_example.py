#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for basic SCD30 functionality
"""

import sensirion_epics.sensirion.scd.scd30 as scd30
import sensirion_epics.utils.log_utils as log_utils

if __name__ == '__main__':
    logger = log_utils.get_logger('INFO')

    # Create SCD30 object
    mysensor = scd30.SCD30(bus_intf=1)

    with mysensor.i2c_daq():
        # Check firmware version
        logger.info(f'firmware version = {mysensor.firmware_version}')
        # Check S/N
        logger.info(f'serial number = {mysensor.sn}')
        # Start continuous measurement
        mysensor.continuous_meas()
        while True:
            # Fetch data when ready
            mysensor.fetch()
            logger.info(f'CO2 concentration = {mysensor.co2} ppm')
            logger.info(f'Temperature = {mysensor.t} °C')
            logger.info(f'Relative Humidity = {mysensor.rh}%')
            logger.info(f'Dew Point = {mysensor.dp} °C')
