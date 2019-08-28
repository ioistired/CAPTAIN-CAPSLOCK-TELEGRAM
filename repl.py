#!/usr/bin/env python3

from utils.shout import is_shout

while True:
	try:
		sentence = input('📣 ')
	except (KeyboardInterrupt, EOFError):
		break

	print(is_shout(eval(sentence)))
