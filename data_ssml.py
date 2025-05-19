
PROFILE = True

import datetime, re, base64, json, time
import globalPluginHandler
from logHandler import log
import speech
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
			phonemeIpa = val
			r = [PhonemeCommand(phonemeIpa, text=nonSsmlStr_)]
			INSERT_HACK_PAUSE_AFTER = 1
			if INSERT_HACK_PAUSE_AFTER:
				# inspired by 1) the line in MathCAT.py which says "There needs to be a space after the phoneme command" (a comment I don't understand), 2) by my aural observation that NVDA's announcement sounded like "woundlink" (i.e. with no space).
				# hard to say if the cure is worse than the disease here.  without it: "lead" is too fast.  with it: "tear" is too slow. 
				r.insert(0, RateCommand(-30))
				r.append(RateCommand(0))
		else:
			raise SsmlError()
	except (json.decoder.JSONDecodeError, SsmlError, KeyError) as e:
		r = [origWholeUnmodifiedText_]
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

# This function lazy-calls on findHidingPlaceElementInA11yTree() b/c it takes ~ 13 ms per call.  this amounts to calling that function only for parts of a web page which have our encoded data-ssml. 
@profile
def decodeAllStrs(str_, hidingPlaceElemRef_):
	assert(isinstance(hidingPlaceElemRef_, list) and len(hidingPlaceElemRef_) == 1)
	logInfo(f'decodeAllStrs input (len {len(str_)}): {repr(str_)}')
 
	r = []
	lastEnd = 0
	matchCount = 0

	for match in pattern.finditer(str_):
		matchCount += 1
		start, end = match.span()
		encodedSsmlIndexInGlobalList, textToAffect = match.groups()
		origWholeUnmodifiedText = match.group(0)

		logInfo(f'encodedSsmlIndexInGlobalList: {repr(encodedSsmlIndexInGlobalList)}')
		logInfo(f'nonSsmlStr (len {len(textToAffect)}): {repr(textToAffect)}')

		if start > lastEnd:
			pre = str_[lastEnd:start]
			logInfo(f'	plain text before match: {repr(pre)}')
			r.append(pre)

		success = False
		try:
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
		except (Exception, IndexError) as e:
			logInfo(f"Couldn't decode or figure out what to do with string '{encodedSsmlIndexInGlobalList}'.  Will use unmodified text.")
			if 0:
				log.exception(e)
				logInfo(f'	encoded string (raw): {repr(encodedSsmlIndexInGlobalList)}')
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
		r = [''.join(r)]

	return r

def getGlobalListFromHidingPlaceElem(hidingPlaceElem_):
	assert hidingPlaceElem_
	hidingPlaceElemTextContent = hidingPlaceElem_.name
	HIDING_PLACE_GUID = '4b9b696c-8fc8-49ca-9bb9-73afc9bd95f7'
	pattern = rf'{HIDING_PLACE_GUID}\s*(\[.*?\])'
	match = re.search(pattern, hidingPlaceElemTextContent)
	if not match: return None
	globalListStr = match.group(1)
	globalListObj = json.loads(globalListStr)
	return globalListObj

g_lastSynthPatched = None

def patchCurrentSynth():
	currentSynthOrigSpeakFunc = synthDriverHandler.getSynth().speak
	@profile
	def patchedSpeakFunc(speechSequence, *args, **kwargs):
		modifiedSpeechSequence = []
		#logInfo(f'g_a11yTreeRoot: {g_a11yTreeRoot.name if g_a11yTreeRoot else None}') 
		#logInfo(f'a11yTree:\n{a11yTreeToStr(g_a11yTreeRoot)}') 
		hidingPlaceElemRef = [None]
		logInfo(f'original speech sequence: {speechSequence}')
		for element in speechSequence:
			if isinstance(element, str):
				#logInfo(f'patched synth got string len {len(element)}: "{element}"')
				logInfo(f'patched synth got string len {len(element)}: "{repr(element)}"')
				modifiedSpeechSequence.extend(decodeAllStrs(element, hidingPlaceElemRef))
			else:
				modifiedSpeechSequence.append(element)
		logInfo(f'modified speech sequence: {modifiedSpeechSequence}')
		logInfo(f'speech sequence changed: {modifiedSpeechSequence != speechSequence}')
		return currentSynthOrigSpeakFunc(modifiedSpeechSequence, *args, **kwargs)
	synthDriverHandler.getSynth().speak = patchedSpeakFunc

def patchCurrentSynthIfNecessary():
	global g_lastSynthPatched
	currentSynth = synthDriverHandler.getSynth()
	if currentSynth != g_lastSynthPatched:
		logInfo(f'patching synth "{currentSynth}".')
		g_lastSynthPatched = currentSynth
		patchCurrentSynth()
	else:
		# it's unclear to me if this will ever happen. 
		logInfo(f'patch of synth "{currentSynth}" not necessary.')

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

def patchedSpeakTextInfo(info, *args, **kwargs):
	global g_a11yTreeRoot
	nvdaObjectAtStart = info.NVDAObjectAtStart
	a11yTreeRoot = nvdaObjectAtStart.treeInterceptor.rootNVDAObject
	g_a11yTreeRoot = a11yTreeRoot
	return g_original_speakTextInfo(info, *args, **kwargs)

def patchSpeakTextInfoFunc():
	speech.speakTextInfo = patchedSpeakTextInfo

class GlobalPlugin(globalPluginHandler.GlobalPlugin):

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		synthDriverHandler.synthChanged.register(self.onSynthChanged) 
		patchCurrentSynthIfNecessary()
		patchSpeakTextInfoFunc()

	def onSynthChanged(self, *args, **kwargs):
		logInfo('synth changed.')
		patchCurrentSynthIfNecessary()
		
