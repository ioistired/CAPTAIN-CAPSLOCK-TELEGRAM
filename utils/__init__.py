import asyncio
import inspect
import subprocess
import traceback
from functools import wraps

from telethon import tl
from telethon.helpers import add_surrogate

from . import shout

def ensure_corofunc(f):
	if inspect.iscoroutinefunction(f):
		return f

	@wraps(f)
	async def wrapped(*args, **kwargs):
		return f(*args, **kwargs)

	return wrapped

# modified from jishaku/exception_handling.py @ 1.18.2
# © 2019 Devon (Gorialis) R
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

async def send_traceback(message, verbosity: int, *exc_info):
	"""
	Sends a traceback of an exception to a destination.
	Used when REPL fails for any reason.

	:param message: What message to reply to with this information
	:param verbosity: How far back this traceback should go. 0 shows just the last stack. None shows all.
	:param exc_info: Information about this exception, from sys.exc_info or similar.
	:return: The last message sent
	"""
	traceback_content = "".join(traceback.format_exception(*exc_info, verbosity))

	def code_converter(content):
		content = content.strip()
		return content, [tl.types.MessageEntityCode(offset=0, length=len(add_surrogate(content)))]

	return await message.reply(traceback_content, parse_mode=code_converter)

class ReplExceptionCatcher:  # pylint: disable=too-few-public-methods
	def __init__(self, message):
		self.message = message

	async def __aenter__(self):
		return None

	async def __aexit__(self, exc_type, exc_val, exc_tb):
		# nothing went wrong, who cares lol
		if not exc_val:
			return

		if isinstance(exc_val, (SyntaxError, asyncio.TimeoutError, subprocess.TimeoutExpired)):
			limit = 0
		else:
			limit = None

		await send_traceback(self.message, limit, exc_type, exc_val, exc_tb)
		return True	 # the exception has been handled
