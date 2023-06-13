#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SHT85 Python wrapper library of smbus2
"""

import sensirion_epics.sensirion_i2c.sensirion_i2c as sensirion_i2c
import sensirion_epics.utils.log_utils as log_utils
import sensirion_epics.sensirion_i2c.sht.sht as sht

logger = log_utils.get_logger()


class SHT85(sht.SHT):
    """SHT85 class"""
    def __init__(self, bus_intf=1, rep='high', mps=1):
        """Constructor"""
        super().__init__()

        self._addr = 0x44
        self._bus_intf = bus_intf
        # Assertion checks
        assert rep in ['high', 'medium', 'low'], f'Repetition number "{rep}" is not allowed, ' \
                                                 'only "high", "medium" or "low"!'
        assert mps in [0.5, 1, 2, 4, 10], f'Measurements per second number "{mps}" is not allowed, '\
                                          'only 0.5, 1, 2, 4, 10!'

        self.rep = rep
        self.mps = mps

    @property
    def sn(self):
        return self._sn(cmd=[0x36, 0x82])

    @property
    def status(self):
        """Read Status Register"""
        self.write_data_i2c([0xF3, 0x2D])
        self.read_data_i2c(3)
        status = self.buffer[0] << 8 | self.buffer[1]
        status_to_bit = f'{status:016b}'
        status_dict = {
            'Checksum status': status_to_bit[0],
            'Command status': status_to_bit[1],
            'System reset': status_to_bit[4],
            'T tracking alert': status_to_bit[10],
            'RH tracking alert': status_to_bit[11],
            'Heater status': status_to_bit[13],
            'Alert pending status': status_to_bit[15]
        }
        return status_dict

    def check_status_for_non_default(self):
        """Check Status Register for non-default values"""
        status = self.status
        default_status_dict = {
            'Checksum status': '0',
            'Command status': '0',
            'System reset': '0',
            'T tracking alert': '0',
            'RH tracking alert': '0',
            'Heater status': '0',
            'Alert pending status': '0'
        }
        non_default_status_dict = {key: value for key, value in status.items() if value != default_status_dict[key]}
        for key, value in non_default_status_dict.items():
            if key == 'Checksum status':
                logger.warning('Checksum of last write transfer failed!')
            elif key == 'Command status':
                logger.warning('Last command not processed! It was either invalid or failed the integrated command '
                               'checksum!')
            elif key == 'System reset':
                logger.warning('no reset detected since last "clearstatus register" command!')
            elif key == 'T tracking alert':
                logger.warning('T tracking alert!')
            elif key == 'RH tracking alert':
                logger.warning('RH tracking alert!')
            elif key == 'Heater status':
                logger.warningn('Heater is ON!')
            elif key == 'Alert pending status':
                logger.warning('At least one pending alert!')

    def single_shot(self):
        """Single Shot Data Acquisition Mode"""
        rep_code = {
            'high': [0x24, 0x00],
            'medium': [0x24, 0x0B],
            'low': [0x24, 0x16]
        }
        self.write_data_i2c(rep_code[self.rep])
        self.read_measurement()

    @sensirion_i2c.printer
    def periodic(self):
        """Start Periodic Data Acquisition Mode"""
        periodic_code = {
            0.5: {
                'high': [0x20, 0x32],
                'medium': [0x20, 0x24],
                'low': [0x20, 0x2F]
            },
            1: {
                'high': [0x21, 0x30],
                'medium': [0x21, 0x26],
                'low': [0x21, 0x2D]
            },
            2: {
                'high': [0x22, 0x36],
                'medium': [0x22, 0x20],
                'low': [0x22, 0x2B]
            },
            4: {
                'high': [0x23, 0x34],
                'medium': [0x23, 0x22],
                'low': [0x23, 0x29]
            },
            10: {
                'high': [0x27, 0x37],
                'medium': [0x27, 0x21],
                'low': [0x27, 0x2A]
            }
        }
        logger.info(f'Initiating Periodic Data Acquisition with frequency of "{self.mps} Hz" and '
                    f'"{self.rep}" repetition...')
        self.write_data_i2c(periodic_code[self.mps][self.rep])

    @sensirion_i2c.printer
    def fetch(self):
        """Fetch command to transmit the measurement data. After the transmission the data memory is cleared"""
        logger.debug('Fetching data...')
        self.write_data_i2c([0xE0, 0x00])

    @sensirion_i2c.printer
    def art(self):
        """Start the Accelerated Response Time (ART) feature"""
        logger.info('Activating Accelerated Response Time (ART)...')
        self.write_data_i2c([0x2B, 0x32])

    @sensirion_i2c.printer
    def stop(self):
        """Break command to stop Periodic Data Acquisition Mode or ART feature"""
        logger.debug('Issuing Break Command...')
        self.write_data_i2c([0x30, 0x93])

    @sensirion_i2c.printer
    def reset(self):
        """Apply Soft Reset"""
        self.stop()
        logger.debug('Applying Soft Reset...')
        self.write_data_i2c([0x30, 0xA2])

    @sensirion_i2c.printer
    def enable_heater(self):
        """Enable heater"""
        logger.warning('Enabling heater...')
        self.write_data_i2c([0x30, 0x6D])

    @sensirion_i2c.printer
    def disable_heater(self):
        """Disable heater"""
        logger.info('Disabling heater...')
        self.write_data_i2c([0x30, 0x66])

    @sensirion_i2c.printer
    def clear_status(self):
        """Clear Status Register"""
        logger.info('Clearing Status Register...')
        self.write_data_i2c([0x30, 0x41])

    def temp_conversion(self, temp_digital):
        """Calculate temperature from data"""
        # Significant digits based on the SHT85 resolution of 0.01 degrees Celsius
        return round(-45 + 175 * temp_digital / (2 ** 16 - 1), 2)

    def rhw_conversion(self, rh_digital):
        """Calculate relative humidity from data"""
        # Significant digits based on the SHT85 resolution of 0.01 %RH
        rh_analog = round(100 * rh_digital / (2 ** 16 - 1), 2)
        # Make sure that relative humidity never returns a 0% value, otherwise the dew point calculation will fail
        rh_analog = 1e-3 if rh_analog < 0.01 else rh_analog
        return rh_analog
