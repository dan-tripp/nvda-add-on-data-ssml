
PROFILE = None
LOG_BRAILLE = None
NEXT_SYNTH_SHORTCUT = None

NVDA_CONFIG_KEY = 'data-ssml'
HIDING_PLACE_GUID_FOR_ALL_TECHNIQUES = '4b9b696c-8fc8-49ca-9bb9-73afc9bd95f7'
HIDING_PLACE_GUID_FOR_INDEX_TECHNIQUE = 'b4f55cd4-8d9e-40e1-b344-353fe387120f'
HIDING_PLACE_GUID_FOR_PAGE_WIDE_TECHNIQUE = 'c7a998a5-4b7e-4683-8659-f2da4aa96eee'

def logInfo(str_):
	log.info(f'data-ssml: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} {str_}')

def ourAssert(bool_, str_=''):
	if not bool_:
		raise AssertionError(str_)

''' If you change the chars here, you need to also change them in the JS encode function.  
And vice versa.  Write comments about these chars here, not there. '''
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
'''
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
	\u180E: almost worked, but got filtered sometimes, or caused premature string split.  tested on chrome only IIRC.  more notes in test-page-for-encoding-chars.html . 
	\u200B: got filtered out on the "repeat 1000" test on our test page for encoding chars.  
	\u061C: got filtered out by firefox. 
'''
ourAssert(len(set(ENCODING_CHARS)) == len(ENCODING_CHARS), "encodingChars contains duplicates")

import datetime, re, base64, json, time, types, dataclasses, sys, traceback
import globalPluginHandler, api, scriptHandler, ui
from logHandler import log
import speech, speech.commands, speech.extensions, braille
import synthDriverHandler, config
from controlTypes import roleLabels

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

def setGlobalVarsBasedOnNvdaConfig():
	global PROFILE, LOG_BRAILLE, NEXT_SYNTH_SHORTCUT
	if NVDA_CONFIG_KEY not in config.conf:
		config.conf[NVDA_CONFIG_KEY] = {}
	settings = config.conf[NVDA_CONFIG_KEY]
	def strToBool(str__):
		return {'True': True, 'False': False}[str__]
	PROFILE = strToBool(settings.get('profile', 'False'))
	LOG_BRAILLE = strToBool(settings.get('logBraille', 'False'))
	NEXT_SYNTH_SHORTCUT = strToBool(settings.get('nextSynthShortcut', 'False'))

def profile(fn):
	def wrapped(*args, **kwargs):
		t0 = time.perf_counter()
		try:
			return fn(*args, **kwargs)
		finally:
			t1 = time.perf_counter()
			if PROFILE:
				logInfo(f"profile: {fn.__name__} took {int((t1-t0)*1000)} ms.")
	return wrapped
	
class StopWatch:
	def __init__(self, label=""):
		self.label = label
		self.lastTime = time.perf_counter()
		self.numClicks = 0

	def click(self, message=""):
		nowTime = time.perf_counter()
		self.numClicks += 1
		elapsedMillis = (nowTime - self.lastTime) * 1000
		self.lastTime = nowTime
		output = f"stopwatch: {self.label} {message} {self.numClicks} took {elapsedMillis:.0f} ms"
		logInfo(output)



# various data that influences how this plugin is supposed to work.
# 
# this reflects the web page we're on and the currently-set options of NVDA.  the main point of having this as a class is so we can write unit tests easily.  when our code is running in nvda (not a unit test): an instance of this class might be short-lived, or at least have it's values changing often.  b/c the appropriate values could change from one moment to the next eg. if the user changes browser tab, or nvda synth.
# 
# it /almost/ makes sense for an instance of this class to exist only if the current nvda navigator object is a web page that has our SSML stuff on it.  almost, but not quite, because when technique=inline, we don't know if the current web page has our stuff or not.  we'll only know that when and if our speech filter encounters some of our encoded characters.  so if we're on a web page that has our stuff with technique=inline, or we're on a web page that doesn't use our stuff, or we're not on a web page, then an instance of this class will exist, and have technique == 'inline'. 
@dataclasses.dataclass 
class State:
	
	# NVDA state:
	useCharacterModeCommand: bool = True
	isLanguageEnglish: bool = True

	# our plugin state, based on the current web page: 
	technique: str = None
	techniqueIndexListOfSsmlStrs: list = None
	techniquePageWideDictOfPlainTextToSsmlStr: dict = None
	a11yTreeRoot = None

	def initNvdaStateFieldsFromRealNvdaState(self):
		self.useCharacterModeCommand = getUseCharacterModeCommandFromNvdaState()
		self.isLanguageEnglish = getIsLanguageEnglishFromNvdaState()

		
