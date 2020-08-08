from builtins import range
from builtins import object
import logging
import threading
import time

import bluepy.btle as btle
import random

import utils


class UUIDS(object):
    FIRMWARE_VERSION   = btle.UUID('64ac0001-4a4b-4b58-9f37-94d3c52ffdf7')

    BATTERY_LEVEL      = btle.UUID('00002A19-0000-1000-8000-00805F9B34FB')

    APP_CHALLENGE      = btle.UUID('64AC0002-4A4B-4B58-9F37-94D3C52FFDF7')
    DEVICE_CHALLENGE   = btle.UUID('64AC0003-4A4B-4B58-9F37-94D3C52FFDF7')
    DEVICE_RESPONSE    = btle.UUID('64AC0004-4A4B-4B58-9F37-94D3C52FFDF7')

    CONFIG             = btle.UUID('06ef0002-2e06-4b79-9e33-fce2c42805ec')
    PROBE1_TEMPERATURE = btle.UUID('06ef0002-2e06-4b79-9e33-fce2c42805ec')
    PROBE1_THRESHOLD   = btle.UUID('06ef0003-2e06-4b79-9e33-fce2c42805ec')
    PROBE2_TEMPERATURE = btle.UUID('06ef0004-2e06-4b79-9e33-fce2c42805ec')
    PROBE2_THRESHOLD   = btle.UUID('06ef0005-2e06-4b79-9e33-fce2c42805ec')
    PROBE3_TEMPERATURE = btle.UUID('06ef0006-2e06-4b79-9e33-fce2c42805ec')
    PROBE3_THRESHOLD   = btle.UUID('06ef0007-2e06-4b79-9e33-fce2c42805ec')
    PROBE4_TEMPERATURE = btle.UUID('06ef0008-2e06-4b79-9e33-fce2c42805ec')
    PROBE4_THRESHOLD   = btle.UUID('06ef0009-2e06-4b79-9e33-fce2c42805ec')
    HEATING_ELEMENTS   = btle.UUID('6c91000a-58dc-41c7-943f-518b278ceaaa')


class IDevicePeripheral(btle.Peripheral):
    encryption_key = None
    btle_lock = threading.Lock()
    has_battery = None
    has_heating_element = None

    def __init__(self, address, name, num_probes, has_battery=True, has_heating_element=False):
        """
        Connects to the device given by address performing necessary authentication
        """
        logging.debug("Trying to connect to the device with address {}".format(address))
        with self.btle_lock:
            logging.debug("Calling btle.Peripheral.__init__ with lock: {}".format(id(self.btle_lock)))
            btle.Peripheral.__init__(self, address)
            logging.debug("Releasing lock: {}".format(id(self.btle_lock)))
        self.name = name
        self.has_battery = has_battery
        self.has_heating_element = has_heating_element
        # iDevice devices require bonding. I don't think this will give us bonding
        # if no bonding exists, so please use bluetoothctl to create a bond first
        self.setSecurityLevel('medium')

        # enumerate all characteristics so we can look up handles from uuids
        self.characteristics = self.getCharacteristics()

        # Set handle for reading battery level
        if has_battery:
            self.battery_char = self.characteristic(UUIDS.BATTERY_LEVEL)

        # Set handle for reading main elements
        if has_heating_element:
            self.heating_elements = self.characteristic(UUIDS.HEATING_ELEMENTS)

        # authenticate with iDevices custom challenge/response protocol
        if not self.authenticate():
            raise RuntimeError('Unable to authenticate with device')

        # find characteristics for temperature
        self.num_probes = num_probes
        self.temp_chars = {}

        for probe_num in range(1, self.num_probes + 1):
            temp_char_name = "PROBE{}_TEMPERATURE".format(probe_num)
            temp_char = self.characteristic(getattr(UUIDS, temp_char_name))
            self.temp_chars[probe_num] = temp_char
            logging.debug("Added probe with index {0}, name {1}, and UUID {2}".format(probe_num, temp_char_name, temp_char))

    def characteristic(self, uuid):
        """
        Returns the characteristic for a given uuid.
        """
        for c in self.characteristics:
            if c.uuid == uuid:
                return c

    def authenticate(self):
        """
        Performs iDevices challenge/response handshake. Returns if handshake succeeded
        Works for all devices using this handshake, no key required
        (copied from https://github.com/kins-dev/igrill-smoker, thanks for the tip!)
        """
        logging.debug("Authenticating...")

        # send app challenge (16 bytes) (must be wrapped in a bytearray)
        challenge = bytes(b'\0' * 16)
        logging.debug("Sending key of all 0's")
        self.characteristic(UUIDS.APP_CHALLENGE).write(challenge, True)

        """
        Normally we'd have to perform some crypto operations:
            Write a challenge (in this case 16 bytes of 0)
            Read the value
            Decrypt w/ the key
            Check the first 8 bytes match our challenge
            Set the first 8 bytes 0
            Encrypt with the key
            Send back the new value
        But wait!  Our first 8 bytes are already 0.  That means we don't need the key.
        We just hand back the same encrypted value we get and we're good.
        """
        encrypted_device_challenge = self.characteristic(UUIDS.DEVICE_CHALLENGE).read()
        self.characteristic(UUIDS.DEVICE_RESPONSE).write(encrypted_device_challenge, True)

        logging.debug("Authenticated")

        return True

    def read_battery(self):
        return float(bytearray(self.battery_char.read())[0]) if self.has_battery else None

    def read_heating_elements(self):
        return bytearray(self.heating_elements.read()) if self.has_heating_element else None

    def read_temperature(self, publish_empty, missing_value):
        empty = False if not publish_empty else missing_value
        temps = {1: False, 2: False, 3: False, 4: False}

        for probe_num, temp_char in list(self.temp_chars.items()):
            temp = bytearray(temp_char.read())[1] * 256
            temp += bytearray(temp_char.read())[0]
            temps[probe_num] = float(temp) if float(temp) != 63536.0 else empty

        return temps


