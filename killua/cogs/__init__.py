from importlib.abc import MetaPathFinder
import pkgutil

# This module's submodules.
__all__ = []

for loader, name, pkg in pkgutil.walk_packages(__path__):
	# Load the module.
	loader = loader.find_module(name, None) \
		if isinstance(loader, MetaPathFinder) else loader.find_module(name)
	module = loader.load_module(name)

	# Make it a global.
	globals()[name] = module
	# Put it in the list.
	__all__.append(module)
