#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for basic SHT2x functionality
"""

import sensirion_epics.sensirion.sht.sht2x as sht2x
import time
import sensirion_epics.utils.log_utils as log_utils

if __name__ == '__main__':
    logger = log_utils.get_logger('INFO')

    # Create SHT85 object
    mysensor = sht2x.SHT2x(bus_intf=1, mode='hold')

    # Check S/N
    logger.info(f'serial number = {mysensor.sn}')

    with mysensor.i2c_daq():
        # Check S/N
        logger.info(f'serial number = {mysensor.sn}')
        while True:
            mysensor.single_shot(param='t')
            logger.info(f'Temperature = {mysensor.t} °C')
            mysensor.single_shot(param='rh')
            logger.info(f'Relative Humidity = {mysensor.rh}%')
            logger.info(f'Dew Point = {mysensor.dp} °C')
            time.sleep(1)
