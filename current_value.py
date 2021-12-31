from dotenv import load_dotenv
from miio import airhumidifier_mjjsq, heater_miot

load_dotenv()
heater = heater_miot.HeaterMiot(ip=os.getenv('HEATER_IP'), token=os.getenv('HEATER_TOKEN'))
humidifier = airhumidifier_mjjsq.AirHumidifierMjjsq(ip=os.getenv('HUMIDIFIER_IP'), token=os.getenv('HUMIDIFIER_TOKEN'))

print("{:*^30}\n{}".format("HUMIDIFIER STATUS", humidifier.status()))
print("{:*^30}\n{}".format("HEATER STATUS", heater.status()))
