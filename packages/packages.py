# ClowdFlows packages are defined here!
# A brief overview of how it works:
# This module needs to export a variable called PACKAGE_TREE which is imported from settings.py
#

# Each entry in the PACKAGE_TREE should look something like this:
# {
#   "name": "Widgets",  # The actual name of the set of widgets that will be displayed in the treeview
#   "packages": ['cf_core','...'],  # Importable package names that are installed in the python path.
# These names can be different than their PyPi package names
#   "order": 1000,  # An integer used to sort the items in the treeview.
# }

# What we are actually defining here is the structure of the treeview on the left hand side of the GUI.
# Each section of the treeview can have many packages or just one.

PACKAGE_TREE = [{"name": "Utility", "packages": ['cf_core'], "order": 1000}
                # {"name": "Relational data mining","packages": ['rdm.db','rdm.wrappers'],"order": 1 }
                ]
