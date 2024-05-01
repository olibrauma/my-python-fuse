from silo_api_client import SiloAPIClient
import re, magic

CONFIG_PATH = '~/.config/silo/config.json'
sac = SiloAPIClient(CONFIG_PATH)

class Silo:
    def __init__(self):
        # Start Silo API Client
        self.__crops = sac.get_json('/')
        self.__crate = {}

    def __iter__(self):
        return SiloIterator(self.__crops)
    
    def stat(self, path):
        return next(filter(lambda c: c["filePath"] == path, self), None)
    
    def list(self, path='/'):
        # path = '/' の場合、次の正規表現でスラッシュが連続しないようにする
        path_ = path if path != '/' else ''
        # '{path}/.silo' 以外の '{path}/****' を抽出する
        p = rf"^{path_}/(?!.*\.silo$)"
        
        return list(filter(lambda c: re.search(p, c['filePath']) is not None, self))

    def fetch(self, path):
        return sac.get_file(path)
    
    def discard(self, path):
        if self.stat(path) is None:
            raise FileNotFoundError(f'File not found: {path}')
        else:
            sac.delete_file(path)
            self.__crops = list(filter(lambda c: c["filePath"] != path, self))
            return 0

    def pack(self, path, buf, offset):
        path_ = hash(path)
        
        if path_ not in self.__crate:
            self.__crate[path_] = b''

        self.__crate[path_] += buf
        
        return len(buf)
    
    def store(self, path):
        path_ = hash(path)

        if len(self.__crate[path_]) == 0:
            return 0
        else:
            file_magic = magic.detect_from_content(self.__crate[path_])
            sac.write_file(path, self.__crate[path_], file_magic.mime_type)
            del self.__crate[path_]
            return self.__crate

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