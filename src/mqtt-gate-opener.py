#!/usr/bin/env python3

import time
import argparse
import pathlib
import signal
import sys
import configparser
import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO

GPIO_PIN = None
command_topic = "gate-opener/open"
response_topic = "gate-opener/opened"

# class Device:
#     """Object to represent a generic MQTT device in Home Assistant."""

#     def __init__(self, device_type, object_id, node_id=None):
#         self.client = mqtt.Client()
#         self._device_type = device_type
#         self._object_id = object_id
#         self._node_id = node_id
#         self._discovery_payload = None

#         # This is a dict where the keys are topics, and the values are the corresponding callbacks
#         self._topic_subscriptions = {}
        
#         self._config_topic = self._get_topic_prefix() + "config"

#         self.client.on_connect = self._on_connect
#         self.client.on_disconnect = self._on_disconnect
#         self.connected = False

#     def _on_connect(self, client, userdata, flags, rc):
#         if rc == 0:
#             client.publish(self._config_topic, self._discovery_payload, retain=True)
#             for topic in self._topic_subscriptions.keys():
#                 self._subscribe(topic, self._topic_subscriptions[topic])
#             self.connected = True

#     def _on_disconnect(self, client, userdata, rc):
#         self.connected = False
            
#     def _subscribe(self, topic, callback):
#         self.client.subscribe(topic)
#         self.client.message_callback_remove(topic)
#         self.client.message_callback_add(topic, callback)
            
#     def add_subscription(self, topic, callback):
#         self._topic_subscriptions[topic] = callback
#         if self.connected:
#             self._subscribe(topic, callback)
        
#     def _get_topic_prefix(self):
#         if self._node_id:
#             return "homeassistant/{}/{}/{}/".format(self._device_type,
#                                                     self._node_id,
#                                                     self._object_id)
#         else:
#             return "homeassistant/{}/{}/".format(self._device_type,
#                                                     self._object_id)

#     def set_discovery_payload(self, discovery_payload):
#         self._discovery_payload = json.dumps(discovery_payload)


#     def connect(self, host, port=1883, keepalive=60, bind_address=""):
#         self.client.will_set(self._config_topic)
#         self.client.connect_async(host, port, keepalive, bind_address)

#     def disconnect(self):
#         self.client.disconnect()

# class Button(Device):
#     def __init__(self, object_id, command_callback, name, icon, node_id=None):
#         super().__init__("button", object_id, node_id)
#         self._state_topic = self._get_topic_prefix()+"state"
#         self._command_topic = self._get_topic_prefix()+"command"
        
#         self.set_discovery_payload({"name": name,
#                                     "object_id": object_id,
#                                     "icon": icon,
#                                     "command_topic": self._command_topic,
#                                     "state_topic": self._state_topic,
#                                     "unique_id": object_id})
        
#         self.add_subscription(self._command_topic, self._trigger)
#         self.add_subscription(self._state_topic, self._trigger)

#     def _trigger(self, client, userdata, message):
#         print(message.payload)


def trigger_gate(mqtt_client):
    print("Opening gate")
    sys.stdout.flush()
    GPIO.output(GPIO_PIN, GPIO.HIGH)
    time.sleep(0.25)
    GPIO.output(GPIO_PIN, GPIO.LOW)
    mqtt_client.publish(response_topic, True, qos=1)

def open_called(mqtt_client, userdata, msg):
    trigger_gate(mqtt_client)

def on_connect(mqtt_client, userdata, flags, rc):
    mqtt_client.message_callback_add(command_topic, open_called)
    mqtt_client.subscribe(command_topic)

def mqtt_disconnect(mqtt_client):
    print("Shutting down MQTT gate opener")
    sys.stdout.flush()
    print(" Disconnecting MQTT client")
    sys.stdout.flush()
    mqtt_client.disconnect()
    GPIO.cleanup(GPIO_PIN)
    print(" Shut down successful")
    sys.stdout.flush()
    sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", action='store', default='mqtt-gate-opener.conf', type=pathlib.Path, help="The config file to use (defaults to %(default)s)", metavar="CONFIG_FILENAME", dest="config_filename")
    args = parser.parse_args()

    print("Loading MQTT gate opener")
    sys.stdout.flush()

    parser = configparser.ConfigParser()
    parser.read(args.config_filename.resolve())
    if "Gate Opener" not in parser.sections():
        print("ERROR! Misconfigured config file {}.\nPlease view https://github.com/jgillula/rpi-gate-opener/blob/main/src/mqtt-gate-opener.conf for an example of a valid config file".format(str(args.config_filename.resolve())))
        sys.stdout.flush()
        exit(1)
    config = parser["Gate Opener"]
    GPIO_PIN = int(config.get('GPIO_PIN', 11))
    mqtt_server = config.get('mqtt_server', 'localhost')
    mqtt_server_port = int(config.get('mqtt_server_port', 1883))
    print("Configuration read from {}:".format(str(args.config_filename.resolve())))
    print(" GPIO_PIN={}".format(GPIO_PIN))
    print(" mqtt_server={}".format(mqtt_server))
    print(" mqtt_server_port={}".format(mqtt_server_port))
    sys.stdout.flush()

    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(GPIO_PIN, GPIO.OUT)

    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = on_connect
    mqtt_client.connect(mqtt_server, mqtt_server_port)

    #gate_opener_button = Button("gate_opener", trigger_gate, "Gate Opener", "mdi:gate-arrow-left")
    #gate_opener_button.connect(mqtt_server, mqtt_server_port)
    
    print("MQTT gate opener running")
    sys.stdout.flush()
    signal.signal(signal.SIGTERM, lambda x,y: mqtt_disconnect(mqtt_client))
 
    try:
        mqtt_client.loop_forever()
    except KeyboardInterrupt:
        print("Killing MQTT gate opener")
        mqtt_disconnect(mqtt_client)
