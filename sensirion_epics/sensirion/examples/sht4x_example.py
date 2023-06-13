#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for basic SHT4x functionality
"""

import sensirion_epics.sensirion.sht.sht4x as sht4x
import time
import sensirion_epics.utils.log_utils as log_utils

if __name__ == '__main__':
    logger = log_utils.get_logger('INFO')

    # Create SHT4x object
    mysensor = sht4x.SHT4x(addr=0x45, bus_intf=1, rep='high')

    # Check S/N
    logger.info(f'serial number = {mysensor.sn}')

    with mysensor.i2c_daq():
        # Check S/N
        logger.info(f'serial number = {mysensor.sn}')
        while True:
            mysensor.single_shot()
            logger.info(f'Temperature = {mysensor.t} °C')
            logger.info(f'Relative Humidity = {mysensor.rh}%')
            logger.info(f'Dew Point = {mysensor.dp} °C')
            time.sleep(1)
