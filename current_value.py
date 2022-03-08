from dotenv import load_dotenv
from miio import airhumidifier_mjjsq, heater_miot
import os
import paho.mqtt.client as mqtt
import logging

logging.basicConfig(level=logging.INFO)

def _check_miio():
    heater = heater_miot.HeaterMiot(ip=os.getenv('HEATER_IP'), token=os.getenv('HEATER_TOKEN'))
    humidifier = airhumidifier_mjjsq.AirHumidifierMjjsq(ip=os.getenv('HUMIDIFIER_IP'), token=os.getenv('HUMIDIFIER_TOKEN'))

    print("{:*^30}\n{}".format("HUMIDIFIER STATUS", humidifier.status()))
    print("{:*^30}\n{}".format("HEATER STATUS", heater.status()))

def _on_connect(client, userdata, flags, rc):
    print("Connected with code" + str(rc))
    client.subscribe('#')

def _on_message(client, userdata, msg):
    topic = msg.topic.split('/')
    location = topic[0]
    sensor_type = topic[1]
    decoded_msg = msg.payload.decode('utf-8')
    logging.info("{}\nLOCATION: {}\nSENSOR: {}\nPAYLOAD: {}".format(datetime.now(timezone('Asia/Seoul')), location, sensor_type, decoded_msg))

def main():
    load_dotenv()
    client = mqtt.Client('Test')
    client.username_pw_set(os.getenv('ID'), os.getenv('PW'))
    client.on_connect = _on_connect
    client.on_message = _on_message
    client.connect(os.getenv('IP'))

if __name__ == '__main__':
    main()