from functools import lru_cache
from .client import ConohaDNSClient
from .utils import normalize_domain, handle_api_error
import requests
import sys
import csv

from .id_converter import get_short_id

def is_short_id(s: str) -> bool:
    """短いID（8文字の16進数文字列）かどうかを判定する"""
    if len(s) != 8:
        return False
    try:
        int(s, 16)
        return True
    except ValueError:
        return False

class DomainManager:
    def __init__(self, client: ConohaDNSClient):
        self.client = client

    @lru_cache(maxsize=1)
    def _fetch_all_domains(self):
        """全ドメインの情報をAPIから取得する（キャッシュ付き）"""
        return self.client.get("/v1/domains").get("domains", [])

    def get_domain_id(self, identifier: str) -> str:
        """ドメイン名またはIDからドメインID(uuid)を検索して返す"""
        domains = self._fetch_all_domains()

        # 1. IDとして一致するものを探す
        if is_short_id(identifier):
            for domain in domains:
                if get_short_id(domain['uuid']) == identifier:
                    return domain['uuid']

        # 2. ドメイン名として一致するものを探す
        normalized_name = normalize_domain(identifier)
        for domain in domains:
            if domain['name'] == normalized_name:
                return domain['uuid']

        raise ValueError(f"ドメイン '{identifier}' が見つかりませんでした。")

    def get_domain_name_from_id(self, domain_id: str) -> str:
        """ドメインID(uuid)からドメイン名を検索して返す"""
        domains = self._fetch_all_domains()
        for domain in domains:
            if domain['uuid'] == domain_id:
                return domain['name']
        raise ValueError(f"ドメインID '{domain_id}' が見つかりませんでした。")

    def list_domains(self, output_format: str = None):
        try:
            domains = self._fetch_all_domains()

            if output_format == 'csv':
                print("ドメイン一覧をCSV形式で出力します...", file=sys.stderr)
                if not domains:
                    print("  (ドメインはありません)", file=sys.stderr)
                    return
                writer = csv.writer(sys.stdout)
                writer.writerow(['ID', 'Name'])
                for domain in domains:
                    short_id = get_short_id(domain['uuid'])
                    writer.writerow([short_id, domain['name']])
            else:
                if not domains:
                    print("  (ドメインはありません)")
                    return

                header = f"  {'ID':<10} {'Name':<30}"
                print(header)
                print(f"  {'-'*10} {'-'*30}")
                for domain in domains:
                    short_id = get_short_id(domain['uuid'])
                    print(f"  {short_id:<10} {domain['name']:<30}")

        except requests.exceptions.RequestException as e:
            handle_api_error(e)
        except IOError as e:
            print(f"ファイル書き込みエラー: {e}", file=sys.stderr)

    def add_domain(self, name: str, email: str):
        normalized_name = normalize_domain(name)
        print(f"ドメイン '{normalized_name}' を追加しています...")
        payload = {"name": normalized_name, "email": email}
        try:
            domain = self.client.post("/v1/domains", payload)
            print("ドメインが正常に追加されました。")
            print(f"  ID: {domain['uuid']}, Name: {domain['name']}")
        except requests.exceptions.RequestException as e:
            handle_api_error(e)

    def delete_domain(self, identifier: str):
        try:
            domain_id = self.get_domain_id(identifier)
            domain_name = self.get_domain_name_from_id(domain_id)
            print(f"ドメイン '{domain_name}' (ID: {domain_id}) を削除しています...")
            self.client.delete(f"/v1/domains/{domain_id}")
            print("ドメインが正常に削除されました。")
        except (ValueError, requests.exceptions.RequestException) as e:
            handle_api_error(e) if isinstance(e, requests.exceptions.RequestException) else print(f"エラー: {e}")
