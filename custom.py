import discord
from discord import Permissions
from discord.ext import commands

from wasmer import engine, Store, Module, Instance, ImportObject, Function, Type, FunctionType
from wasmer_compiler_cranelift import Compiler

from random import SystemRandom
from sys import stdout, stderr

def wasm_to_u32(value: int) -> int:
	"""Reinterprets an i32 passed across the wasm ffi boundary as a u32."""

	return int.from_bytes(value.to_bytes(4, "big", signed=True), "big", signed=False)

def mem_to_u32(memory, offset: int) -> int:
	"""Reads a u32 to a memory buffer."""

	return int.from_bytes(memory[offset:offset + 4], "little", signed=False)

def u32_to_mem(memory, offset: int, value: int):
	"""Writes a u32 to a memory buffer."""

	memory[offset:offset + 4] = value.to_bytes(4, "little", signed=False)

def register_blanks(imports: ImportObject, store: Store, mem):
	template = {
		#"random_get": FunctionType([Type.I32, Type.I32], [Type.I32]),
		"args_get": FunctionType([Type.I32, Type.I32], [Type.I32]),
		"args_sizes_get": FunctionType([Type.I32, Type.I32], [Type.I32]),
		"clock_time_get": FunctionType([Type.I32, Type.I64, Type.I32], [Type.I32]),
		"fd_close": FunctionType([Type.I32], [Type.I32]),
		"fd_filestat_get": FunctionType([Type.I32, Type.I32], [Type.I32]),
		"fd_filestat_set_size": FunctionType([Type.I32, Type.I64], [Type.I32]),
		"fd_read": FunctionType([Type.I32, Type.I32, Type.I32, Type.I32], [Type.I32]),
		"fd_readdir": FunctionType([Type.I32, Type.I32, Type.I32, Type.I64, Type.I32], [Type.I32]),
		"fd_sync": FunctionType([Type.I32], [Type.I32]),
		#"fd_write": FunctionType([Type.I32, Type.I32, Type.I32, Type.I32], [Type.I32]),
		"path_create_directory": FunctionType([Type.I32, Type.I32, Type.I32], [Type.I32]),
		"path_filestat_get": FunctionType([Type.I32, Type.I32, Type.I32, Type.I32, Type.I32], [Type.I32]),
		"path_link": FunctionType([Type.I32, Type.I32, Type.I32, Type.I32, Type.I32, Type.I32, Type.I32], [Type.I32]),
		"path_open": FunctionType([Type.I32, Type.I32, Type.I32, Type.I32, Type.I32, Type.I64, Type.I64, Type.I32, Type.I32], [Type.I32]),
		"path_readlink": FunctionType([Type.I32, Type.I32, Type.I32, Type.I32, Type.I32, Type.I32], [Type.I32]),
		"path_remove_directory": FunctionType([Type.I32, Type.I32, Type.I32], [Type.I32]),
		"path_rename": FunctionType([Type.I32, Type.I32, Type.I32, Type.I32, Type.I32, Type.I32], [Type.I32]),
		"path_unlink_file": FunctionType([Type.I32, Type.I32, Type.I32], [Type.I32]),
		"poll_oneoff": FunctionType([Type.I32, Type.I32, Type.I32, Type.I32], [Type.I32]),
		"sched_yield": FunctionType([], [Type.I32]),
		"fd_seek": FunctionType([Type.I32, Type.I64, Type.I32, Type.I32], [Type.I32]),
		"environ_sizes_get": FunctionType([Type.I32, Type.I32], [Type.I32]),
		"proc_exit": FunctionType([Type.I32], []),
		"environ_get": FunctionType([Type.I32, Type.I32], [Type.I32]),
		"fd_fdstat_get": FunctionType([Type.I32, Type.I32], [Type.I32])
	}

	blanks = dict()
	for name, ty in template.items():
		def noop(*args, name=name):
			print(f"blank {name} was called")
			return -1
		blanks[name] = Function(store, noop, ty)

	rng = SystemRandom()
	def random_get(buf: int, buf_len: int) -> int:
		memory = mem["value"].uint8_view() # Marshall memory.
		buf = wasm_to_u32(buf) # Marshall i32 as u32.
		buf_len = wasm_to_u32(buf_len) # ...

		# Replace memory region with secure random data.
		memory[buf:buf + buf_len] = [rng.randrange(256) for i in range(buf_len)]
		return 0 # Ok(())
	blanks["random_get"] = Function(store, random_get, FunctionType([Type.I32, Type.I32], [Type.I32]))

	def fd_write(fd: int, io_vec: int, io_vec_len: int, written: int) -> int:
		#print("fd_write called", fd, io_vec, io_vec_len, written) # Debug info.
		memory = mem["value"].uint8_view() # Marshall memory.
		fd = wasm_to_u32(fd) # Marshall i32 as u32.
		io_vec = wasm_to_u32(io_vec) # ...
		io_vec_len = wasm_to_u32(io_vec_len) # ...
		written = wasm_to_u32(written) # ...

		if fd == 1 or fd == 2:
			# Data read from all vectors.
			read = []

			# For each IO vector...
			for offset in range(io_vec_len):
				buf = mem_to_u32(memory, io_vec + offset * 8)
				buf_len = mem_to_u32(memory, io_vec + 4 + offset * 8)

				# Read the entire vector and write it all to our buffer.
				vector = memory[buf:buf + buf_len]
				vector = vector if isinstance(vector, list) else [vector]
				read.extend([chr(char) for char in vector])

			# Print the read data.
			file = stdout if fd == 1 else stderr
			print("".join(read), end="", file=file)

			u32_to_mem(memory, written, len(read)) # Write bytes written.
			return 0 # No error.
		else:
			return 2 # Permission denied.
	blanks["fd_write"] = Function(store, fd_write, FunctionType([Type.I32, Type.I32, Type.I32, Type.I32], [Type.I32]))

	imports.register(
		"wasi_snapshot_preview1",
		blanks
	)

class CustomCommands(commands.Cog):
	def __init__(self, client):
		self.client = client

	@commands.has_permissions(manage_nicknames=True)
	@commands.command()
	async def custom(self, *args, **kvargs):
		print(args)
		print(kvargs)

store = Store(engine.JIT(Compiler))
module = Module(store, open("python-sandbox/target/wasm32-wasi/debug/python_sandbox.wasm", "rb").read())

imports = ImportObject()
imports.register(
	"env",
	{
		"test": Function(
			store,
			print,
			FunctionType([Type.I32], [])
		)
	}
)
mem = {"value": None}
register_blanks(imports, store, mem)

try:
	instance = Instance(module, imports)
	mem["value"] = instance.exports.memory
	print(instance.exports.main(0, 0))
except Exception as error:
	import re

	match_a = re.search("Function\(FunctionType { params: \[([\w,\s]*)\], results: \[([\w,\s]*)\] }\)", str(error))
	match_b = re.search("Error while importing \"wasi_snapshot_preview1\".\"(\w+)\":", str(error))
	if match_a is None or match_b is None:
		print(error)
	else:
		name = match_b[1]
		params = ", ".join([f"Type.{item}" for item in match_a[1].split(", ")])
		ret = ", ".join([f"Type.{item}" for item in match_a[2].split(", ")])

		print(f"\"{name}\": FunctionType([{params}], [{ret}])")
	exit()

Cog = CustomCommands
