import requests
# from conf.config import config, logger
import urllib.parse
import os
# Configuration


# PIHOLE_API_URL = "http://pihole/api"
# PIHOLE_AUTH_URL = "http://pihole/api/auth"


url = "http://localhost:3000/api/sendText"
headers = {
    "Content-Type": "application/json",
}
data = {
    "session": "default",
    "chatId": "917318019211@c.us",
    "text": "Hi there!"
}


class Alerts:
    def __init__(self, API_KEY):
        self.url = url
        self.headers = headers
        self.data = data
        self.headers["X-Api-Key"] = API_KEY
    def send_message(self, title="", body=""):
        try:
            data['text'] = title + "\n" + body
            response = requests.post(url, json=self.data, headers=self.headers)
        except Exception as e:
            print(f"Error sending message: {e}")



