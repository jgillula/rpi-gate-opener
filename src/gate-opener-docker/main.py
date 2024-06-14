#!/usr/bin/env python3

import os
import threading
import subprocess
import signal
import paho.mqtt.client as mqtt

# We use flask to handle the HTTP requests
# https://flask.palletsprojects.com/en/2.0.x/
from flask import Flask, abort, send_from_directory
import json

# access_tokens is a set, so we have at most one of each token
access_tokens = set(json.loads(os.environ.get("ACCESS_TOKENS_LIST", '[]')))

# this condition lock allows us to wait until we're sure the Raspberry Pi received the command
connect_lock = threading.Condition()
connect_timeout = 10

# this condition lock allows us to wait until we're sure the Raspberry Pi received the command
ack_lock = threading.Condition()
ack_timeout = 10

mqtt_server_hostname = os.environ.get("MQTT_SERVER_HOSTNAME", None)
mqtt_server_port = int(os.environ.get("MQTT_SERVER_PORT", 8883))
mqtt_server_username = os.environ.get("MQTT_SERVER_USERNAME", None)
mqtt_server_password = os.environ.get("MQTT_SERVER_PASSWORD", None)
mqtt_server_use_tls = json.loads(os.environ.get("MQTT_USE_TLS", "true"))
mqtt_server_ca_certs = os.environ.get("MQTT_SERVER_CA_CERTS", None)
mqtt_command_topic = os.environ.get("MQTT_COMMAND_TOPIC", "gate-opener/open")
mqtt_response_topic = os.environ.get("MQTT_RESPONSE_TOPIC", "gate-opener/opened")

mqtt_client = mqtt.Client()
mqtt_client_connected = False


def response_received(client, userdata, msg):
    with ack_lock:
        ack_lock.notify_all()

def on_connect(client, userdata, flags, rc):
    global mqtt_client_connected
    print(f"MQTT client successfully connected. Subscribing to {mqtt_response_topic}")
    client.message_callback_add(mqtt_response_topic, response_received)
    client.subscribe(mqtt_response_topic)
    mqtt_client_connected = True
    with connect_lock:
        connect_lock.notify_all()

def on_disconnect(client, userdata, rc):
    global mqtt_client_connected
    mqtt_client_connected = False
    print(f"MQTT client disconnected")
    
if mqtt_server_username is not None and mqtt_server_password is not None:
    mqtt_client.username_pw_set(mqtt_server_username, mqtt_server_password)

if mqtt_server_use_tls:
    mqtt_client.tls_set(ca_certs=mqtt_server_ca_certs)

if mqtt_server_hostname is not None:
    mqtt_client.on_connect = on_connect
    mqtt_client.on_disconnect = on_disconnect
    try:
        mqtt_client.connect(mqtt_server_hostname, port=mqtt_server_port)                            
        mqtt_client.loop_start()
        signal.signal(signal.SIGTERM, lambda x,y: mqtt_client.disconnect())
    except ConnectionRefusedError as e:
        print(f"Connection error when connecting to {mqtt_server_hostname}:{mqtt_server_port} as user={mqtt_server_username}, {e}")
else:
    print(f"No MQTT server specified")

app = Flask(__name__)

def wait_for_mqtt_connected():
    if mqtt_client_connected:
        return True
    with connect_lock:
        connect_lock.wait(connect_timeout)
    return mqtt_client_connected

# This is called when a web browser clicks the button to open the gate
@app.route('/<string:access_token>/open', methods=['POST'])
def open_handler(access_token):
    if validate_access_token(access_token):
        if wait_for_mqtt_connected():
            mqtt_client.publish(mqtt_command_topic, access_token, qos=1)
            with ack_lock:
                ack = ack_lock.wait(ack_timeout)
                if ack:            
                    return ""
        else:
            abort(503)
    abort(504)


# This is called whenever a web browser accesses the site
@app.route('/<string:access_token>/')
def index_handler(access_token):
    if validate_access_token(access_token):
        print("Access token valid")
        if wait_for_mqtt_connected():
            return(send_from_directory(".", "index.html"))
        else:
            print("MQTT client not connected when trying to serve index.html")
            abort(503)
#    else:
#        print("Invalid access token {}".format(access_token))
#        for token in access_tokens:
#            print(" {}".format(token))

    
# This is used to serve static files to the web browser
@app.route('/<string:access_token>/<path:subpath>')
def static_handler(access_token, subpath):
    if validate_access_token(access_token):
        return(send_from_directory(".", subpath))


# This checks to see if the provided token is in the set of access_tokens that has been uploaded by the Raspberry Pi client
def validate_access_token(token):
    if token in access_tokens:
        return True
    abort(404)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
