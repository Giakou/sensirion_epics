#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SCD30 Python wrapper library of smbus2
"""

import time

import sensirion_epics.sensirion.sensirion_base as sensirion
import sensirion_epics.utils.log_utils as log_utils
import sensirion_epics.sensirion.scd.scd as scd

logger = log_utils.get_logger()


class SCD30(scd.SCD):
    """SCD30 class"""
    def __init__(self, bus_intf=1, meas_interval=2, asc=0, frc=400, temp_offset=0, altitude_compensation=0):
        """Constructor"""
        super().__init__()
        self._addr = 0x61
        self._bus_intf = bus_intf
        self.meas_interval = meas_interval
        self.automatic_self_calibration = asc
        self.frc = frc
        self.temp_offset = temp_offset
        self.altitude_compensation = altitude_compensation

    @property
    def sn(self):
        return self._sn(cmd=[0xD0])

    @sensirion.printer
    def reset(self):
        """Apply Soft Reset to force the sensor to the same state as after powering up"""
        logger.debug('Applying Soft Reset...')
        self.write_data_i2c([0xD3, 0x04])

    @sensirion.printer
    def continuous_meas(self, amb_pressure):
        """Starting continuous measurement with ambient pressure compensation"""
        assert amb_pressure == 0 or 700 <= amb_pressure <= 1200
        logger.debug(f'Starting continuous measurement with ambient pressure compensation of {amb_pressure} mBar...')
        msb = (amb_pressure >> 8) & 0xFF
        lsb = amb_pressure & 0xFF
        self.write_data_i2c([0x00, 0x10, msb, lsb])

    @sensirion.printer
    def stop(self):
        """Stop command to stop continuous measurement"""
        logger.debug('Issuing Stop Command...')
        self.write_data_i2c([0x01, 0x04])

    @property
    @sensirion.calculate_crc
    def meas_interval(self):
        self.write_data_i2c([0x46, 0x00])
        self.read_data_i2c(3)
        return self.buffer[0] << 8 | self.buffer[1]

    @meas_interval.setter
    @sensirion.printer
    def meas_interval(self, interval):
        """Set measurement interval of continuous measurement"""
        assert 2 <= interval <= 1800
        logger.debug(f'Setting measurement interval of {interval} s...')
        msb = (interval >> 8) & 0xFF
        lsb = interval & 0xFF
        self.write_data_i2c([0x46, 0x00, msb, lsb])

    @property
    @sensirion.calculate_crc
    def ready_status(self):
        self.write_data_i2c([0x02, 0x02])
        self.read_data_i2c(3)
        return self.buffer[0] << 8 | self.buffer[1]

    def fetch(self):
        """Fetch latest results from continuous measurement when ready"""
        while not self.ready_status:
            time.sleep(0.003)
        self.write_data_i2c([0x03, 0x00])
        time.sleep(0.003)
        self.read_measurement()

    @property
    @sensirion.calculate_crc
    def automatic_self_calibration(self):
        """Get Automatic Self-Calibration (ASC) state"""
        self.write_data_i2c([0x53, 0x06])
        self.read_data_i2c(3)
        return self.buffer[0] << 8 | self.buffer[1]

    @automatic_self_calibration.setter
    @sensirion.printer
    def automatic_self_calibration(self, state):
        """Continuous Automatic Self-Calibration (ASC) can be (de-)activated with this command. When activated for the
        first time a period of minimum 7 days is needed so that the algorithm can find its initial parameter set for
        ASC. The sensor has to be exposed to fresh air for at least 1 hour every day. Also during that period, the
        sensor may not be disconnected from the power supply, otherwise the procedure to find calibration parameters is
        aborted and has to be restarted from the beginning. The successfully calculated parameters are stored in
        non-volatile memory of the SCD30 having the effect that after a restart the previously found parameters for ASC
        are still present. Note that the most recently found self-calibration parameters will be actively used for
        self-calibration disregarding the status of this feature. Finding a new parameter set by the here described
        method will always overwrite the settings from external recalibration and vice-versa. The feature is switched
        off by default. To work properly SCD30 has to see fresh air on a regular basis. Optimal working conditions are
        given when the sensor sees fresh air for one hour every day so that ASC can constantly re-calibrate. ASC only
        works in continuous measurement mode. ASC status is saved in non-volatile memory. When the sensor is powered
        down while ASC is activated SCD30 will continue with automatic self-calibration after repowering without
        sending the command."""
        assert state in [0, 1]
        state_bit = 0x01 if state else 0x00
        self.write_data_i2c([0x53, 0x06, 0x00, state_bit])

    @property
    @sensirion.calculate_crc
    def frc(self):
        """Get Forced Recalibration Value (FRC)"""
        self.write_data_i2c([0x52, 0x04])
        self.read_data_i2c(3)
        return self.buffer[0] << 8 | self.buffer[1]

    @frc.setter
    @sensirion.printer
    def frc(self, co2_ppm):
        """Forced recalibration (FRC) is used to compensate for sensor drifts when a reference value of the CO2
        concentration in close proximity to the SCD30 is available. For best results, the sensor has to be run in a
        stable environment in continuous mode at a measurement rate of 2s for at least two minutes before applying the
        FRC command and sending the reference value. Setting a reference CO2 concentration by the method described here
        will always supersede corrections from the ASC and vice-versa. The reference CO2 concentration has to be within
        the range 400 ppm ≤ cref(CO2) ≤ 2000 ppm."""
        assert 400 <= co2_ppm <= 2000
        msb = (co2_ppm >> 8) & 0xFF
        lsb = co2_ppm & 0xFF
        self.write_data_i2c([0x52, 0x04, msb, lsb])

    @property
    @sensirion.calculate_crc
    def temp_offset(self):
        """Get temperature offset in K/°C"""
        self.write_data_i2c([0x54, 0x03])
        self.read_data_i2c(3)
        return (self.buffer[0] << 8 | self.buffer[1]) / 100

    @temp_offset.setter
    @sensirion.printer
    def temp_offset(self, offset):
        """Set temperature offset in K/°C"""
        offset *= 100
        msb = (offset >> 8) & 0xFF
        lsb = offset & 0xFF
        self.write_data_i2c([0x54, 0x03, msb, lsb])

    @property
    @sensirion.calculate_crc
    def altitude_compensation(self):
        """Get height over sea level in m above 0 to compensate CO2 measurement for altitude differences."""
        self.write_data_i2c([0x51, 0x02])
        self.read_data_i2c(3)
        return self.buffer[0] << 8 | self.buffer[1]

    @altitude_compensation.setter
    @sensirion.printer
    def altitude_compensation(self, altitude):
        """Set height over sea level in m above 0 to compensate CO2 measurement for altitude differences."""
        msb = (altitude >> 8) & 0xFF
        lsb = altitude & 0xFF
        self.write_data_i2c([0x51, 0x02, msb, lsb])

    @property
    @sensirion.calculate_crc
    def firmware_version(self):
        """Get firmware version in Major.Minor format"""
        self.write_data_i2c([0xD1, 0x00])
        self.read_data_i2c(3)
        return f'{self.buffer[0]}.{self.buffer[1]}'
