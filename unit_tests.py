import sys, types, unittest
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

		for mod in [
			"globalPluginHandler", "speech", "ui", "logHandler", "synthDriverHandler"
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

		encodedSsmlInMacroContext = data_ssml.START_MARKER + encodedSsmlAsJson + data_ssml.END_MARKER + "123456" + data_ssml.START_MARKER + data_ssml.END_MARKER
		decodedSpeechCommands = data_ssml.decodeAllStrs(encodedSsmlInMacroContext)
		self.assertEqual(decodedSpeechCommands, ["100 prime"])
        
        


if __name__ == "__main__":
	unittest.main()




