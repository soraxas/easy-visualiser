import glob
import inspect
import sys
from os.path import basename, dirname, isfile, join

# gather all module in current folder.
modules = glob.glob(join(dirname(__file__), "*.py"))
__all__ = [
    basename(f)[:-3] for f in modules if isfile(f) and not f.endswith("__init__.py")
]


def import_all_classes_from_module(module_name: str, prefix: str):
    """Given a module name, inject all classes within the current
    directory with a name that is prefixxed with a given criteria."""

    __import__(module_name)

    injected_names = set()
    for name, obj in inspect.getmembers(sys.modules[module_name]):
        if name.startswith(prefix) and inspect.isclass(obj):
            if name in injected_names:
                raise RuntimeError(f"A class with the name {name} already exists!")
            injected_names.add(name)
            globals()[name] = obj
    return list(injected_names)


injected_classes = []
for ext in __all__:
    ext_module_name = f"{__name__}.{ext}"
    added_names = import_all_classes_from_module(ext_module_name, "Visualisable")
    injected_classes.extend(added_names)

__all__.extend(added_names)
