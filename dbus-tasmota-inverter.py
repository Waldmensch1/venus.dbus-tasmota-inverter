#!/usr/bin/env python

"""
Created by Waldmensch aka Waldmaus in 2023.

Inspired by:
 - https://github.com/Marv2190/venus.dbus-MqttToGridMeter (Inspiration)
 - https://github.com/victronenergy/velib_python/blob/master/dbusdummyservice.py (Template)


This code and its documentation can be found on: https://github.com/Waldmensch1/venus.dbus-tasmota-inverter
Used https://github.com/victronenergy/velib_python/blob/master/dbusdummyservice.py as basis for this service.
Reading information from Tasmota SENSOR MQTT and puts the info on dbus as pvinverter.

"""


# our own packages
import configparser
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

def getConfig():
    config = configparser.ConfigParser()
    config.read("%s/config.ini" % (os.path.dirname(os.path.realpath(__file__))))
    return config

config = getConfig()

def getMQTTName():
    return config.get('MQTTBroker','name', fallback = 'MQTT_to_Inverter')

def getMQTTAddress():
    address = config.get('MQTTBroker','address', fallback = None)
    if address == None:
        logger.error("No MQTT Broker set in config.ini")
        return address
    else:
        return address

def getMQTTPort():
    port = config.get('MQTTBroker','port', fallback = None)
    if port != None:
        return int(port)
    else:
        return 1883

def connectBroker():
    broker_address = getMQTTAddress()
    broker_port = getMQTTPort()

    try:
        logger.info('connecting to MQTTBroker ' + broker_address + ' on Port ' + str(broker_port))

        if broker_address != None:
            client.connect(broker_address, port=broker_port)  # connect to broker
            client.loop_start()
        else:
            logger.error("couldn't connect to MQTT Broker")
    except Exception as e:
        logger.exception("Error in Connect to Broker")
        logger.exception(e)

def getPosition():
    return int(config.get('Setup','Inverter_Position', fallback = 0))

def getTopicL1():
    return config.get('Topics','L1', fallback ='')

def getTopicL2():
    return config.get('Topics','L2', fallback ='')

def getTopicL3():
    return config.get('Topics','L3', fallback ='')
    
devices = {
    'L1': {'topic': getTopicL1(), 'power': 0, 'voltage': 0, 'current': 0, 'total': 0, 'path': ''},
    'L2': {'topic': getTopicL2(), 'power': 0, 'voltage': 0, 'current': 0, 'total': 0, 'path': ''},
    'L3': {'topic': getTopicL3(), 'power': 0, 'voltage': 0, 'current': 0, 'total': 0, 'path': ''},
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
        connectBroker()
    except Exception as e:
        logger.exception("Error in Retrying to Connect with Broker")
        logger.exception(e)

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Connected to MQTT Broker!")
        if devices['L1']['topic'] != '':
            client.subscribe(devices['L1']['topic'])
        if devices['L2']['topic'] != '':
            client.subscribe(devices['L2']['topic'])
        if devices['L3']['topic'] != '':
            client.subscribe(devices['L3']['topic'])
    else:
        logger.info("Failed to connect, return code %d\n", rc)

def on_message(client, userdata, msg):
    try:

        logger.debug(msg.topic)

        if msg.topic == devices['L1']['topic']:
            jsonpayload = json.loads(msg.payload)
            devices['L1']['power'] = float(jsonpayload["ENERGY"]["Power"])
            devices['L1']['current'] = float(jsonpayload["ENERGY"]["Current"])
            devices['L1']['voltage'] = float(jsonpayload["ENERGY"]["Voltage"])
            devices['L1']['total'] = float(jsonpayload["ENERGY"]["Total"])

        if msg.topic == devices['L2']['topic']:
            jsonpayload = json.loads(msg.payload)
            devices['L2']['power'] = float(jsonpayload["ENERGY"]["Power"])
            devices['L2']['current'] = float(jsonpayload["ENERGY"]["Current"])
            devices['L2']['voltage'] = float(jsonpayload["ENERGY"]["Voltage"])
            devices['L2']['total'] = float(jsonpayload["ENERGY"]["Total"])

        if msg.topic == devices['L3']['topic']:
            jsonpayload = json.loads(msg.payload)
            devices['L3']['power'] = float(jsonpayload["ENERGY"]["Power"])
            devices['L3']['current'] = float(jsonpayload["ENERGY"]["Current"])
            devices['L3']['voltage'] = float(jsonpayload["ENERGY"]["Voltage"])
            devices['L3']['total'] = float(jsonpayload["ENERGY"]["Total"])

    except Exception as e:
        logger.exception(
            "Programm Tasmota Inverter ist abgestuerzt. (on message Funkion)")
        logger.exception(e)

# Konfiguration MQTT
client = mqtt.Client(getMQTTName())  # create new instance
client.on_disconnect = on_disconnect
client.on_connect = on_connect
client.on_message = on_message
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
        self._dbusservice.add_path('/Position', getPosition())
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

    connectBroker()

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


if __name__ == "__main__":
    main()
