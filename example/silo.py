from functools import reduce
import time
from silo_api_client import SiloAPIClient
import re

CONFIG_PATH = '~/.config/silo/config.json'
sac = SiloAPIClient(CONFIG_PATH)

class Silo:
    def __init__(self):
        self.__silo = sac.get_json()        

    def __iter__(self):
        return SiloIterator(self.__silo)
    
    def stat(self, path):
        return next(filter(lambda s: s["filePath"] == path, self), None)
    
    def index(self, path):
        return [i for i, n in enumerate(self) if n['filePath'] == path].pop()
        
    def list(self, path='/'):
        # path = '/' の場合、次の正規表現でスラッシュが連続しないようにする
        path_ = path if path != '/' else ''
        # '{path}/.silo' 以外の '{path}/****' を抽出する
        p = rf"^{path_}/(?!.*\.silo$)"
        list_ = list(filter(lambda s: re.search(p, s['filePath']) is not None, self))
        
        # 対象のフォルダ以下のファイルを知らなければ取得して再抽出
        if len(list_) == 0:
            self.sync(path + '/')
            list_ = list(filter(lambda s: re.search(p, s['filePath']) is not None, self))

        return list_

    # path = '/hoge/fuga' > path_ = '/hoge/'
    def sync(self, path):
        path_list = path.split('/')
        path_list.pop()
        path_ = '/'.join(path_list) + '/'
        
        self.__silo += sac.get_json(path_)
        self.__silo = self._unique()
        return 0

    def _unique(self):
        return reduce(
            lambda acc, x: acc + [x] if x['filePath'] not in [y['filePath'] for y in acc] else acc, 
            self, [])

    def haul(self, path, size, offset):
        if self.stat(path).get('content', None) is None:
            self.content(path)
        return self.stat(path)['content'][offset:offset + size]

    def content(self, path):
        i = self.index(path)
        if self.__silo[i].get('content', None) is None:
            self.__silo[i]['content'] = sac.get_file(path)
            print(f'### content() - len: {len(self.__silo[i]['content'])}')
        return 

    def empty(self, path):
        crop = self.stat(path)
        if crop is None:
            raise FileNotFoundError(f'File not found: {path}')
        else:
            sac.delete_file(path)
            self.__silo = list(filter(lambda s: s["filePath"] != path, self))
            return 0

    def load(self, path, buf, offset):
        i = self.index(path)

        if self.__silo[i].get('content', None) is None:
            self.__silo[i]['content'] = b''

        self.__silo[i]['content'] += buf
        
        return len(buf)
    
    def fill(self, path, **kw):
        caller = kw.get('caller', None)
        print(caller)

        if caller == 'create':
            sac.write_file(path, b'')
            while self.stat(path) is None:
                self.sync(path)

        elif caller == 'mkdir': # path は作りたいフォルダ
            sac.write_file(path + '/.silo', b'Silo blank file')
            while self.stat(path) is None:
                self.sync(path)
        
        elif caller == 'copy':
            sac.write_file(path, kw.get('data'))
            while self.stat(path) is None:
                self.sync(path)
        
        elif self.stat(path)['contentLength'] == len(self.__silo[self.index(path)]['content']):
            print(f'### fill() - do nothing for path: {path}')
            return 0
        else:
            sac.write_file(path, self.__silo[self.index(path)]['content'])

        return 0
    
    def copy(self, path_old, path_new):
        i_old = self.index(path_old)

        if self.__silo[i_old].get('content', None) is None:
            self.content(path_old)

        self.fill(path_new, caller = 'copy', data = self.__silo[i_old]['content'])
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