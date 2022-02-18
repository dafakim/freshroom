from influxdb import InfluxDBClient
from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv()
client = InfluxDBClient(host=os.getenv('DB_IP'), port=8086, username=os.getenv('DB_ID'), password=os.getenv('DB_PW'))

def db_exist(dbname):
    db_list = client.get_list_database()
    for db in db_list:
        if dbname in db["name"]:
            return True
    return False

def db_init(dbname):
    if not db_exist(dbname):
        client.create_database(dbname)
    else:
        return False

def db_insert(dbname, jsondata):
    if db_exist(dbname):
        client.switch_database(dbname)
        client.write_points(jsondata)
        return True
    else:
        print("db does not exist {}".format(dbname))
        return False

if __name__ == '__main__':
    #db_init("hyoja")
    client.switch_database("hyoja")
    print(client.get_list_database())
    response = client.query('SELECT * FROM "temperature"')
    print(response.raw)