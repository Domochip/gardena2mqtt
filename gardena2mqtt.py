import logging
import time
import os
import signal
from threading import Thread
import json
from gardena.smart_system import SmartSystem
import paho.mqtt.client as mqtt

def publish_device(device):
    global locationName
    infos = {}
    for attrName in vars(device):
        if not attrName.startswith('_') and attrName not in ('smart_system', 'callbacks'):
            infos[attrName] = getattr(device, attrName)
    mqttclient.publish(f"{mqttprefix}/{locationName}/{device.name}", json.dumps(infos))

def publish_everything():
    global smart_system
    for location in smart_system.locations.values():
        for device in location.devices.values():
            publish_device(device)

def subscribe_device(device):
    if mqttclientconnected:
        mqttclient.subscribe(f"{mqttprefix}/{locationName}/{device.name}/control")

def subscribe_everything():
    global smart_system
    for location in smart_system.locations.values():
        for device in location.devices.values():
            subscribe_device(device)


# callback when the broker responds to our connection request.
def on_mqtt_connect(client, userdata, flags, rc):
    global mqttclientconnected
    mqttclientconnected = True
    logging.info("Connected to MQTT host")
    subscribe_everything()
    if not smartsystemclientconnected:
        mqttclient.publish(f"{mqttprefix}/connected", "1", 0, True)
    else:
        mqttclient.publish(f"{mqttprefix}/connected", "2", 0, True)
        publish_everything()


# callback when the client disconnects from the broker.
def on_mqtt_disconnect(client, userdata, rc):
    global mqttclientconnected
    mqttclientconnected = False
    logging.info("Disconnected from MQTT host")
    
# callback when a message has been received on a topic that the client subscribes to.
def on_mqtt_message(client, userdata, msg):
    logging.info(f'MQTT received : {msg.payload}')

    # looking for the right device
    splittedTopic = msg.topic.split('/')
    thisLocationName = splittedTopic[len(splittedTopic)-3]
    for location in smart_system.locations.values():
        if location.name == thisLocationName:
            thisLocation = location
    thisDeviceName = splittedTopic[len(splittedTopic)-2]
    for device in thisLocation.devices.values():
        if device.name == thisDeviceName:
            thisDevice = device
    
    # parse payload
    try:
        parsedPayload = json.loads(msg.payload)
    except:
        logging.info(f'Incorrect JSON received : {msg.payload}')
        return

    if 'command' not in parsedPayload:
        logging.info(f'command missing in payload received : {msg.payload}')
        return

    if not type(parsedPayload['command']) is str:
        logging.info(f'Incorrect command in payload received : {msg.payload}')
        return

    # looking for the method requested
    try:
        thisDeviceMethod = getattr(thisDevice, parsedPayload['command'])
    except:
        logging.info(f'command received doesn\'t exists for this device: {msg.payload}')
        return

    if not callable(thisDeviceMethod):
        logging.info(f'command received doesn\'t exists for this device: {msg.payload}')
        return

    try:
        thisDeviceMethod()
    except:
        logging.exception(f'execution of the command failed: {msg.payload}')
        return

def on_ws_status_changed(status):
    global smartsystemclientconnected
    logging.info(f'WebSocket status : {status}')
    smartsystemclientconnected = status
    if mqttclientconnected:
        mqttclient.publish(f"{mqttprefix}/connected", ("2" if smartsystemclientconnected else "1"), 0, True)
        if status:
            publish_everything()

def on_device_update(device):
    print(f"The device {device.name} has been updated !")
    if mqttclientconnected:
        publish_device(device)


def shutdown(signum=None, frame=None):
    smart_system.quit()
    if mqttclientconnected:
        mqttclient.publish(f"{mqttprefix}/connected", "0", 0, True)
    mqttclient.disconnect()
    mqttthread.join()





if __name__ == "__main__":
    logging.basicConfig(format="%(asctime)s: %(message)s", level=logging.INFO, datefmt="%H:%M:%S")

    versionnumber = '0.7.0'

    logging.info(f'===== gardena2mqtt v{versionnumber} =====')

    # devmode is used to start container but not the code itself, then you can connect interactively and run this script by yourself
    # docker exec -it gardena2mqtt /bin/sh
    if os.getenv("DEVMODE", 0) == "1":
        logging.info('DEVMODE mode : press Enter to continue')
        try:
            input()
            logging.info('')
        except EOFError as e:
            # EOFError means we're not in interactive so loop forever
            while 1:
                time.sleep(3600)

    gardenauser = os.getenv("GARDENA_USER")
    gardenapassword = os.getenv("GARDENA_PASSWORD")
    gardenaapikey = os.getenv("GARDENA_APIKEY")
    mqttprefix = os.getenv("PREFIX", "gardena2mqtt")
    mqtthost = os.getenv("HOST", "localhost")
    mqttport = os.getenv("PORT", 1883)
    mqttclientid = os.getenv("CLIENTID", "gardena2mqtt")
    mqttuser = os.getenv("USER")
    mqttpassword = os.getenv("PASSWORD")

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    logging.info('===== Prepare MQTT Client =====')
    mqttclient = mqtt.Client(mqttclientid)
    mqttclient.username_pw_set(mqttuser, mqttpassword)
    mqttclient.on_connect = on_mqtt_connect
    mqttclient.on_disconnect = on_mqtt_disconnect
    mqttclient.on_message = on_mqtt_message
    mqttclient.will_set(f"{mqttprefix}/connected", "0", 0, True)
    mqttthread = Thread(target=mqttclient.loop_forever)

    mqttclientconnected = False


    logging.info('===== Prepare SmartSystem Client =====')
    logging.info(' - create')
    smart_system = SmartSystem(email=gardenauser, password=gardenapassword, client_id=gardenaapikey)
    logging.info(' - authenticate')
    smart_system.authenticate()
    logging.info(' - update location list')
    smart_system.update_locations()
    for location in smart_system.locations.values():
        logging.info(f' - update device list for location : {location.name}')
        locationName = location.name
        smart_system.update_devices(location)

    # add callbacks
    smart_system.add_ws_status_callback(on_ws_status_changed)
    for device in location.devices.values():
        device.add_callback(on_device_update)

    smartsystemclientconnected = False


    logging.info('===== Connection To MQTT Broker =====')
    mqttclient.connect(mqtthost, mqttport)
    mqttthread.start()

    # Wait up to 5 seconds for MQTT connection
    for i in range(50):
        if mqttclientconnected == True:
            break
        time.sleep(0.1)

    if mqttclientconnected == False:
        shutdown()


    logging.info('===== Connection To Gardena SmartSystem =====')
    for locationid in smart_system.locations:
        smart_system.start_ws(smart_system.locations[locationid])

    # tie to mqtt client
    mqttthread.join()
