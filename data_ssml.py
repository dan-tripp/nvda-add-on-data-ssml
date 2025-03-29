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

def isPowerOfTwo(n_):
    return n_ > 0 and (n_ & (n_ - 1)) == 0

def decodeSingleStr(str_):
	''' If you change the chars here, you need to also change them in the JS encode function.  
	And vice versa.  Write comments about these chars here, not there. 
	chars not used AKA unused: 
		\u070F: tempting, but it's not invisible. 
		\u17B4: didn't make it through chrome.  showed up as some characters in the synth.  I don't get it. 
		\u17B5: same. 
		\u202A: got filtered out by firefox. 
		\u202B: got filtered out by firefox. 
		\u001C: got filtered out by firefox. 
		\u001D: got filtered out by firefox. 
		\u001E: got filtered out by firefox. 
		\u001F: got filtered out by firefox. 
		\u0000: got filtered out by firefox. 
		\u202C: seems to get filtered out by firefox 
		\u202D: seems to get filtered out by firefox 
		\u180E: almost worked, but got filtered sometimes, or caused premature string split.  tested on chrome only IIRC. 
		\u200B: got filtered out on the "repeat 1000" test on our test page for encoding chars.  
		\u061C: got filtered out by firefox. 
	'''
	ENCODING_CHARS = [
		'\uFFF9', 
		'\u200C', 
		'\u200D',
		'\u2060',
		'\u2061',
		'\uFEFF',
		'\u2063',
		'\u2064',
		'\uFFFB',
		'\uFFFA',
		'\u206A',
		'\u206B',
		'\u206C',
		'\u206D',
		'\u206E',
		'\u206F', 
	]
	assert len(set(ENCODING_CHARS)) == len(ENCODING_CHARS), "encodingChars contains duplicates"

	n = len(ENCODING_CHARS)
	if not isPowerOfTwo(n):
		raise ValueError("Base must be a power of 2")

	digitValues = [ENCODING_CHARS.index(c) for c in str_]
	number = 0
	for d in digitValues:
		number = number * n + d

	numBytes = (number.bit_length() + 7) // 8

	bytes = number.to_bytes(numBytes, 'big') if numBytes > 0 else b''

	logInfo(f'input string (len {len(str_)}): "{str_}"')
	logInfo(f"digitValues: {digitValues}")
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
		INSERT_HACK_PAUSE_AFTER = 1
		if INSERT_HACK_PAUSE_AFTER:
			# inspired by 1) the line in MathCAT.py which says "There needs to be a space after the phoneme command" (a comment I don't understand), 2) by my aural observation that NVDA's announcement sounded like "woundlink" (i.e. with no space).
			# hard to say if the cure is worse than the disease here.
			r.insert(0, RateCommand(-30))
			r.append(RateCommand(0))
	else:
		raise Exception()
	return r

# Matches the javascript encoding side.  If you change that then change this, and vice versa. 
MARKER = '\u2062'
MACRO_END_MARKER = MARKER * 2

pattern = re.compile(
	f'{re.escape(MARKER)}'
	f'(.*?)'
	f'{re.escape(MARKER)}'
	f'(.*?)'
	f'{re.escape(MACRO_END_MARKER)}',
	flags=re.DOTALL
)

def decodeAllStrs(str_):
	logInfo(f'decodeAllStrs input (len {len(str_)}): {repr(str_)}')

	markerCount = str_.count(MARKER)
	macroEndCount = str_.count(MACRO_END_MARKER)

	if not ((markerCount % 4 == 0) and (markerCount // 4 == macroEndCount)):
		raise Exception(f'[decodeAllStrs] marker mismatch: {markerCount} singles, {macroEndCount} doubles')

	r = []
	lastEnd = 0
	matchCount = 0

	for match in pattern.finditer(str_):
		matchCount += 1
		start, end = match.span()
		encodedSsml, nonSsmlStr = match.groups()

		logInfo(f'encodedSsml (len {len(encodedSsml)}): {repr(encodedSsml)}')
		logInfo(f'nonSsmlStr (len {len(nonSsmlStr)}): {repr(nonSsmlStr)}')

		if start > lastEnd:
			pre = str_[lastEnd:start]
			logInfo(f'	plain text before match: {repr(pre)}')
			r.append(pre)

		try:
			decodedSsml = decodeSingleStr(encodedSsml)
			logInfo(f'	decodedSsml: {decodedSsml}')
			r.extend(turnSsmlIntoSpeechCommandList(decodedSsml, nonSsmlStr))
		except Exception as e:
			log.exception(e)
			logInfo(f'	encoded string (raw): {repr(encodedSsml)}')
			raise

		lastEnd = end

	if lastEnd < len(str_):
		trailing = str_[lastEnd:]
		logInfo(f'trailing text after last match: {repr(trailing)}')
		r.append(trailing)

	return r


g_synthNamesPatched = set()

def patchCurrentSynth():
	currentSynthOrigSpeakFunc = synthDriverHandler.getSynth().speak
	def patchedSpeakFunc(speechSequence, *args, **kwargs):
		modifiedSpeechSequence = []
		logInfo(f'original speech sequence: {speechSequence}')
		for element in speechSequence:
			if isinstance(element, str):
				#logInfo(f'patched synth got string len {len(element)}: "{element}"')
				logInfo(f'patched synth got string len {len(element)}: "{repr(element)}"')
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
		



