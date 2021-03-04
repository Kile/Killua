"""Manages sandboxing.
"""

from __future__ import annotations
from collections import deque
from inspect import signature
from itertools import islice
from numpy import frombuffer, uint8, uint32
from random import SystemRandom
from sys import stderr, stdout
from typing import Any, Iterable, Iterator, Optional, TypeVar, Union, cast
from wasmer import Function, FunctionType, ImportObject, Memory, Store, \
	Type as WASMType

T = TypeVar("T")

def skip(iterable, start=0, end=0):
	it = iter(iterable)

	# Skip first X.
	for x in islice(it, start):
		pass

	# Use up to last Y.
	queue = deque(islice(it, end))
	for x in it:
		queue.append(x)
		yield queue.popleft()

# TODO: Make this class even better.
class WASMPointer:
	@classmethod
	def __from_wasm__(cls, memory: Memory, pointer: uint32) -> WASMPointer:
		return cls(memory, pointer)

	def __init__(self, memory: Memory, pointer: uint32):
		self.memory = memory
		self.pointer = pointer

	def __to_wasm__(self) -> uint32:
		return self.pointer

	def read(self, ty: type[T]) -> T:
		binding = WASMBind([ty])
		value = list(binding.wasm_to_python(self.memory, iter(self[:])))
		return value[0]

	def write(self, value: Any):
		binding = WASMBind([type(value)])
		memory = list(binding.python_to_wasm([value]))
		self[:len(memory)] = memory

	def offset(self, bytes: int) -> WASMPointer:
		return WASMPointer(self.memory, uint32(self.pointer + bytes))

	def __getitem__(self, key) -> list[uint8]:
		start, stop, step = (key.start, key.stop, key.step) \
			if isinstance(key, slice) else (key, None, None)

		if not isinstance(start, int):
			if hasattr(start, "__index__"):
				start = start.__index__()
			elif start is not None:
				raise TypeError(f"bad start index, expected {int} found {type(start)}")
		elif not isinstance(stop, int):
			if hasattr(stop, "__index__"):
				stop = stop.__index__()
			elif stop is not None:
				raise Exception("bad stop")
		elif not isinstance(step, int):
			if hasattr(step, "__index__"):
				step = step.__index__()
			elif step is not None:
				raise Exception("bad step")

		memory = self.memory.uint8_view()
		start = self.pointer + (0 if start is None else start)
		stop = self.pointer + (len(memory) if stop is None else stop)
		step = 1 if step is None else step

		data = memory[start:stop:step]
		result = data if isinstance(data, list) else [data]
		return [uint8(data) for data in result]

	def __setitem__(self, key, value):
		start, stop, step = (key.start, key.stop, key.step) \
			if isinstance(key, slice) else (key, None, None)

		if not isinstance(start, int):
			if hasattr(start, "__index__"):
				start = start.__index__()
			elif start is not None:
				raise Exception("bad start")
		elif not isinstance(stop, int):
			if hasattr(stop, "__index__"):
				stop = stop.__index__()
			elif stop is not None:
				raise Exception("bad stop")
		elif not isinstance(step, int):
			if hasattr(step, "__index__"):
				step = step.__index__()
			elif step is not None:
				raise Exception("bad step")

		memory = self.memory.uint8_view()
		start = self.pointer + (0 if start is None else start)
		stop = self.pointer + (len(memory) if stop is None else stop)
		step = 1 if step is None else step

		memory[start:stop:step] = value

class Slice:
	@classmethod
	def __from_wasm__(cls, memory: Memory, buf: WASMPointer, buf_len: uint32) \
			-> Slice:
		return cls(memory, buf, buf_len)

	def __init__(self, memory: Memory, buf: WASMPointer, buf_len: uint32):
		self.buf = buf
		self.buf_len = buf_len

def wasi_to_wasm(types: Iterator[WASMType], values: Iterator[int]):
	for ty, value in zip(types, values):
		if ty is WASMType.I32:
			yield from (
				uint8(byte) for byte in value.to_bytes(4, "little", signed=True)
			)
		else:
			raise Exception("todo")

Tree = list[tuple[type, Union["WASMBind", list[WASMType]]]]

