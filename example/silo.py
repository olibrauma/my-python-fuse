#!/usr/bin/env python

#    Copyright (C) 2006  Andrew Straw  <strawman@astraw.com>
#
#    This program can be distributed under the terms of the GNU LGPL.
#    See the file COPYING.
#

import base64
import os, stat, errno
import time

import dateutil.parser
# pull in some spaghetti to make this stuff work without fuse-py being installed
try:
    import _find_fuse_parts
except ImportError:
    pass
import fuse
from fuse import Fuse
from silo_api_client import SiloAPIClient
from datetime import datetime

if not hasattr(fuse, '__version__'):
    raise RuntimeError("your fuse-py doesn't know of fuse.__version__, probably it's too old.")

fuse.fuse_python_api = (0, 2)

# Create a dictionary and store File objects with path as key
# arg is the relative path from the mounted root dir
# The mount root dir's path is '/'
silo_api_client = SiloAPIClient()
files = silo_api_client.get_json("/")

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
    writing = b""

    def getattr(self, path):
        print('### getattr() is called. Path is ' + path)
        st = MyStat()
        if path == '/':
            st.st_mode = stat.S_IFDIR | 0o755
            st.st_nlink = 2
        elif path in [f['filePath'] for f in files]:
            # 対象のファイル名を取得
            file = None
            for f in files:
                if f["filePath"] == path:
                    file = f
                    break
            if int(file['contentLength']) > 0:
                print(f'### Here "file" is {file}')
                st.st_mode = stat.S_IFREG | 0o444
                st.st_nlink = 1
                st.st_size = int(file['contentLength'])
                st.st_mtime = float(file['lastModifiedTime']) / 1000
                #st.st_ctime = float(file['createdTime']) / 1000
            elif len(self.writing) > 0: # writing に data が入ってるなら PUT する
                print(f"### getattr() for a new file! path: {path}, len(writing): {len(self.writing)}")
                # まずデータをアップロード
                silo_api_client.write_file(path, self.writing)
                 # writing を初期化
                self.writing = b""
                # アップロードしたデータを改めて取得
                headers = silo_api_client.get_file(path, True)
                print(f"### get_file() done. headers: {headers}")
                # file を更新
                file['contentLength'] = headers['Content-Length']
                dt_str = headers['Last-Modified']
                dt = dateutil.parser.parse(dt_str)
                dt_timestamp = dt.timestamp()
                #file['lastModifiedTime'] = .timestamp
                print(f"### file updated in getattr(). dt_str: {dt_str}, dt: {dt}, dt_timestamp: {dt_timestamp}")

                # st を更新
                st.st_mode = stat.S_IFREG | 0o444
                st.st_nlink = 1
                st.st_size = int(file['contentLength'])
                st.st_mtime = int(dt_timestamp)
            else: # writing が空なら何もしない
                print(f"### getattr() for a new file but no content found in args")
                st.st_mode = stat.S_IFREG | 0o444
                st.st_nlink = 1
        else:
            return -errno.ENOENT
        return st

    def readdir(self, path, offset):
        for r in  '.', '..', *[f["filename"] for f in files]:
            print(f'### readdir() is called. Direntry for {r}')
            yield fuse.Direntry(r)

    def open(self, path, flags):
        if path not in [f['filePath'] for f in files]:
            return -errno.ENOENT
        if (flags & os.O_RDONLY) != os.O_RDONLY:
            return -errno.EACCES
        return 0

    def read(self, path, size, offset):
        if path in [f['filePath'] for f in files]:
            # 対象のファイルを取得
            print(f'### read() is called (1)! path is {path}, size is {size}, offset is {offset}')
            buf = silo_api_client.get_file(path)
            slen = len(buf)
            if offset < slen:
                if offset + size > slen:
                    size = slen - offset
                buf = buf[offset:offset+size]
        else:
            buf = b''
        print(f'### read() is called (2)! path is {path}, size is {size}, offset is {offset}')
        print(f"### Buf's type is {type(buf)}, length is {len(buf)}")
        return buf

    def unlink(self, path):
        print(f"### unlink() is called! Path is {path}.")
        # Check if path exists
        if path not in [f['filePath'] for f in files]:
            return -errno.ENOENT
        # Delete the file object from `files`
        elif silo_api_client.delete_file(path) == 0 or 400:
            # 対象のファイルを files の配列から削除
            for i, f in enumerate(files):
                if f["filePath"] == path:
                    del files[i]
                    break 
            print(f"Deleted file not in files > {files}")
            return 0
        else:
            # Success
            return -errno.EAGAIN

    '''
    def mknod(self, path, mode, dev):
        # dev は、デバイスならデバイス ID、ファイルなら 0
        print(f"mknod() is called! path is {path}, mode is {mode}")
        try:
            files.append({"filePath":path,"isDirectory":False, "filename":"bbq-clock.jpg"})
        except OSError as e:
            if e.errno == errno.ENOENT:
                raise OSError(errno.ENOENT, "No such file or directory: %s" % path)
            else:
                raise
    '''
    def create(self, path, mistery, mode):
        
        filename = f"{path.split("/")[-1]}"
        filePath = f"/{path.split("/")[-1]}"
        print(f"### create() is called! path: {filePath}, mistery: {mistery}, mode: {mode}, filename: {filename}")

        files.append(
            {
                "filePath": path,
                "isDirectory": False, 
                "filename": filename,
                "contentLength": 0,
                "lastModifiedTime": time.time() * 1000,
                "contentType": "image/jpg"
            }
        )
        print(f"create() is called! files: {files}")
        return 0

    def write(self, path, buf, offset):
        print(f"### write() is called! path: {path}, type(buf): {type(buf)}, offset: {offset}")
        self.writing += buf 
        print(f'### writing is {len(self.writing)}')
        return len(buf)

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