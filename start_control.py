import paho.mqtt.client as mqtt
from dotenv import load_dotenv
import os

def _on_connect(client, userdata, flags, rc):
    print("Connected with code" + str(rc))
    client.subscribe('#')

def _on_message(client, userdata, msg):
    print("TOPIC IS <" + msg.topic+">\n"+ "PAYLOAD iS {" + msg.payload.decode('utf-8')+"}")


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