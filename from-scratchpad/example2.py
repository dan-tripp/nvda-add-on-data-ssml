# Developer guide example 3

import globalPluginHandler
from scriptHandler import script
import ui
import versionInfo
from logHandler import log
import speech

class GlobalPlugin(globalPluginHandler.GlobalPlugin):

    #@script(gesture="kb:NVDA+shift+v")
    #def script_announceNVDAVersion(self, gesture):
    #    ui.message(versionInfo.version)

    def event_gainFocus(self, obj, nextHandler):
        try:
            import tones
            tones.beep(500, 50)
            nextHandler()
        except Exception as e:
            log.exception(e)
            # Translators: this message directs users to look in the log file
            speech.speakMessage("Error in data-ssml plugin.  See NVDA error log for details.")
        



