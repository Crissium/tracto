import regex as re
import unicodedata


CHINESE_WORD_RATIO = 1.5

re_sentence_sep_zh = re.compile(r'(?<=[。？！；])')
re_space_before_punct = re.compile(r' ([,\.\?!:;，。？！：；])')
re_no_space_after_punct_en = re.compile(r'([,\.\?!:;%&\)\}\]])([\p{Latin}\p{Greek}])')
re_chinese_char = re.compile(r'[\p{Han}]')
re_halfwidth_punct_after_chinese = re.compile(r'([\p{Han}])([,.;:?!])')
chinese_punct_replacement = str.maketrans(',.;:?!', '，。；：？！')
re_banned_chars_en = re.compile(r'[^\p{Common}\p{Latin}\p{Greek}\p{General_Punctuation}\p{Superscripts_And_Subscripts}\p{Currency_Symbols}]')
re_banned_chars_zh = re.compile(r'[^\p{Han}\p{Common}\p{Latin}\p{Greek}\p{General_Punctuation}\p{Superscripts_And_Subscripts}\p{Currency_Symbols}]')
re_punct_symbol_except_hyphen_and_apostrophe = re.compile(
	# Match any punctuation or symbol
	r"[\p{P}\p{S}]"
	+
	# But exclude these exceptions
	r"(?<!"
	+
	# Not apostrophes, hyphens, or percent signs
	r"[''\-%]"
	+
	r"|"
	+
	# Not commas between digits
	r"(?<=\d),(?=\d)"
	+
	r"|"
	+
	# Not periods between digits or at start of decimal
	r"(?<=\d)\.(?=\d)"
	+
	r"|"
	+
	r"(?<=^|\s)\.(?=\d)"
	+
	r"|"
	+
	# Not currency symbols before digits
	r"(?<=\p{Sc})(?=\d)"
	+
	r")"
)

COMMON_PUNCT = {
	'“',
	'”',
	'‘',
	'’',

	# TODO: Chinese only uses exactly two consecutive ellipsis/em-dash characters
	'…',
	'—',

	'-',
	'‐',

	# TODO: Chinese only uses the following punctuation for numbers
	'.',
	'%',
	',',
	'#'
}
EXCLUSIVELY_CHINESE_PUNCT = {
	'，',
	'、',
	'。',
	'：',
	'；',
	'？',
	'！',
	'（',
	'）',
	'〈',
	'〉',
	'《',
	'》',
	'「',
	'」',
	'『',
	'』',
	'【',
	'】',
	'〔',
	'〕',
	'〖',
	'〗',
	'·',
	'～'
}
IN_WORD_PUNCT = {"'", '-', '‐', '’'}



def is_whitespace(c: str) -> bool:
	category = unicodedata.category(c)
	return category[0] == 'Z' or category == 'Cc'


def is_punct(c: str) -> bool:
	category = unicodedata.category(c)
	return category[0] == 'P' or category == 'Sc'


def is_symbol(c: str) -> bool:
	return unicodedata.category(c)[0] == 'S'


def is_chinese_char(c: str) -> bool:
	return re_chinese_char.match(c) is not None


def is_chinese_punct(c: str) -> bool:
	return c in COMMON_PUNCT or c in EXCLUSIVELY_CHINESE_PUNCT


def is_chinese(c: str, strict: bool = False) -> bool:
	if strict:
		return is_chinese_char(c) or c in EXCLUSIVELY_CHINESE_PUNCT
	else:
		return is_chinese_char(c) or is_chinese_punct(c)


def is_letter(c: str) -> bool:
	return unicodedata.category(c) in ('Lu', 'Ll', 'Lt', 'Lm')


def has_case(c: str) -> bool:
	return unicodedata.category(c) in ('Lu', 'Ll')


