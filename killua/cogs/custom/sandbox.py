"""Manages sandboxing.
"""

from numpy import uint32
from random import SystemRandom
from sys import stderr, stdout
from typing import cast, Optional
from .wasm import WASMApi, WASMPointer, WASMSlice, register_blanks, \
	wasm_function
from wasmer import FunctionType, Memory, Type

# Temporary decorator to suppress errors.
@register_blanks({
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
})
class WASI(WASMApi):
	loopback: bool
	rng: SystemRandom

	def __init__(self, loopback=False):
		super().__init__("wasi_snapshot_preview1")
		self.loopback = loopback
		self.rng = SystemRandom()

	@wasm_function
	def random_get(self, buf: WASMPointer, buf_len: uint32) -> uint32:
		# Write secure random.
		buf[:buf_len] = [self.rng.randrange(256) for i in range(buf_len)]
		return uint32(0) # Okay!

	@wasm_function
	def fd_write(self, fd: uint32, io_vec: WASMPointer, io_vec_len: uint32,
			written: WASMPointer) -> uint32:
		if self.loopback and fd == 1 or fd == 2:
			read = [] # Data read from all vectors.

			# For each IO vector...
			for offset in range(io_vec_len):
				# Read the entire vector and write it all to our buffer.
				vec = io_vec.offset(offset * 8).read(WASMSlice)
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
				vec = io_vec.offset(offset * 8).read(WASMSlice)
				read = read + vec.buf_len

			written.write(uint32(read)) # Write bytes written.
			return uint32(0) # Okay!
		else:
			return uint32(8) # Bad file descriptor.
