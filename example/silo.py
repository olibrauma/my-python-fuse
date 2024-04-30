from silo_api_client import SiloAPIClient
import re

CONFIG_PATH = '~/.config/silo/config.json'
silo_api_client = SiloAPIClient(CONFIG_PATH)

class Silo:
    def __init__(self):
        # Start Silo API Client
        self.__crops = silo_api_client.get_json('/')

    def __iter__(self):
        return SiloIterator(self.__crops)
    
    def stat(self, path):
        return next(filter(lambda c: c["filePath"] == path, self.__crops), None)
    
    def list(self, path='/'):
        # path = '/' の場合、次の正規表現でスラッシュが連続しないようにする
        path_ = path if path != '/' else ''
        # '{path}/.silo' 以外の '{path}/****' を抽出する
        p = rf"^{path_}/(?!.*\.silo$)"
        
        return list(filter(lambda c: re.search(p, c['filePath']) is not None, self.__crops))

    def fetch(self, path):
        return silo_api_client.get_file(path)
    
    def discard(self, path):
        if self.stat(path) is None:
            raise FileNotFoundError(f'File not found: {path}')
        else:
            silo_api_client.delete_file(path)
            self.__crops = list(filter(lambda c: c["filePath"] != path, self.__crops))
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