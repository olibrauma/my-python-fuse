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

if not hasattr(fuse, '__version__'):
    raise RuntimeError("your fuse-py doesn't know of fuse.__version__, probably it's too old.")

fuse.fuse_python_api = (0, 2)

# 設定ファイルの path を渡して Silo API Client を初期化
silo_api_client = SiloAPIClient('~/.config/silo/config.json')

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

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.files = silo_api_client.get_json("/")
        print(f"### HelloFS init() called! files: {self.files}")

    def getattr(self, path):
        st = MyStat()
        print(f'### getattr() called. path: {path}, files: {self.files}')

        # `/` は files 内に無いので、この `if` は消せない
        if path == '/':
            st.st_mode = stat.S_IFDIR | 0o755
            st.st_nlink = 2

        # `files` に存在する対象を処理する
        elif path in [f['filePath'] for f in self.files]:
            print(f'### getattr() for which `files` know')
            # 対象のファイルを取得
            file = next(filter(lambda file: file["filePath"] == path, self.files))
            print(f'### Here "file" is {file}')

            # もし file がディレクトリなら
            if file['isDirectory']:
                # files からこのフォルダを除いたリストを作る
                files_filtered = [file for file in self.files if file['filePath'] != path]
                # このフォルダ内のファイルの情報を持っているか？
                # たとえば path = '/test' のとき、'/test_2' があると、'/test/' 以下を知らなくても知ってる判定になる
                # それを避けるために path + '/' = '/test/' で始まる path の有無を見る
                path_folder = path + '/'
                hasFile = reduce(lambda acc, f: acc or f['filePath'].startswith(path_folder), files_filtered, False)
                
                print(f'### {path} is a directory. hasFile: {hasFile}')
                st.st_mode = stat.S_IFDIR | 0o755
                st.st_nlink = 2
                st.st_mtime = float(file['lastModifiedTime']) / 1000
                st.st_ctime = float(file['createdTime']) / 1000

                # もしそのフォルダ内のファイルを持ってないなら読み込む
                if not hasFile:
                    print(f'### Unknown dir searched!')
                    print(f'### path: {path}, files: {self.files}')
                    self.files += silo_api_client.get_json(path + '/')
            
            # もし file がディレクトリでなくファイルなら
            else:
                st.st_mode = stat.S_IFREG | 0o444
                st.st_nlink = 1
                st.st_size = int(file['contentLength'])
                st.st_mtime = float(file['lastModifiedTime']) / 1000
                st.st_ctime = float(file['createdTime']) / 1000
        
        # `files` に存在しない対象の処理
        else:
            return -errno.ENOENT
        return st

    def readdir(self, path, offset):
        for r in  '.', '..', *[f["filename"] for f in self.files]:
            print(f'### readdir() called. path: {path}, Direntry: {r}')
            yield fuse.Direntry(r)

    def open(self, path, flags):
        if path not in [f['filePath'] for f in self.files]:
            return -errno.ENOENT
        if (flags & os.O_RDONLY) != os.O_RDONLY:
            return -errno.EACCES
        return 0

    def read(self, path, size, offset):
        # 存在するファイルなら読み込む
        if path in [f['filePath'] for f in self.files]:

            # 対象のファイルをコンソールに表示
            print(f'### read() called (1)! path: {path}, size: {size}, offset: {offset}')
            
            # メモリに無ければダウンロードする
            if path not in self.reading:
                    self.reading[path] = silo_api_client.get_file(path)
            else:
                print(f'### {path} in files... get_file() NOT called!')

            # reading の正しい位置を切り出して buf に代入
            slen = len(self.reading[path])
            if offset < slen:
                if offset + size > slen:
                    size = slen - offset
                buf = self.reading[path][offset:offset+size]
        
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
        self.writing += buf 
        print(f'### writing: {len(self.writing)}')
        return len(buf)
    
    def flush(self, path, **kw):
        print(f"### flush() called! path: {path}, len(writing): {len(self.writing)}")

        if len(self.writing) == 0:
            print(f"### flush('{path}'), do nothing, len(writing) == 0")
            return 0
        else: # writing が空でなければデータをアップロード
            print(f"### flush('{path}'), call write_file(), len(writing) == {len(self.writing)} != 0")
            
            silo_api_client.write_file(path, self.writing)
            # writing を初期化
            self.writing = b""

            # write_file() 後すぐだと失敗するっぽいので少し待つ
            time.sleep(3)
            
            # flush() の呼び出し元で場合分け
            caller = kw.get('caller', None)
            if caller == 'mkdir':
                # .silo がある dir の上の dir の path を取得
                # 例) path = '/root/folder/.silo' > path_ppd = '/root/'
                path_ppd = pathmaker.parent_parent_dir_of(path)
                json_ppd = silo_api_client.get_json(path_ppd)

                # .silo がある dir の path から末尾の '/' を取り、
                # その dir の情報を files に追加
                path_pd_no_slash = pathmaker.parent_dir_of(path)[:-1]
                dir = next(filter(lambda f: f['filePath'] == path_pd_no_slash, json_ppd))
                self.files.append(dir)
            elif caller == 'rename':
                # flush したファイルがある dir の path を取得
                # 例) path = '/dir/file' > path_pd = '/dir/'
                path_pd = pathmaker.parent_dir_of(path)
                pd_json = silo_api_client.get_json(path_pd)
                print(f'### flush() by rename(), pd_json: {pd_json}')

                # フォルダの情報からアップロードした file の情報を抜き出して files に追記
                for f in pd_json:
                    if f['filePath'] == path:
                        self.files.append(f)
                        print(f'### flush() by rename(), renamed: {f}')                    
                    else:
                        pass
            else:
                # flush したファイルがある dir の path を取得
                # 例) path = '/dir/file' > path_pd = '/dir/'
                path_pd = pathmaker.parent_dir_of(path)
                pd_json = silo_api_client.get_json(path_pd)
                print(f'### flush() - No caller, pd_json: {pd_json}')

                # フォルダの情報からアップロードした file の情報を抜き出して files を更新
                # 更新前は create() が書いたダミーが入ってる
                for i, f in enumerate(self.files):
                    if f['filePath'] == path:
                        self.files[i] = next(filter(lambda file: file["filePath"] == path, pd_json))    
                        print(f'### flush() - update file: {self.files[i]}')                    
                    else:
                        pass
                # create() が作ったダミーに関するキャッシュを無効化
                super().Invalidate(path)
                print(f'### flush() and cache invalidated!')

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
        self.flush(path_new, caller='rename')

        # delete file at path_ole
        self.unlink(path_old)

        # Success
        return 0

    def create(self, path, mistery, mode):
        data = b'' # 空のバイト列を送信
        silo_api_client.write_file(path, data)

        # アップロードしたファイルの dir
        # 例) path = '/dir/new_file' > path_pd = '/dir/'
        path_pd = pathmaker.parent_dir_of(path)

        # バックオフ時間を管理するジェネレータ
        # = [1, 2, 4, 8, 16, 32, 64, 64, 64, ...]
        backoff = (2 ** power if power < 6 else 64 for power in range(7))

        while True:
            try:
                # アップロードしたファイルがある dir に get_json() して、
                # アップロードしたファイルの情報を取得
                files_pd = silo_api_client.get_json(path_pd)
                file = next(filter(lambda f: f['filePath'] == path, files_pd))
                break
            except StopIteration:
                bo_time = next(backoff)
                print(f'### create() re-excec backed off by {bo_time}')
                time.sleep(bo_time)
                continue

        self.files.append(file)

        print(f"### create() done. files: {self.files}")

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