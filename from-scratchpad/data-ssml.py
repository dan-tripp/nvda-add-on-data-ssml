# Developer guide example 3

import datetime, re, base64, json
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


def decodeSingleStrOctal(str_):
	zero_width_char_map = {
		'\uFFF9': '0',
		'\u200C': '1',
		'\u200D': '2',
		'\u2060': '3',
		'\u2061': '4',
		'\uFEFF': '5',
		'\u202C': '6',
		'\u202D': '7'
	}

	base8_str = ''.join(zero_width_char_map[c] for c in str_ if c in zero_width_char_map)
	number = int(base8_str, 8)

	# Calculate the number of bytes needed
	byte_length = (number.bit_length() + 7) // 8
	decoded_bytes = number.to_bytes(byte_length, 'big') if byte_length > 0 else b''

	if 0: 
		logInfo(f'input string: "{str_}"')
		logInfo(f"Base8 string: {base8_str}")
		logInfo(f"Integer: {number}")
		logInfo(f"Decoded bytes (hex): {decoded_bytes.hex()}")

	return decoded_bytes.decode('utf-8')

def turnSsmlIntoSpeechCommandList(ssmlAsJsonStr_, nonSsmlStr_):
	ssmlAsDict = json.loads(ssmlAsJsonStr_)
	if len(ssmlAsDict) != 1: raise Exception()
	if 'sub' not in ssmlAsDict: raise Exception()
	subVal = ssmlAsDict['sub']
	if 'alias' not in subVal: raise Exception()
	aliasVal = subVal['alias']
	r = [aliasVal]
	return r

# returns a list where each element is a string or a speech command.  
def decodeAllStrsOctal(str_):
	# Matches the javascript encoding side.  If you change that then change this, and vice versa. 
	START_MARKER = '\u2062\u2063'
	END_MARKER = '\u2063\u2062'

	startMarkerCount = str_.count(START_MARKER)
	endMarkerCount = str_.count(END_MARKER)
	macroEndCount = str_.count(START_MARKER+END_MARKER)
	if not ((startMarkerCount == endMarkerCount) and (startMarkerCount % 2 == 0) and (endMarkerCount/2 == macroEndCount)):
		raise Exception(f'markers are bad.  str was: "{str_}"')

	r = []
	searchStartPos = 0

	while True:
		startMarkerStartPos = str_.find(START_MARKER, searchStartPos)
		if startMarkerStartPos == -1:
			r.append(str_[searchStartPos:])
			break
		prevSsmlStr = str_[searchStartPos:startMarkerStartPos]
		if prevSsmlStr:
			r.append(prevSsmlStr)
		ssmlStartPos = startMarkerStartPos + len(START_MARKER)
		endMarkerStartPos = str_.find(END_MARKER, ssmlStartPos)
		if endMarkerStartPos == -1:
			raise Exception(f'markers bad.  end marker not found.  str was: {str_}')

		encodedSsml = str_[ssmlStartPos:endMarkerStartPos]
		if encodedSsml:
			logInfo(f'non-empty encoded string i.e. macro start marker with ssml.')
			try:
				decodedSsml = decodeSingleStrOctal(encodedSsml)
				logInfo(f'decodedSsml: {decodedSsml}')
				nextMacroStartPos = str_.find(START_MARKER, endMarkerStartPos)
				if nextMacroStartPos == -1: raise Exception()
				endMarkerEndPos = endMarkerStartPos + len(END_MARKER)
				nonSsmlStr = str_[searchStartPos:nextMacroStartPos]
				r.extend(turnSsmlIntoSpeechCommandList(decodedSsml, nonSsmlStr))
			except Exception as e:
				log.exception(e)
				logInfo(f'encoded string was: {encodedSsml}')
		else:
			logInfo(f'empty encoded string i.e. macro end marker.')

		searchStartPos = endMarkerStartPos + len(END_MARKER)

	return r


original_synth_speak = synthDriverHandler.getSynth().speak

def custom_synth_speak(speechSequence, *args, **kwargs):
	modifiedSpeechSequence = []
	for element in speechSequence:
		if isinstance(element, str):
			modifiedSpeechSequence.extend(decodeAllStrsOctal(element))
		else:
			modifiedSpeechSequence.append(element)
	logInfo(f'original speech sequence: {speechSequence}')
	logInfo(f'modified speech sequence: {modifiedSpeechSequence}')
	logInfo(f'speech sequence changed: {modifiedSpeechSequence != speechSequence}')
	return original_synth_speak(modifiedSpeechSequence, *args, **kwargs)


class GlobalPlugin(globalPluginHandler.GlobalPlugin):

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		synthDriverHandler.getSynth().speak = custom_synth_speak





