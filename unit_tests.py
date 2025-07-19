import sys, types, unittest, traceback
from unittest import mock

class BeepCommand: pass
class PitchCommand: pass
class VolumeCommand: pass
class RateCommand: pass
class LangChangeCommand: pass
class BreakCommand: pass

class CharacterModeCommand:
	def __init__(self, mode):
		self.mode = mode

	def __eq__(self, other):
		return isinstance(other, CharacterModeCommand) and self.mode == other.mode

	def __repr__(self):
		return f"CharacterModeCommand(mode={self.mode!r})"

class PhonemeCommand: pass
class IndexCommand: pass

mock_speech_commands = types.ModuleType("speech.commands")

mock_speech_commands.BeepCommand = BeepCommand
mock_speech_commands.PitchCommand = PitchCommand
mock_speech_commands.VolumeCommand = VolumeCommand
mock_speech_commands.RateCommand = RateCommand
mock_speech_commands.LangChangeCommand = LangChangeCommand
mock_speech_commands.BreakCommand = BreakCommand
mock_speech_commands.CharacterModeCommand = CharacterModeCommand
mock_speech_commands.PhonemeCommand = PhonemeCommand
mock_speech_commands.IndexCommand = IndexCommand

sys.modules["speech.commands"] = mock_speech_commands


class MockLog:
	def info(self, msg):
		print(f"[log info] {msg}")

	def exception(self, exc):
		print(f"[log exception]:")
		traceback.print_exception(type(exc), exc, exc.__traceback__, file=sys.stdout)
		print(f"[end log exception]")

mock_logHandler = types.ModuleType("logHandler")
mock_logHandler.log = MockLog()

sys.modules["logHandler"] = mock_logHandler


for mod in ["globalPluginHandler", "speech", "ui", "synthDriverHandler", "api", "speech", "speech.extensions", "braille", "controlTypes", "globalPluginHandler", "config", "scriptHandler", "ui"]:
	if mod not in sys.modules:
		sys.modules[mod] = unittest.mock.MagicMock()




sys.path.append('./addon/globalPlugins')
import data_ssml 

class Test1(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		pass

	def testTechniqueInlineSsmlSub(self):
		ssmlAsJson = '{"sub": {"alias": "100 prime"}}'
		encodedSsmlAsJson = "\u2064\u206b\u200d\u200d\u2064\u2060\u2064\ufeff\u2063\u200d\u200d\u200d\u2060\u206a\u200d\ufff9\u2064\u206b\u200d\u200d\u2063\u200c\u2063\u206c\u2063\ufffa\u2063\u200c\u2064\u2060\u200d\u200d\u2060\u206a\u200d\ufff9\u200d\u200d\u2060\u200c\u2060\ufff9\u2060\ufff9\u200d\ufff9\u2064\ufff9\u2064\u200d\u2063\ufffa\u2063\u206d\u2063\ufeff\u200d\u200d\u2064\u206d\u2064\u206d"
        
		decodedEncodedSsmlAsJson = data_ssml.decodeSingleStr(encodedSsmlAsJson)
		self.assertEqual(decodedEncodedSsmlAsJson, ssmlAsJson)
		
		start = data_ssml.MARKER; end = data_ssml.MARKER

		state = data_ssml.State()
		state.useCharacterModeCommand = True
		state.technique = 'inline'

		encoded = start + encodedSsmlAsJson + end + "11023456" + start + end
		decodedSpeechCommands = data_ssml.decodeAllStrs(encoded, state)
		self.assertEqual(decodedSpeechCommands, ["100 prime"])

		encoded = "preamble" + start + encodedSsmlAsJson + end + "123456" + start + end + "postamble"
		decodedSpeechCommands = data_ssml.decodeAllStrs(encoded, state)
		self.assertEqual(decodedSpeechCommands, ["preamble"+"100 prime"+"postamble"])

		encoded = "preamble1" + start + encodedSsmlAsJson + end + "123" + start + end + "between" + start + encodedSsmlAsJson + end + "456" + start + end + "postamble2"
		decodedSpeechCommands = data_ssml.decodeAllStrs(encoded, state)
		self.assertEqual(decodedSpeechCommands, ["preamble1"+"100 prime"+"between"+"100 prime"+"postamble2"])


	def testTechniqueInlineSsmlSayAs(self):
		ssmlAsJson = '{"say-as": {"interpret-as": "characters"}}'
		encodedSsmlAsJson = "\u2064\u206b\u200d\u200d\u2064\u2060\u2063\u200c\u2064\ufffa\u200d\u206d\u2063\u200c\u2064\u2060\u200d\u200d\u2060\u206a\u200d\ufff9\u2064\u206b\u200d\u200d\u2063\ufffa\u2063\u206e\u2064\u2061\u2063\ufeff\u2064\u200d\u2064\ufff9\u2064\u200d\u2063\ufeff\u2064\u2061\u200d\u206d\u2063\u200c\u2064\u2060\u200d\u200d\u2060\u206a\u200d\ufff9\u200d\u200d\u2063\u2060\u2063\ufffb\u2063\u200c\u2064\u200d\u2063\u200c\u2063\u2060\u2064\u2061\u2063\ufeff\u2064\u200d\u2064\u2060\u200d\u200d\u2064\u206d\u2064\u206d"
        
		decodedEncodedSsmlAsJson = data_ssml.decodeSingleStr(encodedSsmlAsJson)
		self.assertEqual(decodedEncodedSsmlAsJson, ssmlAsJson)
		
		start = data_ssml.MARKER; end = data_ssml.MARKER

		state = data_ssml.State()
		state.useCharacterModeCommand = True
		state.technique = 'inline'

		encoded = start + encodedSsmlAsJson + end + 'FAQ' + start + end
		decodedSpeechCommands = data_ssml.decodeAllStrs(encoded, state)
		self.assertEqual(decodedSpeechCommands, [CharacterModeCommand(True), 'FAQ', CharacterModeCommand(False)])

		encoded = start + encodedSsmlAsJson + end + 'faq' + start + end
		state.useCharacterModeCommand = False
		decodedSpeechCommands = data_ssml.decodeAllStrs(encoded, state)
		self.assertEqual(decodedSpeechCommands, [' f  eigh  q '])

		state.isLanguageEnglish = False
		decodedSpeechCommands = data_ssml.decodeAllStrs(encoded, state)
		self.assertEqual(decodedSpeechCommands, [' f  a  q '])
	



if __name__ == "__main__":
	
	unittest.main()




