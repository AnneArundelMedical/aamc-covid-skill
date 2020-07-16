#!/usr/bin/env python3
import datetime, requests, json, socket, pathlib, os.path, uuid
import traceback
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TEST_HOST = "localhost:44301"

class MessageApi:

    def __init__(self, api_host, username=None, password=None):
        self.__host = api_host
        if username and password:
            self.__auth = (username, password)
        else:
            self.__auth = None
        self.__verify = False # FIXME: Configure with client cert
        self.__message_handlers = {}
        self.ip_address = self.get_ip_address()
        self.guid = self.get_guid()
        self.device_id = self.register_device()

    def get_ip_address(self):
        return socket.gethostbyname(socket.gethostname()) # FIXME: might not work everywhere

    def get_guid(self):
        home_dir = pathlib.Path.home()
        guid_path = os.path.join(home_dir, "aamc_device_guid")
        if os.path.exists(guid_path):
            with open(guid_path) as f:
                guid = f.read().strip()
        else:
            guid = str(uuid.uuid4())
            with open(guid_path, "w") as f:
                print(guid, file=f)
        return guid

    def __url(self, route):
        return 'https://%s/api/%s' % (self.__host, route)

    def send_message(self, message_type, payload):
        self.post("event/client", {
            "senderDeviceId": self.device_id,
            "messageType": message_type,
            "payload": payload,
        })

    def receive_messages(self):
        return self.get("event/server/%d" % self.device_id)

    def register_device(self):
        return self.post("event/device", { "guid": self.guid, "ipAddress": self.ip_address })

    def get(self, route):
        r = requests.get(self.__url(route), auth=self.__auth, verify=self.__verify)
        return self.__process_response(r)

    def post(self, route, args):
        print("ARGS:", args)
        r = requests.post(
            self.__url(route),
            data=json.dumps(args),
            headers={"content-type": "application/json"},
            auth=self.__auth,
            verify=self.__verify,
            )
        return self.__process_response(r)

    def __process_response(self, r):
        if r.status_code == 200:
            if r.text == "":
                return None
            return r.json()
        else:
            raise RequestError(r.status_code)

    def report_proning_position(self, position_number: int):
        self.send_message("ReportProning", { "position": position_number })

    def call_nurse(self):
        self.send_message("CallNurse", {})

    def add_message_handler(self, message_name, message_handler):
        self.__message_handlers[message_name] = message_handler

    def poll_messages(self):
        print("poll_messages: begin")
        messages = self.receive_messages()
        for msg in messages:
            print("poll_messages:", json.dumps(msg))
            mt = msg["messageType"]
            handler = self.__message_handlers.get(mt)
            if not handler:
                print("Unhandled event: " + json.dumps(msg))
                #self.log.error("Unhandled event: " + json.dumps(msg))
                pass
            try:
                handler(mt, msg["payload"])
                self.mark_message_complete(msg["messageId"])
            except Exception as e:
                #self.log.error(msg)
                print("ERROR HANDLING MESSAGE:")
                traceback.print_exc()

    def mark_message_complete(self, message_id):
        return self.post("event/server/%d/%d/complete" % (self.device_id, message_id), {})

class RequestError(Exception):
    pass

class Tester:
    def __init__(self, host=None):
        if not host:
            host = TEST_HOST
        self.api = MessageApi(host)
        self.api.add_message_handler("StartProning", self.h_start_proning)
        self.api.add_message_handler("StopProning", self.h_stop_proning)
        self.position = 0
    def status(self):
        print("Mycroft Test Status:")
        print("  Proning position:", self.position)
    def poll(self):
        print("poll: begin")
        self.api.poll_messages()
        print("poll: end")
    def call(self):
        self.api.call_nurse()
    def proning(self, position):
        self.api.report_proning_position(position)
        self.position = position
    def h_start_proning(self, message_type, payload):
        print("START PRONING")
        position = payload["position"]
        print("SPEAK: Start proning position %d." % position)
        self.status()
        self.api.report_proning_position(position)
    def h_stop_proning(self, message_type, payload):
        print("STOP PRONING")
        self.api.report_proning_position(0)

def test():
    x = Tester()
    x.poll()
    x.call()

