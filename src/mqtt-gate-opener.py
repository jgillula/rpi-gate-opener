#!/usr/bin/env python3

import time
import signal
import sys
import configparser
import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO

config_filename = "mqtt-gate-opener.conf"
GPIO_PIN = None
command_topic = "gate-opener/open"

def open_called(client, userdata, msg):
    GPIO.output(GPIO_PIN, GPIO.HIGH)
    time.sleep(0.25)
    GPIO.output(GPIO_PIN, GPIO.LOW)
    
def on_connect(client, userdata, flags, rc):
    client.message_callback_add(command_topic, open_called)
    client.subscribe(command_topic)

def disconnect(client):
    print("Shutting down MQTT gate opener")
    client.disconnect()
    GPIO.cleanup(GPIO_PIN)
    sys.exit(0)

if __name__ == "__main__":
    print("Loading MQTT gate opener")
    sys.stdout.flush()
    signal.signal(signal.SIGTERM, lambda x,y: disconnect(client))

    parser = configparser.ConfigParser()
    with open(config_filename) as stream:
        parser.read_string("[Gate-Opener]\n" + stream.read())
    config = parser["Gate-Opener"]
    GPIO_PIN = int(config.get('GPIO_PIN', 11))
    mqtt_server = config.get('mqtt_server', 'server.local')
    mqtt_server_port = int(config.get('mqtt_server_port', 1883))
    print("Configuration read from {}:".format(config_filename))
    print(" GPIO_PIN={}".format(GPIO_PIN))
    print(" mqtt_server={}".format(mqtt_server))
    print(" mqtt_server_port={}".format(mqtt_server_port))
    sys.stdout.flush()
    
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(GPIO_PIN, GPIO.OUT)
    
    client = mqtt.Client()
    client.on_connect = on_connect
    client.connect(mqtt_server, mqtt_server_port)

    print("MQTT gate opener running")
    sys.stdout.flush()
    
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("Killing MQTT gate opener")
        client.disconnect()
        GPIO.cleanup(GPIO_PIN)
