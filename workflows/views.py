import sys
from workflows import module_importer


def setattr_local(name, value, package):
   setattr(sys.modules[__name__], name, value)

module_importer.import_all_packages_libs("views", setattr_local)
