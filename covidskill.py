#!/usr/bin/env python3
# vim: et ts=8 sts=4 sw=4
from mycroft import MycroftSkill, intent_file_handler
from mycroft.skills.audioservice import AudioService
from mycroft.util.time import now_local, now_utc
from mycroft.util.log import LOG
import datetime
import requests, json, os, os.path, sys, random
import subprocess

from . import messaging

PRONING_STAGE_COUNT = 4
PRONING_CHECKIN_DELAY_MINS = 15
PRONING_CHECKIN_EVENT_NAME = "aamc.covid.checkin"
PRONING_NEXTPOS_EVENT_NAME = "aamc.covid.nextpos"
PRONING_CHECKIN_ITERATION_COUNT = 4

POLL_EVENTS_FREQUENCY_SECS = 15
POLL_EVENTS_EVENT_NAME = "aamc.covid.pollevents"
POLL_EVENTS_USER = "mycroft_covid"
POLL_EVENTS_PWD = "xyz"

API_HOST = "localhost"
API_USERNAME = None
API_PASSWORD = None

SETTING_MESSAGE_SERVER_HOST = "message_server_host"

INIT_MESSAGING_EVENT_NAME = "aamc.covid.initmessaging"

SECS_PER_MIN = 60
MS_PER_SEC = 1000
MS_PER_MIN = MS_PER_SEC * SECS_PER_MIN

MUSIC_URLS = [
    "http://ks.imslp.info/files/imglnks/usimg/2/28/IMSLP270843-PMLP15427-dso20120512-005-mahler-symphony-no1-mvtI-langsam-schleppend.mp3",
    "http://ks4.imslp.net/files/imglnks/usimg/a/ad/IMSLP93754-PMLP08063-mahler_symphony5.mp3",
    "http://ks.imslp.info/files/imglnks/usimg/2/2a/IMSLP484062-PMLP01607-beethoven-9-01-concertgebouw-klemperer-1956-16048.mp3",
]

def now():
    #return now_local()
    return now_utc()

def _calc_delay(delay_secs):
    delay = datetime.timedelta(seconds=delay_secs)
    return now() + delay

def mycroft_restart_all():
    cmd = ["which", "mycroft-start"]
    exe_path = subprocess.check_output(cmd).decode().rstrip()
    pid = os.fork("")
    if pid == 0:
        os.execl(exe_path, "all", "restart")

def mycroft_restart_audio_and_voice():
    for service in ["audio", "voice"]:
        cmd = ["mycroft-start", service, "restart"]
        subprocess.run(cmd, stdout=os.devnull, check=True)

def set_language(language):
    cmd = ["mycroft-config", "set", "lang", language]
    proc = subprocess.run(cmd, check=True)
    mycroft_restart_audio_and_voice()

def load_file_params(filename):
    with open("file_params.json") as f:
        json.read(f)
        return file_params[filename]

