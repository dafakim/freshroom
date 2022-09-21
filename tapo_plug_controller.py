import json

from tapo_plug import tapoPlugApi


class tapo_device:
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
        status = tapoPlugApi.getDeviceRunningInfo(self.device_info)
        status = json.loads(status)
        return status["result"]["device_on"]

    def turn_on(self):
        tapoPlugApi.plugOn(self.device_info)
        return self.device_status()
    
    def turn_off(self):
        tapoPlugApi.plugOn(self.device_info)
        return self.device_status()