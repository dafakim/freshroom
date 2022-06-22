from argparse import Action
from ctypes import py_object
import logging
import json
import os
from tempfile import tempdir
from tkinter.filedialog import askdirectory
import traceback
from datetime import datetime
from multiprocessing import Process

import paho.mqtt.client as mqtt
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from miio import airhumidifier_mjjsq, heater_miot
from miio.exceptions import DeviceException
from pytz import timezone
from tapo_plug import tapoPlugApi

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

EVENT_TYPE_CO2 = "CO2"
EVENT_TYPE_HUMIDITY = "humidity"
EVENT_TYPE_TEMPERATURE = "temperature"
EVENT_TYPE_LIGHT = "light"

DATA_REQUEST_CHANNEL = "hyoja/dataRequest"
HUMIDIFIER_CONTROL_CHANNEL = "hyoja/humidifierStatus"
LIGHT_CONTROL_CHANNEL = "hyoja/lightStatus"


class FormatError(Exception):
    def __init__(self, msg):
        self.msg = msg
        super().__init__(self.msg)

class ZeroDataError(Exception):
    def __init__(self, msg):
        self.msg = msg
        super().__init__(self.msg)

'''
class FreshroomMQTTClient(object):
    mqtt_client
    scheduler

    listener
'''

def _process_temperature_data(location, data_list):
    #time = datetime.strftime(datetime.now(), "%Y-%M-%D %H:%M:%S")
    if 0 not in data_list:
        json_body = [
            {
                "measurement": "temperature",
                "time": datetime.now(timezone("Asia/Seoul")),
                "fields": {
                    "T1": data_list[0],
                    "T2": data_list[1],
                    "action": False
                }
            }
        ]
        temp_avg = sum(data_list)/len(data_list)

        try:
            heater = heater_miot.HeaterMiot(ip=os.getenv('HEATER_IP'), token=os.getenv('HEATER_TOKEN'))
        except Exception as e:
            print(e)
            sn.send_notification("Error", "Could not connect to heater")
            return -1

        is_on = heater.status().is_on
        if temp_avg > TEMPHIGH and is_on:
            heater.off()
        elif temp_avg < TEMPLOW and not is_on:
            heater.on()
        else:
            pass
        json_body[0]["fields"]["action"] = heater.status().is_on
    else:
        raise ZeroDataError("Temperature data has 0")
    dbm.db_insert(location, json_body)

def _process_humidity_data(location, data_list, client):
    if 0 not in data_list:
        json_body = [
            {
                "measurement": "humidity",
                "time": datetime.now(timezone("Asia/Seoul")),
                "fields": {
                    "H1": data_list[0],
                    "H2": data_list[1],
                    "action": False
                }
            }
        ]

        humidity_avg = sum(data_list)/len(data_list)
        
        if humidity_avg > HUMHIGH:
            client.publish(HUMIDIFIER_CONTROL_CHANNEL, OFF)
            json_body[0]["fields"]["action"] = OFF
        elif humidity_avg < HUMLOW:
            client.publish(HUMIDIFIER_CONTROL_CHANNEL, ON)
            json_body[0]["fields"]["action"] = ON
        else:
            pass
    else:
        raise ZeroDataError("Humidity data has 0")
    dbm.db_insert(location, json_body)

def turn_light(state, client):
    try:
        client.publish(LIGHT_CONTROL_CHANNEL, state)
    except Exception as e:
        print(e)
        sn.send_notification("Error", "Failed to publish to MQTT server")

def turn_airwash(state):
    # state is int value of 1(ON) or 0(off)
    device = {
    "tapoIp": "192.168.0.25",
    "tapoEmail": "realkim93@gmail.com",
    "tapoPassword": "mushfresh1"
    }
    if state:
        try:
            print(tapoPlugApi.plugOn(device))
            sn.send_notification("System Notification", "Turning airwash ON")
        except Exception as e:
            print(e)
            sn.send_notification("Error", "Could not turn on airwash")
    else:
        try:
            print(tapoPlugApi.plugOff(device))
            sn.send_notification("System Notification", "Turning airwash OFF")
        except Exception as e:
            print(e)
            sn.send_notification("Error", "Could not turn off airwash")

def request_data(client):
    client.publish(DATA_REQUEST_CHANNEL, 1)

def _on_connect(client, userdata, flags, rc):
    print("Connected with code" + str(rc))
    client.subscribe('#')

def _parse_payload(payload):
    if "," in payload:
        data1, data2 = payload.split(",")
        data_list = [float(data1), float(data2)]

        return data_list
    else:
        raise FormatError("Payload Invalid.\nReceived Payload: {}".format(payload))
    # split by ,
    # check if there are two numbers
    # raise error if there arent exactly two numbers

def _decode_msg(msg):
    # check msg validity
    if "/" in msg.topic:
        location, sensor_type = msg.topic.split("/")
        decoded_payload = msg.payload.decode("utf-8")

        return location, sensor_type, decoded_payload
    else:
        raise FormatError("Message Topic Invalid.\nReceived Message: {}".format(msg))

def _on_message(client, userdata, msg):
    try:
        location, sensor_type, payload = _decode_msg(msg)
        data_list = _parse_payload(payload)
        if EVENT_TYPE_HUMIDITY in sensor_type:
            _process_humidity_data(location, data_list, client)
        elif EVENT_TYPE_TEMPERATURE in sensor_type:
            _process_temperature_data(location, data_list)
        elif EVENT_TYPE_LIGHT in sensor_type:
            pass
        else:
            pass
    except FormatError as e:
        # send message and ignore current message
        sn.send_notification("Error", e)
    except ValueError as e:
        sn.send_notification("Error", e)
    except ZeroDataError as e:
        print(e)

def init_client():
    # type: () -> mqtt.Client
    # populate type_to_processor with valid processor instances
    client = mqtt.Client('M1')
    client.username_pw_set(os.getenv('ID'), os.getenv('PW'))
    client.on_connect = _on_connect
    client.on_message = _on_message

    return client

def add_datarequest_schedule(scheduler, client):
    scheduler.add_job(request_data, 'interval', seconds=10, args=[client])

def main():
    load_dotenv()
    SERVER_IP = os.getenv('IP')

    retry_count = 0
    while retry_count < 3:
        try:
            mqtt_client = init_client()
            mqtt_client.connect(SERVER_IP)
            '''
            Actor, Monitor

            Actor --> Action
                => set humidity
                => set temp
                => set light
                => set airwash

            <Actor trigger>
                
            Monitor --> take in values, call <actor trigger>
                --> Recorder 로 기록
                --> 필요시 action trigger
            BackgroundScheduler -> call <actor trigger>
                --> action trigger
            '''

            data_pulse_scheduler = BackgroundScheduler(timezone='Asia/Seoul')
            add_datarequest_schedule(data_pulse_scheduler, mqtt_client)
            sn.send_notification("System Notification", "Hyoja System Initiated")
        except Exception as e:
            logging.debug("Client Init Failed\n{}".format(e))
            sn.send_notification("Error", "Could not connect to MQTT server. Count {}".format(retry_count))
            retry_count += 1

        try:
            retry_count = 0
            data_pulse_scheduler.start()
            mqtt_client.loop_forever()
        except Exception as e:
            logging.debug("Client Loop Exited\n{}".format(e))
            sn.send_notification("Error", "RPI Stopped Due to Following Error\n{}\nRestarting ...".format(e))


if __name__ == '__main__':
    main()
