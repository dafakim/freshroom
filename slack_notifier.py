import requests
import json
import os 

def send_notification(title, msg):
	slack_data = {
	"username": "StatusBot",
	"icon_emoji": ":warning:",
	"text": title,
	"attachments": [
		{
		"fields": [
			{
				"title": title,
				"value": msg,
				"short": "false",
			}]
			}]
		}
	url = os.getenv('SLACK_WEBHOOK_URL')
	response = requests.post(url, data=json.dumps(slack_data))

def main():
	send_notification("Notification from libary", "SUCCESS")

if __name__ == "__main__":
	main()
