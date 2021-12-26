#!/usr/bin/env python3

import os
import threading
import subprocess

# We use flask to handle the HTTP requests
# https://flask.palletsprojects.com/en/2.0.x/
from flask import Flask, abort, send_from_directory
# We use flask_socketio to handle the socket connections (which aren't necessarily websockets, but a similar idea)
# https://flask-socketio.readthedocs.io/en/latest/index.html
#from flask_socketio import SocketIO, send
import socketio
import dns.resolver

from google.cloud import secretmanager
from google.cloud import resourcemanager

# The auth token is retrieved from the Google Secrets Manager
AUTH_TOKEN = None
ALLOWED_HOST = None

import logging
logging.basicConfig(format="%(levelname)s %(name)s:%(filename)s[%(lineno)d]: %(message)s", level=logging.WARNING)
from flask.logging import default_handler

app = Flask(__name__)
sio = socketio.Server(async_mode="threading") #, logger=True, engineio_logger=True)

# access_tokens is a set, so we have at most one of each token
access_tokens = set()
access_tokens_lock = threading.Lock()

# this condition lock allows us to wait until we're sure the Raspberry Pi received the command
ack_lock = threading.Condition()
ack_timeout = 10

# This is called whenever a client (i.e. the Raspberry Pi) connects via a socket
@sio.event
def connect(sid, environ, auth):
    # GAE_ENV only exists when running on AppEngine, so this is how we make sure we only verify the client's IP address when running in the cloud
    if os.environ.get("GAE_ENV"):
        remote_ip = environ["HTTP_X_APPENGINE_USER_IP"]
        dns_answers = dns.resolver.resolve(ALLOWED_HOST)
        if len(dns_answers) > 0:
            allowed_ip = dns_answers[0].address
            if allowed_ip != remote_ip:
                return False
        else:
            return False
    if isinstance(auth, dict):
        if auth.get("auth_token", None) == AUTH_TOKEN:
            return True
    return False


# This is called whenever a client (i.e. the Raspberry Pi) disconnects
@sio.event
def disconnect(sid):
    print("Clearing access tokens due to disconnect")
    with access_tokens_lock:
        access_tokens.clear()

# This is called whenever a client (i.e. the Raspberry Pi) sends a message over the socket
@sio.event
def message(sid, data):
    if isinstance(data, list):
        if data[0] == "clear_access_tokens":
            print("Clearing access tokens via message")
            with access_tokens_lock:
                access_tokens.clear()
        elif data[0] == "add_access_tokens" and len(data) >= 2:
            print("Adding access tokens")
            with access_tokens_lock:
                access_tokens.update(data[1])
        # elif data[0] == "get_access_tokens":
        #     with access_tokens_lock:
        #         sio.send(["access_tokens_list", list(access_tokens)])
        elif data[0] == "set_ack_timeout" and len(data) >= 2:
            with ack_lock:
                ack_timeout = data[1]
        elif data[0] == "ack":
            with ack_lock:
                ack_lock.notify_all()


# This is called when a web browser clicks the button to open the gate
@app.route('/<string:access_token>/open', methods=['POST'])
def open_handler(access_token):
    if validate_access_token(access_token):
        sio.send(["open_gate", access_token])
        with ack_lock:
            ack = ack_lock.wait(ack_timeout)
            if ack:            
                return ""
    abort(504)


# This is called whenever a web browser accesses the site
@app.route('/<string:access_token>/')
def index_handler(access_token):
    if validate_access_token(access_token):
        return(send_from_directory(".", "index.html"))
    else:
        print("Invalid access token {}".format(access_token))
        for token in access_tokens:
            print(" {}".format(token))

    
# This is used to serve static files to the web browser
@app.route('/<string:access_token>/resources/<path:subpath>')
def static_handler(access_token, subpath):
    if validate_access_token(access_token):
        return(send_from_directory("resources", subpath))


# This checks to see if the provided token is in the set of access_tokens that has been uploaded by the Raspberry Pi client
def validate_access_token(token):
    with access_tokens_lock:
        if token in access_tokens:
            return True
    abort(404)


if __name__ == '__main__':
    resource_client = resourcemanager.ProjectsClient()
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", None)
    if project_id is None:
        project_id = subprocess.getoutput("gcloud app describe | grep -oP \"^id: \K.*\"")
    project_name = resource_client.search_projects(query="id:{}".format(project_id)).projects[0].name

    secrets_client = secretmanager.SecretManagerServiceClient()
    AUTH_TOKEN_SECRET_NAME = os.environ.get("AUTH_TOKEN_SECRET_NAME", "gate_opener_auth_token")
    secret_response = secrets_client.access_secret_version(request={"name": project_name + "/secrets/" + AUTH_TOKEN_SECRET_NAME + "/versions/latest"})
    AUTH_TOKEN = secret_response.payload.data.decode("UTF-8")

    ALLOWED_HOST_SECRET_NAME = os.environ.get("ALLOWED_HOST_SECRET_NAME", "gate_opener_allowed_host")
    secret_response = secrets_client.access_secret_version(request={"name": project_name + "/secrets/" + ALLOWED_HOST_SECRET_NAME + "/versions/latest"})
    ALLOWED_HOST = secret_response.payload.data.decode("UTF-8")

    SOCKETIO_PATH_SECRET_NAME = os.environ.get("SOCKETIO_PATH_SECRET_NAME", "gate_opener_socketio_path")
    secret_response = secrets_client.access_secret_version(request={"name": project_name + "/secrets/" + SOCKETIO_PATH_SECRET_NAME + "/versions/latest"})
    socketio_path = secret_response.payload.data.decode("UTF-8")
    
    app.wsgi_app = socketio.WSGIApp(sio, app.wsgi_app, socketio_path=socketio_path)
    app.logger.removeHandler(default_handler)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    app.run(port=os.environ["PORT"])
