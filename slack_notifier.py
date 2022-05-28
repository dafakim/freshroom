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