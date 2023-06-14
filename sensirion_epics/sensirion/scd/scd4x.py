#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SCD4x Python wrapper library of smbus2
"""

import time

import sensirion_epics.sensirion.sensirion_base as sensirion
import sensirion_epics.sensirion.sht.utils.conversion_utils as cu
import sensirion_epics.utils.log_utils as log_utils
import sensirion_epics.sensirion.scd.scd as scd

logger = log_utils.get_logger()


class SCD4x(scd.SCD):
    """SCD4x class"""
    def __init__(self, bus_intf=1, asc=1, frc=400, temp_offset=4, altitude_compensation=0, ambient_pressure=101300):
        """Constructor"""
        super().__init__()
        self._addr = 0x62
        self._bus_intf = bus_intf
        self.automatic_self_calibration = asc
        self.frc = frc
        self.temp_offset = temp_offset
        self.altitude_compensation = altitude_compensation
        self.ambient_pressure = ambient_pressure

    @sensirion.calculate_crc
    def _sn(self, cmd):
        """Output of the serial number"""
        self.stop()
        self.write_data_i2c(cmd, wait=0.001)
        self.read_data_i2c(9)
        serial_number = (self.buffer[0] << 40) + (self.buffer[1] << 32) + (self.buffer[3] << 24) \
            + (self.buffer[4] << 16) + (self.buffer[6] << 8) + self.buffer[7]
        return serial_number

    @property
    def sn(self):
        return self._sn(cmd=[0x36, 0x82])

    @sensirion.printer
    def periodic(self):
        """Start periodic measurement with signal update interval of 5 seconds"""
        self.stop()
        logger.debug(f'Starting periodic measurement...')
        self.write_data_i2c([0x21, 0xb1])

    @sensirion.printer
    def periodic_low_pwr(self):
        """Start low power periodic measurement with signal update interval of approximately 30 seconds"""
        self.stop()
        logger.debug(f'Starting low power periodic measurement...')
        self.write_data_i2c([0x21, 0xac])

    @sensirion.printer
    def stop(self):
        """Stop periodic measurement to change the sensor configuration or to save power. Note that the sensor will only
        respond to other commands after waiting 500 ms after issuing the stop command."""
        logger.debug('Issuing Stop Command...')
        self.write_data_i2c([0x3f, 0x86], wait=0.5)

    @property
    @sensirion.calculate_crc
    def ready_status(self):
        """Check if data is already written to the buffer and ready to read out"""
        self.write_data_i2c([0xe4, 0xb8], wait=0.001)
        self.read_data_i2c(3)
        # Bitwise AND with 0b0000011111111111 to check if the least significant 11 bits are 0
        return (self.buffer[0] << 8 | self.buffer[1]) & 0x7ff

    @sensirion.calculate_crc
    def read_measurement(self):
        """Readout single measurement during periodic measurement mode and signal conversion to physical values"""
        # The measurement data consists of 18 bytes (4 for each measurement value and 2 for each checksum)
        self.read_data_i2c(9)
        # CO2 in ppm
        self.co2 = self.buffer[0] << 8 | self.buffer[1]
        temp_digital = self.buffer[3] << 8 | self.buffer[4]
        # Temperature in °C
        self.t = self.temp_conversion(temp_digital)
        # Relative humidity in %
        rh_digital = self.buffer[6] << 8 | self.buffer[7]
        rhw = self.rhw_conversion(rh_digital)
        self.rh = rhw if self.t >= 0 else self.rhi_conversion(rhw)
        # Dew point in °C
        self.dp = cu.dew_point(self.t, self.rh)

    def fetch(self):
        """Fetch latest results from continuous measurement when ready"""
        while not self.ready_status:
            time.sleep(0.003)
        self.write_data_i2c([0xec, 0x05], wait=0.001)
        self.read_measurement()

    @property
    @sensirion.calculate_crc
    def automatic_self_calibration(self):
        """Get Automatic Self-Calibration (ASC) state"""
        self.stop()
        self.write_data_i2c([0x23, 0x13], wait=0.001)
        self.read_data_i2c(3)
        return self.buffer[0] << 8 | self.buffer[1]

    @automatic_self_calibration.setter
    @sensirion.printer
    def automatic_self_calibration(self, state):
        """Set the current state (enabled / disabled) of the automatic self-calibration. By default, ASC is enabled.
        To save the setting to the EEPROM, the persist_setting command must be issued."""
        assert state in [0, 1]
        state_bit = 0x01 if state else 0x00
        self.stop()
        self.write_data_i2c([0x24, 0x16, 0x00, state_bit], wait=0.001)

    @sensirion.printer
    @sensirion.calculate_crc
    def set_frc(self, co2_ppm):
        """Forced recalibration (FRC) is used to compensate for sensor drifts when a reference value of the CO2
        concentration in close proximity to the SCD30 is available. For best results, the sensor has to be run in a
        stable environment in continuous mode at a measurement rate of 2s for at least two minutes before applying the
        FRC command and sending the reference value. Setting a reference CO2 concentration by the method described here
        will always supersede corrections from the ASC and vice-versa. The reference CO2 concentration has to be within
        the range 400 ppm ≤ cref(CO2) ≤ 2000 ppm."""
        assert 400 <= co2_ppm <= 2000
        msb = (co2_ppm >> 8) & 0xFF
        lsb = co2_ppm & 0xFF
        self.stop()
        self.write_data_i2c([0x36, 0x2f, msb, lsb], wait=0.4)
        self.read_data_i2c(3)
        return self.buffer[0] << 8 | self.buffer[1]

    @property
    @sensirion.calculate_crc
    def temp_offset(self):
        """Get temperature offset in K/°C"""
        self.stop()
        self.write_data_i2c([0x23, 0x18], wait=0.001)
        self.read_data_i2c(3)
        offset_digital = self.buffer[0] << 8 | self.buffer[1]
        return 175 * offset_digital / (2 ** 16 - 1)

    @temp_offset.setter
    @sensirion.printer
    def temp_offset(self, offset):
        """Set temperature offset in K/°C"""
        if offset < 0 or offset > 20:
            logger.warning(f'Temperature offset will be set to {offset} °C, which is outside [0, 20] °C and it is not '
                           f'recommended!')
        self.stop()
        offset_digital = offset * (2 ** 16 - 1) / 175
        msb = (offset_digital >> 8) & 0xFF
        lsb = offset_digital & 0xFF
        self.write_data_i2c([0x24, 0x1d, msb, lsb], wait=0.001)

    @property
    @sensirion.calculate_crc
    def altitude_compensation(self):
        """Get height over sea level in m above 0 to compensate CO2 measurement for altitude differences."""
        self.stop()
        self.write_data_i2c([0x23, 0x22], wait=0.001)
        self.read_data_i2c(3)
        return self.buffer[0] << 8 | self.buffer[1]

    @altitude_compensation.setter
    @sensirion.printer
    def altitude_compensation(self, altitude):
        """Set height over sea level in m above 0 to compensate CO2 measurement for altitude differences."""
        self.stop()
        assert 0 <= altitude <= 3000
        msb = (altitude >> 8) & 0xFF
        lsb = altitude & 0xFF
        self.write_data_i2c([0x24, 0x27, msb, lsb], wait=0.001)

    @property
    @sensirion.calculate_crc
    def ambient_pressure(self):
        """Set ambient pressure during periodic commands."""
        self.write_data_i2c([0xe0, 0x00], wait=0.001)
        self.read_data_i2c(3)
        return (self.buffer[0] << 8 | self.buffer[1]) * 100

    @ambient_pressure.setter
    @sensirion.printer
    def ambient_pressure(self, pressure):
        """Set ambient pressure during periodic commands."""
        assert 70000 <= pressure <= 120000
        pressure /= 100
        msb = (pressure >> 8) & 0xFF
        lsb = pressure & 0xFF
        self.write_data_i2c([0xe0, 0x00, msb, lsb], wait=0.001)

    @sensirion.printer
    def persist_settings(self):
        """Configuration settings such as the temperature offset, sensor altitude and the ASC enabled/disabled parameter
        are by default stored in the volatile memory (RAM) only and will be lost after a power-cycle. The
        persist_settings command stores the current configuration in the EEPROM of the SCD4x, making them persistent
        across power-cycling. To avoid unnecessary wear of the EEPROM, the persist_settings command should only be sent
        when persistence is required and if actual changes to the configuration have been made. The EEPROM is guaranteed
        to endure at least 2000 write cycles before failure. Note that field calibration history (i.e. FRC and ASC) is
        automatically stored in a separate EEPROM dimensioned for the specified sensor lifetime."""
        self.stop()
        self.write_data_i2c([0x36, 0x15], wait=0.8)

    @sensirion.calculate_crc
    def self_test(self):
        """The perform_self_test feature can be used as an end-of-line test to check sensor functionality and the
        customer power supply to the sensor."""
        self.stop()
        self.write_data_i2c([0x36, 0x39], wait=10)
        self.read_data_i2c(3)
        malfunction = self.buffer[0] << 8 | self.buffer[1]
        if malfunction:
            logger.warning('Malfunction detected!')
        else:
            logger.info('Self-test detected no malfunctions.')

    @sensirion.printer
    def factory_reset(self):
        """The factory_reset command resets all configuration settings stored in the EEPROM and erases the
        FRC and ASC algorithm history."""
        self.stop()
        self.write_data_i2c([0x36, 0x32], wait=1.2)

    @sensirion.printer
    def reinit(self):
        """The reinit command re-initializes the sensor by reloading user settings from EEPROM. Before sending the
        reinit command, the stop measurement command must be issued. If the reinit command does not trigger the desired
        re-initialization, a power-cycle should be applied to the SCD4x."""
        self.stop()
        self.write_data_i2c([0x36, 0x46], wait=0.03)

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


class SCD41(SCD4x):
    """SCD41 class"""
    def __init__(self, bus_intf=1, asc=1, frc=400, temp_offset=4, altitude_compensation=0, ambient_pressure=101300,
                 asc_initial_period=44, asc_standard_period=156):
        """Constructor"""
        super().__init__(bus_intf=bus_intf, asc=asc, frc=frc, temp_offset=temp_offset,
                         altitude_compensation=altitude_compensation, ambient_pressure=ambient_pressure)
        self.asc_initial_period = asc_initial_period
        self.asc_standard_period = asc_standard_period

    def single_shot(self):
        """On-demand measurement of CO2 concentration, relative humidity and temperature. The sensor output is read
        using the read_measurement command (chapter 3.5.2)."""
        self.stop()
        self.write_data_i2c([0x21, 0x9d], wait=5)

    def single_shot_rht(self):
        """On-demand measurement of relative humidity and temperature only. The sensor output is read using the
        read_measurement command (chapter 3.5.2). CO2 output is returned as 0 ppm."""
        self.stop()
        self.write_data_i2c([0x21, 0x96], wait=0.05)

    @sensirion.printer
    def power_down(self):
        """Put the sensor from idle to sleep to reduce current consumption. Can be used to power down when operating the
        sensor in power-cycled single shot mode"""
        self.stop()
        self.write_data_i2c([0x36, 0xe0], wait=0.001)

    @sensirion.printer
    def wake_up(self):
        """Wake up the sensor from sleep mode into idle mode. To verify that the sensor is in the idle state after
        issuing the wake_up command, the serial number can be read out. Note that the first reading obtained using
        single_shot() after waking up the sensor should be discarded."""
        self.stop()
        self.write_data_i2c([0x36, 0xf6], wait=0.03)

    @property
    @sensirion.calculate_crc
    def asc_initial_period(self):
        self.stop()
        self.write_data_i2c([0x23, 0x40], wait=0.001)
        self.read_data_i2c(3)
        return self.buffer[0] << 8 | self.buffer[1]

    @asc_initial_period.setter
    @sensirion.printer
    def asc_initial_period(self, period):
        """Set the initial period for ASC correction (in hours) based on the single shot measurement interval.
        By default, the initial period for ASC correction is 44 hours. Allowed values are integer multiples of 4 hours.
        Note: a value of 0 results in an immediate correction. To save the setting to the EEPROM, the persist_settings
        command must be issued"""
        self.stop()
        assert period % 4 == 0
        msb = (period >> 8) & 0xFF
        lsb = period & 0xFF
        self.write_data_i2c([0x24, 0x45, msb, lsb], wait=0.001)

    @property
    @sensirion.calculate_crc
    def asc_standard_period(self):
        """Get the standard period for ASC correction (in hours) based on the single shot measurement interval."""
        self.stop()
        self.write_data_i2c([0x23, 0x4b], wait=0.001)
        self.read_data_i2c(3)
        return self.buffer[0] << 8 | self.buffer[1]

    @asc_standard_period.setter
    @sensirion.printer
    def asc_standard_period(self, period):
        """Set the standard period for ASC correction (in hours) based on the single shot measurement interval.
        By default, the standard period for ASC correction is 156 hours. Allowed values are integer multiples
        of 4 hours. To save the setting to the EEPROM, the persist_settings command must be issued."""
        self.stop()
        assert period % 4 == 0
        msb = (period >> 8) & 0xFF
        lsb = period & 0xFF
        self.write_data_i2c([0x24, 0x4e, msb, lsb], wait=0.001)
