import argparse
import os
import sys
from dotenv import load_dotenv
from .client import ConohaDNSClient
from .domain import DomainManager
from .record import RecordManager


def validate_record_options(parser, record_type, priority=None, weight=None, port=None):
    normalized_type = record_type.upper()
    if normalized_type == "MX" and priority is None:
        parser.error("MXレコードには --priority の指定が必要です。")
    if normalized_type == "SRV":
        missing = []
        if priority is None:
            missing.append("--priority")
        if weight is None:
            missing.append("--weight")
        if port is None:
            missing.append("--port")
        if missing:
            parser.error(f"SRVレコードには {', '.join(missing)} の指定が必要です。")


def main():
    load_dotenv(dotenv_path=os.path.expanduser("~/.conoha-env"))
    epilog_text = """
使用例:
  # APIトークンを認証・取得
  conoha-dns --auth

  # APIトークンを強制的に再認証・更新
  conoha-dns --renew

  # ドメイン一覧表示
  conoha-dns -l

  # レコード一覧をCSV形式で標準出力
  conoha-dns -l example.com --output csv > records.csv

  # Aレコード追加 (サブドメインtestを補完してtest.example.comを追加)
  conoha-dns -ar example.com @ A 192.0.2.1
  conoha-dns -ar example.com test A 192.0.2.1
  conoha-dns -ar example.com mail MX mail.example.net. --priority 10
  conoha-dns -ar example.com _sip._tcp SRV sip.example.net. --priority 10 --weight 20 --port 5060

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
    group.add_argument("--renew", action="store_true", help="APIトークンを強制的に再認証・更新する")
    group.add_argument("-l", "--list", nargs='?', const=True, default=None, metavar="DOMAIN", help="ドメイン一覧または指定ドメインのレコード一覧表示")
    group.add_argument("-ad", "--add-domain", nargs=2, metavar=("NAME", "EMAIL"), help="ドメイン追加")
    group.add_argument("-dd", "--delete-domain", metavar="DOMAIN", help="ドメインを名前またはIDで削除")
    group.add_argument("-ar", "--add-record", nargs=4, metavar=("DOMAIN", "NAME", "TYPE", "DATA"), help="レコード追加")
    group.add_argument("-ur", "--update-record", nargs=2, metavar=("DOMAIN", "RECORD_ID"), help="レコード更新")
    group.add_argument("-dr", "--delete-record", nargs=2, metavar=("DOMAIN", "RECORD_ID"), help="レコード削除")
    
    # General options
    parser.add_argument("-t", "--ttl", type=int, default=300, help="レコード追加時のTTL(秒)。デフォルト: 300")
    parser.add_argument("-o", "--output", choices=['csv'], help="出力形式をCSVにします。'-l'での一覧表示時のみ有効です。")
    parser.add_argument("--priority", type=int, help="MX/SRVレコード追加時の優先度")
    parser.add_argument("--weight", type=int, help="SRVレコード追加時の重み")
    parser.add_argument("--port", type=int, help="SRVレコード追加時のポート番号")

    # Options for --update-record
    parser.add_argument("--new-name", help="更新後のレコード名")
    parser.add_argument("--new-type", help="更新後のレコードタイプ")
    parser.add_argument("--new-data", help="更新後のレコードデータ")
    parser.add_argument("--new-ttl", type=int, help="更新後のTTL")
    parser.add_argument("--new-priority", type=int, help="更新後の優先度")
    parser.add_argument("--new-weight", type=int, help="更新後の重み")
    parser.add_argument("--new-port", type=int, help="更新後のポート番号")

    args = parser.parse_args()

    try:
        if args.renew:
            client = ConohaDNSClient(renew=True)
            if client.token:
                print("APIトークンが正常に更新されました。")
            return

        if args.auth:
            client = ConohaDNSClient()
            if client.token:
                print("認証に成功し、APIトークンが利用可能です。")
            return

        client = ConohaDNSClient()
        domain_manager = DomainManager(client)
        record_manager = RecordManager(client, domain_manager)

        if args.list is not None:
            output_format = args.output
            if output_format and output_format != 'csv':
                 parser.error("現在サポートしている出力形式は'csv'のみです。")

            if args.list is True:
                domain_manager.list_domains(output_format=output_format)
            else:
                record_manager.list_records(args.list, output_format=output_format)
        elif args.add_domain:
            domain_manager.add_domain(args.add_domain[0], args.add_domain[1])
        elif args.delete_domain:
            domain_manager.delete_domain(args.delete_domain)
        elif args.add_record:
            validate_record_options(
                parser,
                args.add_record[2],
                priority=args.priority,
                weight=args.weight,
                port=args.port,
            )
            record_manager.add_record(
                args.add_record[0],
                args.add_record[1],
                args.add_record[2],
                args.add_record[3],
                args.ttl,
                priority=args.priority,
                weight=args.weight,
                port=args.port,
            )
        elif args.update_record:
            if not any([
                args.new_name,
                args.new_type,
                args.new_data,
                args.new_ttl is not None,
                args.new_priority is not None,
                args.new_weight is not None,
                args.new_port is not None,
            ]):
                parser.error("--update-recordには、--new-name, --new-type, --new-data, --new-ttl, --new-priority, --new-weight, --new-port のいずれか1つ以上の指定が必要です。")
            if args.new_type is not None:
                validate_record_options(
                    parser,
                    args.new_type,
                    priority=args.new_priority,
                    weight=args.new_weight,
                    port=args.new_port,
                )
            record_manager.update_record(
                args.update_record[0],
                args.update_record[1],
                new_name=args.new_name,
                new_type=args.new_type,
                new_data=args.new_data,
                new_ttl=args.new_ttl,
                new_priority=args.new_priority,
                new_weight=args.new_weight,
                new_port=args.new_port,
            )
        elif args.delete_record:
            record_manager.delete_record(args.delete_record[0], args.delete_record[1])
            
    except ValueError as e:
        print(f"エラー: {e}", file=sys.stderr)
        sys.exit(3)
    except Exception as e:
        print(f"予期せぬエラーが発生しました: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
