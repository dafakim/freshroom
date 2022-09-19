import argparse
import json
import os 
import paho.mqtt.client as mqtt

from dotenv import load_dotenv
from system_monitor import send_new_condition

list_tp = lambda x:list(map(int, x.split(',')))
parser = argparse.ArgumentParser(description="Send a new configuration to ESP boards in the same mqtt channel")
parser.add_argument('-t', '--temperature', type=list_tp, default=[20,25])
parser.add_argument('-hu', '--humidity', type=list_tp, default=[8,12])
args = parser.parse_args()

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

config = {"temperature_threshold": args.temperature,
"humidity_threshold": args.humidity,
"led_time": [22, 7],
"air_flush_time": [15, 5]}
new_config = json.dumps(config)
print("publishing new config\n{}".format(new_config))
mqtt_client.publish(PATCH_CONFIG_CHANNEL, new_config)