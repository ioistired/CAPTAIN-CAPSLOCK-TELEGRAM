#!/usr/bin/env python

import unicodedata

from utils.shout import is_shout

assert not is_shout('W')
assert not is_shout('')
assert not is_shout('\u200b' * 10)
assert not is_shout('PR it')
assert not is_shout('hello 10 GiB')
assert not is_shout('I shall')
assert not is_shout('Ok')
assert not is_shout('OK')
assert not is_shout('XD')
assert not is_shout('8)')
assert not is_shout('8D')
assert not is_shout('DX')
assert not is_shout('X-D')
assert not is_shout('D-X')
assert not is_shout('XP')
assert not is_shout('X-P')
assert not is_shout(';D')
assert not is_shout('OwO')
assert not is_shout('UwU')
assert not is_shout('66666666666666666666666 🅱')

assert is_shout('tfw MANUALLY_INITIATED_CRASH')
assert is_shout(''.join(unicodedata.lookup('NEGATIVE SQUARED LATIN CAPITAL LETTER ' + c) for c in 'LONEBOY'))
assert is_shout('I SHALL')
assert is_shout('PR IT')
assert is_shout('F U')
assert is_shout('FU')
assert is_shout('you went to college to be a WELL EDUCATED CITIZEN OF THE WORLD, nick')
assert is_shout('🅱️🅱️🅱️')
