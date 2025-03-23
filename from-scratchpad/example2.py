# Developer guide example 3

import datetime
import globalPluginHandler
from scriptHandler import script
import ui
import versionInfo
from logHandler import log
import speech
import tones 
import gettext
import synthDriverHandler

_ = gettext.gettext

# speech/SSML processing borrowed from NVDA's mathPres/mathPlayer.py
from speech.commands import (
    BeepCommand,
    PitchCommand,
    VolumeCommand,
    RateCommand,
    LangChangeCommand,
    BreakCommand,
    CharacterModeCommand,
    PhonemeCommand,
    IndexCommand,
)

def logInfo(str_):
	log.info(f'data-ssml: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} {str_}')

original_synth_speak = synthDriverHandler.getSynth().speak

# this works, to a point: it seems to intercept all speech incl. arrow keys.  challenge is: how to smuggle data-ssml into here. unlike the focus event, here I have no accName/accDesc. 
def custom_synth_speak(speechSequence, *args, **kwargs):
	logInfo(f'here 2. {str(speechSequence)}')
	modified_sequence = []
	for element in speechSequence:
		if isinstance(element, str):
			logInfo(f'here 3.')
			element = "sub"
		modified_sequence.append(element)
	return original_synth_speak(modified_sequence, *args, **kwargs)

class GlobalPlugin(globalPluginHandler.GlobalPlugin):

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		synthDriverHandler.getSynth().speak = custom_synth_speak

	#@script(gesture="kb:NVDA+shift+v")
	#def script_announceNVDAVersion(self, gesture):
	#    ui.message(versionInfo.version)

	def event_gainFocus(self, obj, nextHandler):
		if 1:
			nextHandler()
			return
		try:
			callNextHandler = True
			if 0:
				#ui.message(f'location: {obj.location}')
				#ui.message(f'name: {obj.name}')
				logInfo(obj.name)
			if obj.description:
				if 0:
					logInfo(f'got description: {obj.description} (for name = "{obj.name}")')
					#log.info(f'data-ssml: supported commands: {str(synth.supportedCommands)}')
				#speech.speakMessage(obj.description)
				ipa = obj.description
				#speech.speak([PhonemeCommand(ipa, obj.name)])
				speech.speak([CharacterModeCommand(True), obj.name, CharacterModeCommand(False)])
				callNextHandler = False
			tones.beep(200, 20)
			if callNextHandler:
				nextHandler()
		except Exception as e:
			log.exception(e)
			# Translators: this message directs users to look in the log file
			speech.speakMessage("Error in data-ssml plugin.  See NVDA error log for details.")






