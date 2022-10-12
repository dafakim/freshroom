import json

from tapo_plug import tapoPlugApi


class Tapo_device:
    def __init__(self, ip, email, passwd):
        self.ip = ip
        self.email = email
        self.passwd = passwd
        self.device_info = {
            "tapoIp": ip,
            "tapoEmail": email,
            "tapoPassword": passwd
        }

    def device_status(self):
        try:
            status = tapoPlugApi.getDeviceRunningInfo(self.device_info)
            status = json.loads(status)
            result = status["result"]["device_on"]
        except:
            result = "unreachable"
        return result

    def turn_on(self):
        tapoPlugApi.plugOn(self.device_info)
        return self.device_status()
    
    def turn_off(self):
        tapoPlugApi.plugOff(self.device_info)
        return self.device_status()