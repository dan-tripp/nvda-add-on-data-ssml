
PROFILE = False
LOG_BRAILLE = False

HIDING_PLACE_GUID_FOR_ALL_TECHNIQUES = '4b9b696c-8fc8-49ca-9bb9-73afc9bd95f7'
HIDING_PLACE_GUID_FOR_INDEX_TECHNIQUE = 'b4f55cd4-8d9e-40e1-b344-353fe387120f'
HIDING_PLACE_GUID_FOR_PAGE_WIDE_OVERRIDE_TECHNIQUE = 'c7a998a5-4b7e-4683-8659-f2da4aa96eee'

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

import datetime, re, base64, json, time, types
import globalPluginHandler, api
from logHandler import log
import speech, speech.commands, speech.extensions, braille
import gettext
import synthDriverHandler
from controlTypes import roleLabels
from documentBase import textInfos


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


def profile(fn):
	if PROFILE:
		def wrapped(*args, **kwargs):
			t0 = time.perf_counter()
			try:
				return fn(*args, **kwargs)
			finally:
				t1 = time.perf_counter()
				logInfo(f"profile: {fn.__name__} took {int((t1-t0)*1000)} ms.")
		return wrapped
	else:
		return fn
	
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

def isPowerOfTwo(n_):
	return n_ > 0 and (n_ & (n_ - 1)) == 0

@profile
def decodeSingleStr(str_):

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

class SsmlError(Exception):
    pass

@profile
def turnSsmlIntoSpeechCommandList(ssmlAsJsonStr_, nonSsmlStr_, origWholeUnmodifiedText_):
	try:
		ssmlAsDict = json.loads(ssmlAsJsonStr_)
		if len(ssmlAsDict) != 1: raise SsmlError()
		key = next(iter(ssmlAsDict)); val = ssmlAsDict[key]
		if key == 'sub':
			aliasVal = val['alias']
			r = [aliasVal]
		elif key == 'say-as':
			if val != 'characters': raise SsmlError()

			# The best test case for reproducing the problem that this code solves is <span data-ssml='{"say-as": "characters"}'>ABCDEFGHIJKLMNOP</span>

			# Some code here was copied from MathCAT.py, which was added in https://github.com/NSoiffer/MathCATForPython/commit/76679ad206749d4d0cf20bcade4a8880831e7904 to fix https://github.com/NSoiffer/MathCATForPython/issues/32 
			# From MathCAT.py: as of 7/23, oneCore voices do not implement the CharacterModeCommand despite it being in supported_commands
			synth = synthDriverHandler.getSynth()
			useCharacterModeCommand = (CharacterModeCommand in synth.supportedCommands and synth.name != "oneCore")
			if useCharacterModeCommand:
				r = [CharacterModeCommand(True), nonSsmlStr_, CharacterModeCommand(False)]
			else:
				# This language code was copied from MathCAT.py.  It might not work in Chrome, as per comments at https://github.com/NSoiffer/MathCATForPython/commit/76679ad206749d4d0cf20bcade4a8880831e7904 .   I'm very unclear on whether this handles language changes in the HTML (vs. the synth) and how that all works. 
				language = speech.getCurrentLanguage()
				language = language.lower() # b/c MathCAT.py did this, maybe, sometimes. 
				isLanguageEnglish = language.startswith("en")

				r = []
				for ch in nonSsmlStr_:
					# I'm using this "eigh" from MathCAT even though I couldn't reproduce the problem that it is solving, which is described at https://github.com/NSoiffer/MathCATForPython/issues/32 and https://github.com/nvaccess/nvda/issues/13596 , most thoroughly at the latter. 
					r.extend((" ", "eigh" if ch == "a" and isLanguageEnglish else ch, " "))

		elif key == 'ph':
			# With phonemes, there are some things I don't understand:
			# - judging by sound, PhonemeCommand only reliably works with synth=onecore 
			# - PhonemeCommand appears in supportedCommands of all three synths (onecore, sapi5, espeak).  
			# 	- all 3 synths have identical supportedCommands: {<class 'speech.commands.PitchCommand'>, <class 'speech.commands.BreakCommand'>, <class 'speech.commands.LangChangeCommand'>, <class 'speech.commands.PhonemeCommand'>, <class 'speech.commands.CharacterModeCommand'>, <class 'speech.commands.VolumeCommand'>, <class 'speech.commands.IndexCommand'>, <class 'speech.commands.RateCommand'>} 
			# I know of one phoneme that works in all 3 synths: "θ" i.e. "th".  this is on the test page.  
			# 	- I found this phoneme at https://github.com/nvaccess/nvda/blob/b501e16a2392aaa89892879d77725f02b9f2835d/source/synthDrivers/sapi5.py#L423 

			phonemeIpa = val
			r = [PhonemeCommand(phonemeIpa, text=nonSsmlStr_)]
			INSERT_HACK_SPACE_AFTER = 1
			if INSERT_HACK_SPACE_AFTER:
				# ~ march 2025: this is here because of my aural observation that NVDA's announcement sounded like "woundlink" (i.e. with no space).
				# 2025-05-19: today when I disabled this code, I couldn't hear the problem.  so it's unclear if this code is necessary.  
				r.append(" ")
		else:
			raise SsmlError()
	except (json.decoder.JSONDecodeError, SsmlError, KeyError) as e:
		logInfo(f'Error happened while processing SSML JSON string.  We will fall back to the plain text.  The SSML string was "{ssmlAsJsonStr_}".  The exception, which we will suppress, was:')
		log.exception(e)
		r = [origWholeUnmodifiedText_]
	return r

