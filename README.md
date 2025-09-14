# ConoHa DNS CLI

ConoHa DNSをコマンドラインから操作するためのツールです。

```bash
$ conoha-dns -h
usage: conoha-dns [-h]
                  (--auth | -l | -ad NAME EMAIL | -dd DOMAIN_NAME | -lr DOMAIN_NAME | -ar DOMAIN_NAME NAME TYPE DATA | -ur DOMAIN_NAME RECORD_ID | -dr DOMAIN_NAME RECORD_ID)
                  [-t TTL] [--new-name NEW_NAME] [--new-type NEW_TYPE] [--new-data NEW_DATA]
                  [--new-ttl NEW_TTL]

ConoHa DNS API (v1) を操作するCLIツール

options:
  -h, --help            show this help message and exit
  --auth                APIトークンを認証・取得する
  -l, --list            ドメイン一覧表示
  -ad NAME EMAIL, --add-domain NAME EMAIL
                        ドメイン追加
  -dd DOMAIN_NAME, --delete-domain DOMAIN_NAME
                        ドメインを名前で削除
  -lr DOMAIN_NAME, --list-records DOMAIN_NAME
                        レコード一覧表示
  -ar DOMAIN_NAME NAME TYPE DATA, --add-record DOMAIN_NAME NAME TYPE DATA
                        レコード追加
  -ur DOMAIN_NAME RECORD_ID, --update-record DOMAIN_NAME RECORD_ID
                        レコード更新
  -dr DOMAIN_NAME RECORD_ID, --delete-record DOMAIN_NAME RECORD_ID
                        レコード削除
  -t TTL, --ttl TTL     レコード追加時のTTL(秒)。デフォルト: 300
  --new-name NEW_NAME   更新後のレコード名
  --new-type NEW_TYPE   更新後のレコードタイプ
  --new-data NEW_DATA   更新後のレコードデータ
  --new-ttl NEW_TTL     更新後のTTL

使用例:
  # APIトークンを認証・取得
  conoha-dns --auth

  # ドメイン一覧表示
  conoha-dns -l

  # レコード一覧表示
  conoha-dns -lr example.com

  # Aレコード追加 (サブドメインtestを補完してtest.example.comを追加)
  conoha-dns -ar example.com @ A 192.0.2.1
  conoha-dns -ar example.com test A 192.0.2.1

  # レコード更新 (レコードIDを指定し、新しいIPアドレスを設定)
  conoha-dns -ur example.com <record_id> --new-data 192.0.2.2

  # レコード削除 (レコードIDは -lr で確認)
  conoha-dns -dr example.com <record_id>
```

## インストール

はじめに、ConoHaの認証情報を記述した`~/.conoha-env`ファイルをホームディレクトリに作成します。
APIエンドポイントはConoHaのリージョンによって異なるため、適宜変更してください。  
[ConoHaコントロールパネル](https://cp.conoha.jp/VPS/API/)  の「API情報」から確認できます。  

**~/.conoha-env**:  
```
CONOHA_USER_ID="your_user_id"                             # API ユーザー: ユーザID
CONOHA_PASSWORD="your_password"                           # API ユーザー: パスワード
TENANT_ID="your_tenant_id"                                # テナント情報: テナントID	
CONOHA_AUTH_URL="https://identity.sample.conoha.io"       # エンドポイント: Identity Service URL
CONOHA_DNS_API_URL="https://dns-service.sample.conoha.io" # エンドポイント: DNS Service URL
```

次に、Makefileを使ってビルドとインストールを実行します。

```bash
make install
```

これにより、`conoha-dns`コマンドがインストールされます。

## 使い方

このコマンドは、実行したい操作をフラグで指定します。一度に指定できる操作は1つだけです。

### 一般的なコマンド

**ヘルプ表示**
```bash
conoha-dns -h
```

**認証**
認証情報を使って新しいAPIトークンを取得し、`~/.conoha-env`ファイルに保存します。
```bash
conoha-dns --auth
```

### ドメイン管理

**ドメイン一覧**
```bash
conoha-dns -l
```

**ドメイン追加**
```bash
conoha-dns -ad <ドメイン名> <メールアドレス>
```
*実行例:*
```bash
conoha-dns -ad example.com admin@example.com
```

**ドメイン削除**
```bash
conoha-dns -dd <ドメイン名>
```
*実行例:*
```bash
conoha-dns -dd example.com
```

### レコード管理

内部的に、ConoHa APIから取得したレコードIDは長いため、xxhashを用いて短いハッシュ値に変換して表示・利用しています。

**レコード一覧**
```bash
conoha-dns -lr <ドメイン名>
```
*実行例:*
```bash
conoha-dns -lr example.com
```

**レコード追加**
```bash
conoha-dns -ar <ドメイン名> <レコード名> <種別> <値> [--ttl <秒数>]
```
- `<レコード名>`: ルートドメインを指す場合は`@`を使用します。
- `--ttl`: 省略可能です。デフォルトは300秒です。

*実行例:*
```bash
# www.example.com のAレコードを追加
conoha-dns -ar example.com www A 192.0.2.1

# example.com のルートAレコードをTTL 600秒で追加
conoha-dns -ar example.com @ A 192.0.2.2 --ttl 600
```

**レコード更新**
`record_id`（`conoha-dns -lr <ドメイン名>`で確認可能）と、少なくとも1つの`--new-*`オプションを指定する必要があります。
```bash
conoha-dns -ur <ドメイン名> <record_id> [--new-name <名前>] [--new-type <種別>] [--new-data <値>] [--new-ttl <TTL>]
```
*実行例:*
```bash
# レコードのIPアドレスを更新
conoha-dns -ur example.com 0b8e19a2-a297-47f7-b3c8-a54d85382413 --new-data 198.51.100.5
```

**レコード削除**
```bash
conoha-dns -dr <ドメイン名> <record_id>
```
*実行例:*
```bash
conoha-dns -dr example.com 0b8e19a2-a297-47f7-b3c8-a54d85382413
```

## 応用例：xargsを使った一括操作

`xargs`と組み合わせることで、ファイルに記載されたドメインリストに対して一括で操作を実行できます。

例えば、以下のようなドメインリストが書かれた`domain-list.txt`があるとします。

**domain-list.txt**
```
example1.com
example2.com
example3.com
```

このファイル内の各ドメインに対して、一括でルートAレコードを追加するには、以下のコマンドを実行します。

```bash
cat domain-list.txt | xargs -I{} conoha-dns -ar {} @ A 192.0.2.1
```

これにより、`domain-list.txt`の各行が`{}`に代入され、ドメインごとにレコード追加コマンドが実行されます。
