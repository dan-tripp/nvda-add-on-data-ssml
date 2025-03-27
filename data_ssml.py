# Developer guide example 3

import datetime, re, base64, json
import globalPluginHandler
from logHandler import log
import speech
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


def decodeSingleStr(str_):
	encodingChars = [
		'\uFFF9', 
		'\u200C', 
		'\u200D',
		'\u2060',
		'\u2061',
		'\uFEFF',
		'\u200B',
		'\u2064',
	]
	# '\u17B4' # didn't make it through chrome.  showed up as some characters.  I don't get it. 
	# '\u202C' # seems to get filtered out by firefox 
	# '\u202D' # seems to get filtered out by firefox 

	n = len(encodingChars)
	baseNStr = ''.join(str(encodingChars.index(c)) for c in str_)
	number = int(baseNStr, n)

	assert n == 8 # b/c of the line below 
	numBytes = (number.bit_length() + 7) // n
	bytes = number.to_bytes(numBytes, 'big') if numBytes > 0 else b''

	if 0: 
		logInfo(f'input string: "{str_}"')
		logInfo(f"Base8 string: {baseNStr}")
		logInfo(f"Integer: {number}")
		logInfo(f"Decoded bytes (hex): {bytes.hex()}")

	r = bytes.decode('utf-8')
	return r

def turnSsmlIntoSpeechCommandList(ssmlAsJsonStr_, nonSsmlStr_):
	ssmlAsDict = json.loads(ssmlAsJsonStr_)
	if len(ssmlAsDict) != 1: raise Exception()
	key = next(iter(ssmlAsDict)); val = ssmlAsDict[key]
	if key == 'sub':
		aliasVal = val['alias']
		r = [aliasVal]
	elif key == 'say-as':
		if val != 'characters': raise Exception()
		r = [CharacterModeCommand(True), nonSsmlStr_, CharacterModeCommand(False)]
	elif key == 'ph':
		phonemeIpa = val
		r = [PhonemeCommand(phonemeIpa, text=nonSsmlStr_)]
		INSERT_HACK_PAUSE_AFTER = 0
		if INSERT_HACK_PAUSE_AFTER:
			# inspired by 1) the line in MathCAT.py which says "There needs to be a space after the phoneme command" (a comment I don't understand), 2) by my observation in NVDA's speech viewer that there wasn't a space when tabbing to a link w/ a phoneme eg. speech viewer said "woundlink", 3) by my aural observation that NVDA's announcement sounded like "woundlink" (i.e. with no space).
			# later: disabled b/c that problem stopped happening.  maybe b/c of new encoding chars ~ 2025-03-27 00:41. 
			r.insert(0, RateCommand(-30))
			r.append(RateCommand(0))
	else:
		raise Exception()
	return r

# Matches the javascript encoding side.  If you change that then change this, and vice versa. 
START_MARKER = '\u2062\u2063'
END_MARKER = '\u2063\u2062'

# returns a list where each element is a string or a speech command.  
def decodeAllStrs(str_):

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
			nonSsmlStr = str_[searchStartPos:]
			if nonSsmlStr:
				r.append(nonSsmlStr)
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
				logInfo(f'encodedSsml: {encodedSsml}')
				decodedSsml = decodeSingleStr(encodedSsml)
				logInfo(f'decodedSsml: {decodedSsml}')
				nextStartMarkerStartPos = str_.find(START_MARKER, endMarkerStartPos)
				if nextStartMarkerStartPos == -1: raise Exception()
				endMarkerEndPos = endMarkerStartPos + len(END_MARKER)
				nonSsmlStr = str_[endMarkerEndPos:nextStartMarkerStartPos]
				r.extend(turnSsmlIntoSpeechCommandList(decodedSsml, nonSsmlStr))
				searchStartPos = nextStartMarkerStartPos
			except Exception as e:
				log.exception(e)
				logInfo(f'encoded string was: {encodedSsml}')
				raise
		else:
			logInfo(f'empty encoded string i.e. macro end marker.')
			searchStartPos = endMarkerStartPos + len(END_MARKER)

	return r


g_synthNamesPatched = set()

def patchCurrentSynth():
	currentSynthOrigSpeakFunc = synthDriverHandler.getSynth().speak
	def patchedSpeakFunc(speechSequence, *args, **kwargs):
		modifiedSpeechSequence = []
		logInfo(f'original speech sequence: {speechSequence}')
		for element in speechSequence:
			if isinstance(element, str):
				modifiedSpeechSequence.extend(decodeAllStrs(element))
			else:
				modifiedSpeechSequence.append(element)
		logInfo(f'modified speech sequence: {modifiedSpeechSequence}')
		logInfo(f'speech sequence changed: {modifiedSpeechSequence != speechSequence}')
		return currentSynthOrigSpeakFunc(modifiedSpeechSequence, *args, **kwargs)
	synthDriverHandler.getSynth().speak = patchedSpeakFunc

def patchCurrentSynthIfNecessary():
	global g_synthNamesPatched
	currentSynthName = synthDriverHandler.getSynth().name
	if currentSynthName not in g_synthNamesPatched:
		logInfo(f'patching synth "{currentSynthName}".')
		g_synthNamesPatched.add(currentSynthName)
		patchCurrentSynth()
	else:
		logInfo(f'patch of synth "{currentSynthName}" not necessary.')

class GlobalPlugin(globalPluginHandler.GlobalPlugin):

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		synthDriverHandler.synthChanged.register(self.onSynthChanged) 
		patchCurrentSynthIfNecessary()

	def onSynthChanged(self, *args, **kwargs):
		logInfo('synth changed.')
		patchCurrentSynthIfNecessary()
		



