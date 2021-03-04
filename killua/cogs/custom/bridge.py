from asyncio import run_coroutine_threadsafe, get_event_loop
from numpy import uint32
from typing import Any, cast
from .wasm import WASMApi, WASMPointer, WASMSlice, wasm_function

class Bridge(WASMApi):
	message: Any
	content: Any

	def __init__(self):
		super().__init__("env")
		self.message = None
		self.content = None

	@wasm_function
	def message_reply(self, message: WASMSlice):
		loop = get_event_loop()
		coroutine = self.message.reply("".join([chr(cast(int, char)) for char in message.buf[:message.buf_len]]))
		run_coroutine_threadsafe(coroutine, loop)

	@wasm_function
	def context_read_code(self, buf: WASMPointer) -> uint32:
		if len(self.content) > 2000:
			raise Exception("too large")
		buf[:len(self.content)] = [ord(char) for char in self.content]
		return uint32(len(self.content))
