import json
import logging
import os
import datetime

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

import db_manager as dbm
import slack_notifier as sn


logging.basicConfig(filename = "debug.log", level=logging.DEBUG)


KST = datetime.timezone(datetime.timedelta(hours=9))
LOCATION = "hyoja"
# make a separate config file to contain the following global variables & make a config listening logic
ON = 1
OFF = 0
# for ON and OFF make a separate class with on, off as enumerations
AIRWASHTIME = 5

LIGHTSTARTTIME = 8
LIGHTENDTIME = 0

HUMHIGH = 92
HUMLOW = 88

TEMPHIGH = 12
TEMPLOW = 8

WRONGMSGCOUNT = 0

EVENT_TYPE_STATUS = "status"
EVENT_TYPE_CONDITION = "condition"

VALUE_TYPE_TEMPERATURE = "temperature"
VALUE_TYPE_HUMIDITY = "humidity"

RUNNING_CONDITION_CHANNEL = "hyoja/running_condition"


class FormatError(Exception):
    """ catch format errors in either payload or messages from subscribed topics """

class ZeroDataError(Exception):
    """ catch no data coming in through subscribed topics"""

def _log_value(value_json):
    db_name = LOCATION
    try:
        dbm.db_insert(db_name, json_string)
    except Exception as e:
        print(e)

def _log_temperature(values):
    t1 = float(values[0])
    t2 = float(values[1])
    value_json = [
        {
            "measurement": VALUE_TYPE_TEMPERATURE,
            "fields": {
                "T1": t1,
                "T2": t2,
            },
            "time": str(datetime.datetime.now(KST))
        }
    ]
    print("Temperature is {}, {}".format(t1, t2))
    _log_value(value_json)

def _log_humidity(values):
    h1 = float(values[0])
    h2 = float(values[1])
    value_json = [
        {
            "measurement": VALUE_TYPE_HUMIDITY,
            "fields": {
                "H1": h1,
                "H2": h2,
            },
            "time": str(datetime.datetime.now(KST))
        }
    ]
    print("Humidity is {}, {}".format(h1, h2))
    _log_value(value_json)

def send_new_condition(client, new_condition):
    client.publish(RUNNING_CONDITION_CHANNEL, new_condition)

def _handle_topic_payload(location, topic, payload):
    if "null" == payload:
        pass
    else:
        values = json.loads(payload)
        print(values)
        for value in values:
            if VALUE_TYPE_TEMPERATURE in value:
                _log_temperature(values[value])
            elif VALUE_TYPE_HUMIDITY in value:
                _log_humidity(values[value])
            else:
                pass

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
        else:
            pass
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