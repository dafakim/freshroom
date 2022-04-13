import requests
import json
url = "https://hooks.slack.com/services/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"

def send_notification(title, msg):
	slack_data = {
	"username": "StatusBot",
	"icon_emoji": ":warning:",
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
	response = requests.post(url, data=json.dumps(slack_data))