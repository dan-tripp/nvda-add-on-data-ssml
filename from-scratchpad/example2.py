# Developer guide example 3

import globalPluginHandler
from scriptHandler import script
import ui
import versionInfo


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    @script(gesture="kb:NVDA+shift+v")
    def script_announceNVDAVersion(self, gesture):
        ui.message(versionInfo.version)

        


        