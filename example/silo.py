from silo_api_client import SiloAPIClient
import re

CONFIG_PATH = '~/.config/silo/config.json'
sac = SiloAPIClient(CONFIG_PATH)

class Silo:
    def __init__(self):
        # Start Silo API Client
        self.__crops = sac.get_json()
        self.__crates = {}

    def __iter__(self):
        return SiloIterator(self.__crops)
    
    def stat(self, path):
        return next(filter(lambda crop: crop["filePath"] == path, self), None)
    
    def list(self, path='/'):
        # path = '/' の場合、次の正規表現でスラッシュが連続しないようにする
        path_ = path if path != '/' else ''
        # '{path}/.silo' 以外の '{path}/****' を抽出する
        p = rf"^{path_}/(?!.*\.silo$)"
        
        return list(filter(lambda crop: re.search(p, crop['filePath']) is not None, self))

    def haul(self, path, size, offset):
        path_ = hash(path)

        if path_ not in self.__crates:
            self.__crates[path_] = sac.get_file(path)
        
        return self.__crates[path_][offset:offset + size]
    
    def ditch(self, path):
        if self.stat(path) is None:
            raise FileNotFoundError(f'File not found: {path}')
        else:
            sac.delete_file(path)
            self.__crops = list(filter(lambda crop: crop["filePath"] != path, self))
            return 0

    def feed(self, path, buf, offset):
        path_ = hash(path)
        
        if path_ not in self.__crates:
            self.__crates[path_] = b''

        self.__crates[path_][offset:] += buf
        
        return len(buf)
    
    def put(self, path):
        path_ = hash(path)

        if len(self.__crates[path_]) == 0:
            return 0
        else:
            sac.write_file(path, self.__crates[path_])
            del self.__crates[path_]
            return 0

class SiloIterator:
    def __init__(self, crops):
        self.crops = crops
        self.index = 0
    
    def __next__(self):
        if self.index < len(self.crops):
            crop = self.crops[self.index]
            self.index += 1
            return crop
        else:
            raise StopIteration