#!/usr/bin/env python

"""
Changed a lot of a Script originall created by Ralf Zimmermann (mail@ralfzimmermann.de) in 2020.
The orginal code and its documentation can be found on: https://github.com/RalfZim/venus.dbus-fronius-smartmeter
Used https://github.com/victronenergy/velib_python/blob/master/dbusdummyservice.py as basis for this service.
"""

"""
/data/Pathtothisscript/vedbus.py
/data/Pathtothisscript/ve_utils.py
python -m ensurepip --upgrade
pip install paho-mqtt
"""


# our own packages
from vedbus import VeDbusService
import paho.mqtt.client as mqtt
import os
import json
import sys
import time
import logging
from logging.handlers import RotatingFileHandler
import platform
from gi.repository import GLib as gobject  # Python 3.x
import _thread as thread   # for daemon = True  / Python 3.x

sys.path.insert(1, os.path.join(
    os.path.dirname(__file__), '../ext/velib_python'))

os.makedirs('/var/log/dbus-tasmota-inverter', exist_ok=True) 
logging.basicConfig(
    format = '%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
    datefmt = '%Y-%m-%d %H:%M:%S',
    level = logging.DEBUG,
    handlers = [
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler = RotatingFileHandler('/var/log/dbus-tasmota-inverter/current.log', maxBytes=200000, backupCount=5)
handler.setLevel(logging.DEBUG)
handler.setFormatter(formatter)
logger.addHandler(handler)

# MQTT Setup
broker_address = "192.168.178.46"
MQTTNAME = "MQTT_to_Inverter"

devices = {
    'L1': {'mqttpath': '',  'power': 0, 'voltage': 0, 'current': 0, 'total': 0, 'path': ''},
    'L2': {'mqttpath': 'tele/stadtweg/ga/pvgarten/SENSOR', 'power': 0, 'voltage': 0, 'current': 0, 'total': 0, 'path': ''},
    'L3': {'mqttpath': 'tele/stadtweg/eg/growatt/SENSOR',  'power': 0, 'voltage': 0, 'current': 0, 'total': 0, 'path': ''},
}

# MQTT Abfragen:
def on_disconnect(client, userdata, rc):
    logger.info("Client Got Disconnected")
    if rc != 0:
        logger.info('Unexpected MQTT disconnection. Will auto-reconnect')

    else:
        logger.info('rc value:' + str(rc))

    try:
        logger.info("Trying to Reconnect")
        client.connect(broker_address)
    except Exception as e:
        logger.exception("Error in Retrying to Connect with Broker")
        logger.exception(e)

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Connected to MQTT Broker!")
        if devices['L1']['mqttpath'] != '':
            client.subscribe(devices['L1']['mqttpath'])
        if devices['L2']['mqttpath'] != '':
            client.subscribe(devices['L2']['mqttpath'])
        if devices['L3']['mqttpath'] != '':
            client.subscribe(devices['L3']['mqttpath'])
    else:
        logger.info("Failed to connect, return code %d\n", rc)

def on_message(client, userdata, msg):
    try:

        # logger.debug(msg.topic)

        if msg.topic == devices['L1']['mqttpath']:
            jsonpayload = json.loads(msg.payload)
            devices['L1']['power'] = float(jsonpayload["ENERGY"]["Power"])
            devices['L1']['current'] = float(jsonpayload["ENERGY"]["Current"])
            devices['L1']['voltage'] = float(jsonpayload["ENERGY"]["Voltage"])
            devices['L1']['total'] = float(jsonpayload["ENERGY"]["Total"])

        if msg.topic == devices['L2']['mqttpath']:
            jsonpayload = json.loads(msg.payload)
            devices['L2']['power'] = float(jsonpayload["ENERGY"]["Power"])
            devices['L2']['current'] = float(jsonpayload["ENERGY"]["Current"])
            devices['L2']['voltage'] = float(jsonpayload["ENERGY"]["Voltage"])
            devices['L2']['total'] = float(jsonpayload["ENERGY"]["Total"])

        if msg.topic == devices['L3']['mqttpath']:
            jsonpayload = json.loads(msg.payload)
            devices['L3']['power'] = float(jsonpayload["ENERGY"]["Power"])
            devices['L3']['current'] = float(jsonpayload["ENERGY"]["Current"])
            devices['L3']['voltage'] = float(jsonpayload["ENERGY"]["Voltage"])
            devices['L3']['total'] = float(jsonpayload["ENERGY"]["Total"])

    except Exception as e:
        logger.exception(
            "Programm Tasmota Inverter ist abgestuerzt. (on message Funkion)")
        logger.exception(e)

class DbusDummyService:
    def __init__(self, servicename, deviceinstance, paths, productname='Tasmota Inverter', connection='MQTT'):
        self._dbusservice = VeDbusService(servicename)
        self._paths = paths

        logger.debug("%s /DeviceInstance = %d" %
                      (servicename, deviceinstance))

        # Create the management objects, as specified in the ccgx dbus-api document
        self._dbusservice.add_path('/Mgmt/ProcessName', __file__)
        self._dbusservice.add_path(
            '/Mgmt/ProcessVersion', 'Unkown version, and running on Python ' + platform.python_version())
        self._dbusservice.add_path('/Mgmt/Connection', connection)

        # Create the mandatory objects
        self._dbusservice.add_path('/DeviceInstance', deviceinstance)
        # value used in ac_sensor_bridge.cpp of dbus-cgwacs
        self._dbusservice.add_path('/ProductId', 16)
        self._dbusservice.add_path('/ProductName', productname)
        self._dbusservice.add_path('/FirmwareVersion', 0.1)
        self._dbusservice.add_path('/HardwareVersion', 0)
        self._dbusservice.add_path('/Connected', 1)
        self._dbusservice.add_path('/StatusCode', 0)
        self._dbusservice.add_path('/Position', 0)
        self._dbusservice.add_path('/Latency', None)

        for path, settings in self._paths.items():
            self._dbusservice.add_path(
                path, settings['initial'], writeable=True, onchangecallback=self._handlechangedvalue)

        # pause 1000ms before the next request
        gobject.timeout_add(1000, self._update)

        # add _signOfLife 'timer' to get feedback in log every 5minutes
        gobject.timeout_add(5 * 60 * 1000, self._signOfLife)

    def _signOfLife(self):
        logger.info("Service is running")

    def _update(self):
        self._dbusservice['/Ac/Power'] = devices['L1']['power'] + \
            devices['L2']['power'] + devices['L3']['power']
        self._dbusservice['/Ac/L1/Voltage'] = devices['L1']['voltage']
        self._dbusservice['/Ac/L2/Voltage'] = devices['L2']['voltage']
        self._dbusservice['/Ac/L3/Voltage'] = devices['L3']['voltage']
        self._dbusservice['/Ac/L1/Current'] = devices['L1']['current']
        self._dbusservice['/Ac/L2/Current'] = devices['L2']['current']
        self._dbusservice['/Ac/L3/Current'] = devices['L3']['current']
        self._dbusservice['/Ac/L1/Power'] = devices['L1']['power']
        self._dbusservice['/Ac/L2/Power'] = devices['L2']['power']
        self._dbusservice['/Ac/L3/Power'] = devices['L3']['power']

        index = self._dbusservice['/UpdateIndex'] + 1  # increment index
        if index > 255:   # maximum value of the index
            index = 0       # overflow from 255 to 0
        self._dbusservice['/UpdateIndex'] = index
        return True

    def _handlechangedvalue(self, path, value):
        logger.debug("someone else updated %s to %s" % (path, value))
        return True  # accept the change


def main():
    thread.daemon = True  # allow the program to quit

    from dbus.mainloop.glib import DBusGMainLoop
    # Have a mainloop, so we can send/receive asynchronous calls to and from dbus
    DBusGMainLoop(set_as_default=True)

    pvac_output = DbusDummyService(
        servicename='com.victronenergy.pvinverter.tasmota',
        deviceinstance=0,
        paths={
            '/Ac/Power': {'initial': 0},
            '/Ac/L1/Voltage': {'initial': 0},
            '/Ac/L2/Voltage': {'initial': 0},
            '/Ac/L3/Voltage': {'initial': 0},
            '/Ac/L1/Current': {'initial': 0},
            '/Ac/L2/Current': {'initial': 0},
            '/Ac/L3/Current': {'initial': 0},
            '/Ac/L1/Power': {'initial': 0},
            '/Ac/L2/Power': {'initial': 0},
            '/Ac/L3/Power': {'initial': 0},
            '/Ac/Energy/Forward': {'initial': 0}, # energy bought from the grid
            '/Ac/Energy/Reverse': {'initial': 0},  # energy sold to the grid
            '/UpdateIndex': {'initial': 0},
        })

    logger.info(
        'Connected to dbus, and switching over to gobject.MainLoop() (= event based)')
    mainloop = gobject.MainLoop()
    mainloop.run()


# Konfiguration MQTT
client = mqtt.Client(MQTTNAME)  # create new instance
client.on_disconnect = on_disconnect
client.on_connect = on_connect
client.on_message = on_message
client.connect(broker_address)  # connect to broker

client.loop_start()

if __name__ == "__main__":
    main()
