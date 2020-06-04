from mycroft import MycroftSkill, intent_file_handler


class AamcCovid(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self)

    @intent_file_handler('covid.aamc.intent')
    def handle_covid_aamc(self, message):
        self.speak_dialog('covid.aamc')


def create_skill():
    return AamcCovid()

