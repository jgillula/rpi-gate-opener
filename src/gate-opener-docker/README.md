# Running the mqtt-gate-opener Docker Container

In order to control your gate opener from anywhere, you can run this Docker container (also available at https://hub.docker.com/repository/docker/flyingsaucrdude/mqtt-gate-opener-remote) on your favorite service. This README contains instructions for doing so on [Google Cloud Run](https://cloud.google.com/run/).

## 0. Prerequisites

This tutorial assumes you already have an MQTT broker running somewhere. (It can be the same Raspberry Pi you're using to control the gate opener, but it doesn't have to be. As long as the gate opener Raspberry Pi can talk to the MQTT server, you should be fine.) 

It also assumes that you can access that MQTT broker from the Internet. If you need help setting that up, you can [check out my tutorial here](https://www.hackster.io/jeremy-gillula/mqtt-encryption-acls-and-client-authentication-cfa61d) on how to setup mosquitto with a dynamic DNS domain name from [DuckDNS](https://www.duckdns.org), username/password authentication, access controls, and TLS using a certificate from [Let's Encrypt](https://letsencrypt.org).

Finally, it assumes you have a Google account, and you've installed the Google Cloud SDK on your machine [following the instructions here](https://cloud.google.com/sdk/docs/install#deb).

## 1. Setup a new project

First, set a project name variable that we can reuse:
```
export PROJECT_NAME=pick-some-name
```

Then create the project and set up the repo:

```
gcloud auth login
gcloud projects create $PROJECT_NAME --set-as-default
gcloud artifacts repositories create --location=us-west1 --repository-format=docker gate-opener-repo
gcloud auth configure-docker us-west1-docker.pkg.dev
```

If it asks you to enable the Artifact Registry, do so and then retry the last two commands. Then continue with

## 2. Deploy the docker image

Now do:

```
docker pull flyingsaucrdude/mqtt-gate-opener-remote 
docker tag flyingsaucrdude/mqtt-gate-opener-remote us-west1-docker.pkg.dev/$PROJECT_NAME/gate-opener-repo/gate-opener
docker push us-west1-docker.pkg.dev/$PROJECT_NAME/gate-opener-repo/gate-opener
gcloud run deploy gate-opener --allow-unauthenticated --min-instances=0 --max-instances=1 --image us-west1-docker.pkg.dev/$PROJECT_NAME/gate-opener-repo/gate-opener
```

If it asks you to enable the Cloud Run API, do so.

## 3. Configure the docker container

Now we need to set the following environment variables used to configure the container:
* `MQTT_SERVER_HOSTNAME` — (Required) The hostname of your MQTT broker
* `MQTT_SERVER_PORT` — (Optional) The port of your MQTT broker. Defaults to 8883.
* `MQTT_SERVER_USERNAME` — (Optional) The username to use to log in to the MQTT broker. If not given, the MQTT client won't use a username/password.
* `MQTT_SERVER_PASSWORD` — (Optional) The password to use to log in to the MQTT broker. If not given, the MQTT client won't use a username/password.
* `MQTT_USE_TLS` — (Optional) Whether or not to use an encrypted TLS connection to connect to the MQTT broker, including verifying that it has a valid certificate. Defaults to true. Set to false to disable encryption.
* `MQTT_COMMAND_TOPIC` — (Optional) The topic to use to trigger the gate opener. Defaults to `gate-opener/open`.
* `MQTT_RESPONSE_TOPIC` — (Optional) The topic to listen on to receive confirmation messages from the gate opener. Defaults to `gate-opener/opened`.
* `ACCESS_TOKENS_LIST` — (Required) A json list of access tokens to use to access the service on the web. These tokens are the only thing protecting your gate opener from being accessed by anyone, so they should be long and random so that they can't be guessed or brute-forced, e.g. `['token1-I2JJVsEV5LCfbDqMMM1iL5rCh3VaNiqKNN2RQZrkZv7BjV7MShEmwxFXsx1210J6', 'token2-H3udRjyhuXKOUi2OU8E6PGpST5S78Fc79lDeftVurht6QKIbyqxZHsftIp8NMvfE']`

You could try setting these via the command line (by providing `--update-env-vars=KEY1=VALUE1,KEY2=VALUE2,...` to the last command), but I find it much easier to do so via Google's web-based Cloud Console.

* Open up the Cloud Console by visiting https://console.cloud.google.com/run/detail/us-west1/gate-opener/metrics?project=PROJECT_NAME, where `PROJECT_NAME` is the same project name you chose earlier.
* Choose "Edit & Deploy New Revision" from near the top.
* Select the "Variables & Secrets" tab.
* Click "Add Variable" to add and set the appropriate environment variables
* Click "Deploy" at the bottom
* Wait until the new revision is deployed

## 4. Check that it works

Once you have your container running, you can access it over the web by visiting

> `https://HOSTNAME/ACCESS_TOKEN/`

where `HOSTNAME` is the service URL of your docker container (which you can get by running `gcloud run services describe gate-opener | grep "URL:"`) and `ACCESS_TOKEN` is one of the access tokens from the `ACCESS_TOKENS_LIST`.

As you can see, instead of requiring a username or password, the website's security ***depends on the uniqueness and length of the access tokens you choose***. The downside is that you must use ***very long*** (I recommend at least 64 characters) and ***random*** (i.e. generated by your computer) tokens. You can generate such a token with the simple Python script:

```
import random, string
''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(64))
```

Although the resulting access URLs aren't memorable, they are persistent, bookmarkable, and shareable, so you can, e.g., give a unique access token/URL to each of your friends and family, and all they have to do is bookmark that URL to be able to come back and open your gate whenever they need to.
