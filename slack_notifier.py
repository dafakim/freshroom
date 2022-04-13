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

def main():
	send_notification("Notification from libary", "SUCCESS")

if __name__ == "__main__":
	main()