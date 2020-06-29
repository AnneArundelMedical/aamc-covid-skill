from mycroft import MycroftSkill, intent_file_handler
from mycroft.util.time import now_local
from mycroft.util.log import LOG
import datetime

def create_skill():
    return AamcCovid()

PRONING_STAGE_COUNT = 4
PRONING_CHECKIN_DELAY_MINS = 15
PRONING_CHECKIN_EVENT_NAME = "aamc.covid.checkin"
PRONING_NEXTPOS_EVENT_NAME = "aamc.covid.nextpos"

class AamcCovid(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self)

    @intent_file_handler('covid.aamc.intent')
    def handle_covid_aamc(self, message):
        self.speak_dialog('covid.aamc')

    @intent_file_handler('dying.intent')
    def handle_dying(self, message):
        self.speak_dialog('dying')

    @intent_file_handler("start_routine.intent")
    def handle_start_routine(self, message):
        #checkin_delay = datetime.timedelta(minutes=PRONING_CHECKIN_DELAY_MINS)
        self.__do_nextpos_event(1)

    @intent_file_handler("stop_routine.intent")
    def handle_stop_routine(self, message):
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
        checkin_event_time = now_local() + checkin_delay
        checkin_event_frequency = 0
        self.log.info("Checkin event: %s / %s / %s"
                      % (
                          checkin_event_time,
                          checkin_event_frequency,
                          PRONING_CHECKIN_EVENT_NAME,
                      ))
        self.schedule_repeating_event(
            self.__handle_checkin_event,
            checkin_event_time,
            checkin_event_frequency,
            name=PRONING_CHECKIN_EVENT_NAME,
        )
        nextpos_delay = datetime.timedelta(seconds=60)
        nextpos_event_time = now_local() + nextpos_delay
        nextpos_event_frequency = nextpos_delay
        next_stage = stage + 1
        if next_stage <= PRONING_STAGE_COUNT:
            self.schedule_repeating_event(
                self.__handle_nextpos_event,
                nextpos_event_time,
                0,
                name=PRONING_NEXTPOS_EVENT_NAME,
                data={ "stage": next_stage },
            )
        self.speak_dialog("proning_stage_" + str(stage))

    def __schedule_event(handler, delay_secs, event_name, freq_secs=None, data=None):
        delay = datetime.timedelta(seconds=delay_secs)
        event_time = now_local() + delay
        event_frequency = datetime.timedelta(seconds=(freq_secs or 0))
        self.log.info("Checkin event: now=%s; time=%s; freq=%s; name=%s"
                      % (
                          now_local(),
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
        self.log.info("Checkin. Data: " + str(message.data))
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
        self.log.info("Checkin. Data: " + str(message.data))
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