def getUseCharacterModeCommandFromNvdaState():
	# A good test case for reproducing the problem that this code solves is <span data-ssml='{"say-as": "characters"}'>ABCDEFGHIJKLMNOP</span>

	# Some code here was copied from MathCAT.py, which was added in https://github.com/NSoiffer/MathCATForPython/commit/76679ad206749d4d0cf20bcade4a8880831e7904 to fix https://github.com/NSoiffer/MathCATForPython/issues/32 
	# From MathCAT.py: as of 7/23, oneCore voices do not implement the CharacterModeCommand despite it being in supported_commands

	synth = synthDriverHandler.getSynth()
	r = (CharacterModeCommand in synth.supportedCommands and synth.name != "oneCore")
	return r

def getIsLanguageEnglishFromNvdaState():
	# This was copied from MathCAT.py.  It might not work in Chrome, as per comments at https://github.com/NSoiffer/MathCATForPython/commit/76679ad206749d4d0cf20bcade4a8880831e7904 .   I'm very unclear on whether this handles language changes in the HTML (vs. the synth) and how that all works. 
	language = speech.getCurrentLanguage()
	language = language.lower() # b/c MathCAT.py did this, maybe, sometimes. 
	isLanguageEnglish = language.startswith("en")
	return isLanguageEnglish

def isPowerOfTwo(n_):
	return n_ > 0 and (n_ & (n_ - 1)) == 0

@profile
def decodeEncodedSsmlInstructionStr(str_):
	try:
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
	except ValueError as e:
		raise NonRetriableSsmlError() from e

class NonRetriableSsmlError(Exception):
    pass

# our retrying involves forcing a refresh of our state from the a11y root, then we try to do our whole "convert speech string into a speech command list" again.  we do this retry max once per speech filter call.
class RetriableSsmlError(Exception):
    pass

def getBreakTimeMillisFromStr(str_):
	if str_.endswith("ms"):
		r = float(str_[:-2])
	elif str_.endswith("s"):
		r = float(str_[:-1]) * 1000
	else:
		assert False
	return r