class AamcCovid(MycroftSkill):

    def __init__(self):
        MycroftSkill.__init__(self)
        # Initialize these properties so that referencing them before
        # assignment doesn't throw an exception.
        self.messenger = None
        self.audio_service = None
        self.position = None
        self.next_proning_event = None
        self.proning_logic_state = [None, None, None]

    def initialize(self):
        self.audio_service = AudioService(self.bus)
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
        return self.__schedule_event(
            __init_messaging, 0,
            name=INIT_MESSAGING_EVENT_NAME,
            freq_secs=15,
        )

    def __init_messaging(self):
        self.log.info("Init messaging.")
        host = self.settings.get(SETTING_MESSAGE_SERVER_HOST)
        if not host:
            self.log.error("Setting unset: " + SETTING_MESSAGE_SERVER_HOST)
            return
        self.api = messaging.MessageApi(
            host, self.config_dir,
            username=API_USERNAME, password=API_PASSWORD, log=self.log)
        self.api.add_message_handler("StartProning", self.__handle_message_start_proning)
        self.api.add_message_handler("StopProning", self.__handle_message_stop_proning)
        self.messenger = messaging.AamcCovidMessenger(self.api)
        self.cancel_scheduled_event(INIT_MESSAGING_EVENT_NAME)
        self.log.info("Init messaging successful.")

    def __handle_message_start_proning(self, message_type, message_payload):
        position = message_payload["position"]
        if position < 1 or position > 4:
            raise Exception("Invalid position: %d" % position)
        self.__stop_proning()
        self.__start_proning(position)

    def __handle_message_stop_proning(self, message_type, message_payload):
        self.__stop_proning()

    @intent_file_handler("english.intent")
    def handle_english(self, message):
        set_language("en-us")

    @intent_file_handler("spanish.intent")
    def handle_spanish(self, message):
        set_language("es")

    @intent_file_handler("routine_start.intent")
    def handle_start_routine(self, message):
        self.__start_proning()

    @intent_file_handler("routine_stop.intent")
    def handle_stop_routine(self, message):
        self.__stop_proning()

    @intent_file_handler("routine_pause.intent")
    def handle_stop_routine(self, message):
        self.__pause_proning()

    @intent_file_handler("call_nurse.intent")
    def __call_nurse(self):
        self.speak_dialog("call_nurse")
        if not self.messenger:
            self.log.warn("Unable to call nurse, messenger not initialized.")
        else:
            self.messenger.call()

    @intent_file_handler("repeat.intent")
    def __repeat(self):
        if self.position:
            dialog = "proning_%d.2_move" % self.position
            self.speak_dialog(dialog)
        else:
            self.speak_dialog("repeat_fail")

    @intent_file_handler("restart.intent")
    def __restart(self):
        if self.position:
            self.__proning_logic("ASK", self.position)
        else:
            self.speak_dialog("restart_fail")

    @intent_file_handler("continue.intent")
    def __continue_proning(self):
        state, position, arg = self.proning_logic_state
        if not self.next_proning_event:
            self.speak_dialog("continue_fail")
        elif state == "ASK":
            self.__proning_logic("MOVE", position)
        else:
            self.speak_dialog("continue_invalid")

    @intent_file_handler("next.intent")
    def __next_proning_event(self):
        if self.next_proning_event:
            self.__proning_logic(*self.next_proning_event)
        else:
            self.speak_dialog("next_fail")

    @intent_file_handler("proning_0_pause.intent")
    def __pause(self):
        self.__proning_logic("PAUSE")

    @intent_file_handler("proning_0_resume.intent")
    def __resume(self):
        self.__proning_logic("RESUME")

    def __update_proning_position(self, position_number):
        if not self.messenger:
            self.log.warn("Unable to update proning position, messenger not initialized.")
        else:
            self.messenger.report_proning_position(position_number)

    def __start_proning(self, position=0):
        #self.__do_nextpos_event(position)
        if position == 0:
            self.__proning_logic("START")
        else:
            self.__proning_logic("ASK", position)

    def __stop_proning(self):
        try:
            self.cancel_scheduled_event(PRONING_CHECKIN_EVENT_NAME)
        except:
            pass
        try:
            self.cancel_scheduled_event(PRONING_NEXTPOS_EVENT_NAME)
        except:
            pass
        try:
            self.cancel_scheduled_event("PRONING_LOGIC")
        except:
            pass
        self.__proning_logic("STOP")

    def __pause_proning(self):
        self.__paused = True
        pass # TODO: IMPLEMENT PAUSE
        self.speak_dialog("routine_pause")

    def __proning_logic_sched(self, message):
        state, position, arg = message.data
        self.__proning_logic(state, position, arg)

    def __proning_logic(self, state, position=None, arg=None, delay_mins=None):

        try:
            self.cancel_scheduled_event("PRONING_LOGIC")
        except:
            pass

        args_tuple = (state, position, arg)

        if delay_mins and delay_mins > 0:
            self.next_proning_event = args_tuple
            self.log.info("Delay: %d minutes" % delay_mins)
            self.__schedule_event(
                self.__proning_logic_sched,
                delay_mins * SECS_PER_MIN,
                "PRONING_LOGIC",
                data=(state, position, arg))
            return

        #old_state, old_position, old_arg = self.proning_logic_state
        self.proning_logic_state = args_tuple
        #self.messenger.report_proning_state(*args_tuple)

        if state is None:
            self.__proning_logic("START")

        elif state == "STOP":
            self.speak_dialog("routine_stop")
            self.position = None
            self.__update_proning_position(0)

        elif state == "START":
            self.speak_dialog("proning_0_intro")
            self.__proning_logic("ASK", 1)

        elif state == "PAUSE":
            self.speak_dialog("proning_0_pause")
            # The routine pauses because there's no next step triggered here.

        elif state == "RESUME":
            if not self.position:
                self.speak_dialog("proning_0_resume_no_position")
            else:
                self.speak_dialog("proning_0_resume")
                self.__proning_logic("ASK", self.position)

        elif state == "ASK":
            if position > 4:
                self.position = None
                self.__proning_logic("COMPLETE")
            else:
                self.position = position
                self.__update_proning_position(position)
                dialog = "proning_%d.1_ask" % position
                params = load_file_params(dialog + ".dialog")
                on_yes = lambda: self.__proning_logic("MOVE", position)
                on_no = lambda: self.__proning_logic("ASK", position, delay_mins=1)
                if params.get("EXPECTED") == "no":
                    on_yes, on_no = on_no, on_yes # Expect "no" as the "affirmative" response
                self.__choice(dialog, on_yes, on_no)

        elif state == "MOVE":
            self.speak_dialog("proning_%d.2_move" % position)
            # TODO: Update position on server
            self.__proning_logic("CHECKUP", position, delay_mins=3)

        elif state == "CHECKUP":
            dialog = "proning_%d.3_checkup" % position
            #self.speak_dialog(dialog)
            #self.__proning_logic("CHECKUP2", position, 4, delay_mins=15)
            self.__choice(dialog,
                lambda: self.__proning_logic("CHECKUP_OK", position,
                                             arg=PRONING_CHECKIN_ITERATION_COUNT),
                self.__call_nurse,
                self.__call_nurse)

        elif state == "CHECKUP_OK":
            self.speak_dialog("proning_checkup_ok")
            self.__proning_logic("CHECKUP2", position, arg, delay_mins=15),

        elif state == "CHECKUP2":
            iteration_count = arg - 1
            if iteration_count > 0:
                self.__choice("proning_%d.4_checkup2" % position,
                    lambda: self.__proning_logic("CHECKUP_OK", position, iteration_count),
                    self.__call_nurse,
                    self.__call_nurse)
            else:
                self.__proning_logic("ASK", position + 1)

        elif state == "COMPLETE":
            self.position = None
            self.__update_proning_position(0)
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
        self.speak_dialog("proning_stage_" + str(stage))

    def __schedule_event(self, handler, delay_secs, event_name, freq_secs=None, data=None):
        self.log.info("__schedule_event: delay=%d, event=%s" % (delay_secs, event_name))
        event_time = _calc_delay(delay_secs)
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
         action_if_no_response=None,
         action_if_continue=None,
    ):
        #response = self.get_response(prompt_intent)
        #validator=lambda u: return u in ["yes"]
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

    @intent_file_handler("playmusic.intent")
    def play_music(self):
        url = random.choice(MUSIC_URLS)
        self.audio_service.play(url)

    @intent_file_handler("stopmusic.intent")
    def stop_music(self):
        self.audio_service.stop()

