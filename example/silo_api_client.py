import time
import requests
import json
import pathlib

CONFIG_PATH = pathlib.Path("~/.config/silo/config.json").expanduser()

class SiloAPIClient:
    def __init__(self):
        # ファイルを読み込む
        try:
            with open(CONFIG_PATH, "r") as f:
                self.config = json.load(f)
        except FileNotFoundError:
            print(f"Silo 設定ファイルが見つかりません: {CONFIG_PATH}")
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
    
    def _format_files(self, files):
        # files の 'filePath' 要素の先頭 6 字を削除
        files_1 = list(map(lambda f: f | {'filePath': f['filePath'][6:]}, files))

        # files の 'filePath' が '/' で終わる場合、それを削除
        files_2 = list(map(lambda f: f | {'filePath': f['filePath'][:-1]} if f['filePath'].endswith('/') else f, files_1))
        
        # files の 'filename' が '/' で終わる場合、それを削除
        files_3 = list(map(lambda f: f | {'filename': f['filename'][:-1]} if f['filename'].endswith('/') else f, files_2))

        # debug print
        return files_3
    
    def get_json(self, path):
        url = self._build_url(path)
        print(f'### get_json() called! path: {path}, url: {url}')

        try:
            response = requests.get(url)
            if response.status_code == 200:
                files_raw = json.loads(response.text)
                files = self._format_files(files_raw)

                print(f'### get_json() called! Response is {files}')
                return files
            else:
                print(f"Error: HTTP status code {response.status_code}")
                return None
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

    def delete_file(self, path):
        url = self._build_url(path)
        print(f'### delete_file() called! path: {path}, url: {url}')

        try:
            response = requests.delete(url)
            if response.status_code == 204:
                print(f'### delete_file() is called! Path is {path}')
                print(f'### delete_file() called! Status code is {response.status_code}')
                return 0
            else:
                return response.status_code
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            return None

    def write_file(self, path, data, mime_type):
        url = self._build_url(path)
        print(f'### write_file() is called! Path: {url}, len(data): {len(data)}')

        headers = {'Content-type': mime_type}

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