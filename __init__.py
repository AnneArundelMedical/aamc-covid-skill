from mycroft import MycroftSkill, intent_file_handler
from mycroft.util.time import now_local
from mycroft.util.log import LOG
import datetime

def create_skill():
    return AamcCovid()

PRONING_CHECKIN_DELAY_MINS = 15
PRONING_CHECKIN_EVENT_NAME = "aamc.covid.checkin"

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
        checkin_delay = datetime.timedelta(seconds=10)
        checkin_event_time = now_local() + checkin_delay
        checkin_event_frequency = 0
        self.schedule_repeating_event(
            self.__handle_checkin_event,
            checkin_event_time,
            checkin_event_frequency,
            name=PRONING_CHECKIN_EVENT_NAME,
        )
        self.speak_dialog("proning_stage_1")

    def __handle_checkin_event(self, message):
        """ Repeating event handler. Check if user is OK in new position.  """
        #self.speak_dialog("checkin")
        self.log.debug("checkin")
        response = self.ask_yesno("checkin.ask")
        self.log.debug("Response: " + response)
        if response == "yes":
            self.speak_dialog("checkin.needhelp")
        else:
            self.speak_dialog("checkin.nohelp")

