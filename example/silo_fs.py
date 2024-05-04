#!/usr/bin/env python

#    Copyright (C) 2006  Andrew Straw  <strawman@astraw.com>
#
#    This program can be distributed under the terms of the GNU LGPL.
#    See the file COPYING.
#

from functools import reduce
import os, stat, errno
import time

# pull in some spaghetti to make this stuff work without fuse-py being installed
try:
    import _find_fuse_parts
except ImportError:
    pass
import fuse
from fuse import Fuse
from silo_api_client import SiloAPIClient
import pathmaker
from silo import Silo


if not hasattr(fuse, '__version__'):
    raise RuntimeError("your fuse-py doesn't know of fuse.__version__, probably it's too old.")

fuse.fuse_python_api = (0, 2)

# 設定ファイルの path を渡して Silo API Client を初期化
silo_api_client = SiloAPIClient('~/.config/silo/config.json')
silo = Silo()

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
    reading = {}

    def getattr(self, path):
        st = MyStat()
        print(f'### getattr() called. path: {path}')
        crop = silo.stat(path)

        # `/` は files 内に無いので、この `if` は消せない
        if path == '/':
            st.st_mode = stat.S_IFDIR | 0o755
            st.st_nlink = 2

        # `files` に存在する対象を処理する
        elif crop is not None:
            # 対象のファイルを取得

            print(f'### getattr() - path: {path}, file: {crop}')

            # もし file がディレクトリなら
            if crop['isDirectory']:
                has_file = (len(silo.list(path)) >= 1)
                
                print(f'### {path} is a directory. hasFile: {has_file}')
                st.st_mode = stat.S_IFDIR | 0o755
                st.st_nlink = 2
                st.st_mtime = float(crop['lastModifiedTime']) / 1000
                st.st_ctime = float(crop['createdTime']) / 1000

                # もしそのフォルダ内のファイルを持ってないなら読み込む
                if not has_file:
                    print(f'### Unknown dir - path: {path}')
                    print(f'### getattr() - called silo.add({path}, 0)')                    
                    silo.add(path, 0)            
            # もし file がディレクトリでなくファイルなら
            else:
                st.st_mode = stat.S_IFREG | 0o444
                st.st_nlink = 1
                st.st_size = int(crop['contentLength'])
                st.st_mtime = float(crop['lastModifiedTime']) / 1000
                st.st_ctime = float(crop['createdTime']) / 1000
        
        # `files` に存在しない対象の処理
        else:
            print(f'### getattr() - crop = silo.stat({path}) is None')
            return -errno.ENOENT
        return st

    def readdir(self, path, offset):
        for r in  '.', '..', *[c["filename"] for c in silo.list()]:
            print(f'### readdir() called. path: {path}, Direntry: {r}')
            yield fuse.Direntry(r)

    def open(self, path, flags):
        if silo.stat(path) is None:
            return -errno.ENOENT
        if (flags & os.O_RDONLY) != os.O_RDONLY:
            return -errno.EACCES
        return 0

    def read(self, path, size, offset):
        # 存在するファイルなら読み込む
        if silo.stat(path) is not None:

            # 対象のファイルをコンソールに表示
            print(f'### read() called (1)! path: {path}, size: {size}, offset: {offset}')
            buf = silo.haul(path, size, offset)
        
        # 存在しないファイルは読み込まない
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

    def write(self, path, buf, offset):
        print(f"### write() called! path: {path}, type(buf): {type(buf)}, offset: {offset}")
        
        return silo.load(path, buf, offset)
    
    def flush(self, path, **kw):
        print(f"### flush() called! path: {path}, len(writing): {len(self.writing)}")
        print(f'### flush() - kw: {kw}')
        silo.fill(path, kw)

        return 0
    
    def rename(self, path_old, path_new):
        print(f"### rename() called! path_old: {path_old}, path_new: {path_new}")
        # Check if old path exists
        if silo.stat(path_old) is None:
            return -errno.ENOENT

        # Check if new path already exists
        if silo.stat(path_new) is not None:
            return -errno.EEXIST

        # Get file at path_old and upload it to path_new
        self.writing = silo_api_client.get_file(path_old)
        self.flush(path_new, caller='rename')

        # delete file at path_ole
        self.unlink(path_old)

        # Success
        return 0

    def create(self, path, mistery, mode):
        silo.load(path, b'', 0)
        silo.fill(path)
        return 0

    def mkdir(self, path, mode):
        # ダミー用の空ファイルの中身
        self.writing = b'Silo blank file'
        
        # modified の path に、ダミーの空ファイル '.silo' を作る
        # 引数の path = '/test' みたいな感じなので
        # path_mod = '/test/.silo' になるはず
        path_mod = path + '/.silo'
        print(f"### mkdir() called! path_mod: {path_mod}")

        self.flush(path_mod, caller='mkdir')

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