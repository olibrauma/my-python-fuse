from functools import reduce
import time
from silo_api_client import SiloAPIClient
import re

CONFIG_PATH = '~/.config/silo/config.json'
sac = SiloAPIClient(CONFIG_PATH)

class Silo:
    def __init__(self):
        # Start Silo API Client
        self.__silo = sac.get_json()
        self.__silage = {}

    def __iter__(self):
        return SiloIterator(self.__silo)
    
    def stat(self, path):
        return next(filter(lambda s: s["filePath"] == path, self), None)
    
    def list(self, path='/'):
        # path = '/' の場合、次の正規表現でスラッシュが連続しないようにする
        path_ = path if path != '/' else ''
        # '{path}/.silo' 以外の '{path}/****' を抽出する
        p = rf"^{path_}/(?!.*\.silo$)"
        
        return list(filter(lambda s: re.search(p, s['filePath']) is not None, self))
    
    # path と遡上階数を指定して silo に json を追加
    # 0. フォルダ化: '/hoge/fuga' > '/hoge/fuga/'
    # 1. 遡上:      '/hoge/fuga' > '/hoge/'
    # 2. 2 つ遡上:   '/hoge/fuga' > '/'
    def add(self, path, backtrack=0):
        def _backtrack(path, count):
            if count < 1:
                return path + '/'
            else:
                path_list = path.split('/')
                path_list.pop()
                new_path = '/'.join(path_list)
                return _backtrack(new_path, count - 1)
        
        path_ = _backtrack(path, backtrack)
        self.__silo += sac.get_json(path_)
        self.__silo = self._unique()
        return 0

    def _unique(self):
        return reduce(
            lambda acc, x: acc + [x] if x['filePath'] not in [y['filePath'] for y in acc] else acc, 
            self, [])

    def haul(self, path, size, offset):
        if path not in self.__silage:
            self.__silage[path] = sac.get_file(path)
        
        print(f'### haul() - path: {path}, from {offset} to {offset + size} in {len(self.__silage[path])}')
        return self.__silage[path][offset:offset + size]
    
    def empty(self, path):
        if self.stat(path) is None:
            raise FileNotFoundError(f'File not found: {path}')
        else:
            sac.delete_file(path)
            self.__silo = list(filter(lambda s: s["filePath"] != path, self))
            if path not in self.__silage:
                del self.__silage[path]
            return 0

    def load(self, path, buf, offset):
        if path not in self.__silage:
            self.__silage[path] = b''

        self.__silage[path] += buf
        
        return len(buf)
    
    def fill(self, path, **kw):
        caller = kw.get('caller', None)
        print(caller)

        if caller == 'create':
            sac.write_file(path, self.__silage[path])
            while self.stat(path) is None:
                self.add(path, 1)

        elif caller == 'mkdir':
            sac.write_file(path, self.__silage[path])
            self.add(path, 2)
        
        elif caller == 'copy':
            sac.write_file(path, self.__silage[path])
            while self.stat(path) is None:
                self.add(path, 1)
        
        elif self.stat(path)['contentLength'] == len(self.__silage[path]):
            print(f'### fill() - do nothing for path: {path}')
            return 0
        else:
            sac.write_file(path, self.__silage[path])

        return 0
    
    def copy(self, path_old, path_new):
        if self.__silage[path_old] is None:
            self.__silage[path_old] = sac.get_file(path_old)

        self.__silage[path_new] = self.__silage[path_old]
        self.fill(path_new, caller='copy')
        return 0

class SiloIterator:
    def __init__(self, silo_):
        self.silo = silo_
        self.index = 0
    
    def __next__(self):
        if self.index < len(self.silo):
            s = self.silo[self.index]
            self.index += 1
            return s
        else:
            raise StopIteration