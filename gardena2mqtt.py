import logging
import time
import os
from threading import Thread
import json
from gardena.smart_system import SmartSystem
import paho.mqtt.client as mqtt

import pprint

def publish_everything():
    logging.info('publish_everything')

# callback when the broker responds to our connection request.
def on_mqtt_connect(client, userdata, flags, rc):
    global mqttclientconnected
    mqttclientconnected = True
    logging.info("Connected to MQTT host")
    

# callback when the client disconnects from the broker.
def on_mqtt_disconnect(client, userdata, rc):
    global mqttclientconnected
    mqttclientconnected = False
    logging.info("Disconnected from MQTT host")
    

def on_mqtt_message(client, userdata, msg):
    logging.info(f'MQTT received : {msg.payload}')

def on_ws_status_changed(status):
    logging.info(f'WebSocket status : {status}')


def shutdown():
    mqttclient.disconnect()
    mqttthread.join()






if __name__ == "__main__":
    logging.basicConfig(format="%(asctime)s: %(message)s", level=logging.INFO, datefmt="%H:%M:%S")

    versionnumber = '0.1.0'

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


    logging.info('===== Connection to MQTT Broker =====')
    mqttclient = mqtt.Client(mqttclientid)
    mqttclient.username_pw_set(mqttuser, mqttpassword)
    mqttclient.on_connect = on_mqtt_connect
    mqttclient.on_disconnect = on_mqtt_disconnect
    mqttclient.on_message = on_mqtt_message
    mqttclient.will_set(f"{mqttprefix}/connected", "0", 0, True)
    mqttthread = Thread(target=mqttclient.loop_forever)

    mqttclientconnected = False

    mqttclient.connect(mqtthost, mqttport)
    mqttthread.start()

    for i in range(50):
        if mqttclientconnected == True:
            break
        time.sleep(0.1)

    if mqttclientconnected == False:
        shutdown()


    logging.info('===== Connection to SmartSystem =====')
    logging.info(' - create')
    smart_system = SmartSystem(email=gardenauser, password=gardenapassword, client_id=gardenaapikey)
    logging.info(' - authenticate')
    smart_system.authenticate()
    logging.info(' - update location list')
    smart_system.update_locations()
    for location in smart_system.locations.values():
        logging.info(f' - update device list for location : {location.name}')
        smart_system.update_devices(location)

    smart_system.ws_status_callback = on_ws_status_changed

    # smart_system.start_ws(smart_system.locations[LOCATION_ID])


    # Work In Progress

    for location in smart_system.locations.values():
        LOCATION_ID = location.id
        locationDict = dict(location.__dict__)
        del locationDict['smart_system']
        pprint.pprint(json.dumps(locationDict))
        pprint.pprint(location.__dict__)
        for device in location.devices.values():
            deviceDict = dict(device.__dict__)
            del deviceDict['smart_system']
            pprint.pprint(json.dumps(deviceDict))

    # pprint(smart_system.locations[LOCATION_ID].devices['XX'])

    
