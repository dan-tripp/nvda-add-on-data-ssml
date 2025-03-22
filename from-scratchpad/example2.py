# Developer guide example 3

import globalPluginHandler
from scriptHandler import script
import ui
import versionInfo
from logHandler import log
import speech
import tones 

class GlobalPlugin(globalPluginHandler.GlobalPlugin):

	#@script(gesture="kb:NVDA+shift+v")
	#def script_announceNVDAVersion(self, gesture):
	#    ui.message(versionInfo.version)

	def event_gainFocus(self, obj, nextHandler):
		try:
			#log.info(f'data-ssml: {obj.name} {obj.description}')
			#log.info(f'data-ssml: {dir(obj)}')
			if obj.description:
				log.info(f'data-ssml: got description: {obj.description} (for name = "{obj.name}")')
			tones.beep(200, 20)
			nextHandler()
		except Exception as e:
			log.exception(e)
			# Translators: this message directs users to look in the log file
			speech.speakMessage("Error in data-ssml plugin.  See NVDA error log for details.")