def compress_whitespace(s: str) -> str:
	buf = []
	i = 0
	while i < len(s) and is_whitespace(s[i]):
		i += 1
	while i < len(s):
		if is_whitespace(s[i]):
			buf.append(' ')
			while i < len(s) and is_whitespace(s[i]):
				i += 1
		else:
			buf.append(s[i])
			i += 1
	if len(buf) > 0 and buf[-1] == ' ':
		buf.pop()

	return re_space_before_punct.sub(r'\1', ''.join(buf))


def normalise_whitespace(s: str, add_space_between_en_zh: bool = True) -> str:
	s = compress_whitespace(s)
	buf = []
	i = 0

	while i < len(s):
		if is_chinese(s[i], True):
			if is_chinese_char(s[i]):
				if add_space_between_en_zh and len(buf) > 0 and not is_whitespace(buf[-1]) and not is_chinese(buf[-1]) and buf[-1] not in IN_WORD_PUNCT:
					buf.append(' ')
				elif not add_space_between_en_zh and len(buf) > 0 and is_whitespace(buf[-1]):
					buf.pop()
			else:
				while len(buf) > 0 and is_whitespace(buf[-1]) and s[i] not in IN_WORD_PUNCT:
					buf.pop()

			buf.append(s[i])
			i += 1
			while i < len(s) and is_whitespace(s[i]):
				i += 1
		else:
			if add_space_between_en_zh and len(buf) > 0 and is_chinese(buf[-1]) and not is_chinese_punct(buf[-1]):
				buf.append(' ')

			buf.append(s[i])
			i += 1

	return re_no_space_after_punct_en.sub(r'\1 \2', ''.join(buf))
	# return ''.join(buf)


def split_into_words(text: str, include_punct: bool = True) -> list[str]:
	words = []
	buf = []
	for c in text:
		if is_whitespace(c):
			if len(buf) > 0:
				words.append(''.join(buf))
				buf.clear()
		elif not c in IN_WORD_PUNCT and (is_punct(c) or is_symbol(c)):
			if len(buf) > 0:
				words.append(''.join(buf))
				buf.clear()
			if include_punct:
				words.append(c)
		elif not c in IN_WORD_PUNCT and is_chinese(c):
			if len(buf) > 0:
				words.append(''.join(buf))
				buf.clear()
			words.append(c)
		else:
			buf.append(c)
	if len(buf) > 0:
		words.append(''.join(buf))

	return words


def is_predominantly_chinese(text: str = '', words: list[str] = []) -> bool:
	if len(words) == 0:
		words = split_into_words(text)
	chinese_count = 0
	english_count = 0
	for word in words:
		if all(c.isdigit() or is_punct(c) for c in word):
			continue
		elif any(is_chinese_char(c) for c in word):
			chinese_count += 1
		else:
			english_count += 1

	return chinese_count > CHINESE_WORD_RATIO * english_count


def split_into_sentences_zh(text: str) -> list[str]:
	for match in re_halfwidth_punct_after_chinese.finditer(text):
		text = text[:match.start(2)] + match.group(2).translate(chinese_punct_replacement) + text[match.end(2):]
	return [s_stripped for s in re_sentence_sep_zh.split(text) if (s_stripped := s.strip())]


def join_sentences(sentences: list[str]) -> str:
	buf = []
	for i, s in enumerate(sentences):
		s = s.strip()
		if i == 0 or (is_chinese(sentences[i - 1][-1], True) and is_chinese(s[0], True)):
			buf.append(s)
		else:
			buf.append(' ' + s)
	return ''.join(buf)


def beautify_en(text: str) -> str:
	text = re_banned_chars_en.sub('', text)
	text = normalise_whitespace(text)
	return text


def beautify_zh(text: str, normalises_whitespace: bool = True) -> str:
	for match in re_halfwidth_punct_after_chinese.finditer(text):
		text = text[:match.start(2)] + match.group(2).translate(chinese_punct_replacement) + text[match.end(2):]
	text = text.replace('(', '（').replace(')', '）')
	text = re_banned_chars_zh.sub('', text)
	if normalises_whitespace:
		text = normalise_whitespace(text)
	else:
		text = compress_whitespace(text)
	return text
