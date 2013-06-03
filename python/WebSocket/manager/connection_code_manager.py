import os
from model.words import Words

class ConnectionCodeManager:

	USE_WORDS = True

	# if os.path.dirname(os.path.abspath(__file__)).find('/dev/') != -1 or os.path.dirname(os.path.abspath(__file__)).find('/test/') != -1:
		# USE_WORDS = False

	print 'using words: %s' % USE_WORDS

	@staticmethod
	def to_word(code):
		return Words.ALL[(int(code) % len(Words.ALL))]

	@staticmethod
	def from_word(word):
		return Words.ALL.index(word)