# Matches the javascript encoding side.  If you change that then change this, and vice versa. 
MARKER = '\u2062'
MACRO_END_MARKER = MARKER * 2

@profile
def decodeAllStrs(str_):
	logInfo(f'decodeAllStrs input (len {len(str_)}): {repr(str_)}')
 
	if g_indexTechniqueGlobalList != None:
		technique = 'index'
	elif g_pageWideOverrideTechniqueMapOfPlainTextToSpeechCommandList != None:
		technique = 'page-wide-override'
	else:
		technique = 'inline'

	if technique in ('index', 'inline'):
		r = decodeAllStrs_indexAndInlineTechniques(str_)
	elif technique == 'page-wide-override':
		r = decodeAllStrs_pageWideOverrideTechnique(str_)
	else:
		ourAssert(False)

	# concat adjacent strings.  handles two situations: 1) technique=inline|index and we see encoding characters in the wild.  2) technique=*: consecutive sub-aliases, or a sub-alias with leading or trailing text. 
	# in both cases: I don't know how important this code is.  but it seems prudent to do it, in the spirit of being minimally invasive. 
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
    


def decodeAllStrs_pageWideOverrideTechnique(str_):
	ourAssert(g_pageWideOverrideTechniqueMapOfPlainTextToSpeechCommandList != None)
	m = g_pageWideOverrideTechniqueMapOfPlainTextToSpeechCommandList
	plainTexts = sorted(m.keys(), key=lambda e: -len(e)) # so that if we have plainTexts "3'" and "3'~", our pattern will match "3'~".  the way regex '|' works, it will match the leftmost branch.  so we want the longest one to be the leftmost.  this sort does that. 
	patternForAllPlainTexts = re.compile('(?i)' + '|'.join(r'(?<!\w)'+re.escape(plainText)+r'(?!\w)' for plainText in plainTexts))
	r = []
	prevEndIdx = 0
	for match in patternForAllPlainTexts.finditer(str_):
		startIdx, endIdx = match.span()
		plainText = match.group(0)
		logInfo(f'matched {repr(plainText)} at start pos {startIdx}')
		if startIdx > prevEndIdx:
			textBeforeMatch = str_[prevEndIdx:startIdx]
			logInfo(f'	text before this match: {repr(textBeforeMatch)}')
			r.append(textBeforeMatch)
		speechCommandList = m[plainText.lower()]
		r.extend(speechCommandList)
		prevEndIdx = endIdx

	if prevEndIdx < len(str_):
		textAfterMatch = str_[prevEndIdx:]
		logInfo(f'text after last match: {repr(textAfterMatch)}')
		r.append(textAfterMatch)

	return r

