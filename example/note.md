Goofys が実装している FUSE オペレーションは以下の通りです。

**コアオペレーション**:
* getattr: ファイル属性を取得
* readdir: ディレクトリ内のファイル一覧を取得
* open: ファイルを開く
* read: ファイルからデータを読み込む
* write: ファイルにデータ書き込む
* release: ファイルを閉じる
* flush: ファイルバッファをフラッシュ
* fsync: ファイルデータを同期
* lseek: ファイルポインタの位置を変更
* truncate: ファイルを切り詰める
* utimens: ファイルのタイムスタンプを変更
* fgetattr: 開いているファイルの属性を取得
* ftruncate: 開いているファイルを切り詰める
* fallocate: ファイル領域を割り当てる

**拡張オペレーション**:
* create: ファイルを作成
* unlink: ファイルを削除
* mkdir: ディレクトリを作成
* rmdir: ディレクトリを削除
* rename: ファイルまたはディレクトリの名前を変更
* link: ファイルへのハードリンクを作成
* symlink: シンボリックリンクを作成
* readlink: シンボリックリンクの参照先を取得
* chown: ファイルの所有者を変更
* chmod: ファイルのパーミッションを変更
* statfs: ファイルシステムの情報を取得
* getxattr: 拡張属性を取得
* listxattr: 拡張属性の一覧を取得
* setxattr: 拡張属性を設定
* removexattr: 拡張属性を削除

Goofys はこれらのオペレーションを使用して、Google Cloud Storage 上のファイルシステムを FUSE 経由でマウントします。

**参考資料**:
* Goofys documentation: https://github.com/kahing/goofys/blob/master/README.md