import html
import regex as re
import unicodedata
from smartypants import smartypants as smarten_quotes


CHINESE_WORD_RATIO = 1.5

re_sentence_sep_zh = re.compile(r'(?<=[。？！；])')
re_space_before_punct = re.compile(r' ([,\.\?!;，。？！；])')
re_chinese_char = re.compile(r'[\p{Han}]')
re_halfwidth_punct_after_chinese = re.compile(r'([\p{Han}])([,.;:?!])')
chinese_punct_replacement = str.maketrans(',.;:?!', '，。；：？！')
re_banned_chars_en = re.compile(r'[^\p{Common}\p{Latin}\p{Greek}\p{General_Punctuation}\p{Superscripts_And_Subscripts}\p{Currency_Symbols}]')
re_banned_chars_zh = re.compile(r'[^\p{Han}\p{Common}\p{Latin}\p{Greek}\p{General_Punctuation}\p{Superscripts_And_Subscripts}\p{Currency_Symbols}]')

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

	'.',
	'%',
	',',
	'#'
}
CHINESE_PUNCT_WITH_SPECIAL_NAME = {
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
	'·'
}
IN_WORD_PUNCT = {"'", '-', '’'}

def is_whitespace(c: str) -> bool:
	category = unicodedata.category(c)
	return category[0] == 'Z' or category == 'Cc'


def is_punct(c: str) -> bool:
	return unicodedata.category(c).startswith('P')


def is_chinese_char(c: str) -> bool:
	return re_chinese_char.match(c) is not None


def is_chinese_punct(c: str) -> bool:
	if c in COMMON_PUNCT or c in CHINESE_PUNCT_WITH_SPECIAL_NAME:
		return True

	try:
		name = unicodedata.name(c)
	except ValueError:
		return False
	
	return is_punct(c) and (name.startswith('IDEOGRAPHIC') or name.startswith('FULLWIDTH'))


def is_chinese(c: str) -> bool:
	return is_chinese_char(c) or is_chinese_punct(c)


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
	s = smarten_quotes(s)
	s = html.unescape(s)
	buf = []
	i = 0

	while i < len(s):
		if is_chinese(s[i]):
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

	return ''.join(buf)


def split_into_words(text: str) -> list[str]:
	words = []
	buf = []
	for c in text:
		if is_whitespace(c):
			if len(buf) > 0:
				words.append(''.join(buf))
				buf.clear()
		elif is_chinese(c):
			if len(buf) > 0:
				words.append(''.join(buf))
				buf.clear()
			words.append(c)
		else:
			buf.append(c)
	if len(buf) > 0:
		words.append(''.join(buf))

	return words


def is_predominantly_chinese(text: str) -> bool:
	tokens = split_into_words(text)
	chinese_count = 0
	english_count = 0
	for token in tokens:
		if all(c.isdigit() or is_punct(c) for c in token):
			continue
		elif any(is_chinese_char(c) for c in token):
			chinese_count += 1
		else:
			english_count += 1

	return chinese_count > CHINESE_WORD_RATIO * english_count


def split_into_sentences_zh(text: str) -> list[str]:
	for match in re_halfwidth_punct_after_chinese.finditer(text):
		text = text[:match.start(2)] + match.group(2).translate(chinese_punct_replacement) + text[match.end(2):]
	return [s_stripped for s in re_sentence_sep_zh.split(text) if (s_stripped := s.strip())]


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
