"""Abstractions over WASM ffi.
"""

from __future__ import annotations
from collections import deque
from dataclasses import dataclass
from inspect import signature, _empty # type: ignore
from itertools import islice, zip_longest
from numpy import frombuffer, generic, uint8, uint16, uint32, uint64
from traceback import print_tb
from typing import Any, Callable, Generator, Generic, GenericAlias, Iterable, \
	Iterator, Optional, TypeVar, Union, cast, get_args, get_origin
from wasmer import Function, FunctionType, ImportObject, Memory, Store, \
	Type as WASMType

T = TypeVar("T")
I = TypeVar("I", bound=generic)
AnyType = Union[type, GenericAlias]
TreeData = Union["WASMBind", list[WASMType]]
Tree = list[tuple[AnyType, TreeData]]

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

def from_tuple(value: tuple[T, ...]) -> Union[None, T, tuple[T, ...]]:
	return None if len(value) == 0 else \
		value if len(value) != 1 else value[0]

def to_tuple(value: Union[None, T, tuple[T, ...]]) -> tuple[T, ...]:
	return () if value is None else \
		value if isinstance(value, tuple) else (value,)

def wasmer_to_wasm(types: Iterator[WASMType], values: Iterator[int]):
	for ty, value in zip(types, values):
		if ty is WASMType.I32:
			yield from (
				uint8(byte) for byte in value.to_bytes(4, "little", signed=True)
			)
		elif ty is WASMType.I64:
			yield from (
				uint8(byte) for byte in value.to_bytes(8, "little", signed=True)
			)
		else:
			raise Exception("todo")

def wasm_to_wasmer(types: Iterator[WASMType], values: Iterator[uint8]):
	for ty in types:
		if ty is WASMType.I32:
			# uint8 is correctly treated as an int.
			bytez = bytearray(cast(Iterator[int], islice(values, 4)))
			yield int.from_bytes(bytez, "little", signed=True)
		elif ty is WASMType.I64:
			# uint8 is correctly treated as an int.
			bytez = bytearray(cast(Iterator[int], islice(values, 8)))
			yield int.from_bytes(bytez, "little", signed=True)
		else:
			raise Exception("todo")

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

	def write(self, value: Any, ty: Any = None):
		ty = type(value) if ty is None else ty
		binding = WASMBind([ty])
		memory = list(binding.python_to_wasm(iter([value])))
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

class WASMSlice:
	@classmethod
	def __from_wasm__(cls, memory: Memory, buf: WASMPointer, buf_len: uint32) \
			-> WASMSlice:
		return cls(memory, buf, buf_len)

	# TODO: What happened here?
	def __init__(self, _: Memory, buf: WASMPointer, buf_len: uint32):
		self.buf = buf
		self.buf_len = buf_len

def wasm_to_numpy(cls: Union[type[I], GenericAlias], data: Iterator[uint8]) \
		-> I:
	args = bytearray(islice(data, None, cls().itemsize)) # type: ignore
	return frombuffer(args, dtype=cls)[0]

def numpy_to_wasm(cls: Union[type[I], GenericAlias], value: I) \
		-> Iterator[uint8]:
	return (uint8(byte) for byte in value.tobytes())

@dataclass
class PrimitiveWASMBind(Generic[T]):
	from_wasm: Callable[
		[Union[type[T], GenericAlias], Iterator[uint8]],
		T
	]

	to_wasm: Callable[
		[Union[type[T], GenericAlias], T],
		Iterator[uint8]
	]

	wasm_ty: list[WASMType]

