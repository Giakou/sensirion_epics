#!/usr/bin/python3

import time
import sensirion_epics.sensirion_i2c.sht.sht85 as sht85
from pcaspy import Driver, SimpleServer

prefix = 'sht85'
pvdb = {
    'temperature': {
        'prec': 3,
        'type': 'float',
        'unit': '°C',
        'mdel': -1
    },
    'rel_humidity': {
        'prec': 2,
        'type': 'float',
        'unit': '%',
        'mdel': -1
    },
    'dew_point': {
        'prec': 3,
        'type': 'float',
        'unit': '°C',
        'mdel': -1
    }
}


if __name__ == '__main__':
    # Instantiating the Server for CA requests
    server = SimpleServer()
    # Creating PVs
    server.createPV(prefix, pvdb)
    # Instantiating the Driver
    driver = Driver()
    # Instantiate the SHT85 sensor
    mysht = sht85.SHT85(bus_intf=1, rep='high', mps=1)
    start_time = time.time()
    with mysht.i2c_daq():
        # Check S/N
        print(f'serial number = {mysht.sn}')
        while True:
            t = time.time()
            # measure and update the PV value every 4 seconds
            if (t - start_time) >= 4:
                # Take a single measurement in single shot mode
                mysht.single_shot()
                # Set PV values
                driver.setParam('temperature', mysht.t)
                driver.setParam('rel_humidity', mysht.rh)
                driver.setParam('dew_point', mysht.dp)
                # Update PVs
                driver.update()
                server.process(0.1)
