import logging
import time
import os
import signal
from threading import Thread
import json
from gardena.smart_system import SmartSystem
import paho.mqtt.client as mqtt

def publish_device(device):
    infos = {"datetime":time.strftime("%Y-%m-%d %H:%M:%S")}
    for attrName in vars(device):
        if not attrName.startswith('_') and attrName not in ('location', 'callbacks'):
            infos[attrName] = getattr(device, attrName)
    mqttclient.publish(f"{mqttprefix}/{device.location.name}/{device.name}", json.dumps(infos))

def publish_everything():
    global smart_system
    for location in smart_system.locations.values():
        for device in location.devices.values():
            publish_device(device)

def subscribe_device(device):
    if mqttclientconnected:
        mqttclient.subscribe(f"{mqttprefix}/{device.location.name}/{device.name}/control")

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

    splittedTopic = msg.topic.split('/')
    splittedTopic[len(splittedTopic)-1] = 'result'
    resultTopic = '/'.join(splittedTopic)

    try:
        decodedPayload = msg.payload.decode('utf-8')
    except:
        logging.error('Message skipped: payload %s is not valid on topic %s', msg.payload.hex(), msg.topic)
        mqttclient.publish(resultTopic, json.dumps({"result":"error", "reason":"Message ignored as payload can't be decoded", "datetime":time.strftime("%Y-%m-%d %H:%M:%S"), "request":msg.payload.hex()}, ensure_ascii=False))
        return

    # looking for the right device
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
        parsedPayload = json.loads(decodedPayload)
    except:
        logging.error(f'Incorrect JSON received : {decodedPayload}')
        mqttclient.publish(resultTopic, json.dumps({"result":"error", "reason":"Incorrect JSON received", "datetime":time.strftime("%Y-%m-%d %H:%M:%S"), "request":decodedPayload}, ensure_ascii=False))
        return

    if 'command' not in parsedPayload:
        logging.error(f'command missing in payload received : {decodedPayload}')
        mqttclient.publish(resultTopic, json.dumps({"result":"error", "reason":"command missing in payload received", "datetime":time.strftime("%Y-%m-%d %H:%M:%S"), "request":decodedPayload}, ensure_ascii=False))
        return

    if not type(parsedPayload['command']) is str:
        logging.error(f'Incorrect command in payload received : {decodedPayload}')
        mqttclient.publish(resultTopic, json.dumps({"result":"error", "reason":"Incorrect command in payload received", "datetime":time.strftime("%Y-%m-%d %H:%M:%S"), "request":decodedPayload}, ensure_ascii=False))
        return

    # looking for the method requested
    try:
        thisDeviceMethod = getattr(thisDevice, parsedPayload['command'])
    except:
        logging.error(f'command received doesn\'t exists for this device: {decodedPayload}')
        mqttclient.publish(resultTopic, json.dumps({"result":"error", "reason":"command received doesn\'t exists for this device", "datetime":time.strftime("%Y-%m-%d %H:%M:%S"), "request":decodedPayload}, ensure_ascii=False))
        return

    if not callable(thisDeviceMethod):
        logging.error(f'command received doesn\'t exists for this device: {decodedPayload}')
        mqttclient.publish(resultTopic, json.dumps({"result":"error", "reason":"command received doesn\'t exists for this device", "datetime":time.strftime("%Y-%m-%d %H:%M:%S"), "request":decodedPayload}, ensure_ascii=False))
        return

    params = []

    # looking fore required params
    listOfParam = list(thisDeviceMethod.__code__.co_varnames)
    for paramName in thisDeviceMethod.__code__.co_varnames:
        if paramName not in ('self', 'data'):
            try:
                params.append(parsedPayload[paramName])
            except:
                logging.error(f'The parameter {paramName} is missing. command can\'t be executed')
                mqttclient.publish(resultTopic, json.dumps({"result":"error", "reason":f'The parameter {paramName} is missing. command can\'t be executed', "datetime":time.strftime("%Y-%m-%d %H:%M:%S"), "request":decodedPayload}, ensure_ascii=False))
                return

    # run the command
    try:
        if len(params) == 0:
            thisDeviceMethod()
        elif len(params) == 1:
            thisDeviceMethod(params[0])
        elif len(params) == 2:
            thisDeviceMethod(params[0], params[1])
    except:
        logging.exception(f'execution of the command failed: {decodedPayload}')
        mqttclient.publish(resultTopic, json.dumps({"result":"error", "reason":"execution of the command failed", "datetime":time.strftime("%Y-%m-%d %H:%M:%S"), "request":decodedPayload}, ensure_ascii=False))
        return

    mqttclient.publish(resultTopic, json.dumps({"result":"success", "datetime":time.strftime("%Y-%m-%d %H:%M:%S"), "request":parsedPayload}, ensure_ascii=False))

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

    versionnumber = '1.0.1'

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