class WASMBind:
	"""Represents a bind that allows passing of arguments from Python to WASM, or
	back.

	This class only represents a single binding, and does not represent a full
	function; terefore, two WASMBinds are required to represent a function's input
	arguments and returned values.
	"""

	@classmethod
	def build_tree(cls, py: type) -> Union[WASMBind, list[WASMType]]:
		cases: dict[type, list[WASMType]] = {
			uint32: [WASMType.I32]
		}

		result = cases.get(py)
		if result is None:
			# Exceptions coming from this line is intended.
			from_sig = signature(py.__from_wasm__) # type: ignore
			# TODO: Check __to_wasm__

			params = (param.annotation for param in from_sig.parameters.values())
			return cls(skip(params, start=1))
		else:
			return result

	tree: Tree

	def __init__(self, raw_types: Iterable[Union[type, str]]):
		# Evaluate annotations if they were not already.
		types = (
			cast(type, eval(ty)) if isinstance(ty, str) else ty \
				for ty in raw_types
		)

		# Build tree.
		self.tree = [(ty, self.build_tree(ty)) for ty in types]

	def wasm_to_python(self, memory: Memory, data: Iterator[uint8]):
		# For each branch...
		for ty, components in self.tree:
			# If it's another tree...
			if isinstance(components, type(self)):
				# Process it and yield ty from it.
				args = components.wasm_to_python(memory, data)
				# Exceptions coming from this line is intended.
				yield ty.__from_wasm__(memory, *list(args)) # type: ignore
			# Special uint32 case.
			elif issubclass(ty, cast(type, uint32)):
				# Collect 4 bytes and convert to a uint32.
				# uint8 is correctly treated as an int.
				args = bytearray(cast(Iterator[int], islice(data, None, 4)))
				yield frombuffer(args, dtype=uint32)[0]
			# Any other case is malformed.
			else:
				raise Exception(f"invalid WASMBind tree (non raw wasm type {ty} was corrolated with raw wasm types {components})")
		# Partial use of data is okay.

	def python_to_wasm(self, data: list[Any]):
		for (index, (ty, components)) in enumerate(self.tree):
			if isinstance(components, type(self)):
				yield from components.python_to_wasm(data[index:])
			elif ty is uint32:
				yield int(data[index])
			else:
				raise Exception("bruh")

	def wasm_signature(self):
		"""Yield's this binding's signature."""

		for _, components in self.tree:
			if isinstance(components, list):
				for item in components:
					yield item
			else:
				yield from components.wasm_signature()

	def __repr__(self) -> str:
		return f"WASMBind{str(self.tree)}"

def wasi_api(function):
	sig = signature(function)

	raw_params = [param.annotation for param in sig.parameters.values()]
	params = WASMBind(skip(raw_params, start=1))

	raw_returns = [sig.return_annotation]
	returns = WASMBind(raw_returns)

	ty_params = list(params.wasm_signature())
	ty_returns = list(returns.wasm_signature())

	def wasi_bind(self, *wasi_params):
		if self.memory is None:
			raise Exception("A WASI API function was used before memory was set.")

		wasm_params = wasi_to_wasm(iter(ty_params), iter(wasi_params))
		py_params = list(params.wasm_to_python(self.memory, wasm_params))
		if True:
			debug_params = [str(param) for param in py_params]
			print(f'debug: {function.__name__}({", ".join(debug_params)})')
		py_returns = function(self, *py_params)
		return list(returns.python_to_wasm([py_returns]))[0]

	wasi_bind.wasm_type = FunctionType(ty_params, ty_returns)
	return wasi_bind

def blanks(blanks):
	def decorator(cls):
		for name, ty in blanks.items():
			def noop(*_, name=name) -> int:
				print(f"debug: blank {name} was called")
				return 1

			noop.wasm_type = ty
			setattr(cls, name, noop)
		return cls
	return decorator

