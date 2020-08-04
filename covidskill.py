#!/usr/bin/env python3
# vim: et ts=8 sts=4 sw=4
from mycroft import MycroftSkill, intent_file_handler
from mycroft.util.time import now_local, now_utc
from mycroft.util.log import LOG
import datetime
import requests, json

from . import messaging

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

INIT_MESSAGING_EVENT_NAME = "aamc.covid.initmessaging"

def now():
    return now_utc()

class AamcCovid(MycroftSkill):

    def __init__(self):
        MycroftSkill.__init__(self)

    def initialize(self):
        try:
            #self.log.info("self.file_system: " + json.dumps(self.file_system))
            self.config_dir = self.file_system.path
            self.__init_messaging()
            self.schedule_poll_events()
        except Exception as e:
            self.log.error(e)

    def __schedule_init_messaging(self):
        """ Repeatedly attempt to set up messaging, until it succeeds. """
        self.log.info("Schedule init messaging.")
        return self.schedule_repeating_event(
            __init_messaging,
            0, 15,
            name=INIT_MESSAGING_EVENT_NAME,
        )

    def __init_messaging(self):
        self.log.info("Init messaging.")
        self.api = messaging.MessageApi(
            API_HOST, self.config_dir,
            username=API_USERNAME, password=API_PASSWORD, log=self.log)
        self.api.add_message_handler("StartProning", self.__handle_message_start_proning)
        self.api.add_message_handler("StopProning", self.__handle_message_stop_proning)
        self.messenger = AamcCovidMessenger(self.api)
        self.cancel_scheduled_event(INIT_MESSAGING_EVENT_NAME)
        self.log.info("Init messaging successful.")

    def __handle_message_start_proning(self, message_payload):
        position = message_payload["position"]
        if position < 1 or position > 4:
            raise Exception("Invalid position: %d" % position)
        self.__stop_proning()
        self.__start_proning(position)

    def __handle_message_stop_proning(self, message_payload):
        self.__stop_proning()

    @intent_file_handler("routine_start.intent")
    def handle_start_routine(self, message):
        self.__start_proning()

    @intent_file_handler("routine_stop.intent")
    def handle_stop_routine(self, message):
        self.__stop_proning()

    @intent_file_handler("routine_pause.intent")
    def handle_stop_routine(self, message):
        self.__pause_proning()

    def __start_proning(self, position=1):
        #self.__do_nextpos_event(position)
        self.__proning_logic("START")

    def __stop_proning(self):
        try:
            self.cancel_scheduled_event(PRONING_CHECKIN_EVENT_NAME)
        except:
            pass
        try:
            self.cancel_scheduled_event(PRONING_NEXTPOS_EVENT_NAME)
        except:
            pass
        self.speak_dialog("routine_stop")

    def __pause_proning(self):
        self.__paused = True
        pass # TODO: IMPLEMENT PAUSE
        self.speak_dialog("routine_pause")

    def __proning_logic_sched(self, message):
        state, position, arg = message.data
        self.__proning_logic(state, position, data)

    def __proning_logic(self, state, position=None, arg=None, delay=None):
        if delay and delay > 0:
            self.schedule_event(
                self.__proning_logic_sched,
                delay * 60,
                data=(state, position, arg))
        if state is None:
            self.__proning_logic("START")
        elif state == "START":
            self.speak_dialog("proning_0_intro")
            self.__proning_logic("ASK", 1)
        elif state == "ASK":
            if position > 4:
                self.__proning_logic("COMPLETE")
            else:
                dialog = "proning_%d.1_ask" % position
                self.__choice(dialog,
                    lambda: self.__proning_logic("MOVE", position),
                    lambda: self.__proning_logic("ASK", position, delay=1))
        elif state == "MOVE":
            self.speak_dialog("proning_%d.2_move" % position)
            # TODO: Update position on server
            self.__proning_logic("CHECKUP", position, delay=3)
        elif state == "CHECKUP":
            dialog = "proning_%d.3_checkup" % position
            self.speak_dialog(dialog)
            self.__proning_logic("CHECKUP2", position, 4, delay=15)
        elif state == "CHECKUP2":
            arg = arg - 1
            if arg > 0:
                self.__choice("proning_%d.4_checkup2" % position,
                    lambda: self.__proning_logic("CHECKUP2", position, arg, delay=15),
                    self.__call_nurse,
                    self.__call_nurse)
            else:
                self.__proning_logic("ASK", position + 1)
        elif state == "COMPLETE":
            self.speak_dialog("proning_complete")
        else:
            self.log.error("Invalid state: " + state)

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
        self.__choice(
            "checkin.ask",
            lambda: self.speak_dialog("checkin.needhelp"),
            lambda: self.speak_dialog("checkin.nohelp"))

    def __handle_nextpos_event(self, message):
        """ Repeating event handler. Check if user is OK in new position.  """
        #self.speak_dialog("checkin")
        self.log.info("Handle nextpos. Data: " + str(message.data))
        stage = message.data["stage"]
        self.__do_nextpos_event(stage)

    def __choice(self,
         prompt_intent,
         action_if_yes,
         action_if_no,
         action_if_no_response=None
    ):
        response = self.ask_yesno(prompt_intent)
        if response == "yes":
            if action_if_yes:
                action_if_yes()
        elif response == "no":
            if action_if_no:
                action_if_no()
        elif not response:
            if action_if_no_response:
                action_if_no_response()
        else:
            self.log.error("Unrecognized response to ask_yesno: '%s'" % response)

    def schedule_poll_events(self):
        self.schedule_repeating_event(
            self.__handle_poll_events,
            0,
            POLL_EVENTS_FREQUENCY_SECS,
            name=POLL_EVENTS_EVENT_NAME,
        )

    def __handle_poll_events(self, message):
        if self.messenger:
            events = self.messenger.poll()

