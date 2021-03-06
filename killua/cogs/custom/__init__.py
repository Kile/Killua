from . import api as API
from .pipe import DataPipe, PipeClosedError, half_async_duplex
from .sandbox import WASI
from .wasm import WASMApi, WASMPointer, WASMSlice, wasm_function
from discord import TextChannel
from discord.ext.commands import Cog as CommandCog, command
from multiprocessing import Process
from numpy import uint8, uint32, uint64
from os import getpid, kill
from re import compile
from signal import SIGKILL
from sys import stderr
from time import perf_counter_ns
from typing import cast
from wasmer import ImportObject, Instance, Module, Store, engine
from wasmer_compiler_cranelift import Compiler

wasm_file = "python-sandbox/target/wasm32-wasi/debug/python_sandbox.wasm"
code_regex = compile(r"^```(?:\w+\n(?!\s*```))?((?:(?!```)(?!(?<=`)``)(?!(?<=``)`)[\w\W])*?)```$")

def sandbox_bootstrap(bridge: DataPipe, module_data: bytearray, code: str,
		guild_id: int, channel_id: int, message_id: int):
	with bridge:
		store = Store(engine.JIT(Compiler))
		# SAFETY: This data is from Custom.custom.
		module = Module.deserialize(store, module_data)

		imports = ImportObject()
		wasi_interface = WASI(True)
		wasi_interface.register(store, imports)
		bridge_interface = Bridge(bridge, code, guild_id, channel_id, message_id)
		bridge_interface.register(store, imports)

		instance = Instance(module, imports)
		wasi_interface.set_memory(instance.exports.memory)
		bridge_interface.set_memory(instance.exports.memory)

		try:
			instance.exports.main(0, 0)
		except RuntimeError as fatal:
			import traceback
			print(fatal)
			pass # TODO

class Bridge(WASMApi):
	pipe: DataPipe
	code: str
	guild_id: int
	channel_id: int
	message_id: int

	def __init__(self, pipe: DataPipe, code: str, guild_id: int, channel_id: int,
			message_id: int):
		super().__init__("discord_bridge")
		self.pipe = pipe
		self.code = code
		self.guild_id = guild_id
		self.channel_id = channel_id
		self.message_id = message_id

	@wasm_function
	def message_send(self, msg: WASMSlice, channel: uint64, reply: uint64,
			id: WASMPointer) -> uint32:
		"""Sends a message.

		Parameters
		----------
		#1: &str, Immutable pointer to message data.
		#2: u64, ID of the channel to send to.
		#3: u64, ID of the message to reply to, or 0.
		#4: &mut u64, Pointer to write the ID of the new message.

		Returns
		-------
		#1: u8, Error number.
			0 for success.
			1 for message too long.
			2 for channel doesn't exist.
			3 for replied to message doesn't exist.
			4 for insufficient permissions.
			5 for unknown.
		"""

		# Read message.
		message = "".join([chr(cast(int, char)) for char in msg.buf[:msg.buf_len]])

		# Pre flight checks.
		if len(message) > 2000:
			return uint8(1)

		# Send message, wait for a reply.
		self.pipe.send(API.MessageSend(message, int(channel), int(reply)))
		response = self.pipe.recv()
		if isinstance(response, API.MessageSendAcknowledge):
			id.write(uint64(response.id))
			return uint32(0)
		elif isinstance(response, API.MessageTooLargeError):
			return uint32(1)
		elif isinstance(response, API.UnknownTextChannelIdError):
			return uint32(2)
		elif isinstance(response, API.UnknownMessageIdError):
			return uint32(3)
		elif isinstance(response, API.InsufficientPermissionsError):
			return uint32(4)
		else:
			return uint32(5)

	@wasm_function
	def context_environment(self, env: WASMPointer):
		"""Returns the Discord environment.

		Parameters
		-------
		#1: u64, ID of the guild.
		#2: u64, ID of the channel this interaction is in.
		#3: u64, ID of the message this interaction is triggered from.
		"""

		env.write((uint64(self.guild_id), uint64(self.channel_id), \
			uint64(self.message_id)), tuple[uint64, uint64, uint64])

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
		if (match := code_regex.match(code)) is not None:
			code = match[1]

		client, bridge = await half_async_duplex()
		module = self.module.serialize()
		process = Process(target=sandbox_bootstrap, args=(client, module, code,
			context.guild.id, context.channel.id, context.message.id))
		process.start()

		now = perf_counter_ns()
		async with bridge:
			while True:
				data = await bridge.recv()

				# I really miss Rust enums right about now.
				if isinstance(data, API.MessageSend):
					channel = context.guild.get_channel(data.channel_id)
					if channel is None or not isinstance(channel, TextChannel):
						await bridge.send(API.UnknownTextChannelIdError)
						continue

					reply = None if data.reply_id == 0 else data.reply_id
					message = await channel.send(data.message, reference=reply)
					await bridge.send(API.MessageSendAcknowledge(message.id))
				else:
					# Our implementation only sends these messages, and although there
					# could be a chance that the pipe becomes broken through natural
					# means, chances are probably more likely that someone has found a
					# security issue in Wasmer, and has exploited it to escape the WASM
					# virtual machine.

					print(f"""SECURITY ERROR, WASM EXECUTION THREAD HAS SENT AN ILLEGAL VALUE.
CAUSED BY MESSAGE THE FOLLOWING MESSAGE.
{context.message}
THE PROCESS WILL NOW KILL IT'S SELF.""", file=stderr)

					process.kill()
					# Maybe this is too extreme. I might change this if I switch from pickle.
					kill(getpid(), SIGKILL)
					while True:
						pass
		elapsed = perf_counter_ns()
		print((elapsed - now) / 1000000000)

Cog = Custom
