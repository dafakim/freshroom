import paho.mqtt.client as mqtt
from dotenv import load_dotenv
import os
from miio import airhumidifier_mjjsq, heater_miot
from datetime import datetime
from pytz import timezone
import logging
import slack_notifier as sn
import db_manager as dbm
from tapo_plug import tapoPlugApi
import json

logging.basicConfig(filename = 'debug.log', level=logging.DEBUG)

TEMPHIGH = 12
TEMPLOW = 8
HUMHIGH = 85
HUMLOW = 80
AIRWASHTIME = 5

def _process_temp(msg):
    msg = msg.split(',')
    #time = datetime.strftime(datetime.now(), "%Y-%M-%D %H:%M:%S")
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
    print(dbm.db_insert("hyoja", json_body))

def _process_humi(msg):
    msg = msg.split(',')
    #time = datetime.strftime(datetime.now(), "%Y-%M-%D %H:%M:%S")
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
    dbm.db_insert("hyoja", json_body)

def _process_airwash():
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

def _on_message(client, userdata, msg):
    topic = msg.topic.split('/')
    location = topic[0]
    sensor_type = topic[1]
    decoded_msg = msg.payload.decode('utf-8')
    #logging.info("{}\nLOCATION: {}\nSENSOR: {}\nPAYLOAD: {}".format(datetime.now(timezone('Asia/Seoul')), location, sensor_type, decoded_msg))
    msg = decoded_msg.split(',')
    if msg[0] == msg[1]:
        if int(float(msg[0])) == 0:
            sn.send_notification("Zero Data Notification", "Receieved 0 at following sensor\nLOCATION: {}\nSENSOR: {}".format(location, sensor_type))
    # disable temperature humidity controls until setup finished
    if "temperature" in sensor_type:
        _process_temp(decoded_msg)
    elif "humidity" in sensor_type:
        _process_humi(decoded_msg)
    else:
        pass
    _process_airwash()

def main():
    load_dotenv()
    client = mqtt.Client('M1')
    client.username_pw_set(os.getenv('ID'), os.getenv('PW'))
    client.on_connect = _on_connect
    client.on_message = _on_message
    client.connect(os.getenv('IP'))
    try:
        client.loop_forever()
    except Exception as e:
        print(e)
        logging.debug(e)
        sn.send_notification("RPI Error Notification", "RPI Stopped Due to Following Error\n{}\nRestarting ...".format(e))
        main()


if __name__ == '__main__':
    main()