# Temporary decorator to suppress errors.
@blanks({
	#"random_get": FunctionType([WASMType.I32, WASMType.I32], [WASMType.I32]),
	"args_get": FunctionType([WASMType.I32, WASMType.I32], [WASMType.I32]),
	"args_sizes_get": FunctionType([WASMType.I32, WASMType.I32], [WASMType.I32]),
	"clock_time_get": FunctionType([WASMType.I32, WASMType.I64, WASMType.I32], [WASMType.I32]),
	"fd_close": FunctionType([WASMType.I32], [WASMType.I32]),
	"fd_filestat_get": FunctionType([WASMType.I32, WASMType.I32], [WASMType.I32]),
	"fd_filestat_set_size": FunctionType([WASMType.I32, WASMType.I64], [WASMType.I32]),
	"fd_read": FunctionType([WASMType.I32, WASMType.I32, WASMType.I32, WASMType.I32], [WASMType.I32]),
	"fd_readdir": FunctionType([WASMType.I32, WASMType.I32, WASMType.I32, WASMType.I64, WASMType.I32], [WASMType.I32]),
	"fd_sync": FunctionType([WASMType.I32], [WASMType.I32]),
	#"fd_write": FunctionType([WASMType.I32, WASMType.I32, WASMType.I32, WASMType.I32], [WASMType.I32]),
	"path_create_directory": FunctionType([WASMType.I32, WASMType.I32, WASMType.I32], [WASMType.I32]),
	"path_filestat_get": FunctionType([WASMType.I32, WASMType.I32, WASMType.I32, WASMType.I32, WASMType.I32], [WASMType.I32]),
	"path_link": FunctionType([WASMType.I32, WASMType.I32, WASMType.I32, WASMType.I32, WASMType.I32, WASMType.I32, WASMType.I32], [WASMType.I32]),
	"path_open": FunctionType([WASMType.I32, WASMType.I32, WASMType.I32, WASMType.I32, WASMType.I32, WASMType.I64, WASMType.I64, WASMType.I32, WASMType.I32], [WASMType.I32]),
	"path_readlink": FunctionType([WASMType.I32, WASMType.I32, WASMType.I32, WASMType.I32, WASMType.I32, WASMType.I32], [WASMType.I32]),
	"path_remove_directory": FunctionType([WASMType.I32, WASMType.I32, WASMType.I32], [WASMType.I32]),
	"path_rename": FunctionType([WASMType.I32, WASMType.I32, WASMType.I32, WASMType.I32, WASMType.I32, WASMType.I32], [WASMType.I32]),
	"path_unlink_file": FunctionType([WASMType.I32, WASMType.I32, WASMType.I32], [WASMType.I32]),
	"poll_oneoff": FunctionType([WASMType.I32, WASMType.I32, WASMType.I32, WASMType.I32], [WASMType.I32]),
	"sched_yield": FunctionType([], [WASMType.I32]),
	"fd_seek": FunctionType([WASMType.I32, WASMType.I64, WASMType.I32, WASMType.I32], [WASMType.I32]),
	"environ_sizes_get": FunctionType([WASMType.I32, WASMType.I32], [WASMType.I32]),
	"proc_exit": FunctionType([WASMType.I32], []),
	"environ_get": FunctionType([WASMType.I32, WASMType.I32], [WASMType.I32]),
	"fd_fdstat_get": FunctionType([WASMType.I32, WASMType.I32], [WASMType.I32])
})
class WASI:
	loopback: bool
	memory: Optional[Memory]
	rng: SystemRandom

	def __init__(self, loopback=False):
		self.loopback = loopback
		self.memory = None
		self.rng = SystemRandom()

	def register(self, store: Store, imports: ImportObject):
		functions = {
			name: Function(store, lambda *a, fn=fn: fn(self, *a), fn.wasm_type)
				for name, fn in vars(type(self)).items()
					if hasattr(fn, "wasm_type") \
						and isinstance(fn.wasm_type, FunctionType)
		}

		imports.register("wasi_snapshot_preview1", functions)

	def set_memory(self, memory: Memory):
		self.memory = memory

	@wasi_api
	def random_get(self, buf: WASMPointer, buf_len: uint32) -> uint32:
		# Write secure random.
		buf[:buf_len] = [self.rng.randrange(256) for i in range(buf_len)]
		return uint32(0) # Okay!

	@wasi_api
	def fd_write(self, fd: uint32, io_vec: WASMPointer, io_vec_len: uint32,
			written: WASMPointer) -> uint32:
		if self.loopback and fd == 1 or fd == 2:
			read = [] # Data read from all vectors.

			# For each IO vector...
			for offset in range(io_vec_len):
				# Read the entire vector and write it all to our buffer.
				vec = io_vec.offset(offset * 8).read(Slice)
				# uint8 is correctly treated as an int.
				read.extend([chr(cast(int, char)) for char in vec.buf[:vec.buf_len]])

			# Print the read data.
			file = stdout if fd == 1 else stderr
			print("".join(read), end="", file=file)
			file.flush()

			written.write(uint32(len(read))) # Write bytes written.
			return uint32(0) # Okay!
		elif not self.loopback and fd == 1 or fd == 2:
			read = 0 # Number of bytes read from all vectors.

			# For each IO vector...
			for offset in range(io_vec_len):
				# Add the number of bytes in the vector to the total number of bytes.
				vec = io_vec.offset(offset * 8).read(Slice)
				read = read + vec.buf_len

			written.write(uint32(read)) # Write bytes written.
			return uint32(0) # Okay!
		else:
			return uint32(8) # Bad file descriptor.
