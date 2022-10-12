from tapo_plug_controller import Tapo_device

tapo_device_humidifier = Tapo_device("192.168.0.17", "realkim93@gmail.com", "mushfresh1")

for i in range(30):
    print("#{} device status is {}".format(i, tapo_device_humidifier.device_status()))
