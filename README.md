# ConoHa DNS CLI

ConoHa DNSをコマンドラインから操作するためのツールです。

デフォルトでは見やすいテーブル形式で一覧表示し、`--output csv` オプションを指定することでCSVファイルとして保存することもできます。

# ConoHa DNS CLI

ConoHa DNSをコマンドラインから操作するためのツールです。

デフォルトでは見やすいテーブル形式で一覧表示し、`--output csv` オプションを指定することでCSV形式で標準出力することもできます。

```bash
$ conoha-dns -h
usage: conoha-dns [-h] [-t TTL] [-o {csv}] [--new-name NEW_NAME] [--new-type NEW_TYPE] [--new-data NEW_DATA] [--new-ttl NEW_TTL]
                  (--auth | -l [DOMAIN] | -ad NAME EMAIL | -dd DOMAIN | -ar DOMAIN NAME TYPE DATA | -ur DOMAIN RECORD_ID | -dr DOMAIN RECORD_ID)

ConoHa DNS API (v1) を操作するCLIツール

options:
  -h, --help            show this help message and exit
  -t TTL, --ttl TTL     レコード追加時のTTL(秒)。デフォルト: 300
  -o {csv}, --output {csv}
                        出力形式をCSVにします。'-l'での一覧表示時のみ有効です。
  --new-name NEW_NAME   更新後のレコード名
  --new-type NEW_TYPE   更新後のレコードタイプ
  --new-data NEW_DATA   更新後のレコードデータ
  --new-ttl NEW_TTL     更新後のTTL

mutually exclusive arguments:
  --auth                APIトークンを認証・取得する
  -l [DOMAIN], --list [DOMAIN]
                        ドメイン一覧または指定ドメインのレコード一覧表示
  -ad NAME EMAIL, --add-domain NAME EMAIL
                        ドメイン追加
  -dd DOMAIN, --delete-domain DOMAIN
                        ドメインを名前またはIDで削除
  -ar DOMAIN NAME TYPE DATA, --add-record DOMAIN NAME TYPE DATA
                        レコード追加
  -ur DOMAIN RECORD_ID, --update-record DOMAIN RECORD_ID
                        レコード更新
  -dr DOMAIN RECORD_ID, --delete-record DOMAIN RECORD_ID
                        レコード削除

使用例:
  # APIトークンを認証・取得
  conoha-dns --auth

  # ドメイン一覧をテーブル表示
  conoha-dns -l

  # レコード一覧をテーブル表示 (ドメイン名またはIDで指定)
  conoha-dns -l example.com

  # レコード一覧をCSV形式で標準出力
  conoha-dns -l example.com --output csv > records.csv

  # Aレコード追加
  conoha-dns -ar example.com @ A 192.0.2.1
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
ドメインを指定する引数 (DOMAIN) には、ドメイン名 (`example.com`) またはドメインID (`ba9b5b9d`など) の両方を使用できます。

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

### ドメイン・レコード管理

**ドメイン一覧・レコード一覧**

`-l` フラグを使用すると、一覧がテーブル形式で表示されます。表示の際にデータが省略されることはありません。

```bash
# ドメイン一覧
conoha-dns -l

# レコード一覧 (ドメイン名またはIDで指定)
conoha-dns -l <ドメイン名/ID>
```
*実行例:*
```bash
$ conoha-dns -l
  ID         Name                          
  0e6f0695   soulminingrig.com.            
  4fb208de   eyes4you.org.                 
  ...
```

**CSV形式での標準出力**

`--output csv` オプションを追加すると、一覧をCSV形式で標準出力します。リダイレクト(`>`)を使えばファイルに保存できます。

```bash
# ドメイン一覧をCSVで標準出力
conoha-dns -l --output csv

# レコード一覧をCSVファイルとして保存
conoha-dns -l <ドメイン名/ID> --output csv > records.csv
```
*実行例:*
```bash
$ conoha-dns -l example.com --output csv
ID,Name,Type,Data,TTL
5057adde,eye4u.org.,SOA,"a.conoha-dns.com. taro.eyes4you.org. 1757833524 3600 600 86400 3600",3600
2eff1245,eye4u.org.,NS,a.conoha-dns.com.,3600
...
```

**ドメイン追加**
```bash
conoha-dns -ad <ドメイン名> <メールアドレス>
```

**ドメイン削除**
```bash
conoha-dns -dd <ドメイン名/ID>
```

### レコード管理

内部的に、ConoHa APIから取得したレコードIDは長いため、xxhashを用いて短いハッシュ値に変換して表示・利用しています。

**レコード追加**
```bash
conoha-dns -ar <ドメイン名/ID> <レコード名> <種別> <値> [--ttl <秒数>]
```

**レコード更新**
`record_id`（`conoha-dns -l <ドメイン名/ID>`で確認可能）と、少なくとも1つの`--new-*`オプションを指定する必要があります。
```bash
conoha-dns -ur <ドメイン名/ID> <record_id> [--new-name <名前>] [--new-type <種別>] [--new-data <値>] [--new-ttl <TTL>]
```

**レコード削除**
```bash
conoha-dns -dr <ドメイン名/ID> <record_id>
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
ドメインを指定する引数 (DOMAIN) には、ドメイン名 (`example.com`) またはドメインID (`ba9b5b9d`など) の両方を使用できます。

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

### ドメイン・レコード管理

**ドメイン一覧・レコード一覧**

`-l` フラグを使用すると、一覧がテーブル形式で表示されます。

```bash
# ドメイン一覧
conoha-dns -l

# レコード一覧 (ドメイン名またはIDで指定)
conoha-dns -l <ドメイン名/ID>
```
*実行例:*
```bash
$ conoha-dns -l
  ID         Name                          
  0e6f0695   soulminingrig.com.            
  4fb208de   eyes4you.org.                 
  ...
```

**CSVファイルへの保存**

`--output csv` オプションを追加すると、一覧をCSVファイルとしてカレントディレクトリに保存します。
- ドメイン一覧の場合: `domains.csv`
- レコード一覧の場合: `ドメイン名.csv` (例: `example.com.csv`)

```bash
# ドメイン一覧をCSVに保存
conoha-dns -l --output csv

# レコード一覧をCSVに保存
conoha-dns -l <ドメイン名/ID> --output csv
```
*実行例:*
```bash
$ conoha-dns -l example.com --output csv
レコード一覧を example.com.csv に保存しています...
保存が完了しました: example.com.csv
```

**ドメイン追加**
```bash
conoha-dns -ad <ドメイン名> <メールアドレス>
```

**ドメイン削除**
```bash
conoha-dns -dd <ドメイン名/ID>
```

### レコード管理

内部的に、ConoHa APIから取得したレコードIDは長いため、xxhashを用いて短いハッシュ値に変換して表示・利用しています。

**レコード追加**
```bash
conoha-dns -ar <ドメイン名/ID> <レコード名> <種別> <値> [--ttl <秒数>]
```

**レコード更新**
`record_id`（`conoha-dns -l <ドメイン名/ID>`で確認可能）と、少なくとも1つの`--new-*`オプションを指定する必要があります。
```bash
conoha-dns -ur <ドメイン名/ID> <record_id> [--new-name <名前>] [--new-type <種別>] [--new-data <値>] [--new-ttl <TTL>]
```

**レコード削除**
```bash
conoha-dns -dr <ドメイン名/ID> <record_id>
```
