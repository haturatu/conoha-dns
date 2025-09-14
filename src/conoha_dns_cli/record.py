from .client import ConohaDNSClient
from .domain import DomainManager
from .utils import normalize_record_name, handle_api_error
import requests

class RecordManager:
    def __init__(self, client: ConohaDNSClient, domain_manager: DomainManager):
        self.client = client
        self.domain_manager = domain_manager

    def list_records(self, domain_name: str):
        try:
            domain_id = self.domain_manager.get_domain_id_from_name(domain_name)
            print(f"ドメイン '{domain_name}' のレコード一覧を取得しています...")
            records = self.client.get(f"/v1/domains/{domain_id}/records").get("records", [])
            print("レコード一覧:")
            if not records:
                print("  (レコードはありません)")
            for record in records:
                print(f"  ID: {record['uuid']}, Name: {record['name']}, Type: {record['type']}, Data: {record['data']}, TTL: {record['ttl']}")
        except (ValueError, requests.exceptions.RequestException) as e:
            handle_api_error(e) if isinstance(e, requests.exceptions.RequestException) else print(f"エラー: {e}")

    def add_record(self, domain_name: str, name: str, type: str, data: str, ttl: int):
        try:
            domain_id = self.domain_manager.get_domain_id_from_name(domain_name)
            normalized_name = normalize_record_name(domain_name, name)
            
            print(f"ドメイン '{domain_name}' にレコード '{normalized_name}' を追加しています...")
            payload = {"name": normalized_name, "type": type, "data": data, "ttl": ttl}
            record = self.client.post(f"/v1/domains/{domain_id}/records", payload)
            print("レコードが正常に追加されました。")
            print(f"  ID: {record['uuid']}, Name: {record['name']}, Type: {record['type']}, Data: {record['data']}")
        except (ValueError, requests.exceptions.RequestException) as e:
            handle_api_error(e) if isinstance(e, requests.exceptions.RequestException) else print(f"エラー: {e}")

    def delete_record(self, domain_name: str, record_id: str):
        try:
            domain_id = self.domain_manager.get_domain_id_from_name(domain_name)
            print(f"ドメイン '{domain_name}' からレコードID '{record_id}' を削除しています...")
            self.client.delete(f"/v1/domains/{domain_id}/records/{record_id}")
            print("レコードが正常に削除されました。")
        except (ValueError, requests.exceptions.RequestException) as e:
            handle_api_error(e) if isinstance(e, requests.exceptions.RequestException) else print(f"エラー: {e}")

    def get_record(self, domain_id: str, record_id: str):
        return self.client.get(f"/v1/domains/{domain_id}/records/{record_id}")

    def update_record(self, domain_name: str, record_id: str, new_name: str = None, new_type: str = None, new_data: str = None, new_ttl: int = None):
        try:
            domain_id = self.domain_manager.get_domain_id_from_name(domain_name)
            
            print(f"レコードID '{record_id}' の現在の情報を取得しています...")
            current_record = self.get_record(domain_id, record_id)
            
            name_to_update = new_name if new_name is not None else current_record['name']
            normalized_name = normalize_record_name(domain_name, name_to_update)

            payload = {
                "name": normalized_name,
                "type": new_type if new_type is not None else current_record['type'],
                "data": new_data if new_data is not None else current_record['data'],
                "ttl": new_ttl if new_ttl is not None else current_record.get('ttl'),
                "description": current_record.get('description'),
                "priority": current_record.get('priority')
            }
            
            if payload['ttl'] is None:
                del payload['ttl']

            print(f"レコードID '{record_id}' を更新しています...")
            updated_record = self.client.put(f"/v1/domains/{domain_id}/records/{record_id}", payload)
            
            print("レコードが正常に更新されました。")
            print(f"  ID: {updated_record['uuid']}, Name: {updated_record['name']}, Type: {updated_record['type']}, Data: {updated_record['data']}, TTL: {updated_record.get('ttl')}")

        except (ValueError, requests.exceptions.RequestException) as e:
            handle_api_error(e) if isinstance(e, requests.exceptions.RequestException) else print(f"エラー: {e}")
