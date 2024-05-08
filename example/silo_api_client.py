import requests
import json
import pathlib
import urllib.parse
import magic

class SiloAPIClient:
    __endpoint = None
    __endpoint_set = False

    @classmethod
    def set_endpoint(cls, config_path):
        if not cls.__endpoint_set:
            config_file = pathlib.Path(config_path).expanduser()

            try:
                with open(config_file, "r") as f:
                    config = json.load(f)
            except FileNotFoundError:
                print(f"Silo 設定ファイルが見つかりません: {config_file}")
                exit(1)

            if config.get("endpoint") is None:
                print("Silo 設定ファイルに 'endpoint' キーが見つかりません")
                exit(1)
            else:
                cls.__endpoint = config.get("endpoint")
                cls.__endpoint_set = True
        else:
            print("Class variable has already been set and cannot be changed.")

    @classmethod
    def _build_url(cls, path):
        path = path.lstrip('/')
        return f"{cls.__endpoint}{path}"

    @classmethod
    def _format_raw_json(cls, json_data):
        result = []
        for f in json_data:
            f['filePath'] = f['filePath'][6:]

            if f['isDirectory']:
                f['filePath'] = f['filePath'][:-1]
                f['filename'] = f['filename'][:-1]

            result.append(f)

        return result

    @classmethod
    def _decode_percent(cls, obj):
        if isinstance(obj, str):
            return urllib.parse.unquote(obj)
        elif isinstance(obj, list):
            return [cls._decode_percent(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: cls._decode_percent(value) for key, value in obj.items()}
        else:
            return obj

    @classmethod
    def get_json(cls, path='/'):
        url = cls._build_url(path)
        print(f'### get_json() called! path: {path}, url: {url}')

        try:
            response = requests.get(url)
            if response.status_code == 200:
                files_raw = json.loads(response.text)
                files_fmt = cls._format_raw_json(files_raw)
                files = cls._decode_percent(files_fmt)

                print(f'### get_json() called! Response is {files}')
                return files
            else:
                print(f"Error: HTTP status code {response.status_code}")
                return []
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            return None

    @classmethod
    def get_file(cls, path, headers_wanted=False):
        url = cls._build_url(path)
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

    @classmethod
    def delete_file(cls, path):
        url = cls._build_url(path)
        print(f'### delete_file() called! path: {path}, url: {url}')

        try:
            response = requests.delete(url)
            if response.status_code == 204:
                print(f'### delete_file() called! Path: {path}, Status code: {response.status_code}')
                return 0
            else:
                return response.status_code
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            return None

    @classmethod
    def write_file(cls, path, data):
        url = cls._build_url(path)
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
