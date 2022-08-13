import json
import logging
import os
from datetime import datetime

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

import db_manager as dbm
import slack_notifier as sn


logging.basicConfig(filename = "debug.log", level=logging.DEBUG)


# make a separate config file to contain the following global variables & make a config listening logic
ON = 1
OFF = 0
# for ON and OFF make a separate class with on, off as enumerations
AIRWASHTIME = 5

LIGHTSTARTTIME = 8
LIGHTENDTIME = 0

HUMHIGH = 85
HUMLOW = 80

TEMPHIGH = 12
TEMPLOW = 8

WRONGMSGCOUNT = 0

EVENT_TYPE_STATUS = "status"
EVENT_TYPE_CONDITION = "condition"

RUNNING_CONDITION_CHANNEL = "hyoja/running_condition"


class FormatError(Exception):
    """ catch format errors in either payload or messages from subscribed topics """

class ZeroDataError(Exception):
    """ catch no data coming in through subscribed topics"""


def _handle_topic_payload(location, topic, payload):
    values = json.loads(payload)
    print("From {} in {}".format(location, topic))
    for value in values:
        print(value, values[value])

def _handle_condition_payload(location, payload):
    # payload is a string in json format
    # load string to python dictionary and print information
    conditions = json.loads(payload)
    print("From {}".format(location))
    for condition in conditions:
        print(condition, conditions[condition])

def _decode_msg(msg):
    # check msg validity
    if "/" in msg.topic:
        # topic from mqtt has location/topic. parse location and topic from the mqtt topic and return
        location, topic = msg.topic.split("/")
        decoded_payload = msg.payload.decode("utf-8")

        return location, topic, decoded_payload
    else:
        raise FormatError("Message Topic Invalid.\nReceived Message: {}".format(msg))

def _on_connect(client, userdata, flags, rc):
    print("Connected with code" + str(rc))
    client.subscribe('#')

def _on_message(client, userdata, msg):
    try:
        location, topic, payload = _decode_msg(msg)
        if EVENT_TYPE_STATUS in topic:
            _handle_topic_payload(location, topic, payload)
        elif EVENT_TYPE_CONDITION in topic:
            _handle_condition_payload(location, payload)
    except FormatError as e:
        # send message and ignore current message
        sn.send_notification("", e)

def init_client(MQTT_SERVER_IP):
    # type: () -> mqtt.Client
    # populate type_to_processor with valid processor instances
    client = mqtt.Client('M1')
    client.username_pw_set(os.getenv('ID'), os.getenv('PW'))
    client.on_connect = _on_connect
    client.on_message = _on_message
    client.connect(MQTT_SERVER_IP)
    return client

def main():
    load_dotenv()
    MQTT_SERVER_IP = os.getenv('IP')

    retry_count = 0
    while retry_count < 3:
        try:
            mqtt_client = init_client(MQTT_SERVER_IP)
            sn.send_notification("System Notification", "Hyoja System Initiated")
        except Exception as e:
            logging.debug("Client Init Failed\n{}".format(e))
            sn.send_notification("Error", "Could not connect to MQTT server. Count {}".format(retry_count))
            retry_count += 1

        try:
            retry_count = 0
            mqtt_client.loop_forever()
        except Exception as e:
            logging.debug("Client Loop Exited\n{}".format(e))
            sn.send_notification("Error", "RPI Stopped Due to Following Error\n{}\nRestarting ...".format(e))

if __name__ == '__main__':
    main()