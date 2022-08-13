import paho.mqtt.client as mqtt
from dotenv import load_dotenv
import os 
import json

from system_monitor import send_new_condition


PATCH_CONFIG_CHANNEL = "hyoja/condition_patch_note"

def _on_connect(client, userdata, flags, rc):
    print("Connected with code" + str(rc))
    client.subscribe('#')

def _on_message(client, userdata, msg):
    print(msg)

def init_client(MQTT_SERVER_IP):
    # populate type_to_processor with valid processor instances
    client = mqtt.Client('testclient')
    client.username_pw_set(os.getenv('ID'), os.getenv('PW'))
    client.on_connect = _on_connect
    client.on_message = _on_message
    client.connect(MQTT_SERVER_IP)
    return client

load_dotenv()
MQTT_SERVER_IP = os.getenv('IP')
mqtt_client = init_client(MQTT_SERVER_IP)

config = {"temperature_threshold": [20, 25],
"humidity_threshold": [90, 85],
"led_time": [22, 7],
"air_flush_time": [15, 5]}
new_config = json.dumps(config)
print("publishing new config\n{}".format(new_config))
mqtt_client.publish(PATCH_CONFIG_CHANNEL, new_config)