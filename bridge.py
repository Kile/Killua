from typing import cast
from wasm import WASMApi, WASMSlice, wasm_function

class Bridge(WASMApi):
	def __init__(self):
		super().__init__("env")

	@wasm_function
	def message_reply(self, message: WASMSlice):
		print("".join([chr(cast(int, char)) for char in message.buf[:message.buf_len]]))
