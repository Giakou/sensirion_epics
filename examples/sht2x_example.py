#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for basic SHT85 functionality
"""

import sht2x
import time
import lib.log_utils

if __name__ == '__main__':
    logger = lib.log_utils.get_logger('INFO')

    # Create SHT85 object
    mysensor = sht2x.SHT2x(bus=1, mps=1, rep='high')

    # Check S/N
    logger.info(f'serial number = {mysensor.sn}')

    try:
        while True:
            # Single shot mode is preferred due to less current consumption (x8-x200) in idle state
            mysensor.single_shot()
            logger.info(f'Temperature = {mysensor.t} °C')
            logger.info(f'Relative Humidity = {mysensor.rh}%')
            logger.info(f'Dew Point = {mysensor.dp} °C')
            time.sleep(mysensor.mps)

    except (KeyboardInterrupt, SystemExit):
        logger.warning("Killing Thread...")
    finally:
        mysensor.stop()
