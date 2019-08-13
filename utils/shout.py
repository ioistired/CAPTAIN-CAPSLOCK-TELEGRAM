import functools
import itertools
import re
from pathlib import Path
from sys import maxunicode

# if the amount of shadowing builtins that i do bothers you, please fix your syntax highlighter

def is_shout(str):
	words = (s for s in re.split(r'\b', str) if s.isalnum())
	stats = [is_shout for is_shout in map(is_shout_word, words) if is_shout is not None]
	return sum(stats) / len(stats) >= 0.5

def is_shout_word(word):
	length = len(word)
	count = 0

	for c in word:
		if c in DEFAULT_IGNORABLE:
			length -= 1
		if c in UPPERCASE_LETTERS:
			count += 1

	if length < 3:
		return None
	return count / length >= 0.9

properties_path = Path(__file__).parent.parent / 'data' / 'DerivedCoreProperties.txt'

def get_derived_core_properties():
	properties = {}

	with open(properties_path) as f:
		for property, range in parse_properties(f):
			properties.setdefault(property, set()).update(map(chr, range))

	return {property: frozenset(chars) for property, chars in properties.items()}

def get_derived_core_property(property):
	chars = set()
	desired = property

	with open(properties_path) as f:
		for property, range in parse_properties(f):
			if property == desired:
				chars.update(range)

	return frozenset(chars)

def parse_properties(f):
	for line in map(str.strip, f):
		if line.startswith('#') or not line:
			continue

		# ignore trailing comments too
		line = ''.join(itertools.takewhile(lambda c: c != '#', line))

		range, property = map(str.strip, line.split(';'))

		range = unicode_range_to_range(range)
		yield property, range

def unicode_range_to_range(range_str):
	return inclusive_range(*map(hex_to_int, range_str.split('..')))

hex_to_int = functools.partial(int, base=16)

def inclusive_range(start, stop=None, step=1):
	if stop is None:
		stop = start + 1
	else:
		stop += 1

	return range(start, start + 1 if stop is None else stop + 1, step)

UPPERCASE_LETTERS = frozenset(filter(str.isupper, map(chr, range(maxunicode + 1))))
DEFAULT_IGNORABLE = get_derived_core_property('Default_Ignorable_Code_Point')
