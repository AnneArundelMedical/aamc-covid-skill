#!/usr/bin/env python3
import datetime, requests, json

class MessageApi:

    def __init__(self, api_host, username=None, password=None):
        self.__host = api_host
        if username and password:
            self.__auth = (username, password)
        else:
            self.__auth = None
        self.__message_handlers = {}

    def __url(self, route):
        return 'https://%s/api/%s' % (self.__host, route)

    def send_message(self, message_type, payload):
        self.post("event/client", message_type, data = payload)

    def receive_messages(self):
        return self.get("event/client")

    def get(self, route):
        r = requests.get(self.__url(route), auth=self.__auth)
        return self.__process_response(r)

    def post(self, route, args):
        r = requests.post(self.__url(route), auth=self.__auth)
        return self.__process_response(r)

    def __process_response(self, r):
        if r.status_code == 200:
            if r.text == "":
                return None
            return json.loads(r.text)
        else:
            raise RequestError(r.status_code, r.status_text)

    def report_proning_position(self, position_number: int):
        self.send_message("ReportProning", { "position": position_number })

    def call_nurse(self):
        self.send_message("CallNurse", {})

    def add_message_handler(self, message_name, message_handler):
        self.__message_handlers[message_name] = message_handler

    def poll_events(self):
        events = self.receive_messages()
        for e in events:
            mt = e["message_type"]
            handler = self.__message_handlers.get(mt)
            if not handler:
                self.log.error("Unhandled event: " + json.dumps(e))
            try:
                handler(e)
            except Exception as e:
                self.log.error(e)

class RequestError(Exception):
    pass

class TestInteractive:
    def __init__(self, host="localhost"):
        self.api = MessageApi(host)
        self.api.add_message_handler("StartProning", self.h_start_proning)
        self.api.add_message_handler("StopProning", self.h_stop_proning)
        self.position = 0
    def status(self):
        print("Mycroft Test Status:")
        print("  Proning position:", self.position)
    def poll_events(self):
        self.api.poll_events()
    def call_nurse(self):
        self.api.call_nurse()
    def proning(self, position):
        self.api.report_proning_position(position)
        self.position = position
    def h_start_proning(self, message_type, payload):
        print("START PRONING")
        print("SPEAK: Start proning position %d." % payload["position"])
    def h_stop_proning(self, message_type, payload):
        print("STOP PRONING")

