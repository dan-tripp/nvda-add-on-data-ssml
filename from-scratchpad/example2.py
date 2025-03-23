# Developer guide example 3

import datetime, re, base64
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




# Matches the javascript encoding side.  If you change that then change this, and vice versa. 
START_MARKER = '\u2060\u2062\u2063'
END_MARKER = '\u2063\u2062\u2060'
ZERO_CHAR = '\u200C'
ONE_CHAR = '\u200D'

def decodeSsmlZeroWidthCharsBinary(str_):
	results = []
	start_index = 0

	while True:
		start_pos = str_.find(START_MARKER, start_index)
		if start_pos == -1:
			break
		start_pos += len(START_MARKER)
		end_pos = str_.find(END_MARKER, start_pos)
		if end_pos == -1:
			break

		encoded = str_[start_pos:end_pos]
		if encoded:
			bits = ''.join('0' if c == ZERO_CHAR else '1' for c in encoded)
			byte_values = [int(bits[i:i+8], 2) for i in range(0, len(bits), 8)]
			decoded_str = bytes(byte_values).decode('utf-8')
			results.append(decoded_str)

		start_index = end_pos + len(END_MARKER)

	return results


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


def decodeAllStrsOctal(str_):
	START_MARKER_OCTAL = '\u2062\u2063'
	END_MARKER_OCTAL = '\u2063\u2062'

	if 1: # tdr 
		if (START_MARKER_OCTAL in str_) != (END_MARKER_OCTAL in str_):
			logInfo('markers bad')
		elif (START_MARKER_OCTAL in str_) and (END_MARKER_OCTAL in str_):
			pass
			#logInfo('markers good')
		else:
			pass

	results = []
	start_index = 0

	while True:
		start_pos = str_.find(START_MARKER_OCTAL, start_index)
		if start_pos == -1:
			break
		start_pos += len(START_MARKER_OCTAL)
		end_pos = str_.find(END_MARKER_OCTAL, start_pos)
		if end_pos == -1:
			break

		encoded_block = str_[start_pos:end_pos]
		if encoded_block:
			try:
				decoded = decodeSingleStrOctal(encoded_block)
				results.append(decoded)
			except Exception as e:
				results.append(f"[decode error: error: {e}, encoded string: '{encoded_block}' ]")
				log.exception(e)

		start_index = end_pos + len(END_MARKER_OCTAL)

	return results


# Matches the javascript encoding side.  If you change that then change this, and vice versa. 
START_MARKER_RE = '\[ssml-start\]'
END_MARKER_RE = '\[ssml-end\]'

def decodeSsmlEncodedAsBase64(str_):
    decoded_payloads = []
    pattern = re.compile(f'{START_MARKER_RE}(.*?){END_MARKER_RE}')
    
    for match in pattern.finditer(str_):
        base64_str = match.group(1)
        try:
            decoded_bytes = base64.b64decode(base64_str)
            decoded_text = decoded_bytes.decode('utf-8')
            decoded_payloads.append(decoded_text)
        except Exception as e:
            decoded_payloads.append(f"[decode error: {e}]")

    return decoded_payloads


original_synth_speak = synthDriverHandler.getSynth().speak

def custom_synth_speak(speechSequence, *args, **kwargs):
	#logInfo(f'here 2. {str(speechSequence)}')
	modified_sequence = []
	for element in speechSequence:
		if isinstance(element, str):
			USE_BASE64 = 0
			if USE_BASE64:
				dataSsmls = decodeSsmlEncodedAsBase64(element)
			else:
				#dataSsmls = decodeSsmlZeroWidthCharsBinary(element)
				dataSsmls = decodeAllStrsOctal(element)
			#logInfo(f'here 3: string "{element}" => ssmls {dataSsmls}')
			#logInfo(f'here 4: str len "{len(element)}"')
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






