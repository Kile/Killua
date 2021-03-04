from sandbox import WASI
from bridge import Bridge

from wasmer import engine, Store, Module, Instance, ImportObject, Function
from wasmer_compiler_cranelift import Compiler

store = Store(engine.JIT(Compiler))
module = Module(store, open("python-sandbox/target/wasm32-wasi/debug/python_sandbox.wasm", "rb").read())

imports = ImportObject()
wasi_interface = WASI(True)
wasi_interface.register(store, imports)
bridge_interface = Bridge()
bridge_interface.register(store, imports)

instance = Instance(module, imports)
wasi_interface.set_memory(instance.exports.memory)
bridge_interface.set_memory(instance.exports.memory)
print(instance.exports.main(0, 0))
