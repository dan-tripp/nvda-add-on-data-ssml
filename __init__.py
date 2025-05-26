
PROFILE = True

import datetime, re, base64, json, time
import globalPluginHandler
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

def logInfo(str_):
	log.info(f'data-ssml: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} {str_}')

def ourAssert(bool_, str_=''):
	if not bool_:
		raise AssertionError(str_)
		

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
		\u180E: almost worked, but got filtered sometimes, or caused premature string split.  tested on chrome only IIRC.  more notes in test-page-for-encoding-chars.html . 
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
	ourAssert(len(set(ENCODING_CHARS)) == len(ENCODING_CHARS), "encodingChars contains duplicates")

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
		r = [origWholeUnmodifiedText_]
	return r

# Matches the javascript encoding side.  If you change that then change this, and vice versa. 
MARKER = '\u2062'
MACRO_END_MARKER = MARKER * 2

# For the index technique: this function lazy-calls findHidingPlaceElementInA11yTree() b/c it takes ~ 13 ms per call.  this amounts to calling that function only for parts of a web page which have our encoded data-ssml. 
@profile
def decodeAllStrs(str_, hidingPlaceElemRef_):
	ourAssert(isinstance(hidingPlaceElemRef_, list) and len(hidingPlaceElemRef_) == 1)
	logInfo(f'decodeAllStrs input (len {len(str_)}): {repr(str_)}')
 
	r = []
	lastEnd = 0
	matchCount = 0

	# the two techniques index and inline have the same start/end markers. 
	pattern = re.compile(
		f'{re.escape(MARKER)}'
		f'(.*?)'
		f'{re.escape(MARKER)}'
		f'(.*?)'
		f'{re.escape(MACRO_END_MARKER)}',
		flags=re.DOTALL)

	technique = None
	for match in pattern.finditer(str_):
		matchCount += 1
		start, end = match.span()
		encodedStr, textToAffect = match.groups()
		origWholeUnmodifiedText = match.group(0)

		logInfo(f'encodedStr: {repr(encodedStr)}')
		logInfo(f'textToAffect (len {len(textToAffect)}): {repr(textToAffect)}')

		if start > lastEnd:
			pre = str_[lastEnd:start]
			logInfo(f'	plain text before match: {repr(pre)}')
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
					if hidingPlaceElemRef_[0] == None:
						hidingPlaceElemRef_[0] = findHidingPlaceElementInA11yTree(g_a11yTreeRoot)
					globalList = getGlobalListFromHidingPlaceElem(hidingPlaceElemRef_[0])
					ssmlStr = globalList[idxInGlobalList]
					r.extend(turnSsmlIntoSpeechCommandList(ssmlStr, textToAffect, origWholeUnmodifiedText))
					success = True
			elif technique == 'inline':
				encodedSsmlStr = encodedStr
				decodedSsmlStr = decodeSingleStr(encodedSsmlStr)
				logInfo(f'	decodedSsmlStr: {decodedSsmlStr}')
				r.extend(turnSsmlIntoSpeechCommandList(decodedSsmlStr, textToAffect, origWholeUnmodifiedText))				
				success = True
			else:
				ourAssert(False)
		except (Exception, IndexError) as e:
			logInfo(f"Couldn't decode or figure out what to do with string '{encodedStr} / {repr(encodedStr)}'.  Will use unmodified text.")
			if 1:
				logInfo('Exception, which we will suppress, was:')
				log.exception(e)
			#raise

		if not success:
			r.append(origWholeUnmodifiedText)

		lastEnd = end

	if lastEnd < len(str_):
		trailing = str_[lastEnd:]
		logInfo(f'trailing text after last match: {repr(trailing)}')
		r.append(trailing)

	if all(isinstance(e, str) for e in r):
		# this is for when we meet 'encoding chars in the wild'.  in that case, the code earlier in this function will 'fallback' to the unmodified string, but it will still make this modification: it will split up str_ into > 1 string.  I suspect that might affect SR pronunciation in some cases.  so here we undo that.  
		# I know know why I didn't do "r = [str_]" here.
		r = [''.join(r)]

	return r

