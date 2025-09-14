# ConoHa DNS CLI

ConoHa DNSをコマンドラインから操作するためのツールです。

## インストール

はじめに、ConoHaの認証情報を記述した`.env`ファイルをプロジェクトルートに作成します。
`CONOHA_AUTH_URL`と`CONOHA_DNS_API_URL`は通常、以下の値で固定です。

```
CONOHA_USER_ID="your_user_id"
CONOHA_PASSWORD="your_password"
TENANT_ID="your_tenant_id"
CONOHA_AUTH_URL="https://identity.sample.conoha.io"
CONOHA_DNS_API_URL="https://dns-service.sample.conoha.io"
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
認証情報を使って新しいAPIトークンを取得し、`.env`ファイルに保存します。
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