class IGrillMiniPeripheral(IDevicePeripheral):
    """
    Specialization of iDevice peripheral for the iGrill Mini
    """

    def __init__(self, address, name='igrill_mini', num_probes=1):
        logging.debug("Created new device with name {}".format(name))
        IDevicePeripheral.__init__(self, address, name, num_probes)


class IGrillV2Peripheral(IDevicePeripheral):
    """
    Specialization of iDevice peripheral for the iGrill v2
    """

    def __init__(self, address, name='igrill_v2', num_probes=4):
        logging.debug("Created new device with name {}".format(name))
        IDevicePeripheral.__init__(self, address, name, num_probes)


class IGrillV3Peripheral(IDevicePeripheral):
    """
    Specialization of iDevice peripheral for the iGrill v3
    """

    def __init__(self, address, name='igrill_v3', num_probes=4):
        logging.debug("Created new device with name {}".format(name))
        IDevicePeripheral.__init__(self, address, name, num_probes)


class Pulse2000Peripheral(IDevicePeripheral):
    """
    Specialization of iDevice peripheral for the Weber Pulse 2000
    """

    def __init__(self, address, name='pulse_2000', num_probes=4):
        logging.debug("Created new device with name {}".format(name))
        IDevicePeripheral.__init__(self, address, name, num_probes, has_heating_element=True)


class DeviceThread(threading.Thread):
    device_types = {'igrill_mini': IGrillMiniPeripheral,
                    'igrill_v2': IGrillV2Peripheral,
                    'igrill_v3': IGrillV3Peripheral,
                    'pulse_2000': Pulse2000Peripheral}

    def __init__(self, thread_id,
                 mqtt_config,
                 run_event,
                 name,
                 address,
                 type,
                 topic,
                 interval,
                 publish_missing_probes=False,
                 missing_probe_value="missing"):

        threading.Thread.__init__(self)
        self.threadID = thread_id
        self.name = name
        self.address = address
        self.type = type
        self.mqtt_client = utils.mqtt_init(mqtt_config)
        self.topic = topic
        self.interval = interval
        self.run_event = run_event
        self.publish_missing_probes = publish_missing_probes
        self.missing_probe_value = missing_probe_value

    def run(self):
        while self.run_event.is_set():
            try:
                logging.debug("Device thread {} (re)started, trying to connect to iGrill with address: {}".format(self.name, self.address))
                device = self.device_types[self.type](self.address, self.name)
                self.mqtt_client.reconnect()
                while True:
                    temperature = device.read_temperature(self.publish_missing_probes, self.missing_probe_value)
                    battery = device.read_battery()
                    heating_element = device.read_heating_elements()
                    #utils.publish(temperature, battery, heating_element, self.mqtt_client, self.topic, device.name)
                    logging.debug("Published temp: {} and battery: {} to topic {}/{}".format(temperature, battery, self.topic, device.name))
                    logging.debug("Sleeping for {} seconds".format(self.interval))
                    time.sleep(self.interval)
            except Exception as e:
                logging.debug(e)
                logging.debug("Sleeping for {} seconds before retrying".format(self.interval))
                time.sleep(self.interval)

        logging.debug('Thread exiting')
