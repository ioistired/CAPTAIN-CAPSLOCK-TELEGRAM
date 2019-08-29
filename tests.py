#!/usr/bin/env python

from pathlib import Path

from utils.shout import is_shout

assert not is_shout('W')
assert not is_shout('')
assert not is_shout('\u200b' * 10)
assert not is_shout('PR it')
assert not is_shout('hello 10 GiB')
assert not is_shout('I shall')

with open(Path(__file__).parent / 'shouts.txt') as f:
	for line in map(str.strip, f):
		if not line.startswith('#'):
			assert is_shout(eval(line)), line
