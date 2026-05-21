import importlib
import pkgutil

# This module's submodules.
all_cogs = []

_package = __name__

for _finder, name, _ispkg in pkgutil.iter_modules(__path__):
    if name.startswith("_"):
        continue
    module = importlib.import_module(f"{_package}.{name}")
    globals()[name] = module
    all_cogs.append(module)
