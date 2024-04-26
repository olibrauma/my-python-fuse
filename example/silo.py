#!/usr/bin/env python

#    Copyright (C) 2006  Andrew Straw  <strawman@astraw.com>
#
#    This program can be distributed under the terms of the GNU LGPL.
#    See the file COPYING.
#

import base64
from functools import reduce
import os, stat, errno
import time
import magic

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

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.files = silo_api_client.get_json("/")
        print(f"### HelloFS init() called! files: {self.files}")


    def getattr(self, path):
        print(f'### getattr() called. Path: {path}, files: {self.files}')
        st = MyStat()
        if path == '/':
            st.st_mode = stat.S_IFDIR | 0o755
            st.st_nlink = 2
        elif path in [f['filePath'] for f in self.files]:
            print(f'### getattr() for which `files` know')
            # 対象のファイル名を取得
            file = next(
                filter(lambda file: file["filePath"] == path, self.files),
                None
            )
                
            print(f'### Here "file" is {file}')
            if file['isDirectory']:
                st.st_mode = stat.S_IFDIR | 0o755
                st.st_nlink = 2
            else:
                st.st_mode = stat.S_IFREG | 0o444
                st.st_nlink = 1
                st.st_size = int(file['contentLength'])
                st.st_mtime = float(file['lastModifiedTime']) / 1000
                st.st_ctime = float(file['createdTime']) / 1000
        else:
            return -errno.ENOENT
        return st

    def readdir(self, path, offset):
        for r in  '.', '..', *[f["filename"] for f in self.files]:
            print(f'### readdir() called. Direntry for {r}')
            yield fuse.Direntry(r)

    def open(self, path, flags):
        if path not in [f['filePath'] for f in self.files]:
            return -errno.ENOENT
        if (flags & os.O_RDONLY) != os.O_RDONLY:
            return -errno.EACCES
        return 0

    def read(self, path, size, offset):
        if path in [f['filePath'] for f in self.files]:
            # 対象のファイルを取得
            print(f'### read() called (1)! path is {path}, size is {size}, offset is {offset}')
            buf = silo_api_client.get_file(path)
            slen = len(buf)
            if offset < slen:
                if offset + size > slen:
                    size = slen - offset
                buf = buf[offset:offset+size]
        else:
            buf = b''
        print(f'### read() called (2)! path: {path}, size: {size}, offset: {offset}')
        print(f"### Buf's type: {type(buf)}, length: {len(buf)}")
        return buf

    def unlink(self, path):
        print(f"### unlink() called! Path: {path}.")
        # Check if path exists
        if path not in [f['filePath'] for f in self.files]:
            return -errno.ENOENT
        # Delete the file object from `files`
        elif silo_api_client.delete_file(path) == 0 or 400:
            # 対象のファイルを files の配列から削除
            for i, f in enumerate(self.files):
                if f["filePath"] == path:
                    del self.files[i]
                    break 
            print(f"Deleted file not in files? > {self.files}")
            return 0
        else:
            # Success
            return -errno.EAGAIN

    def create(self, path, mistery, mode):
        # どんなファイルが書き込まれるかこの時点では不明なので、
        # デフォルトで "application/octet-stream" を使用
        mime_type = "application/octet-stream"
        data = b'' # 空のバイト列を送信
        silo_api_client.write_file(path, data, mime_type)
        
        # files の中身を更新する
        time.sleep(3) # write_file() 後すぐだと失敗するっぽいので少し待つ
        self.files = silo_api_client.get_json("/")
        print(f"### create() done. files: {self.files}")

        return 0

    def write(self, path, buf, offset):
        print(f"### write() called! path: {path}, type(buf): {type(buf)}, offset: {offset}")
        self.writing += buf 
        print(f'### writing: {len(self.writing)}')
        return len(buf)
    
    def flush(self, path):
        print(f"### flush() called! path: {path}, len(writing): {len(self.writing)}")
        
        if len(self.writing) == 0:
            print(f"### flush('{path}'), but nothing done due to len(writing) == {len(self.writing)}")
            return 0
        else: # writing が空でなければデータをアップロード
            print(f"### flush('{path}'), write_file() will be called due to len(writing) == {len(self.writing)} != 0")
            
            file_magic = magic.detect_from_content(self.writing)
            silo_api_client.write_file(path, self.writing, file_magic.mime_type)
            # writing を初期化
            self.writing = b""

            # アップロードした状態で、改めて files の中身を更新
            time.sleep(3) # write_file() 後すぐだと失敗するっぽいので少し待つ
            self.files = silo_api_client.get_json("/")

            # キャッシュを無効化
            super().Invalidate(path)
        return 0
    
    def rename(self, path_old, path_new):
        print(f"### rename() called! path_old: {path_old}, path_new: {path_new}")
        # Check if old path exists
        if path_old not in [f['filePath'] for f in self.files]:
            return -errno.ENOENT

        # Check if new path already exists
        if path_new in [f['filePath'] for f in self.files]:
            return -errno.EEXIST

        # Get file at path_old and upload it to path_new
        self.writing = silo_api_client.get_file(path_old)
        self.flush(path_new)

        # delete file at path_ole
        self.unlink(path_old)

        # Success
        return 0

    def mkdir(self, path, mode):
        # ダミー用の空ファイルの中身
        self.writing = b'Silo blank file'
        
        # modified の path に、ダミーの空ファイル '.silo' を作る
        # 引数の path = '/test' みたいな感じなので
        # path_mod = '/test/.silo' になるはず
        path_mod = path + '/.silo'
        print(f"### mkdir() called! path_mod: {path_mod}")

        self.flush(path_mod)

        # 成功した場合は 0 を返す
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