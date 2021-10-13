#!/usr/bin/env python3

import time
import signal
import sys
import threading
import configparser
import json
import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO
import socketio

GPIO_PIN = None
command_topic = "gate-opener/open"

access_tokens = set()
access_tokens_lock = threading.Lock()
reconnect_socketio_client = True

def connect(socketio_client):
    socketio_client.send(["clear_access_tokens"])
    with access_tokens_lock:
        socketio_client.send(["add_access_tokens", list(access_tokens)])
    print("Connected to AppEngine server")
    sys.stdout.flush()
    
def message(socketio_client, data):
    if isinstance(data, list):
        if data[0] == "open_gate" and len(data) >= 2:
            with access_tokens_lock:
                if data[1] in access_tokens:
                    trigger_gate(data[1])
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

def disconnect(client, socketio_client, socketio_thread):
    print("Shutting down MQTT gate opener")
    reconnect_socketio_client = False
    socketio_client.disconnect()
    socketio_thread.join()
    client.disconnect()
    GPIO.cleanup(GPIO_PIN)
    print("Shut down successful")
    sys.stdout.flush()
    sys.exit(0)

def socketio_thread_function(mqtt_client, cloud_server_url, cloud_auth_token, cloud_socketio_path):
    try:
        while reconnect_socketio_client:
            print("(Re)connecting to Appengine server")
            socketio_client = socketio.Client()
            socketio_client.event(lambda: connect(socketio_client))
            socketio_client.event(lambda data: message(socketio_client, data))
            socketio_client.connect(cloud_server_url,
                                    auth={"auth_token": cloud_auth_token},
                                    socketio_path=cloud_socketio_path)
            sys.stdout.flush()
            socketio_client.wait()
    except KeyboardInterrupt:
        disconnect(mqtt_client, socketio_client)

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

    client = mqtt.Client()
    client.on_connect = on_connect
    client.connect(mqtt_server, mqtt_server_port)

    if "Cloud Settings" in parser.sections():
        cloud_settings = parser["Cloud Settings"]
        cloud_auth_token = cloud_settings.get("auth_token")
        cloud_socketio_path = cloud_settings.get("socketio_path", "socket.io")
        cloud_server_url = cloud_settings.get("server_url")

        with access_tokens_lock:
            access_tokens.update(json.loads(cloud_settings.get("access_tokens", "[]")))
            
        if cloud_server_url:
            print("Using appengine server {}".format(cloud_server_url))
            print(" socketio_path={}".format(cloud_socketio_path))
            print(" access_urls:")
            for token in access_tokens:
                print("  {}/{}".format(cloud_server_url, token))
            socketio_thread = threading.Thread(target=socketio_thread_function,
                                               args=(mqtt_client, cloud_server_url, cloud_auth_token, cloud_socketio_path))
            socketio_thread.start()
    
    print("MQTT gate opener running")
    sys.stdout.flush()
    
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("Killing MQTT gate opener")
        disconnect(client, socketio_client)