@profile
# This function sometimes uses the strategy of not checking that the input SSML is valid - rather, assuming that the JS already checked that it's valid, and if it wasn't, then it wouldn't have made it into this function.  This is inconsistent.  Only parts of this function do it that way.  It would be ideal if the JS did all of the checking, because page authors are (I think) more likely to check the devtools console for error messages compared to the NVDA logs.  Also, the devtools console can be checked earlier, without starting NVDA. 
def convertSsmlStrIntoSpeechCommandList(ssmlStr_, textToAffect_: str, origWholeText_: str, state_: State, okToThrowRetriableError_: bool):
	ourAssert(isinstance(ssmlStr_, str))
	try:
		ssmlObj = json.loads(ssmlStr_)
		if(not isinstance(ssmlObj, dict)):
			if type(ssmlObj) == int and okToThrowRetriableError_:
				# it's an int ==> technique=index.  but the fact that we're in this function - which is supposed to take as an arg an ssml str payload (not an index to one) indicates that we (= the python side) think that technique=inline.  the page is right.  our state on the python side is wrong.  this means that on the JS side, the JS init ran after we (= the python side) got our most recent update of our state from the a11y root.  so we force such an update by raising this: 
				raise RetriableSsmlError('detected late JS init')
			else:
				raise NonRetriableSsmlError(f'expected a dict in the json.  got an object of type: {type(ssmlObj)}.') from None
		if len(ssmlObj) != 1: raise NonRetriableSsmlError()
		key = next(iter(ssmlObj)); val = ssmlObj[key]
		if key == 'sub':
			aliasVal = val['alias']
			r = [aliasVal]
		elif key == 'say-as':
			if not isinstance(val, dict): raise NonRetriableSsmlError()
			if 'interpret-as' not in val: raise NonRetriableSsmlError()
			interpretAs = val['interpret-as']
			if interpretAs not in ['characters', 'spell']: raise NonRetriableSsmlError()
			# ^^ 'spell' is non-standard, I gather.  we treat it as an alias for 'characters'.  more comments in test.html. 

			if state_.useCharacterModeCommand:
				r = [CharacterModeCommand(True), textToAffect_, CharacterModeCommand(False)]
			else:
				r = []
				for ch in textToAffect_:
					# I'm using this "eigh" from MathCAT even though I couldn't reproduce the problem that it is solving, which is described at https://github.com/NSoiffer/MathCATForPython/issues/32 and https://github.com/nvaccess/nvda/issues/13596 , most thoroughly at the latter.
					# Also, I think that this code also takes effect only on lower-case "a", not upper-case "A".  I think MathCAT did that too.  I don't know why.
					r.extend((" ", "eigh" if ch == "a" and state_.isLanguageEnglish else ch, " "))

		elif key == 'phoneme':
			# With phonemes, there are some things I don't understand:
			# - judging by sound, PhonemeCommand only reliably works with synth=onecore 
			# - PhonemeCommand appears in supportedCommands of all three synths (onecore, sapi5, espeak).  
			# 	- all 3 synths have identical supportedCommands: {<class 'speech.commands.PitchCommand'>, <class 'speech.commands.BreakCommand'>, <class 'speech.commands.LangChangeCommand'>, <class 'speech.commands.PhonemeCommand'>, <class 'speech.commands.CharacterModeCommand'>, <class 'speech.commands.VolumeCommand'>, <class 'speech.commands.IndexCommand'>, <class 'speech.commands.RateCommand'>} 
			# I know of one phoneme that works in all 3 synths: "θ" i.e. "th".  this is on the test page.  
			# 	- I found this phoneme at https://github.com/nvaccess/nvda/blob/b501e16a2392aaa89892879d77725f02b9f2835d/source/synthDrivers/sapi5.py#L423 

			phonemeIpa = val['ph']
			r = [PhonemeCommand(phonemeIpa, text=textToAffect_)]
			INSERT_HACK_SPACE_AFTER = 1
			if INSERT_HACK_SPACE_AFTER:
				# ~ march 2025: this is here because of my aural observation that NVDA's announcement sounded like "woundlink" (i.e. with no space).
				# 2025-05-19: today when I disabled this code, I couldn't hear the problem.  so it's unclear if this code is necessary.  
				r.append(" ")
		elif key == 'break':
			if not re.match(r'^\s*$', textToAffect_): raise NonRetriableSsmlError(f'''found a "break" command on text content that includes non-whitespace.  we don't support this.  and it's unclear how this occurrence reached this code, b/c our JS should have prevented that.''')
			timeStr = val['time']
			timeMillis = getBreakTimeMillisFromStr(timeStr)
			# Based on my experiments, the actual duration of the break doesn't match exactly the arg that we pass to BreakCommand.  Sometimes it does eg. synth=espeak at rate=50 and rate=80.  and synt=sapi5 at rate=50.  Sometimes it doesn't eg. sapi5 rate=80: the actual break was roughly 0.5 of the arg to BreakCommand.  (all of my experiments were with rate_boost=off.)  It looks like MathCAT tries to deal with this at https://github.com/NSoiffer/MathCATForPython/blob/0e33d1306db49ac4d47fb5c47348a96aa4f283d0/addon/globalPlugins/MathCAT/MathCAT.py#L152 but I don't understand the values that that MathCAT code arrives at for breakMulti.  they don't match my experiments.  and they don't use the current synth as input - but my experiments indicate that the current synth plays a big role.  as for this plugin: there is probably a bug here i.e. the actual break time does not always match the break time value in the data-ssml.  
			r = [BreakCommand(time=timeMillis)]
		else:
			raise NonRetriableSsmlError()
	except (json.decoder.JSONDecodeError, KeyError, ValueError) as e:
		raise NonRetriableSsmlError() from e
	return r

