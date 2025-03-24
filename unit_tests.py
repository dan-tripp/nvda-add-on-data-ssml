import sys, types, unittest, traceback
from unittest import mock

class Test1(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		mock_speech_commands = types.ModuleType("speech.commands")

		class BeepCommand: pass
		class PitchCommand: pass
		class VolumeCommand: pass
		class RateCommand: pass
		class LangChangeCommand: pass
		class BreakCommand: pass
		class CharacterModeCommand: pass
		class PhonemeCommand: pass
		class IndexCommand: pass

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


		for mod in [
			"globalPluginHandler", "speech", "ui", "synthDriverHandler"
		]:
			if mod not in sys.modules:
				sys.modules[mod] = unittest.mock.MagicMock()

		global data_ssml
		import data_ssml

	def test1(self):
		ssmlAsJson = "{\"sub\": {\"alias\": \"100 prime\"}}"
		encodedSsmlAsJson = "\u200c\u202d\u2060\u200c\ufff9\u2061\u202d\u200c\ufeff\u202c\ufeff\u2060\ufff9\u2061\u200d\u200c\ufff9\u202d\u200d\u200c\ufff9\ufff9\u202d\ufeff\u2061\u2061\u200d\u2060\ufff9\u200d\u202c\u202c\u200c\ufeff\u200c\u2060\ufff9\u200d\u202d\u200c\u2061\u2061\u200d\u200c\u202c\u2061\u200d\ufff9\ufff9\u2061\u200d\u200c\u2061\u200d\u2060\ufff9\ufff9\u202c\ufff9\u200c\ufff9\ufff9\u202d\ufff9\u200c\u202c\u200d\u2060\u200d\u200d\u202c\u202c\ufeff\u2061\ufeff\u200c\ufff9\u2061\u202d\u202c\ufeff\u202d\ufeff"
        
		decodedEncodedSsmlAsJson = data_ssml.decodeSingleStr(encodedSsmlAsJson)
		self.assertEqual(decodedEncodedSsmlAsJson, ssmlAsJson)
		
		start = data_ssml.START_MARKER; end = data_ssml.END_MARKER

		encoded = start + encodedSsmlAsJson + end + "123456" + start + end
		decodedSpeechCommands = data_ssml.decodeAllStrs(encoded)
		self.assertEqual(decodedSpeechCommands, ["100 prime"])

		encoded = "preamble" + start + encodedSsmlAsJson + end + "123456" + start + end + "postamble"
		decodedSpeechCommands = data_ssml.decodeAllStrs(encoded)
		self.assertEqual(decodedSpeechCommands, ["preamble", "100 prime", "postamble"])

		encoded = "preamble1" + start + encodedSsmlAsJson + end + "123" + start + end + "between" + start + encodedSsmlAsJson + end + "456" + start + end + "postamble2"
		decodedSpeechCommands = data_ssml.decodeAllStrs(encoded)
		self.assertEqual(decodedSpeechCommands, ["preamble1", "100 prime", "between", "100 prime", "postamble2"])




if __name__ == "__main__":
	unittest.main()




