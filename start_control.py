import logging
import json
import os
import traceback
from datetime import datetime
from multiprocessing import Process

import paho.mqtt.client as mqtt
from dotenv import load_dotenv
from miio import airhumidifier_mjjsq, heater_miot
from pytz import timezone
from tapo_plug import tapoPlugApi

import db_manager as dbm
import slack_notifier as sn


logging.basicConfig(filename = 'debug.log', level=logging.DEBUG)


TEMPHIGH = 12
TEMPLOW = 8
HUMHIGH = 85
HUMLOW = 80
AIRWASHTIME = 5

#class sensorProcess(Process)

def _process_temp(location, msg):
    #time = datetime.strftime(datetime.now(), "%Y-%M-%D %H:%M:%S")
    if len(msg) > 1:
        json_body = [
            {
                "measurement": "temperature",
                "time": datetime.now(timezone('Asia/Seoul')),
                "fields": {
                    "T1": float(msg[0]),
                    "T2": float(msg[1]),
                    "action": False
                }
            }
        ]
        heater = heater_miot.HeaterMiot(ip=os.getenv('HEATER_IP'), token=os.getenv('HEATER_TOKEN'))
        is_on = heater.status().is_on
        total = 0
        for i in range(len(msg)):
            logging.debug("Sensor: {}, Value: {}".format(i, msg[i]))
            total += float(msg[i])
        avg = total/len(msg)
        if avg > TEMPHIGH and is_on:
            heater.off()
        elif avg < TEMPLOW and not is_on:
            heater.on()
        json_body[0]["fields"]["action"] = heater.status().is_on
    else:
        json_body = [
            {
                "measurement": "temperature",
                "time": datetime.now(timezone('Asia/Seoul')),
                "fields": {
                    "T1": float(msg[0])
                }
            }
        ]
    print(dbm.db_insert(location, json_body))

def _process_humi(location, msg):
    #time = datetime.strftime(datetime.now(), "%Y-%M-%D %H:%M:%S")
    if len(msg) > 1:
        json_body = [
            {
                "measurement": "humidity",
                "time": datetime.now(timezone('Asia/Seoul')),
                "fields": {
                    "H1": float(msg[0]),
                    "H2": float(msg[1]),
                    "action": False
                }
            }
        ]
        humidifier = airhumidifier_mjjsq.AirHumidifierMjjsq(ip=os.getenv('HUMIDIFIER_IP'), token=os.getenv('HUMIDIFIER_TOKEN'))
        is_on = humidifier.status().is_on
        if humidifier.status().no_water:
            logging.error("HUMIDIFIER NO WATER, PLEASE FILL ASAP")
            if is_on:
                humidifier.off()
            else:
                pass
            return -1
        total = 0
        for i in range(len(msg)):
            logging.debug("Sensor: {}, Value: {}".format(i, msg[i]))
            total += float(msg[i])
        avg = total/len(msg)
        if avg > HUMHIGH and is_on:
            # turn off humidifier
            humidifier.off()
        elif avg < HUMLOW and not is_on:
            # turn on humidifier
            humidifier.on()
        json_body[0]["fields"]["action"] = humidifier.status().is_on
    else:
        json_body = [
            {
                "measurement": "humidity",
                "time": datetime.now(timezone('Asia/Seoul')),
                "fields": {
                    "H1": float(msg[0])
                }
            }
        ]
    dbm.db_insert(location, json_body)

def process_airwash():
    device = {
    "tapoIp": "192.168.0.25",
    "tapoEmail": "realkim93@gmail.com",
    "tapoPassword": "mushfresh1"
    }
    now_minute = datetime.now().minute
    plug_is_on = tapoPlugApi.getDeviceRunningInfo(device)
    plug_is_on = json.loads(plug_is_on)
    plug_is_on = plug_is_on["result"]["device_on"]
    if now_minute < AIRWASHTIME:
        if not plug_is_on:
            try:
                print(tapoPlugApi.plugOn(device))
            except Exception as e:
                print(e)
    else:
        if plug_is_on:
            try:
                print(tapoPlugApi.plugOff(device))
            except Exception as e:
                print(e)

def _on_connect(client, userdata, flags, rc):
    print("Connected with code" + str(rc))
    client.subscribe('#')

EVENT_TYPE_HUMIDITY = "humidity"
EVENT_TYPE_TEMPERATURE = "temperature"

type_to_processor = {
    EVENT_TYPE_HUMIDITY: instance,
    EVENT_TYPE_TEMPERATURE: instance
}

def _on_message(client, userdata, msg):
    location, sensor_type = msg.topic.split('/')
    # decoded_msg = decode_msg(msg.payload)
    decoded_msg = msg.payload.decode('utf-8')

    # check validity of decoded_msg, if not valid raise error
    # if valid(decoded_msg):
    #   type_instance=t2p[sensor_type]
    #   type_instance.acton(decoded_msg)
    # else:
    #   raise error
    # 


    messages = decoded_msg.split(',')

    if len(messages) == 2:
        if not (messages[0] == '0' and messages[1] == '0'):
            # error
            pass
        else:
            # error
            pass

    else:
        # unexpected
        logging.error(f"{datetime.now(timezone('Asia/Seoul'))}\n"
                      + f"LOCATION: {location}\n"
                      + f"SENSOR: {sensor_type}\n"
                      + f"PAYLOAD: {decoded_msg}")

    if ',' in decoded_msg:
        split_msg = decoded_msg.split(',')
        if split_msg[0] == split_msg[1]:
            if int(float(split_msg[0])) == 0:
                print("Zero Data")
                #sn.send_notification("Zero Data Notification", "Receieved 0 at following sensor\nLOCATION: {}\nSENSOR: {}".format(location, sensor_type))
    else:
        split_msg = [decoded_msg]
    # disable temperature humidity controls until setup finished
    if "temperature" in sensor_type:
        _process_temp(location, split_msg)
    elif EVENT_TYPE_HUMIDITY in sensor_type:
        _process_humi(location, split_msg)
    else:
        pass
    _process_airwash()

def init_client():
    # type: () -> mqtt.Client
    # populate type_to_processor with valid processor instances
    client = mqtt.Client('M1')
    client.username_pw_set(os.getenv('ID'), os.getenv('PW'))
    client.on_connect = _on_connect
    client.on_message = _on_message

    return client


def main():
    load_dotenv()
    SERVER_IP = os.getenv('IP')

    retry_count = 0
    while retry_count < 3:
        try:
            client = init_client()
            client.connect(SERVER_IP)
            sn.send_notification("System Notification", "Starting Hyoja RPI")
        except Exception as e:
            logging.debug("Client Init Failed\n{}".format(e))
            sn.send_notification("Error", "Could not connect to MQTT server. Count {}".format(retry_count))
            retry_count +=1
        try:
            retry_count = 0
            humitemp_control = Process(target=client.loop_forever)
            airwash_control = Process(target=process_airwash)
            humitemp_control.start()
            airwash_control.start()
        except Exception as e:
            logging.debug("Client Loop Exited\n{}".format(e))
            sn.send_notification("Error", "RPI Stopped Due to Following Error\n{}\nRestarting ...".format(e))


if __name__ == '__main__':
    main()