# Matches the javascript encoding side.  If you change this then change that, and vice versa. 
MARKER = '\u2062'
MACRO_END_MARKER = MARKER * 2


@profile
def convertSpeechStrIntoSpeechCommandList_allMatches(str_: str, state_: State, okToThrowRetriableError_: bool):
	logInfo(f'convertSpeechStrIntoSpeechCommandList_allMatches input (len {len(str_)}): {repr(str_)}')
 
	if state_.technique in ('index', 'inline'):
		r = convertSpeechStrIntoSpeechCommandList_allMatches_techniquesIndexAndInline(str_, state_, okToThrowRetriableError_)
	elif state_.technique == 'page-wide':
		r = convertSpeechStrIntoSpeechCommandList_allMatches_techniquePageWide(str_, state_)
	else:
		ourAssert(False)

	# concat adjacent strings.  handles two situations: 1) technique=inline|index and we see encoding characters in the wild.  2) technique=*: consecutive sub-aliases, or a sub-alias with leading or trailing text. 
	# in both cases: I don't know how important this code is.  but it seems prudent to do it, in the spirit of our speech filter being minimally invasive. 
	newR = []
	i = 0
	while i < len(r):
		if isinstance(r[i], str):
			s = r[i]
			while i+1 < len(r) and isinstance(r[i+1], str):
				s += r[i+1]
				i += 1
			newR.append(s)
		else:
			newR.append(r[i])
		i += 1
	r = newR

	return r
    


def convertSpeechStrIntoSpeechCommandList_allMatches_techniquePageWide(str_: str, state_: State):
	m = state_.techniquePageWideDictOfPlainTextToSsmlStr
	ourAssert(m != None)
	plainTexts = sorted(m.keys(), key=lambda e: -len(e)) # so that if we have plainTexts "3'" and "3'~", our pattern will match "3'~".  the way regex '|' works, it will match the leftmost branch.  so we want the longest one to be the leftmost.  this sort does that. 
	patternForAllPlainTexts = re.compile('(?i)' + '|'.join(r'(?<!\w)'+re.escape(plainText)+r'(?!\w)' for plainText in plainTexts))
	r = []
	prevEndIdx = 0
	for match in patternForAllPlainTexts.finditer(str_):
		startIdx, endIdx = match.span()
		plainText = match.group(0)
		if startIdx > prevEndIdx:
			textBeforeMatch = str_[prevEndIdx:startIdx]
			logInfo(f'text before this match: {repr(textBeforeMatch)}')
			r.append(textBeforeMatch)
		logInfo(f'matched {repr(plainText)} at start pos {startIdx}')
		ssmlStr = m[plainText.lower()]
		speechCommandList = convertSsmlStrIntoSpeechCommandList(ssmlStr, plainText, plainText, state_, False)
		r.extend(speechCommandList)
		prevEndIdx = endIdx

	if prevEndIdx < len(str_):
		textAfterMatch = str_[prevEndIdx:]
		logInfo(f'text after last match: {repr(textAfterMatch)}')
		r.append(textAfterMatch)

	return r