def decodeAllStrs_indexAndInlineTechniques(str_):
	r = []
	prevEndIdx = 0
	matchCount = 0

	# the techniques index and inline have the same start/end markers. 
	pattern = re.compile(f'{re.escape(MARKER)}(.*?){re.escape(MARKER)}(.*?){re.escape(MACRO_END_MARKER)}', flags=re.DOTALL)

	technique = None
	for match in pattern.finditer(str_):
		matchCount += 1
		startIdx, endIdx = match.span()
		encodedStr, textToAffect = match.groups()
		origWholeUnmodifiedText = match.group(0)

		logInfo(f'encodedStr: {repr(encodedStr)}')
		logInfo(f'textToAffect (len {len(textToAffect)}): {repr(textToAffect)}')

		if startIdx > prevEndIdx:
			pre = str_[prevEndIdx:startIdx]
			logInfo(f'	text before this match: {repr(pre)}')
			r.append(pre)

		success = False
		try:
			if technique == None:
				technique = detectTechnique(encodedStr)
			if technique == 'index':
				encodedSsmlIndexInGlobalList = encodedStr
				decodedToStrSsmlIndexInGlobalList = decodeSingleStr(encodedSsmlIndexInGlobalList)
				logInfo(f'	decodedToStrSsmlIndexInGlobalList: "{decodedToStrSsmlIndexInGlobalList}"')
				if decodedToStrSsmlIndexInGlobalList:
					idxInGlobalList = int(decodedToStrSsmlIndexInGlobalList)
					ssmlStr = g_indexTechniqueGlobalList[idxInGlobalList]
					r.extend(turnSsmlIntoSpeechCommandList(ssmlStr, textToAffect, origWholeUnmodifiedText))
					success = True
			elif technique == 'inline':
				encodedSsmlStr = encodedStr
				decodedSsmlStr = decodeSingleStr(encodedSsmlStr)
				logInfo(f'	decodedSsmlStr: "{decodedSsmlStr}"')
				r.extend(turnSsmlIntoSpeechCommandList(decodedSsmlStr, textToAffect, origWholeUnmodifiedText))				
				success = True
			else:
				ourAssert(False)
		except (Exception, IndexError) as e:
			logInfo(f"Couldn't decode or figure out what to do with string '{encodedStr} / {repr(encodedStr)}'.  Will use fall back to the plain text.")
			if 1:
				logInfo('Exception, which we will suppress, was:')
				log.exception(e)
			#raise

		if not success:
			r.append(origWholeUnmodifiedText)

		prevEndIdx = endIdx

	if prevEndIdx < len(str_):
		trailing = str_[prevEndIdx:]
		logInfo(f'text after last match: {repr(trailing)}')
		r.append(trailing)

	return r

def detectTechnique(encodedStr_):
	try:
		int(decodeSingleStr(encodedStr_))
		ourAssert(g_indexTechniqueGlobalList != None)
		return 'index'
	except (ValueError):
		return 'inline'

def getIndexTechniqueGlobalListFromHidingPlaceElem(hidingPlaceElem_):
	ourAssert(hidingPlaceElem_)
	hidingPlaceElemTextContent = hidingPlaceElem_.name
	pattern = rf'{HIDING_PLACE_GUID_FOR_ALL_TECHNIQUES} {HIDING_PLACE_GUID_FOR_INDEX_TECHNIQUE}\s*(\[.*\])'
	match = re.search(pattern, hidingPlaceElemTextContent)
	if not match: return None
	globalListStr = match.group(1)
	globalListObj = json.loads(globalListStr)
	return globalListObj

def getPageWideOverrideTechniqueGlobalMapFromHidingPlaceElem(hidingPlaceElem_):
	ourAssert(hidingPlaceElem_)
	hidingPlaceElemTextContent = hidingPlaceElem_.name
	pattern = HIDING_PLACE_GUID_FOR_ALL_TECHNIQUES+' '+HIDING_PLACE_GUID_FOR_PAGE_WIDE_OVERRIDE_TECHNIQUE+r'\s*(\{.*\})'
	match = re.search(pattern, hidingPlaceElemTextContent)
	if not match: return None
	mapStr = match.group(1)
	plainTextToSsmlStr = json.loads(mapStr)
	r = {}
	for plainText, ssmlStr in plainTextToSsmlStr.items():
		r[plainText.lower()] = turnSsmlIntoSpeechCommandList(ssmlStr, plainText, plainText)
	return r

@profile
def getRole(nvdaObj_):
	try:
		return roleLabels[nvdaObj_.role]
	except (KeyError, IndexError, TypeError):
		return f"unknown role ({nvdaObj_.role})"

@profile
def findHidingPlaceElementInA11yTree(root_):
	logInfo(f'dom root id={id(root_)} {root_}')
	# document > section > text 
	# document: root_ 
	# > section: our hiding place div.  in DOM: last child of <body>.  in this tree: last child of document.  
	# > text: only child of our hiding place div. 
	# in both chrome and ff.  
	# looks like this function is slow.  usually takes 13 ms.  slow parts are: .lastChild and .firstChild. 
	if not root_: return None
	documentLastChild = root_.lastChild
	if not documentLastChild: return None
	if getRole(documentLastChild) != 'section': return None
	section = documentLastChild
	sectionFirstChild = section.firstChild
	if getRole(sectionFirstChild) != 'text': return None
	text = sectionFirstChild
	name = text.name
	textContent = name
	if HIDING_PLACE_GUID_FOR_ALL_TECHNIQUES in textContent: 
		return text

