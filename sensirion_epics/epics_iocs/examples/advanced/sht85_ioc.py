#!/usr/bin/python3

import os
import time
import traceback
import yaml
import sensirion_epics.sensirion.sht.sht85 as sht85
from contextlib import ExitStack
from sensirion_epics.utils import log_utils
from datetime import datetime
from pcaspy import Driver, SimpleServer


class SHT85Server(SimpleServer):
    """SHT85 server which responds to the CA requests"""
    def __int__(self):
        """Constructor"""
        super().__init__()

    def create_pvs(self, pv_config):
        """Define the PV database and create the PVs based on the configuration yaml file"""

        # Define the dictionary with all the climate monitoring PV names
        pvdb = {
            ':'.join([pv_config['prefix'], s_name, pv_name]): {
                attr: value
                for attr, value in pv_attrs.items() if attr not in ['lut', 'error_value']
            }
            for s_name in pv_config['sensor'].keys()
            for pv_name, pv_attrs in pv_config['pv_names'].items()
        }
        logger.info(pvdb)
        # Create the PVs
        self.createPV('', pvdb)


class SHT85Driver(Driver):
    """SHT85 driver which handles the CA requests"""

    def __init__(self):
        """Constructor"""
        super().__init__()

    def read(self, reason):
        """Wrapper method to read the value of the PV"""
        return self.getParam(reason)

    def write(self, reason, value):
        """Wrapper method to write a value to a PV"""
        self.setParam(reason, value)

    def write_pvs(self, s_name, s, pv_config, error_values=False):
        """Write PV values"""
        dt = datetime.now()
        log_message = ''
        if error_values:
            for pv in self.pvDB.keys():
                param = pv.replace(':'.join([pv_config['prefix'], s_name, '']), '')
                value = pv_config['pv_names'][param]['error_value']
                self.write(pv, value)
                log_message += f'\n{pv} = {value}'
        else:
            for pv in self.pvDB.keys():
                if ''.join([':', s_name, ':']) in pv:
                    param = pv.replace(':'.join([pv_config['prefix'], s_name, '']), '')
                    attr = getattr(s, pv_config['pv_names'][param]['lut'])
                    self.write(pv, attr)
                    log_message += f'\n{pv} = {attr} {pv_config["pv_names"][param]["unit"]}'
        return log_message

    @staticmethod
    def stop_sensors(sensors):
        """Issue break command to all the sensors"""
        logger.info('Issuing "break" command to sensors...')
        for s in sensors.values():
            s.stop()


def main():
    """Main function"""

    logger.info('Reading configuration from the yaml file...')
    with open(os.path.abspath(os.path.join(os.path.dirname(__file__), 'sht85_config_custom.yaml')), 'r') as file:
        pv_config = yaml.safe_load(file)

    logger.info('Instantiating the server for CA requests...')
    server = SHT85Server()

    logger.info('Creating PVs...')
    server.create_pvs(pv_config)

    logger.info('Instantiating the SHT85Driver...')
    driver = SHT85Driver()

    logger.info('Creating the SHT85 objects...')
    sensors = {
        name: sht85.SHT85(**s_config)
        for name, s_config in pv_config['sensor'].items()
    }

    with ExitStack() as stack:
        _ = [stack.enter_context(s.i2c_daq()) for s in sensors.values()]

        logger.info('Resetting SHT85 sensors...')
        for s in sensors.values():
            s.clear_status()
            s.reset()

        # Scan sensor parameters, write PVs and update them
        old_time = time.time()
        it = 0
        while True:
            try:
                if time.time() - old_time > pv_config['scan']:
                    for s_name, s in sensors.items():
                        # Take single shot data and update the sensor properties
                        # The average current consumption of the sensor is significantly lower compared to periodic mode
                        s.single_shot()
                        # Checking status register
                        s.check_status_for_non_default()
                        # Write the corresponding PVs
                        log_message = driver.write_pvs(s_name, s, pv_config)
                        if not (it % 10):
                            it = 0
                            logger.info(log_message)
                    old_time = time.time()
                    it += 1
            except Exception as err:
                traceback.print_tb(err.__traceback__)
                # Maybe the sensor got stuck? Issue a soft reset
                for s_name, s in sensors.items():
                    log_message = driver.write_pvs(s_name, s, pv_config, error_values=True)
                    logger.warning(log_message)
                    logger.warning('Sending soft reset to the sensor!')
                    s.reset()
            finally:
                # Update the PVs
                driver.updatePVs()
                # Process CA transactions
                server.process(0.1)


if __name__ == '__main__':
    logger = log_utils.get_logger('INFO')
    logger.info('Start of the SHT85 advanced IOC...')
    main()
