import argparse
import os
from dotenv import load_dotenv
from .client import ConohaDNSClient
from .domain import DomainManager
from .record import RecordManager

def main():
    load_dotenv(dotenv_path=os.path.expanduser("~/.conoha-env"))
    epilog_text = """
使用例:
  # APIトークンを認証・取得
  conoha-dns --auth

  # ドメイン一覧表示
  conoha-dns -l

  # レコード一覧表示
  conoha-dns -l example.com

  # Aレコード追加 (サブドメインtestを補完してtest.example.comを追加)
  conoha-dns -ar example.com @ A 192.0.2.1
  conoha-dns -ar example.com test A 192.0.2.1

  # レコード更新 (レコードIDを指定し、新しいIPアドレスを設定)
  conoha-dns -ur example.com <record_id> --new-data 192.0.2.2

  # レコード削除 (レコードIDは -l example.com で確認)
  conoha-dns -dr example.com <record_id>
"""
    parser = argparse.ArgumentParser(
        description="ConoHa DNS API (v1) を操作するCLIツール",
        epilog=epilog_text,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group(required=True)

    # Actions
    group.add_argument("--auth", action="store_true", help="APIトークンを認証・取得する")
    group.add_argument("-l", "--list", nargs='?', const=True, default=None, metavar="DOMAIN_NAME", help="ドメイン一覧または指定ドメインのレコード一覧表示")
    group.add_argument("-ad", "--add-domain", nargs=2, metavar=("NAME", "EMAIL"), help="ドメイン追加")
    group.add_argument("-dd", "--delete-domain", metavar="DOMAIN_NAME", help="ドメインを名前で削除")
    group.add_argument("-ar", "--add-record", nargs=4, metavar=("DOMAIN_NAME", "NAME", "TYPE", "DATA"), help="レコード追加")
    group.add_argument("-ur", "--update-record", nargs=2, metavar=("DOMAIN_NAME", "RECORD_ID"), help="レコード更新")
    group.add_argument("-dr", "--delete-record", nargs=2, metavar=("DOMAIN_NAME", "RECORD_ID"), help="レコード削除")
    
    # General options
    parser.add_argument("-t", "--ttl", type=int, default=300, help="レコード追加時のTTL(秒)。デフォルト: 300")

    # Options for --update-record
    parser.add_argument("--new-name", help="更新後のレコード名")
    parser.add_argument("--new-type", help="更新後のレコードタイプ")
    parser.add_argument("--new-data", help="更新後のレコードデータ")
    parser.add_argument("--new-ttl", type=int, help="更新後のTTL")

    args = parser.parse_args()

    try:
        client = ConohaDNSClient()
        domain_manager = DomainManager(client)
        record_manager = RecordManager(client, domain_manager)

        if args.auth:
            if client.token:
                print("認証に成功し、APIトークンが利用可能です。")
        elif args.list is not None:
            if args.list is True:
                domain_manager.list_domains()
            else:
                record_manager.list_records(args.list)
        elif args.add_domain:
            domain_manager.add_domain(args.add_domain[0], args.add_domain[1])
        elif args.delete_domain:
            domain_manager.delete_domain(args.delete_domain)
        elif args.add_record:
            record_manager.add_record(args.add_record[0], args.add_record[1], args.add_record[2], args.add_record[3], args.ttl)
        elif args.update_record:
            if not any([args.new_name, args.new_type, args.new_data, args.new_ttl is not None]):
                parser.error("--update-recordには、--new-name, --new-type, --new-data, --new-ttl のいずれか1つ以上の指定が必要です。")
            record_manager.update_record(
                args.update_record[0],
                args.update_record[1],
                new_name=args.new_name,
                new_type=args.new_type,
                new_data=args.new_data,
                new_ttl=args.new_ttl
            )
        elif args.delete_record:
            record_manager.delete_record(args.delete_record[0], args.delete_record[1])
            
    except ValueError as e:
        print(f"エラー: {e}")
    except Exception as e:
        print(f"予期せぬエラーが発生しました: {e}")

if __name__ == "__main__":
    main()
