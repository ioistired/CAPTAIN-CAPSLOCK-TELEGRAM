#!/usr/bin/env python3

import sys

from utils.shout import is_shout

while True:
	try:
		sentence = input('📣 ')
	except (KeyboardInterrupt, EOFError):
		break

	if not sys.stdin.isatty():
		print(sentence)
	print(is_shout(eval(sentence)))
