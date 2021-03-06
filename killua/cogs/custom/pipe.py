from aiofiles import open as aopen
from itertools import chain
from os import pipe2 as os_pipe
from pickle import dumps, loads
from typing import Any

class PipeClosedError(Exception):
	def __init__(self, local_closure: bool, action: str):
		if action != "send" and action != "recv":
			raise ValueError(f"bad action {repr(action)}")

		self._local_closure = local_closure
		self._action = action

	def __str__(self) -> str:
		# This side was closed and read from.
		if self._local_closure and self._action == "recv":
			return "attempt to receive after closing"
		# This side was closed and wrote to.
		elif self._local_closure and self._action == "send":
			return "attempt to send after closing"
		# Other side was closed and this was read from.
		elif not self._local_closure and self._action == "recv":
			return "cannot receive, other end was closed"
		# Other side was closed and this was wrote to.
		elif not self._local_closure and not self._action == "send":
			return "cannot send, other end was closed"
		else:
			raise ValueError("invalid PipeClosureError state")

class DataPipe:
	@property
	def closed(self):
		return self._writer.closed if self._writer is not None else \
			self._reader.closed

	def __init__(self, *, read: int = None, write: int = None):
		if read is None and write is None:
			raise TypeError("at least read or write must be set")

		self._reader = None if read is None else open(read, "rb")
		self._writer = None if write is None else open(write, "wb")

	def send(self, value: Any):
		if self._writer is None:
			raise TypeError("attempt to write to a non writable data pipe")

		try:
			data = bytearray(dumps(value))
			packet = chain([0], len(data).to_bytes(4, "big"), data)
			self._writer.write(bytearray(packet))
			self._writer.flush()
		except BrokenPipeError:
			raise PipeClosedError(False, "send") from None
		except ValueError:
			raise PipeClosedError(True, "send") from None

	def recv(self):
		if self._reader is None:
			raise TypeError("attempt to read from a non readable data pipe")

		try:
			data = self._reader.peek()
			if data[0] == 0:
				size = int.from_bytes(data[2:5], "big")
				value = loads(data[5:size + 5])
				self._reader.read(size + 5)
				return value
			elif data[0] == 1:
				raise PipeClosedError(False, "recv")
			else:
				raise ValueError("pipe is corrupted")
		except ValueError as error:
			if str(error) == "pipe is corrupted":
				raise
			raise PipeClosedError(True, "recv") from None
		except IndexError:
			return None

	def close(self):
		if self._writer is not None:
			try:
				self._writer.write(bytearray([1]))
				self._writer.flush()
			except BrokenPipeError:
				pass
			except ValueError:
				pass

			try:
				self._writer.close()
			except BrokenPipeError:
				pass
		if self._reader is not None:
			self._reader.close()

	def __enter__(self):
		pass

	def __exit__(self, ty, value, traceback):
		self.close()
		return ty is PipeClosedError

class AsyncDataPipe:
	async def __new__(cls, *args, **kwargs) -> "AsyncDataPipe":
		self = super().__new__(cls)
		await self.__init__(*args, **kwargs)
		return self

	async def __init__(self, original: DataPipe = None, *, read: int = None,
			write: int = None):
		if original is None and read is None and write is None:
			raise TypeError("at least original, read or write must be set")

		if original is not None and (read is None and write is None):
			self._reader = None if original._reader is None else \
				await aopen(original._reader.fileno(), "rb")
			self._writer = None if original._writer is None else \
				await aopen(original._writer.fileno(), "wb")
		elif (read is not None or write is not None) and original is None:
			self._reader = None if read is None else await aopen(read, "rb")
			self._writer = None if write is None else await aopen(write, "wb")
		else:
			raise TypeError("original cannot set along side read or write")

	async def send(self, value: Any):
		if self._writer is None:
			raise TypeError("attempt to write to a non writable data pipe")

		try:
			data = bytearray(dumps(value))
			packet = chain([0], len(data).to_bytes(4, "big"), data)
			await self._writer.write(bytearray(packet))
			await self._writer.flush()
		except BrokenPipeError:
			raise PipeClosedError(False, "send") from None
		except ValueError:
			raise PipeClosedError(True, "send") from None

	async def recv(self):
		if self._reader is None:
			raise TypeError("attempt to read from a non readable data pipe")

		try:
			data = await self._reader.peek()
			if data[0] == 0:
				size = int.from_bytes(data[2:5], "big")
				value = loads(data[5:size + 5])
				await self._reader.read(size + 5)
				return value
			elif data[0] == 1:
				raise PipeClosedError(False, "recv")
			else:
				raise ValueError("pipe is corrupted")
		except ValueError as error:
			if str(error) == "pipe is corrupted":
				raise
			raise PipeClosedError(True, "recv") from None
		except IndexError:
			return None

	async def close(self):
		if self._writer is not None:
			try:
				await self._writer.write(bytearray([1]))
				await self._writer.flush()
			except BrokenPipeError:
				pass
			except ValueError:
				pass

			try:
				await self._writer.close()
			except BrokenPipeError:
				pass
		if self._reader is not None:
			await self._reader.close()

	async def __aenter__(self):
		pass

	async def __aexit__(self, ty, value, traceback):
		await self.close()
		return ty is PipeClosedError

def pipe() -> tuple[DataPipe, DataPipe]:
	reader, writer = os_pipe(0)
	return DataPipe(read=reader), DataPipe(write=writer)

async def async_pipe() -> tuple[AsyncDataPipe, AsyncDataPipe]:
	reader, writer = os_pipe(0)
	return (await AsyncDataPipe(read=reader), # type: ignore
		await AsyncDataPipe(write=writer)) # type: ignore

async def async_reader_pipe() -> tuple[AsyncDataPipe, DataPipe]:
	reader, writer = os_pipe(0)
	return (await AsyncDataPipe(read=reader), # type: ignore
		DataPipe(write=writer))

async def async_writer_pipe() -> tuple[DataPipe, AsyncDataPipe]:
	reader, writer = os_pipe(0)
	return DataPipe(read=reader), \
		await AsyncDataPipe(write=writer) # type: ignore

def duplex() -> tuple[DataPipe, DataPipe]:
	a_reader, b_writer = os_pipe(0)
	b_reader, a_writer = os_pipe(0)
	return DataPipe(read=a_reader, write=a_writer), \
		DataPipe(read=b_reader, write=b_writer)

async def async_duplex() -> tuple[AsyncDataPipe, AsyncDataPipe]:
	a_reader, b_writer = os_pipe(0)
	b_reader, a_writer = os_pipe(0)
	return (await AsyncDataPipe(read=a_reader, write=a_writer), # type: ignore
		await AsyncDataPipe(read=b_reader, write=b_writer)) # type: ignore

async def half_async_duplex() -> tuple[DataPipe, AsyncDataPipe]:
	a_reader, b_writer = os_pipe(0)
	b_reader, a_writer = os_pipe(0)
	return DataPipe(read=a_reader, write=a_writer), \
		await AsyncDataPipe(read=b_reader, write=b_writer) # type: ignore
