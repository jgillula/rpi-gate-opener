#!/usr/bin/env python3

import time
import signal
import sys
import threading
import configparser
import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO
import socketio

GPIO_PIN = None
command_topic = "gate-opener/open"

socketio_client = socketio.Client()
access_tokens = {}
access_tokens_lock = threading.Lock()

@socketio_client.on("connect")
def connect():
    socketio_client.send(["clear_access_tokens"])
    with access_tokens_lock:
        socketio_client.send(["add_access_tokens", list(access_tokens.keys())])
    print("Connected to AppEngine server")
    
@socketio_client.on("message")
def message(data):
    if isinstance(data, list):
        if data[0] == "open_gate" and len(data) >= 2:
            with access_tokens_lock:
                if data[1] in access_tokens.keys():
                    trigger_gate(access_tokens[data[1]])
                    socketio_client.send(["ack"])

def trigger_gate(trigger=None):
    print("Opening gate for {}".format(trigger))
    sys.stdout.flush()
    GPIO.output(GPIO_PIN, GPIO.HIGH)
    time.sleep(0.25)
    GPIO.output(GPIO_PIN, GPIO.LOW)
                
def open_called(client, userdata, msg):
    trigger_gate("mqtt")
    
def on_connect(client, userdata, flags, rc):
    client.message_callback_add(command_topic, open_called)
    client.subscribe(command_topic)

def disconnect(client):
    print("Shutting down MQTT gate opener")
    client.disconnect()
    if socketio_client.connected:
        print("Shutting down App Engine client")
        socketio_client.disconnect()
    GPIO.cleanup(GPIO_PIN)
    sys.exit(0)

if __name__ == "__main__":
    print("Loading MQTT gate opener")
    sys.stdout.flush()
    signal.signal(signal.SIGTERM, lambda x,y: disconnect(client))

    parser = configparser.ConfigParser()
    config_filename = "mqtt-gate-opener.conf"
    parser.read(config_filename)
    if "Gate Opener" not in parser.sections():
        print("ERROR! Misconfigured config file {}.\nPlease view https://github.com/jgillula/rpi-gate-opener/blob/main/src/mqtt-gate-opener.conf for an example of a valid config file".format(config_filename))
        sys.stdout.flush()
        exit(1)
    config = parser["Gate Opener"]
    GPIO_PIN = int(config.get('GPIO_PIN', 11))
    mqtt_server = config.get('mqtt_server', 'localhost')
    mqtt_server_port = int(config.get('mqtt_server_port', 1883))
    print("Configuration read from {}:".format(config_filename))
    print(" GPIO_PIN={}".format(GPIO_PIN))
    print(" mqtt_server={}".format(mqtt_server))
    print(" mqtt_server_port={}".format(mqtt_server_port))
    sys.stdout.flush()

    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(GPIO_PIN, GPIO.OUT)

    if "Cloud Settings" in parser.sections():
        cloud_config = parser["Cloud Settings"]
        cloud_auth_token = cloud_config.get("auth_token")
        cloud_socketio_path = cloud_config.get("socketio_path", "socket.io")
        cloud_server_url = cloud_config.get("server_url")

        if "Cloud Tokens" in parser.sections():
            cloud_token_list = parser["Cloud Tokens"]
            with access_tokens_lock:
                for name in cloud_token_list:
                    access_tokens[cloud_token_list[name]] = name
            
        if cloud_server_url:
            print("Using appengine server {}".format(cloud_server_url))
            print(" socketio_path={}".format(cloud_socketio_path))
            print(" access_urls:")
            for key in access_tokens.keys():
                print("  {}: {}/{}".format(access_tokens[key], cloud_server_url, key))
            socketio_client.connect(cloud_server_url,
                                    auth={"auth_token": cloud_auth_token},
                                    socketio_path=cloud_socketio_path)
    
    client = mqtt.Client()
    client.on_connect = on_connect
    client.connect(mqtt_server, mqtt_server_port)

    print("MQTT gate opener running")
    sys.stdout.flush()
    
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("Killing MQTT gate opener")
        socketio_client.disconnect()
        client.disconnect()
        GPIO.cleanup(GPIO_PIN)
