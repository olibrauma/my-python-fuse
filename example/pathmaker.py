# path 操作のサポート関数集

def parent_dir_of(path):
    # 引数が示すファイルが存在する dir の path を返す
    # 例) path = '/root/new_file' > return '/root/'
    # 出力の最後の文字は '/'
    return path[:path.rfind('/') + 1] if '/' in path else path

def parent_parent_dir_of(path):
    # mkdir 後の場合、新しいフォルダを files に追加する
    # path を / で区切り、右から 2 つを削除する
    # 例) path = '/root/new_folder/.silo' > trimmed = '/folder/'
    # 出力の最後の文字は '/'
    parts = path.split('/')
    return '/'.join(parts[:len(parts) - 2] + ['']) if len(parts) > 2 else '/'

