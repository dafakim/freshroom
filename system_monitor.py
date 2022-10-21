import datetime
import db_manager as dbm
import json
import logging
import os
import paho.mqtt.client as mqtt
import slack_notifier as sn

from dotenv import load_dotenv
from tapo_plug_controller import Tapo_device


logging.basicConfig(filename = "debug.log", level=logging.DEBUG)


KST = datetime.timezone(datetime.timedelta(hours=9))
LOCATION = "hyoja"
# make a separate config file to contain the following global variables & make a config listening logic
ON = 1
OFF = 0
# for ON and OFF make a separate class with on, off as enumerations
AIRWASHDURATION = 2
AIRWASHINTERVAL = 40

LIGHTSTARTTIME = 8
LIGHTENDTIME = 0

HUMHIGH = 91
HUMLOW = 89

TEMPHIGH = 12
TEMPLOW = 8

WRONGMSGCOUNT = 0

EVENT_TYPE_STATUS = "status"
EVENT_TYPE_CONDITION = "condition"

VALUE_TYPE_TEMPERATURE = "temperature"
VALUE_TYPE_HUMIDITY = "humidity"

RUNNING_CONDITION_CHANNEL = "hyoja/running_condition"

CRITICAL_HUMIDITY_FLAG = False

tapo_device_airflush = Tapo_device("192.168.0.25", "wbyim716@gmail.com", "mushfresh2022")
tapo_device_humidifier = Tapo_device("192.168.0.17", "realkim93@gmail.com", "mushfresh1")

class FormatError(Exception):
    """ catch format errors in either payload or messages from subscribed topics """

class ZeroDataError(Exception):
    """ catch no data coming in through subscribed topics"""

def _log_value(value_json):
    db_name = LOCATION
    result = dbm.db_insert(db_name, value_json)
    if not result:
        raise Exception("DB Insertion Failed")

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

def _handle_humidity(humidity_values):
    global CRITICAL_HUMIDITY_FLAG
    h1 = float(humidity_values[0])
    h2 = float(humidity_values[0])
    avg_humidity = (h1+h2)/2
    res = ""
    print("avg humidity", avg_humidity)
    '''
    if avg_humidity < HUMLOW:
        print("turning humidifier on...")
        res = tapo_device_humidifier.turn_on()
    elif avg_humidity > HUMHIGH:
        print("turning humidifier off...")
        res = tapo_device_humidifier.turn_off()
    else:
        CRITICAL_HUMIDITY_FLAG = False

    critical_humidity = HUMLOW * 0.9
    if avg_humidity < critical_humidity:
        if not CRITICAL_HUMIDITY_FLAG:
            CRITICAL_HUMIDITY_FLAG = True
            sn.send_notification("System Critical: Low Humidity", "Humidity lower than critical threshold. Current humidity : {}".format(avg_humidity))
    '''
    print("humidifier status is {}".format(res))

def _handle_topic_payload(location, topic, payload):
    if payload == "null":
        pass
    else:
        values = json.loads(payload)
        print(values)
        for value in values:
            if VALUE_TYPE_TEMPERATURE in value:
                #_handle_temperature(values[value])
                _log_temperature(values[value])
            elif VALUE_TYPE_HUMIDITY in value:
                _handle_humidity(values[value])
                _log_humidity(values[value])
            else:
                pass

def _handle_condition_payload(location, payload):
    # payload is a string in json format
    # load string to python dictionary and print information
    if payload == "null":
        pass
    else:
        conditions = json.loads(payload)
        print("From {}".format(location))
        for condition in conditions:
            print(condition, conditions[condition])

def _flush_air(status):
    res = ""
    value_json = [
        {
            "measurement": "air_flush_action",
            "fields": {
                "action": True
            },
            "time": str(datetime.datetime.now(KST))
        }
    ]
    if status:
        res = tapo_device_airflush.turn_on()
    else:
        res = tapo_device_airflush.turn_off()
        value_json[0]["fields"]["action"] = False
    print("airflush status is {}".format(res))
    _log_value(value_json)
    

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
        now_min = datetime.datetime.now().minute
        if now_min%AIRWASHINTERVAL == 0 or now_min%AIRWASHINTERVAL == 1:
            print("turning air flush on")
            _flush_air(True)
        else:
            print("turning airflush off")
            _flush_air(False)
        _flush_air(False)
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