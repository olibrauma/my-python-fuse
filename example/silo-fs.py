#!/usr/bin/env python

#    Copyright (C) 2006  Andrew Straw  <strawman@astraw.com>
#
#    This program can be distributed under the terms of the GNU LGPL.
#    See the file COPYING.
#

import os, stat, errno
# pull in some spaghetti to make this stuff work without fuse-py being installed
try:
    import _find_fuse_parts
except ImportError:
    pass
import fuse
from fuse import Fuse
import silo
import pprint

if not hasattr(fuse, '__version__'):
    raise RuntimeError("your fuse-py doesn't know of fuse.__version__, probably it's too old.")

fuse.fuse_python_api = (0, 2)

class File:
    def __init__(self, name, content):
        self.name = name
        self.content = content

# Create a dictionary and store File objects with path as key
web = silo.get_json("/")
pprint.pprint(web)

# files 

files = {}
files["/hello"] = File("hello", b'Hello World!\n')
files["/bye"] = File("bye", b'Goodbye!\n')

class MyStat(fuse.Stat):
    def __init__(self):
        self.st_mode = 0
        self.st_ino = 0
        self.st_dev = 0
        self.st_nlink = 0
        self.st_uid = 0
        self.st_gid = 0
        self.st_size = 0
        self.st_atime = 0
        self.st_mtime = 0
        self.st_ctime = 0

class HelloFS(Fuse):

    def getattr(self, path):
        st = MyStat()
        if path == '/':
            st.st_mode = stat.S_IFDIR | 0o755
            st.st_nlink = 2
        elif path in files:  # Check for path in dictionary
            st.st_mode = stat.S_IFREG | 0o444
            st.st_nlink = 1
            st.st_size = len(files[path].content)
        else:
            return -errno.ENOENT
        return st

    def readdir(self, path, offset):
        for r in  '.', '..', *[f.name for f in files.values()]:
            yield fuse.Direntry(r)

    def open(self, path, flags):
        if path not in files:
            return -errno.ENOENT
        if (flags & os.O_RDONLY) != os.O_RDONLY:
            return -errno.EACCES
        return 0


    def read(self, path, size, offset):
        if path not in files:
            return -errno.ENOENT
        f = files[path]  # Get matching file object from dictionary
        slen = len(f.content)
        if offset < slen:
            if offset + size > slen:
                size = slen - offset
            buf = f.content[offset:offset+size]
        else:
            buf = b''
        return buf

    def rename(self, old, new):
        # Check if old path exists
        if old not in files:
            return -errno.ENOENT

        # Check if new path already exists
        if new in files:
            return -errno.EEXIST

        # Get the File object from old path
        f = files[old]

        # Update the dictionary with new path as key and old value
        files[new] = f
        del files[old]

        # Success
        return 0

    def unlink(self, path):
        # Check if path exists
        if path not in files:
            return -errno.ENOENT

        # Delete the file object from the dictionary
        del files[path]

        # Success
        return 0
    
def main():
    usage="""
Userspace hello example

""" + Fuse.fusage
    server = HelloFS(version="%prog " + fuse.__version__,
                     usage=usage,
                     dash_s_do='setsingle')

    server.parse(errex=1)
    server.main()

if __name__ == '__main__':
    main()
