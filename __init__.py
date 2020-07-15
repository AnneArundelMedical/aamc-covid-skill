from mycroft import MycroftSkill, intent_file_handler
from mycroft.util.time import now_local, now_utc
from mycroft.util.log import LOG
import datetime
import requests, json

def create_skill():
    return AamcCovid()

PRONING_STAGE_COUNT = 4
PRONING_CHECKIN_DELAY_MINS = 15
PRONING_CHECKIN_EVENT_NAME = "aamc.covid.checkin"
PRONING_NEXTPOS_EVENT_NAME = "aamc.covid.nextpos"

POLL_EVENTS_FREQUENCY_SECS = 15
POLL_EVENTS_EVENT_NAME = "aamc.covid.pollevents"
POLL_EVENTS_USER = "mycroft_covid"
POLL_EVENTS_PWD = "xyz"

API_HOST = "localhost"
API_USERNAME = None
API_PASSWORD = None

def now():
    return now_utc()

class AamcCovid(MycroftSkill):

    def __init__(self):
        MycroftSkill.__init__(self)
        self.api = messaging.MessageApi(API_HOST, API_USERNAME, API_PASSWORD)
        self.api.add_message_handler("StartProning", self.__handle_message_start_proning)
        self.api.add_message_handler("StopProning", self.__handle_message_stop_proning)
        self.schedule_poll_events()

    def __handle_message_start_proning(self, message_payload):
        position = message_payload["position"]
        if position < 1 or position > 4:
            raise Exception("Invalid position: %d" % position)
        self.__stop_proning()
        self.__start_proning(position)

    def __handle_message_stop_proning(self, message_payload):
        self.__stop_proning()

    @intent_file_handler('covid.aamc.intent')
    def handle_covid_aamc(self, message):
        self.speak_dialog('covid.aamc')

    @intent_file_handler('dying.intent')
    def handle_dying(self, message):
        self.speak_dialog('dying')

    @intent_file_handler("start_routine.intent")
    def handle_start_routine(self, message):
        self.__start_proning()

    @intent_file_handler("stop_routine.intent")
    def handle_stop_routine(self, message):
        self.__stop_proning()

    def __start_proning(self, position=1):
        self.__do_nextpos_event(position)

    def __stop_proning(self):
        try:
            self.cancel_scheduled_event(PRONING_CHECKIN_EVENT_NAME)
        except:
            pass
        try:
            self.cancel_scheduled_event(PRONING_NEXTPOS_EVENT_NAME)
        except:
            pass
        self.speak_dialog("stop_routine.dialog")

    def __do_nextpos_event(self, stage):
        self.log.info("__do_nextpos_event")
        checkin_delay = datetime.timedelta(seconds=10)
        checkin_event_time = now() + checkin_delay
        checkin_event_frequency = 0
        self.log.info("Do nextpos event: %s / %s / %s"
                      % (
                          checkin_event_time,
                          checkin_event_frequency,
                          PRONING_CHECKIN_EVENT_NAME,
                      ))
        self.__schedule_event(
            self.__handle_checkin_event,
            10,
            PRONING_CHECKIN_EVENT_NAME,
        )
        #self.schedule_repeating_event(
        #    self.__handle_checkin_event,
        #    checkin_event_time,
        #    checkin_event_frequency,
        #    name=PRONING_CHECKIN_EVENT_NAME,
        #)
        nextpos_delay = datetime.timedelta(seconds=60)
        nextpos_event_time = now() + nextpos_delay
        nextpos_event_frequency = nextpos_delay
        next_stage = stage + 1
        if next_stage <= PRONING_STAGE_COUNT:
            self.__schedule_event(
                self.__handle_nextpos_event,
                60,
                PRONING_NEXTPOS_EVENT_NAME,
                data={ "stage": next_stage },
            )
            #self.schedule_repeating_event(
            #    self.__handle_nextpos_event,
            #    nextpos_event_time,
            #    0,
            #    name=PRONING_NEXTPOS_EVENT_NAME,
            #    data={ "stage": next_stage },
            #)
        self.speak_dialog("proning_stage_" + str(stage))

    def __schedule_event(self, handler, delay_secs, event_name, freq_secs=None, data=None):
        self.log.info("__schedule_event: delay=%d, event=%s" % (delay_secs, event_name))
        delay = datetime.timedelta(seconds=delay_secs)
        event_time = now() + delay
        # Timedelta is the wrong type for the frequency. Need to figure out how
        # to pass this correctly.
        #event_frequency = datetime.timedelta(seconds=(freq_secs or 0))
        event_frequency = None
        self.log.info("Scheduling event: now=%s; time=%s; freq=%s; name=%s"
                      % (
                          now(),
                          event_time,
                          event_frequency,
                          event_name,
                      ))
        return self.schedule_repeating_event(
            handler,
            event_time,
            event_frequency,
            name=event_name,
            data=data,
        )

    def __handle_checkin_event(self, message):
        """ Repeating event handler. Check if user is OK in new position.  """
        #self.speak_dialog("checkin")
        self.log.info("Handle checkin. Data: " + str(message.data))
        response = self.ask_yesno("checkin.ask")
        if response == "yes":
            self.speak_dialog("checkin.needhelp")
        elif response == "no":
            self.speak_dialog("checkin.nohelp")
        else:
            self.log.info("Unrecognized response: %s" % response)

    def __handle_nextpos_event(self, message):
        """ Repeating event handler. Check if user is OK in new position.  """
        #self.speak_dialog("checkin")
        self.log.info("Handle nextpos. Data: " + str(message.data))
        stage = message.data["stage"]
        self.__do_nextpos_event(stage)

    def choice(prompt_intent, action_if_yes, action_if_no):
        response = self.ask_yesno("checkin.ask")
        if response == "yes":
            action_if_yes()
        elif response == "no":
            action_if_no()
        else:
            self.log.info("Unrecognized response: %s" % response)

    def schedule_poll_events(self):
        self.schedule_repeating_event(
            self.__handle_poll_events,
            0,
            POLL_EVENTS_FREQUENCY_SECS,
            name=POLL_EVENTS_EVENT_NAME,
        )

    def __handle_poll_events(self, message):
        events = self.api.poll_events()

    def __handle_event(self, event):
        t = event["EventType"]
        if t == "NEW_PATIENT":
            self.__new_patient(event["Payload"]["Patient"])
        elif t == "START_PRONING":
            self.__start_proning()
        else:
            raise Exception("Invalid event type: " + t)

    def __new_patient(self, patient):
        self.__stop_proning()
        self.__patient_name = patient["Name"]
        self.__patient_start_time = now()

