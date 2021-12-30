import paho.mqtt.client as mqtt
from dotenv import load_dotenv
import os
from miio import airhumidifier_mjjsq
from datetime import datetime
import logging

TEMPHIGH = 25
TEMPLOW = 22
HUMHIGH = 90
HUMLOW = 85

def _process_temp(msg):
    msg = msg.split(',')
    total = 0
    for i in range(len(msg)):
        logging.info("Sensor: {}, Value: {}".format(i, msg[i]))
        total += float(msg[i])
    avg = total/len(msg)
    if avg > TEMPHIGH:
        # turn off heater
        pass
    elif avg < TEMPLOW:
        # turn on heater
        pass
    

def _process_humi(msg):
    humidifier = airhumidifier_mjjsq(ip="192.168.0.18", token="7c3d81298bac616875ed927108087c57")
    msg = msg.split(',')
    total = 0
    for i in range(len(msg)):
        logging.info("Sensor: {}, Value: {}".format(i, msg[i]))
        total += float(msg[i])
    avg = total/len(msg)
    if avg > HUMHIGH:
        # turn off humidifier
        humidifier.off()
    elif avg < HUMLOW:
        # turn on humidifier
        humidifer.on()
    

def _on_connect(client, userdata, flags, rc):
    print("Connected with code" + str(rc))
    client.subscribe('#')

def _on_message(client, userdata, msg):
    topic = msg.topic.split('/')
    location = topic[0]
    sensor_type = topic[1]
    decoded_msg = msg.payload.decode('utf-8')
    logging.debug("{}\nLOCATION: {}\nSENSOR: {}\nPAYLOAD: {}".format(datetime.now(), location, sensor_type, decoded_msg))
    if "temperature" in sensor_type:
        _process_temp(decoded_msg)
    elif "humidity" in sensor_type:
        _process_humi(decoded_msg)
    else:
        pass



def main():
    load_dotenv()
    client = mqtt.Client('M1')
    client.username_pw_set(os.getenv('ID'), os.getenv('PW'))
    client.on_connect = _on_connect
    client.on_message = _on_message
    client.connect(os.getenv('IP'))
    client.loop_forever()

if __name__ == '__main__':
    main()