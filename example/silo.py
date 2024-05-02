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

    def haul(self, path, size, offset):
        if path not in self.__silage:
            self.__silage[path] = sac.get_file(path)
        
        return self.__silage[path][offset:offset + size]
    
    def empty(self, path):
        if self.stat(path) is None:
            raise FileNotFoundError(f'File not found: {path}')
        else:
            sac.delete_file(path)
            self.__silo = list(filter(lambda s: s["filePath"] != path, self))
            del self.__silage[path]
            return 0

    def load(self, path, buf, offset):        
        if path not in self.__silage:
            self.__silage[path] = b''

        self.__silage[path][offset:] += buf
        
        return len(buf)
    
    def fill(self, path):
        if len(self.__silage[path]) == 0:
            return 0
        else:
            sac.write_file(path, self.__silage[path])
            del self.__silage[path]
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