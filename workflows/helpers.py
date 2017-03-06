import os
from mothra.local_settings import FILES_FOLDER


def ensure_dir(f):
    d = os.path.dirname(f)
    if not os.path.exists(d):
        os.makedirs(d)

def safeOpen(filename):
    if filename.startswith(FILES_FOLDER):
        if filename.find("..")==-1:
            return open(filename,'r')
        else:
            raise Exception("Invalid filename")
    else:
        raise Exception("Invalid filename.")