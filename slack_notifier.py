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