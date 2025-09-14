from functools import lru_cache
from .client import ConohaDNSClient
from .utils import normalize_domain, handle_api_error
import requests

from .id_converter import get_short_id

class DomainManager:
    def __init__(self, client: ConohaDNSClient):
        self.client = client

    @lru_cache(maxsize=1)
    def _fetch_all_domains(self):
        """全ドメインの情報をAPIから取得する（キャッシュ付き）"""
        return self.client.get("/v1/domains").get("domains", [])

    def get_domain_id_from_name(self, domain_name: str) -> str:
        """ドメイン名からドメインID(uuid)を検索して返す"""
        normalized_name = normalize_domain(domain_name)
        domains = self._fetch_all_domains()
        for domain in domains:
            if domain['name'] == normalized_name:
                return domain['uuid']
        raise ValueError(f"ドメイン '{normalized_name}' が見つかりませんでした。")

    def list_domains(self):
        try:
            domains = self._fetch_all_domains()
            print("ドメイン一覧:")
            if not domains:
                print("  (ドメインはありません)")
            for domain in domains:
                short_id = get_short_id(domain['uuid'])
                print(f"  ID: {short_id}, Name: {domain['name']}")
        except requests.exceptions.RequestException as e:
            handle_api_error(e)

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

    def delete_domain(self, domain_name: str):
        try:
            domain_id = self.get_domain_id_from_name(domain_name)
            print(f"ドメイン '{domain_name}' (ID: {domain_id}) を削除しています...")
            self.client.delete(f"/v1/domains/{domain_id}")
            print("ドメインが正常に削除されました。")
        except (ValueError, requests.exceptions.RequestException) as e:
            handle_api_error(e) if isinstance(e, requests.exceptions.RequestException) else print(f"エラー: {e}")
