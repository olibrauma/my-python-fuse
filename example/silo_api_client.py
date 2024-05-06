import requests
import json
import pathlib
import urllib.parse
import magic

class SiloAPIClient:
    def __init__(self, config_path):
        config_file = pathlib.Path(config_path).expanduser()

        # ファイルを読み込む
        try:
            with open(config_file, "r") as f:
                self.config = json.load(f)
        except FileNotFoundError:
            print(f"Silo 設定ファイルが見つかりません: {config_file}")
            exit(1)

        # "endpoint" キーの値を取得
        if self.config.get("endpoint") is None:
            print("Silo 設定ファイルに 'endpoint' キーが見つかりません")
            exit(1)
        else:
            self.endpoint = self.config.get("endpoint")


    def _build_url(self, path):
        # path の先頭の '/' を削除
        path = path.lstrip('/')
        return f"{self.endpoint}{path}"

    def _format_raw_json(self, json):
        result = []
        for f in json:
            # 'filePath' 要素の先頭 6 字を削除
            f['filePath'] = f['filePath'][6:]
            
            # dir の 'filePath' と 'filename' の末尾 '/' を削除
            if f['isDirectory']:
                f['filePath'] = f['filePath'][:-1]
                f['filename'] = f['filename'][:-1]
            
            result.append(f)
        
        return result

    def _decode_percent(self, obj):
        if isinstance(obj, str):
            return urllib.parse.unquote(obj)
        elif isinstance(obj, list):
            return [self._decode_percent(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: self._decode_percent(value) for key, value in obj.items()}
        else:
            return obj
  
    def get_json(self, path='/'):
        url = self._build_url(path)
        print(f'### get_json() called! path: {path}, url: {url}')

        try:
            response = requests.get(url)
            if response.status_code == 200:
                files_raw = json.loads(response.text)
                files_fmt = self._format_raw_json(files_raw)
                files = self._decode_percent(files_fmt)

                print(f'### get_json() called! Response is {files}')
                return files
            else:
                print(f"Error: HTTP status code {response.status_code}")
                return []
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            return None

    def get_file(self, path, headers_wanted=False):
        url = self._build_url(path)
        print(f'### get_file() called! path: {path}, url: {url}')
        
        try:
            response = requests.get(url)
            if response.status_code == 200:
                print(f'### get_file() called! Path: {path}, status code: {response.status_code}, Content-type: {response.headers["Content-Type"]}')
                if headers_wanted:
                    return response.headers
                else:
                    return response.content
            else:
                print(f"Error: HTTP status code {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            return None

    def delete_file(self, path, is_directory=False):
        path_ = path + '/' if is_directory else path
        url = self._build_url(path_)
        print(f'### delete_file() called! path: {path_}, url: {url}')

        try:
            response = requests.delete(url)
            if response.status_code == 204:
                print(f'### delete_file() called! Path: {path_}, Status code: {response.status_code}')
                return 0
            else:
                return response.status_code
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            return None

    def write_file(self, path, data):
        url = self._build_url(path)
        print(f'### write_file() called! Path: {url}, len(data): {len(data)}')

        magic_ = magic.detect_from_content(data)
        headers = {'Content-type': magic_.mime_type}

        try:
            response = requests.put(url, data=data, headers=headers)
            if response.status_code == 200:
                print(f"### write_file() succeeded! url: {url}")
                return len(data)
            else:
                print(f"Error: HTTP status code {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            return None