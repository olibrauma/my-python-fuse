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
from datetime import datetime

if not hasattr(fuse, '__version__'):
    raise RuntimeError("your fuse-py doesn't know of fuse.__version__, probably it's too old.")

fuse.fuse_python_api = (0, 2)

# Create a dictionary and store File objects with path as key
# arg is the relative path from the mounted root dir
# The mount root dir's path is '/'
files = silo.get_json("/")

hello_path = '/hello'
hello_str = b'Hello World!\n'

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
        print('### getattr() is called. Path is ' + path)
        st = MyStat()
        if path == '/':
            st.st_mode = stat.S_IFDIR | 0o755
            st.st_nlink = 2
        elif path == hello_path:
            st.st_mode = stat.S_IFREG | 0o444
            st.st_nlink = 1
            st.st_size = len(hello_str)
        elif path in [f['filePath'] for f in files]:
            # 対象のファイル名を取得
            file = None
            for f in files:
                if f["filePath"] == path:
                    file = f
                    break

            print('### Here "file" is:')
            print(file)
            st.st_mode = stat.S_IFREG | 0o444
            st.st_nlink = 1
            st.st_size = int(file['contentLength'])
            st.st_mtime = float(file['lastModifiedTime']) / 1000
            st.st_ctime = float(file['createdTime']) / 1000
        else:
            return -errno.ENOENT
        return st

    def readdir(self, path, offset):
        for r in  '.', '..', 'hello', *[f["filename"] for f in files]:
            print('### readdir() is called. Direntry for ' + r)
            yield fuse.Direntry(r)

    def open(self, path, flags):
        if path == hello_path:
            return 0
        elif path not in [f['filePath'] for f in files]:
            return -errno.ENOENT
        if (flags & os.O_RDONLY) != os.O_RDONLY:
            return -errno.EACCES
        return 0

    def read(self, path, size, offset):
        if path == hello_path:
            slen = len(hello_str)
            if offset < slen:
                if offset + size > slen:
                    size = slen - offset
                buf = hello_str[offset:offset+size]
        elif path in [f['filePath'] for f in files]:
            # 対象のファイルを取得
            print(f'### read() is called (1)! path is {path}, size is {size}, offset is {offset}')
            buf = silo.get_file(path)
            slen = len(buf)
            if offset < slen:
                if offset + size > slen:
                    size = slen - offset
                buf = buf[offset:offset+size]
            print(f'### read() is called (2)! path is {path}, size is {size}, offset is {offset}')
            print(f"### Buf's type is {type(buf)}, length is {len(buf)}")
        else:
            buf = b''

        return buf

    def unlink(self, path):
        print(f"### unlink() is called! Path is {path}.")
        # Check if path exists
        if path not in [f['filePath'] for f in files]:
            return -errno.ENOENT
        # Delete the file object from `files`
        elif silo.delete_file(path) != 0:
            return -errno.ENOENT
        else:
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