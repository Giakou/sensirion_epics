#!/usr/bin/python3

import time
import sensirion_epics.sensirion.scd.scd30 as scd30
from pcaspy import Driver, SimpleServer

prefix = 'scd30'
pvdb = {
    'co2_concentration': {
        'prec': 3,
        'type': 'float',
        'unit': 'ppm',
        'mdel': -1
    },
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
    myscd = scd30.SCD30(bus_intf=1)
    start_time = time.time()

    # Start context manager
    with myscd.i2c_daq():
        # Start continuous measurement with default settings
        myscd.continuous_meas()
        while True:
            t = time.time()
            # measure and update the PV value every 4 seconds
            if (t - start_time) >= 4:
                # Fetch data when ready
                myscd.fetch()
                # Set PV values
                driver.setParam('co2_concentration', myscd.co2)
                driver.setParam('temperature', myscd.t)
                driver.setParam('rel_humidity', myscd.rh)
                driver.setParam('dew_point', myscd.dp)
                # Update PVs
                driver.update()
                server.process(0.1)