def convertSpeechStrIntoSpeechCommandList_allMatches_techniquesIndexAndInline(str_: str, state_: State, okToThrowRetriableError_: bool):
	r = []
	prevEndIdx = 0
	iMatch = -1

	# the techniques index and inline have the same start/end markers. 
	pattern = re.compile(f'{re.escape(MARKER)}(.*?){re.escape(MARKER)}(.*?){re.escape(MACRO_END_MARKER)}', flags=re.DOTALL)

	for match in pattern.finditer(str_):
		iMatch += 1
		startIdx, endIdx = match.span()
		ssmlInstructionStrEncoded, plainTextToAffect = match.groups()
		plainTextWholeMatch = match.group(0)

		if startIdx > prevEndIdx:
			leadingNonMatch = str_[prevEndIdx:startIdx]
			logInfo(f'leadingNonMatch: {repr(leadingNonMatch)}')
			r.append(leadingNonMatch)

		logInfo(f'match [{iMatch}] start: plainTextWholeMatch = {repr(plainTextWholeMatch)}, ssmlInstructionStrEncoded = {repr(ssmlInstructionStrEncoded)}, textToAffect (len {len(plainTextToAffect)}) = {repr(plainTextToAffect)}')

		try:
			speechCommandListForMatch = convertSpeechStrIntoSpeechCommandList_singleMatch_techniquesIndexAndInline(ssmlInstructionStrEncoded, plainTextToAffect, plainTextWholeMatch, state_, okToThrowRetriableError_)
			r.extend(speechCommandListForMatch)
			logInfo(f'match [{iMatch}] result: Ok.  gave us: {speechCommandListForMatch}')
		except NonRetriableSsmlError as e:
			logInfo(f'match [{iMatch}] result: Error happened while processing SSML.  We will fall back to the plain text.  The SSML instruction string encoded was "{ssmlInstructionStrEncoded}".  The exception, which we will suppress, was:')
			log.exception(e)
			r.append(plainTextWholeMatch)
		prevEndIdx = endIdx

	if prevEndIdx < len(str_):
		trailingNonMatch = str_[prevEndIdx:]
		logInfo(f'trailingNonMatch: {repr(trailingNonMatch)}')
		r.append(trailingNonMatch)

	return r

def convertSpeechStrIntoSpeechCommandList_singleMatch_techniquesIndexAndInline(ssmlInstructionStrEncoded_: str, plainTextToAffect_: str, plainTextWholeMatch_: str, state_: State, okToThrowRetriableError_: bool):
	r = [plainTextWholeMatch_]
	if state_.technique == 'index':
		ourAssert(state_.techniqueIndexListOfSsmlStrs != None)
		idxInListAsEncodedStr = ssmlInstructionStrEncoded_
		if not idxInListAsEncodedStr:
			logInfo('ssml instruction string is empty.  we will ignore it.')
		else:
			idxInListAsDecodedStr = decodeEncodedSsmlInstructionStr(idxInListAsEncodedStr)
			logInfo(f'	idxInListAsDecodedStr: "{idxInListAsDecodedStr}"')
			ourAssert(idxInListAsDecodedStr)
			try:
				idxInList = int(idxInListAsDecodedStr)
			except ValueError as e:
				raise NonRetriableSsmlError() from e
			if(idxInList < 0): raise NonRetriableSsmlError("index is negative") # sure, python (with it's -ve list indices) could handle this -ve index.  but our JS will never output a -ve index.  so our JS didn't create this.  so this must be a case of "encoding characters in the wild".  
			if idxInList >= len(state_.techniqueIndexListOfSsmlStrs):
				if okToThrowRetriableError_:
					# could mean that on the JS side, watchForDomChanges == true, and the data-ssml attribute corresponding to this index was added after we (= the python side) did our most recent update of our state from the a11y root.  so we raise this, to force such an update: 
					raise RetriableSsmlError('idx is too high for us')
				else:
					raise NonRetriableSsmlError('idx is too high for us') from None
			ssmlStr = state_.techniqueIndexListOfSsmlStrs[idxInList]
			r = convertSsmlStrIntoSpeechCommandList(ssmlStr, plainTextToAffect_, plainTextWholeMatch_, state_, okToThrowRetriableError_)
	elif state_.technique == 'inline':
		ssmlStrEncoded = ssmlInstructionStrEncoded_
		ssmlStr = decodeEncodedSsmlInstructionStr(ssmlStrEncoded)
		logInfo(f'	ssmlStr: "{ssmlStr}"')
		r = convertSsmlStrIntoSpeechCommandList(ssmlStr, plainTextToAffect_, plainTextWholeMatch_, state_, okToThrowRetriableError_)
	else:
		ourAssert(False)

	return r
	