def detectTechnique(encodedStr_):
	try:
		int(decodeSingleStr(encodedStr_))
		return 'index'
	except (ValueError):
		return 'inline'

def getGlobalListFromHidingPlaceElem(hidingPlaceElem_):
	ourAssert(hidingPlaceElem_)
	hidingPlaceElemTextContent = hidingPlaceElem_.name
	HIDING_PLACE_GUID = '4b9b696c-8fc8-49ca-9bb9-73afc9bd95f7'
	pattern = rf'{HIDING_PLACE_GUID}\s*(\[.*?\])'
	match = re.search(pattern, hidingPlaceElemTextContent)
	if not match: return None
	globalListStr = match.group(1)
	globalListObj = json.loads(globalListStr)
	return globalListObj

@profile
def getRole(nvdaObj_):
	try:
		return roleLabels[nvdaObj_.role]
	except (KeyError, IndexError, TypeError):
		return f"unknown role ({nvdaObj_.role})"

@profile
def findHidingPlaceElementInA11yTree(root_):
	logInfo(f'dom root id {id(root_)}')
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
	GUID = '4b9b696c-8fc8-49ca-9bb9-73afc9bd95f7'
	if GUID in textContent: 
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

g_original_speakTextInfo = speech.speakTextInfo

g_a11yTreeRoot = None

# This functions gets the a11y tree root AKA DOM root, so that later our filter_speechSequence function can get our SSML from there.  This is not as good as getting the DOM root directly from our filter_speechSequence function.  If would do that if I knew how.
def patchedSpeakTextInfo(info, *args, **kwargs):
	global g_a11yTreeRoot
	nvdaObjectAtStart = info.NVDAObjectAtStart
	a11yTreeRoot = nvdaObjectAtStart.treeInterceptor.rootNVDAObject
	oldA11yTreeRoot = g_a11yTreeRoot
	g_a11yTreeRoot = a11yTreeRoot
	logInfo(f'set g_a11yTreeRoot to {str(g_a11yTreeRoot)}.  value changed: {"yes" if (id(oldA11yTreeRoot) != id(g_a11yTreeRoot)) else "no"}.')
	return g_original_speakTextInfo(info, *args, **kwargs)

def patchSpeakTextInfoFunc():
	speech.speakTextInfo = patchedSpeakTextInfo

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	def __init__(self):
		super().__init__()
		patchSpeakTextInfoFunc()
		# Thank you Dalen at https://nvda-addons.groups.io/g/nvda-addons/message/25811 for this idea of using filter_speechSequence instead of monkey-patching the synth. 
		self._ourSpeechSequenceFilter = speech.extensions.filter_speechSequence.register(self.ourSpeechSequenceFilter)
		LOG_BRAILLE = 0
		if LOG_BRAILLE:
			braille.pre_writeCells.register(self.ourBraillePreWriteCells)

	def ourBraillePreWriteCells(self, cells, rawText, currentCellCount):
		logInfo(f'braille: cells={cells}, rawText={rawText}, currentCellCount={currentCellCount}')

	def terminate(self):
		speech.extensions.filter_speechSequence.unregister(self.ourSpeechSequenceFilter)

	def ourSpeechSequenceFilter(self, origSeq: speech.SpeechSequence) -> speech.SpeechSequence:
		modSeq = []
		#logInfo(f'g_a11yTreeRoot: {g_a11yTreeRoot.name if g_a11yTreeRoot else None}') 
		#logInfo(f'a11yTree:\n{a11yTreeToStr(g_a11yTreeRoot)}') 
		hidingPlaceElemRef = [None]
		logInfo(f'original speech sequence: {origSeq}')
		for element in origSeq:
			if isinstance(element, str):
				#logInfo(f'patched synth got string len {len(element)}: "{element}"')
				logInfo(f'filter got string len {len(element)}: "{repr(element)}"')
				modSeq.extend(decodeAllStrs(element, hidingPlaceElemRef))
			else:
				modSeq.append(element)
		logInfo(f'modified speech sequence: {modSeq}')
		logInfo(f'speech sequence changed: {modSeq != origSeq}')
		return modSeq
	