def a11yTreeToStr(root_, maxDepth=10):
	lines = []
	def recurse(node, indent=0):
		if node is None or indent > maxDepth:
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

g_a11yTreeRoot = None
g_indexTechniqueGlobalList = None
g_pageWideOverrideTechniqueMapOfPlainTextToSpeechCommandList = None

def updateA11yTreeRoot(newAllTreeRoot_):
	global g_a11yTreeRoot, g_indexTechniqueGlobalList, g_pageWideOverrideTechniqueMapOfPlainTextToSpeechCommandList
	oldA11yTreeRoot = g_a11yTreeRoot
	g_a11yTreeRoot = newAllTreeRoot_
	a11yTreeRootChanged = (id(oldA11yTreeRoot) != id(newAllTreeRoot_)) # it's unclear if "id" is necessary here.  I used it because I don't know how their equals operator is implemented. 
	logInfo(f'set g_a11yTreeRoot to {str(g_a11yTreeRoot)}.  value changed: {"yes" if a11yTreeRootChanged else "no"}.')
	if a11yTreeRootChanged:
		g_indexTechniqueGlobalList = g_pageWideOverrideTechniqueMapOfPlainTextToSpeechCommandList = None
		success = False
		hidingPlaceElem = findHidingPlaceElementInA11yTree(g_a11yTreeRoot)
		if hidingPlaceElem:
			g_indexTechniqueGlobalList = getIndexTechniqueGlobalListFromHidingPlaceElem(hidingPlaceElem)
			if g_indexTechniqueGlobalList != None:
				logInfo('Found global object for technique=index.')
				success = True
			else:
				g_pageWideOverrideTechniqueMapOfPlainTextToSpeechCommandList = getPageWideOverrideTechniqueGlobalMapFromHidingPlaceElem(hidingPlaceElem)
				if g_pageWideOverrideTechniqueMapOfPlainTextToSpeechCommandList != None:
					logInfo('Found global object for technique=page-wide-override.')
					success = True
		if not success:
			logInfo("Found no global object.  Either this web page uses technique=inline, or this web page didn't run our JS, or this is not a web page.")

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	
	def __init__(self):
		super().__init__()
		#monkeyPatchBrailleHandler()
		# Thank you Dalen at https://nvda-addons.groups.io/g/nvda-addons/message/25811 for this idea of using filter_speechSequence instead of monkey-patching the synth. 
		self._ourSpeechSequenceFilter = speech.extensions.filter_speechSequence.register(self.ourSpeechSequenceFilter)
		if LOG_BRAILLE:
			braille.pre_writeCells.register(self.ourBraillePreWriteCells)

	def ourBraillePreWriteCells(self, cells, rawText, currentCellCount):
		logInfo(f'braille: cells={cells}, rawText={rawText}, currentCellCount={currentCellCount}')

	def terminate(self):
		speech.extensions.filter_speechSequence.unregister(self.ourSpeechSequenceFilter)

	def newUpdateA11yTreeRoot(self):
		try:
			newA11yTreeRoot = api.getNavigatorObject().treeInterceptor.rootNVDAObject
		except (AttributeError) as e:
			newA11yTreeRoot = None
		updateA11yTreeRoot(newA11yTreeRoot)

	def ourSpeechSequenceFilter(self, origSeq: speech.SpeechSequence) -> speech.SpeechSequence:
		self.newUpdateA11yTreeRoot()
		modSeq = []
		#logInfo(f'g_a11yTreeRoot: {g_a11yTreeRoot.name if g_a11yTreeRoot else None}') 
		#logInfo(f'a11yTree:\n{a11yTreeToStr(g_a11yTreeRoot)}') 
		logInfo(f'original speech sequence: {origSeq}')
		for element in origSeq:
			if isinstance(element, str):
				#logInfo(f'patched synth got string len {len(element)}: "{element}"')
				logInfo(f'filter got string len {len(element)}: "{repr(element)}"')
				modSeq.extend(decodeAllStrs(element))
			else:
				modSeq.append(element)
		logInfo(f'modified speech sequence: {modSeq}')
		logInfo(f'speech sequence changed: {modSeq != origSeq}')
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
	