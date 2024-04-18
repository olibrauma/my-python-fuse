import requests
import json
import pathlib

CONFIG_PATH = pathlib.Path("~/.config/silo/config.json").expanduser()

class Silo:
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
        return f"{self.endpoint}/{path}"

    def get_json(self, path):
        url = self._build_url(path)

        try:
            response = requests.get(url)
            if response.status_code == 200:
                data = json.loads(response.text)
                for d in data:
                    d['filePath'] = d['filePath'][6:]
                print(f'### get_json() called! Response is {data}')
                return data
            else:
                print(f"Error: HTTP status code {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            return None

    def get_file(self, path):
        url = self._build_url(path)

        try:
            response = requests.get(url)
            if response.status_code == 200:
                print(f'### get_file() is called! Path is {path}')
                print(f'### get_file() called! Header Content-type is {response.headers["Content-Type"]}')
                return response.content
            else:
                print(f"Error: HTTP status code {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            return None

    def delete_file(self, path):
        url = self._build_url(path)

        try:
            response = requests.delete(url)
            if response.status_code == 204:
                print(f'### delete_file() is called! Path is {path}')
                print(f'### delete_file() called! Status code is {response.status_code}')
                return 0
            else:
                print(f"Error: HTTP status code {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            return None
