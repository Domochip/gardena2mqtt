# Prerequisites

You need one or more Garden Smart system devices : https://www.gardena.com/int/products/smart/  
A developper application to access gardena API : https://developer.husqvarnagroup.cloud/docs/getting-started

# How does it work


# How-to
## Install

Run by executing the following commmand:

```bash
docker run \
    -d \
    --name gardena2mqtt \
    --restart=always \
    -e HOST="192.168.1.x" \
    domochip/gardena2mqtt
```

### Parameters explanation

* `-e HOST="192.168.1.x"`: IP address or hostname of your MQTT broker
* `-e PORT=1883`: **Optional**, port of your MQTT broker
* `-e PREFIX="sms2mqtt"`: **Optional**, prefix used in topics for subscribe/publish
* `-e CLIENTID="sms2mqttclid"`: **Optional**, MQTT client id to use
* `-e USER="usr"`: **Optional**, MQTT user name
* `-e PASSWORD="pass"`: **Optional**, MQTT password

# Troubleshoot
## Logs
You need to have a look at logs using :  
`docker logs gardena2mqtt`

# Updating
To update to the latest Docker image:
```bash
docker stop gardena2mqtt
docker rm gardena2mqtt
docker rmi domochip/gardena2mqtt
# Now run the container again, Docker will automatically pull the latest image.
```
# Ref/Thanks

I want to thanks those repositories for their codes that inspired me :  
