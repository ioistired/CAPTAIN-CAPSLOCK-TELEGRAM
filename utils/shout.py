import functools
import itertools
import re
from sys import maxunicode

codeblock = re.compile(r'(`{1,3}).+?\\1', re.DOTALL)

def is_shout(str):
	str = codeblock.sub(str, '')

	length = len(str)
	count = 0

	for c in str:
		if c in DEFAULT_IGNORABLE:
			length -= 1
		if c in UPPERCASE_LETTERS:
			count += 1

	return length >= 4 and count / length > 0.5

def get_derived_core_properties():
	properties = {}

	with open('data/DerivedCoreProperties.txt') as f:
		for line in map(str.strip, f):
			if line.startswith('#') or not line:
				continue
			# ignore trailing comments too
			line = ''.join(itertools.takewhile(lambda c: c != '#', line))

			range, property = map(str.strip, line.split(';'))
			range = unicode_range_to_range(range)

			properties.setdefault(property, set()).update(map(chr, range))

	return {property: frozenset(chars) for property, chars in properties.items()}

def unicode_range_to_range(line):
	range_str = line.split()[0]
	return inclusive_range(*map(hex_to_int, range_str.split('..')))

hex_to_int = functools.partial(int, base=16)

def inclusive_range(start, stop=None, step=1):
	if stop is None:
		stop = start + 1
	else:
		stop += 1

	return range(start, stop, step)

UPPERCASE_LETTERS = frozenset(filter(str.isupper, map(chr, range(maxunicode+1))))
DERIVED_CORE_PROPERTIES = get_derived_core_properties()
DEFAULT_IGNORABLE = DERIVED_CORE_PROPERTIES['Default_Ignorable_Code_Point']
del DERIVED_CORE_PROPERTIES  # comment if you need that, but we wanna save space
