from functools import reduce
import time
from silo_api_client import SiloAPIClient
import re

CONFIG_PATH = '~/.config/silo/config.json'
sac = SiloAPIClient(CONFIG_PATH)

class Silo:
    def __init__(self):
        self.__silo = []
        self.scan()

    def __iter__(self):
        return SiloIterator(self.__silo)
    
    def stat(self, path):
        return next(filter(lambda s: s["filePath"] == path, self), None)
    
    def index(self, path):
        list_ = list(filter(lambda x: x[1]['filePath'] == path, enumerate(self)))
        return next(map(lambda x: x[0], list_), None)
        
    def list(self, path='/'):
        # path = '/' の場合、次の正規表現でスラッシュが連続しないようにする
        path_ = path if path != '/' else ''
        # '{path}/.silo' 以外の '{path}/****' を抽出する
        p = rf"^{path_}/(?!.*\.silo$)"
        filter_ = filter(lambda s: re.search(p, s['filePath']) is not None, self)
 
        return list(filter_)

    # path = '/hoge/fuga' > path_ = '/hoge/'
    def scan(self, path='/'):
        path_list = path.split('/')
        path_list.pop()
        path_ = '/'.join(path_list) + '/'
        
        self.__silo += sac.get_json(path_)
        self.__silo = self._unique()
        return 0

    def _unique(self):
        seen = {}
        # seen = {"path_1": {crop_1}, "path_2": {crop_2}, ...}
        for crop in self:
            if crop['filePath'] not in seen:
                seen[crop['filePath']] = crop
            else:
                # 既に同じキーがあれば createdTime の遅い方でマージ
                seen_crop = seen[crop['filePath']]
                if crop['createdTime'] > seen_crop['createdTime']:
                    seen[crop['filePath']] = seen_crop | crop
                else:
                    seen[crop['filePath']] = crop | seen_crop
        return list(seen.values())

    def draw(self, path, size, offset):
        self.content(path)
        return self.stat(path)['content'][offset:offset + size]

    def content(self, path):
        i = self.index(path)
        if self.__silo[i].get('content') is None:
            self.__silo[i]['content'] = sac.get_file(path)
            print(f'### content() - len: {len(self.__silo[i]['content'])}')
        return 

    def empty(self, path):
        crop = self.stat(path)
        
        if crop is None:
            return 0
        elif not crop['isDirectory']:
            sac.delete_file(path)
            i = self.index(path)
            del self.__silo[i]
        else:
            if self.stat(path + '/.silo') is not None:
                self.empty(path + '/.silo')

            sac.delete_file(path + '/')
            i = self.index(path)
            del self.__silo[i]

        filePaths = list(map(lambda s: s['filePath'], self))
        print(f'### empty() - filePaths: {filePaths}')
        return 0

    def buffer(self, path, buf, offset):
        i = self.index(path)

        if self.__silo[i].get('content') is None:
            self.__silo[i]['content'] = b''

        self.__silo[i]['content'] += buf
        
        return len(buf)
    
    def put(self, path):
        data = b''
        blank_write = True # 空書き込みかどうか

        crop = self.stat(path)
        if crop is not None:
            if crop.get('content') is not None:
                data = crop.get('content')
                blank_write = False
        print(f'### put() - path: {path}, len(data): {len(data)}')
        
        sac.write_file(path, data)
        
        if blank_write:
            while self.stat(path) is None:
                self.scan(path)
        else:
            while self.stat(path)['contentLength'] == 0:
                self.scan(path)
        return 0
    
    def copy(self, path_old, path_new):
        self.content(path_old)
        i_old = self.index(path_old)
        
        self.put(path_new)
        self.buffer(path_new, self.__silo[i_old]['content'], 0)
        self.put(path_new)
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