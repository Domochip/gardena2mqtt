import logging
import time
import os
from gardena.smart_system import SmartSystem
import paho.mqtt.client as mqtt
import json
import pprint

if __name__ == "__main__":
    logging.basicConfig( format="%(asctime)s: %(message)s", level=logging.INFO, datefmt="%H:%M:%S")

    versionnumber='0.0.3'

    logging.info(f'===== gardena2mqtt v{versionnumber} =====')

    # devmode is used to start container but not the code itself, then you can connect interactively and run this script by yourself
    # docker exec -it gardena2mqtt /bin/sh
    if os.getenv("DEVMODE",0) == "1":
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
    mqttprefix = os.getenv("PREFIX","gardena2mqtt")
    mqtthost = os.getenv("HOST","localhost")
    mqttport = os.getenv("PORT",1883)
    mqttclientid = os.getenv("CLIENTID","gardena2mqtt")
    mqttuser = os.getenv("USER")
    mqttpassword = os.getenv("PASSWORD")

    logging.info('===== Creation of SmartSystem =====')

    smart_system = SmartSystem(email=gardenauser, password=gardenapassword, client_id=gardenaapikey)
    logging.info('===== authenticate =====')
    smart_system.authenticate()
    logging.info('===== update_locations =====')
    smart_system.update_locations()
    for location in smart_system.locations.values():
        logging.info('===== update_devices =====')
        smart_system.update_devices(location)

    for location in smart_system.locations.values():
        LOCATION_ID=location.id
        locationDict=dict(location.__dict__)
        del locationDict['smart_system']
        pprint.pprint(json.dumps(locationDict))
        pprint.pprint(location.__dict__)
        for device in location.devices.values():
            deviceDict=dict(device.__dict__)
            del deviceDict['smart_system']
            pprint.pprint(json.dumps(deviceDict))

    # pprint(smart_system.locations[LOCATION_ID].devices['XX'])

    # smart_system.start_ws(smart_system.locations[LOCATION_ID])