class WASMBind:
	"""Represents a bind that allows passing of arguments from Python to WASM, or
	back.

	This class only represents a single binding, and does not represent a full
	function; terefore, two WASMBinds are required to represent a function's input
	arguments and returned values.
	"""

	special: dict[Union[type, GenericAlias], PrimitiveWASMBind] = {
		uint8: PrimitiveWASMBind[uint8](
			wasm_to_numpy, numpy_to_wasm, [WASMType.I32]),
		uint16: PrimitiveWASMBind[uint16](
			wasm_to_numpy, numpy_to_wasm, [WASMType.I32]),
		uint32: PrimitiveWASMBind[uint32](
			wasm_to_numpy, numpy_to_wasm, [WASMType.I32]),
		uint64: PrimitiveWASMBind[uint64](
			wasm_to_numpy, numpy_to_wasm, [WASMType.I64]),
		_empty: PrimitiveWASMBind[_empty](
			lambda c, d: None, lambda c, v: iter([]), [])
	}

	@classmethod
	def build_tree(cls, py: AnyType) -> TreeData:
		if get_origin(py) is tuple:
			return cls(get_args(py))
		elif (result := cls.special.get(py)) is None:
			# Exceptions coming from this line is intended.
			from_sig = signature(py.__from_wasm__) # type: ignore
			# TODO: Check __to_wasm__

			params = (param.annotation for param in from_sig.parameters.values())
			return cls(skip(params, start=1))
		else:
			return result.wasm_ty

	tree: Tree

	def __init__(self, raw_types: Iterable[Union[type, str]]):
		# Evaluate annotations if they were not already.
		types = (
			cast(type, eval(ty)) if isinstance(ty, str) else ty \
				for ty in raw_types
		)

		# Build tree.
		self.tree = [(ty, self.build_tree(ty)) for ty in types]

	def wasm_to_python(self, memory: Memory, data: Iterator[uint8]) \
			-> Generator[Any, None, None]:
		# For each branch...
		for ty, components in self.tree:
			# If it's another tree...
			if isinstance(components, type(self)):
				if hasattr(ty, "__from_wasm__"):
					# Process it and yield ty from it.
					args = components.wasm_to_python(memory, data)
					# Exceptions coming from this line is intended.
					yield ty.__from_wasm__(memory, *list(args)) # type: ignore
				# If it's a tuple...
				else:
					yield tuple(components.wasm_to_python(memory, data))
			# Special cases.
			elif (special := WASMBind.special.get(ty)):
				yield special.from_wasm(ty, data)
			# Any other case is malformed.
			else:
				raise ValueError(f"invalid WASMBind tree on from_wasm (non raw wasm type {ty} was corrolated with raw wasm types {components})")
		# Partial use of data is okay. (It could be memory.)

	def python_to_wasm(self, data: Iterator[Any]) -> Generator[uint8, None, None]:
		# For each branch (and therefore item in data)...
		for value, branch in zip_longest(data, self.tree):
			# Check if iterator lengths are unbalanced.
			if value is None or branch is None:
				too = "short" if value is None else "long"
				raise ValueError(f"python data too {too} for WASMBind, expected \
{len(self.tree)} python objects")

			ty, components = branch
			# If it's a tuple...
			if isinstance(value, tuple):
				# Process it and yield from.
				yield from components.python_to_wasm(iter(value))
			# If it's another tree...
			elif isinstance(components, WASMBind):
				# Process it and yield from.
				args = value.__to_wasm__()
				yield from components.python_to_wasm(iter(to_tuple(args)))
			# Special cases.
			elif (special := WASMBind.special.get(ty)):
				yield from special.to_wasm(ty, value)
			# Any other case is malformed.
			else:
				raise ValueError(f"invalid WASMBind tree on to_wasm (non raw wasm type {ty} was corrolated with raw wasm types {components})")

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

class WASMApi:
	name: str
	memory: Optional[Memory]

	def __init__(self, name: str):
		self.name = name
		self.memory = None

	def set_memory(self, memory: Memory):
		self.memory = memory

	def register(self, store: Store, imports: ImportObject):
		functions = {
			name: Function(store, lambda *a, fn=fn: fn(self, *a), fn.wasm_type)
				for name, fn in vars(type(self)).items()
					if hasattr(fn, "wasm_type") \
						and isinstance(fn.wasm_type, FunctionType)
		}

		imports.register(self.name, functions)

def wasm_function(function):
	sig = signature(function)

	raw_params = [param.annotation for param in sig.parameters.values()]
	params = WASMBind(skip(raw_params, start=1))

	raw_returns = [sig.return_annotation]
	returns = WASMBind(raw_returns)

	ty_params = list(params.wasm_signature())
	ty_returns = list(returns.wasm_signature())

	def wasi_bind(self, *wasmer_params):
		try:
			if self.memory is None:
				raise Exception("A WASI API function was used before memory was set.")

			wasm_params = wasmer_to_wasm(iter(ty_params), iter(wasmer_params))
			py_params = list(params.wasm_to_python(self.memory, wasm_params))

			if False:
				debug_params = [str(param) for param in py_params]
				print(f'debug: {function.__name__}({", ".join(debug_params)})')
			py_returns = function(self, *py_params)

			wasm_returns = returns.python_to_wasm(iter(to_tuple(py_returns)))
			wasmer_returns = tuple(wasm_to_wasmer(iter(ty_returns), wasm_returns))
			return from_tuple(wasmer_returns)
		except Exception as error:
			print(print_tb(error.__traceback__))
			print(error)
			raise

	wasi_bind.wasm_type = FunctionType(ty_params, ty_returns)
	return wasi_bind

def register_blanks(blanks):
	def decorator(cls):
		for name, ty in blanks.items():
			def noop(*_, name=name) -> int:
				print(f"debug: blank {name} was called")
				return 1

			noop.wasm_type = ty
			setattr(cls, name, noop)
		return cls
	return decorator
