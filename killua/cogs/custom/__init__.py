from .bridge import Bridge
from .sandbox import WASI
from discord.ext.commands import Cog as CommandCog, command
from wasmer import ImportObject, Instance, Module, Store, engine
from wasmer_compiler_cranelift import Compiler

wasm = "python-sandbox/target/wasm32-wasi/debug/python_sandbox.wasm"

class Custom(CommandCog):
	def __init__(self, client):
		self.client = client

		store = Store(engine.JIT(Compiler))
		module = Module(store, open(wasm, "rb").read())

		imports = ImportObject()
		self.wasi_interface = WASI(True)
		self.wasi_interface.register(store, imports)
		self.bridge_interface = Bridge()
		self.bridge_interface.register(store, imports)

		self.instance = Instance(module, imports)
		self.wasi_interface.set_memory(self.instance.exports.memory)
		self.bridge_interface.set_memory(self.instance.exports.memory)

	@command()
	async def custom(self, context, *args, **kwargs):
		self.bridge_interface.content = context.args[2]
		self.bridge_interface.message = context.message
		self.instance.exports.main(0, 0)

Cog = Custom
