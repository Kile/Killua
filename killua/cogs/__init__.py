from importlib.abc import MetaPathFinder
import pkgutil
from importlib.util import find_spec
import pkgutil

# This module's submodules.
all_cogs = []

for loader, name, pkg in pkgutil.walk_packages(__path__):
    # Load the module.
    loader = (
        loader.find_module(name, None)
        if isinstance(loader, MetaPathFinder)
        else loader.find_module(name)
    )
    module = loader.load_module(name)

    # Make it a global.
    globals()[name] = module
    # Put it in the list.
    all_cogs.append(module)
    # This module's submodules.
    all_cogs = []
    for loader, name, is_pkg in pkgutil.iter_modules(__path__):
        # Load the module.
        spec = find_spec(name)
        if not spec:
            continue
        if spec.loader is None:
            continue
        module = spec.loader.load_module()
        # Make it a global.
        globals()[name] = module
        # Put it in the list.
        all_cogs.append(module)
