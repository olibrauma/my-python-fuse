import requests
import json
import pathlib
import pprint

def get_json(path):
    # 設定ファイルパスを指定
    config_path = pathlib.Path("~/.config/silo/config.json").expanduser()

    # ファイルを読み込む
    try:
      with open(config_path, "r") as f:
        config = json.load(f)
    except FileNotFoundError:
      print("Silo 設定ファイルが見つかりません: ~/.config/silo/config.json")
      exit(1)

    # "url" キーの値を取得
    url = config.get("url")

    # url が存在するかどうかを確認
    if url is None:
      print("Silo 設定ファイルに 'url' キーが見つかりません")
      exit(1)

    # path の先頭の '/' を削除
    path.lstrip('/')
    url += path

    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = json.loads(response.text)
            for d in data:
               # print('### get_json() is called. FilePath is ' + d['filePath'])
               d['filePath'] = d['filePath'][6:]
               print('### get_json() called! Response is:')
               print(data)
            return data
        else:
            print(f"Error: HTTP status code {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None

def get_file(path):
    # 設定ファイルパスを指定
    config_path = pathlib.Path("~/.config/silo/config.json").expanduser()

    # ファイルを読み込む
    try:
      with open(config_path, "r") as f:
        config = json.load(f)
    except FileNotFoundError:
      print("Silo 設定ファイルが見つかりません: ~/.config/silo/config.json")
      exit(1)

    # "url" キーの値を取得
    url = config.get("url")

    # url が存在するかどうかを確認
    if url is None:
      print("Silo 設定ファイルに 'url' キーが見つかりません")
      exit(1)

    # path の先頭の '/' を削除
    path.lstrip('/')
    url += path

    try:
        response = requests.get(url)
        if response.status_code == 200:
            print(f'### get_file() is called! Path is {path}')
            print(f'### get_file() called! Header Content-type is {response.headers['Content-Type']}')
            return response.content
        else:
            print(f"Error: HTTP status code {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None

def delete_file(path):
    # 設定ファイルパスを指定
    config_path = pathlib.Path("~/.config/silo/config.json").expanduser()

    # ファイルを読み込む
    try:
      with open(config_path, "r") as f:
        config = json.load(f)
    except FileNotFoundError:
      print("Silo 設定ファイルが見つかりません: ~/.config/silo/config.json")
      exit(1)

    # "url" キーの値を取得
    url = config.get("url")

    # url が存在するかどうかを確認
    if url is None:
      print("Silo 設定ファイルに 'url' キーが見つかりません")
      exit(1)

    # path の先頭の '/' を削除
    path.lstrip('/')
    url += path

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