def getTechniqueIndexListOfSsmlStrsFromHidingPlaceTextNode(hidingPlaceTextNode_):
	ourAssert(hidingPlaceTextNode_)
	hidingPlaceTextNodeValue = hidingPlaceTextNode_.name
	pattern = rf'{HIDING_PLACE_GUID_FOR_ALL_TECHNIQUES} {HIDING_PLACE_GUID_FOR_INDEX_TECHNIQUE}\s*(\[.*\])'
	match = re.search(pattern, hidingPlaceTextNodeValue)
	if not match: return None
	listStr = match.group(1)
	listObj = json.loads(listStr)
	return listObj

def getTechniquePageWideDictOfPlainTextToSsmlStrFromHidingPlaceTextNode(hidingPlaceTextNode_, state_):
	ourAssert(hidingPlaceTextNode_)
	hidingPlaceTextNodeValue = hidingPlaceTextNode_.name
	pattern = HIDING_PLACE_GUID_FOR_ALL_TECHNIQUES+' '+HIDING_PLACE_GUID_FOR_PAGE_WIDE_TECHNIQUE+r'\s*(\{.*\})'
	match = re.search(pattern, hidingPlaceTextNodeValue)
	if not match: return None
	mapStr = match.group(1)
	plainTextToSsmlStr = json.loads(mapStr)
	r = {}
	for plainText, ssmlStr in plainTextToSsmlStr.items():
		r[plainText.lower()] = ssmlStr
	return r

@profile
def getRole(nvdaObj_):
	try:
		return roleLabels[nvdaObj_.role]
	except (KeyError, IndexError, TypeError):
		return f"unknown role ({nvdaObj_.role})"

''' 
the location (in xpath-like syntax) of our hiding place text node: 
	if a11yRoot is an instance of NVDAObjects.IAccessible.chromium.Document (chrome) or NVDAObjects.Dynamic_DocumentMozillaIAccessible (firefox): 
		then it's at /document/section/text 
	elif a11yRoot is an instance of NVDAObjects.Dynamic_ChromiumUIADocumentEditableTextWithAutoSelectDetectionUIA (chrome): 
		then it's at /document/grouping/text 
- ^^ the former is the usual.  the latter: I found difficult to reproduce.  steps to reproduce are probably in the commit message for the commit where this comment appeared. 
- we work around it in chrome.  we don't work around it in firefox, b/c I can't see how, b/c nvda in firefox is broken under those steps to reproduce - even w/o this plugin loaded.  
	- I think I'm running into the same problem as https://github.com/nvaccess/nvda/issues/17766 > "pressing tab brings NVDA directly on track again and the virtual document is loaded as expected".
- for chrome, we work around that strangeness by looking for a "section" or a "grouping" based on the type of a11yRoot.  IDK for reason for that difference in role.  neither role makes much sense, b/c it's a plain div. 
- document is: a11yTreeRoot_ 
- section|grouping is: our hiding place div.  in the DOM: last child of <body>.  in this tree: last child of document.  
- text is: a text node, and it's the only child of our hiding place div. 
- most of the above is true in both chrome and ff.  
- this function is slow.  usually takes 13 ms.  slow parts are: .lastChild and .firstChild.
'''
@profile
def findHidingPlaceTextNodeInA11yTree(a11yTreeRoot_):
	logInfo(f'looking for hiding place element.  dom root id={id(a11yTreeRoot_)} {a11yTreeRoot_}')
	if not a11yTreeRoot_: return None
	a11yTreeRootCurChild = a11yTreeRoot_.lastChild
	if not a11yTreeRootCurChild: return None

	# normally I would do an "isinstance()" here, but I don't know where the class NVDAObjects.Dynamic_ChromiumUIADocumentEditableTextWithAutoSelectDetectionUIA is defined.  I couldn't even find it via google or github search. 
	if "NVDAObjects.Dynamic_ChromiumUIADocumentEditableTextWithAutoSelectDetectionUIA" in str(type(a11yTreeRoot_)):
		ourHidingPlaceElemRole = 'grouping'
	else:
		ourHidingPlaceElemRole = 'section'

	r = None
	while a11yTreeRootCurChild:
		if getRole(a11yTreeRootCurChild) != ourHidingPlaceElemRole:
			logInfo('looking for hiding place element.  skipping, case 1')
		else:
			a11yTreeRootCurChildFirstChild = a11yTreeRootCurChild.firstChild
			if not (a11yTreeRootCurChildFirstChild != None and getRole(a11yTreeRootCurChildFirstChild) == 'text'):
				logInfo('looking for hiding place element.  skipping, case 2')
			else:
				textNode = a11yTreeRootCurChildFirstChild
				name = textNode.name
				textContent = name
				if HIDING_PLACE_GUID_FOR_ALL_TECHNIQUES not in textContent: 
					logInfo('looking for hiding place element.  skipping, case 3')
				else:
					r = textNode
					break
		a11yTreeRootCurChild = a11yTreeRootCurChild.previous
	logInfo(f'found hiding place element: {r != None}.')
	return r

