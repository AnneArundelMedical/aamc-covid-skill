#!/usr/bin/env python3
import datetime, requests, json, socket, pathlib, os.path, uuid, subprocess
import traceback
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TEST_HOST = "localhost:44301"

USE_SSL = False # TODO: add to config

def _format_log_message(message):
    if isinstance(message, str):
        return message
    try:
        return " ".join([ str(field) for field in message ])
    except TypeError:
        return str(message)

class MessageApi:

    def __init__(self, api_host, config_dir, username=None, password=None, log=None):
        if not api_host:
            raise Exception("API host not specified.")
        elif log:
            log.info("Using API host: " + api_host)
        self.__host = api_host
        self.__config_dir = config_dir
        if username and password:
            self.__auth = (username, password)
        else:
            self.__auth = None
        self.__log = log
        self.__verify = False # FIXME: Configure with client cert
        self.__message_handlers = {}
        try:
            self.ip_addresses = self.get_ip_addresses()
        except:
            self.ip_addresses = "<ERROR>"
        self.guid = self.get_guid()
        self.device_id = self.register_device()

    def __log_info(self, *message):
        if self.__log:
            self.__log.info(_format_log_message(message))

    def __log_error(self, *message):
        if self.__log:
            self.__log.error(_format_log_message(message))

    def get_ip_addresses(self):
        ip_addrs_process = subprocess.Popen(
            ["hostname", "-I"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        ip_addrs = ip_addrs_process.stdout.read().decode().split()
        return ip_addrs

    def get_guid(self):
        guid_path = os.path.join(self.__config_dir, "aamc_device_guid")
        if os.path.exists(guid_path):
            with open(guid_path) as f:
                guid = f.read().strip()
        else:
            guid = str(uuid.uuid4())
            with open(guid_path, "w") as f:
                print(guid, file=f)
        return guid

    def __url(self, route):
        protocol = "https" if USE_SSL else "http"
        return '%s://%s/api/%s' % (protocol, self.__host, route)

    def send_message(self, message_type, payload):
        self.post("event/client", {
            "senderDeviceId": self.device_id,
            "messageType": message_type,
            "payload": payload,
        })

    def get_device_id(self):
        return self.device_id

    def receive_messages(self):
        return self.get("event/server/%d" % self.device_id)

    def register_device(self):
        device_id = self.post("event/device", {
            "guid": self.guid,
            "ipAddress": ";".join(self.get_ip_addresses()),
        })
        try:
            # Save the device ID to the config dir for debugging purposes.
            device_id_path = os.path.join(self.__config_dir, "aamc_device_id")
            with open(device_id_path, "w") as f:
                f.write(str(device_id))
        except:
            pass
        return device_id

    def get(self, route):
        url = self.__url(route)
        self.__log_info("GET URL:", url)
        r = requests.get(url, auth=self.__auth, verify=self.__verify)
        return self.__process_response(r)

    def post(self, route, args):
        url = self.__url(route)
        self.__log_info("POST URL:", url)
        args_json = json.dumps(args)
        self.__log_info("POST ARGS:", args_json)
        r = requests.post(
            url,
            data=args_json,
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

    def add_message_handler(self, message_name, message_handler):
        self.__message_handlers[message_name] = message_handler

    def poll_messages(self):
        #print("poll_messages: begin")
        messages = self.receive_messages()
        for msg in messages:
            try:
                self.__log_info("Message received:", json.dumps(msg))
            except:
                self.__log_info("Message received (unable to display)")
            mt = msg["messageType"]
            handler = self.__message_handlers.get(mt)
            if not handler:
                self.__log_error("Unhandled event: " + json.dumps(msg))
                pass
            try:
                handler(mt, msg["payload"])
                self.mark_message_complete(msg["messageId"])
            except Exception as e:
                self.__log_error("ERROR HANDLING MESSAGE: " + json.dumps(msg))
                self.__log_error(traceback.format_exc())

    def mark_message_complete(self, message_id):
        return self.post("event/server/%d/%d/complete" % (self.device_id, message_id), {})

class AamcCovidMessenger:

    def __init__(self, api):
        self.api = api

    def report_proning_position(self, position_number: int):
        self.api.send_message("ReportProning", { "position": position_number })

    def report_proning_state(self, state, position_number: int, args={}):
        payload = { "state": state, "position": position_number, "args": args }
        self.api.send_message("ReportProningState", payload)

    def call_nurse(self):
        self.api.send_message("CallNurse", {})

    def poll(self):
        self.api.poll_messages()

class RequestError(Exception):
    pass

class Tester:
    def __init__(self, host=None):
        if not host:
            host = TEST_HOST
        home_dir = pathlib.Path.home()
        self.api = MessageApi(host, home_dir)
        self.api.add_message_handler("StartProning", self.h_start_proning)
        self.api.add_message_handler("StopProning", self.h_stop_proning)
        self.messenger = AamcCovidMessenger(self.api)
        self.position = 0
    def status(self):
        print("Mycroft Test Status:")
        print("  Proning position:", self.position)
    def poll(self):
        print("poll: begin")
        self.messenger.poll()
        print("poll: end")
    def call(self):
        self.messenger.call_nurse()
    def proning(self, position):
        self.messenger.report_proning_position(position)
        self.position = position
    def h_start_proning(self, message_type, payload):
        print("START PRONING")
        position = payload["position"]
        print("SPEAK: Start proning position %d." % position)
        self.status()
        self.messenger.report_proning_position(position)
    def h_stop_proning(self, message_type, payload):
        print("STOP PRONING")
        self.messenger.report_proning_position(0)
    def get_ip_addresses():
        return self.messenger.get_ip_addresses()

def test():
    x = Tester()
    print(x.get_ip_addresses())
    x.poll()
    x.call()

