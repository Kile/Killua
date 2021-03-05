from .sandbox import WASI
from .wasm import WASMApi, WASMPointer, WASMSlice, wasm_function
from asyncio import Event, get_event_loop
from discord.ext.commands import Cog as CommandCog, command
from multiprocessing import Pipe, Process
from multiprocessing.connection import Connection
from numpy import uint32
from re import compile
from typing import Any, cast
from wasmer import ImportObject, Instance, Module, Store, engine
from wasmer_compiler_cranelift import Compiler

wasm_file = "python-sandbox/target/wasm32-wasi/debug/python_sandbox.wasm"
code_regex = compile(r"^```(?:\w+\n(?!\s*```))?((?:(?!```)(?!(?<=`)``)(?!(?<=``)`)[\w\W])*?)```$")

def sandbox_bootstrap(bridge: Connection, data: bytearray, code: str):
	with bridge:
		store = Store(engine.JIT(Compiler))
		# SAFETY: This data is from Custom.custom.
		module = Module.deserialize(store, data)

		imports = ImportObject()
		wasi_interface = WASI(True)
		wasi_interface.register(store, imports)
		bridge_interface = Bridge(code, bridge)
		bridge_interface.register(store, imports)

		instance = Instance(module, imports)
		wasi_interface.set_memory(instance.exports.memory)
		bridge_interface.set_memory(instance.exports.memory)

		try:
			instance.exports.run(0, 0)
		except RuntimeError as fatal:
			pass # TODO

class IOAvailability:
	def __init__(self, fd: int, ty="read"):
		self.fd = fd
		self.read = True if ty == "read" else False

	async def __aenter__(self):
		event = Event()
		loop = get_event_loop()

		if self.read:
			loop.add_reader(self.fd, event.set)
		else:
			loop.add_writer(self.fd, event.set)

		await event.wait()
		event.clear()

	async def __aexit__(self, err_ty, err, tb):
		pass

class APIReply:
	def __init__(self, message: str):
		self.message = message

class Bridge(WASMApi):
	code: str
	pipe: Connection

	def __init__(self, code: str, pipe: Any):
		super().__init__("env")
		self.code = code
		self.pipe = pipe

	@wasm_function
	def message_reply(self, msg: WASMSlice):
		message = "".join([chr(cast(int, char)) for char in msg.buf[:msg.buf_len]])
		self.pipe.send(APIReply(message))

	@wasm_function
	def context_read_code(self, buf: WASMPointer) -> uint32:
		length = len(self.code)
		if length > 2000:
			raise Exception("too large")

		buf[:length] = [ord(char) for char in self.code]
		return uint32(length)

class Custom(CommandCog):
	def __init__(self, client):
		self.client = client

		store = Store(engine.JIT(Compiler))
		self.module = Module(store, open(wasm_file, "rb").read())

	@command()
	async def custom_debug(self, context, *, code):
		bridge, client = Pipe(False)
		module = self.module.serialize()

		if (match := code_regex.match(code)) is not None:
			code = match[1]

		print(code)
		process = Process(target=sandbox_bootstrap,
			args=(client, module, code))
		process.start()

		try:
			while True:
				async with IOAvailability(bridge.fileno()):
					data = bridge.recv()

					# I really miss Rust enums right about now.
					if isinstance(data, APIReply):
						await context.message.reply(data.message)
					else:
						raise Exception("bad message")
		except EOFError:
			print("PASS")

Cog = Custom