def a11yTreeToStr(root_, maxDepth=None):
	lines = []
	def recurse(node, indent=0):
		if (node is None) or (maxDepth != None and indent > maxDepth):
			return
		indentStr = "  " * indent
		try:
			roleStr = roleLabels[node.role]
		except (KeyError, IndexError, TypeError):
			roleStr = f"unknown ({node.role})"
		name = node.name or ""
		lines.append(f"{indentStr}{roleStr}: {name}")
		child = node.firstChild
		while child:
			recurse(child, indent + 1)
			child = child.next

	recurse(root_)
	return "\n".join(lines)

g_state = State() # never None 
g_state.technique = 'inline'

def updateA11yTreeRoot(forceUpdateOfState_):
	global g_state

	try:
		newA11yTreeRoot = api.getNavigatorObject().treeInterceptor.rootNVDAObject
	except (AttributeError) as e:
		newA11yTreeRoot = None

	oldA11yTreeRoot = g_state.a11yTreeRoot
	a11yTreeRootChanged = (id(oldA11yTreeRoot) != id(newA11yTreeRoot)) # it's unclear if "id" is necessary here.  I used it because I don't know how their equals operator is implemented. 
	# FYI if you reload the page, the a11y root will change to a new one. 
	logInfo(f'a11y tree root is now {str(newA11yTreeRoot)}.  value changed: {"yes" if a11yTreeRootChanged else "no"}.')
	if a11yTreeRootChanged or forceUpdateOfState_:
		g_state = State()
		g_state.a11yTreeRoot = newA11yTreeRoot
		g_state.initNvdaStateFieldsFromRealNvdaState()
		hidingPlaceTextNode = findHidingPlaceTextNodeInA11yTree(g_state.a11yTreeRoot)
		if not hidingPlaceTextNode:
			g_state.technique = 'inline'
		else:
			g_state.techniqueIndexListOfSsmlStrs = getTechniqueIndexListOfSsmlStrsFromHidingPlaceTextNode(hidingPlaceTextNode)
			if g_state.techniqueIndexListOfSsmlStrs != None:
				logInfo('Found global object for technique=index.')
				g_state.technique = 'index'
			else:
				g_state.techniquePageWideDictOfPlainTextToSsmlStr = getTechniquePageWideDictOfPlainTextToSsmlStrFromHidingPlaceTextNode(hidingPlaceTextNode, g_state)
				if g_state.techniquePageWideDictOfPlainTextToSsmlStr != None:
					logInfo('Found global object for technique=page-wide.')
					g_state.technique = 'page-wide'
		if g_state.technique == 'inline':
			logInfo("Found no global object.  Will assume technique=inline.  Either this web page uses technique=inline, or this web page didn't run our JS, or this is not a web page.")

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	
	def __init__(self):
		super().__init__()
		setGlobalVarsBasedOnNvdaConfig()
		#monkeyPatchBrailleHandler()
		# Thank you Dalen at https://nvda-addons.groups.io/g/nvda-addons/message/25811 for this idea of using filter_speechSequence instead of monkey-patching the synth. 
		self._ourSpeechSequenceFilter = speech.extensions.filter_speechSequence.register(self.ourSpeechSequenceFilter)
		if LOG_BRAILLE:
			braille.pre_writeCells.register(self.ourBraillePreWriteCells)
		if NEXT_SYNTH_SHORTCUT:
			self.bindGesture("kb:NVDA+control+alt+n", "nextSynth")

	@scriptHandler.script(description="next synth")
	def script_nextSynth(self, gesture):
		allSynthsExceptSilence = [shortName for shortName, longName in synthDriverHandler.getSynthList()]
		allSynthsExceptSilence.remove('silence')
		curSynth = synthDriverHandler.getSynth().name
		if curSynth == 'silence':
			newSynth = allSynthsExceptSilence[0]
		else:
			curSynthIdx = allSynthsExceptSilence.index(curSynth)
			nextIdx = (curSynthIdx + 1) % len(allSynthsExceptSilence)
			newSynth = allSynthsExceptSilence[nextIdx]
		synthDriverHandler.setSynth(newSynth)
		ui.message(f'''set synth to {newSynth}''')

	def ourBraillePreWriteCells(self, cells, rawText, currentCellCount):
		logInfo(f'braille: cells={cells}, rawText={rawText}, currentCellCount={currentCellCount}')

	def terminate(self):
		speech.extensions.filter_speechSequence.unregister(self.ourSpeechSequenceFilter)

	# if this function raises an exception, then that exception will appear in the nvda logs and nvda will speak normally i.e. speak as though this filter didn't exist.  so we don't bend over backwards to catch all exceptions we might create. 
	def ourSpeechSequenceFilter(self, origSeq: speech.SpeechSequence) -> speech.SpeechSequence:
		updateA11yTreeRoot(False)
		g_state.initNvdaStateFieldsFromRealNvdaState()
		logInfo(f'--> original speech sequence: {origSeq}')
		try:
			modSeq = self.ourSpeechSequenceFilterImpl(origSeq, True)
		except RetriableSsmlError as e:
			logInfo(f'got retriable error w/ message string "{e}".  will retry.')
			updateA11yTreeRoot(True)
			modSeq = self.ourSpeechSequenceFilterImpl(origSeq, False)
		logInfo(f'--> modified speech sequence: {modSeq}')
		logInfo(f'speech sequence changed: {modSeq != origSeq}')
		return modSeq
	
	def ourSpeechSequenceFilterImpl(self, origSeq: speech.SpeechSequence, okToThrowRetriableError_: bool) -> speech.SpeechSequence:
		modSeq = []
		for element in origSeq:
			if isinstance(element, str) and len(element) > 0:
				logInfo(f'filter got string len {len(element)}: "{repr(element)}"')
				modSeq.extend(convertSpeechStrIntoSpeechCommandList_allMatches(element, g_state, okToThrowRetriableError_))
			else:
				modSeq.append(element)
		return modSeq

def monkeyPatchBrailleHandler():
	originalUpdateFunc = braille.handler.update

	def ourUpdateFunc(self):
		logInfo('eureka')
		for region in self.buffer.regions:
			if hasattr(region, "rawText"):
				logInfo(f'braille rawText before: "{region.rawText}"')
				for encodingChar in ENCODING_CHARS:
					region.rawText = region.rawText.replace(encodingChar, "")
				logInfo(f'braille rawText after: "{region.rawText}"')
		self.buffer.update()
		return originalUpdateFunc()

	braille.handler.update = types.MethodType(ourUpdateFunc, braille.handler)




