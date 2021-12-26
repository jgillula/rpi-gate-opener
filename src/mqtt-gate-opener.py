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

def trigger_gate(trigger=None):
    print("Opening gate for {}".format(trigger))
    sys.stdout.flush()
    GPIO.output(GPIO_PIN, GPIO.HIGH)
    time.sleep(0.25)
    GPIO.output(GPIO_PIN, GPIO.LOW)
                
def open_called(mqtt_client, userdata, msg):
    trigger_gate("mqtt")
    
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
    
    print("MQTT gate opener running")
    sys.stdout.flush()
    signal.signal(signal.SIGTERM, lambda x,y: mqtt_disconnect(mqtt_client))
    
    try:
        mqtt_client.loop_forever()
    except KeyboardInterrupt:
        print("Killing MQTT gate opener")
        mqtt_disconnect(mqtt_client)
