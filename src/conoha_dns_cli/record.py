from .client import ConohaDNSClient
from .domain import DomainManager
from .utils import normalize_record_name, handle_api_error
from .id_converter import get_short_id, find_full_uuid
import requests
import sys
import csv

class RecordManager:
    def __init__(self, client: ConohaDNSClient, domain_manager: DomainManager):
        self.client = client
        self.domain_manager = domain_manager

    def _get_all_records(self, domain_id: str) -> list:
        return self.client.get(f"/v1/domains/{domain_id}/records").get("records", [])

    def list_records(self, identifier: str, output_format: str = None):
        try:
            domain_id = self.domain_manager.get_domain_id(identifier)
            domain_name = self.domain_manager.get_domain_name_from_id(domain_id).rstrip('.')
            records = self._get_all_records(domain_id)

            if output_format == 'csv':
                if not records:
                    print("  (レコードはありません)", file=sys.stderr)
                    return
                writer = csv.writer(sys.stdout)
                writer.writerow(['ID', 'Name', 'Type', 'Data', 'TTL'])
                for record in records:
                    short_id = get_short_id(record['uuid'])
                    writer.writerow([short_id, record['name'], record['type'], record['data'], record['ttl']])
            else:
                if not records:
                    print("  (レコードはありません)")
                    return

                # カラムの最大幅を計算 (データは省略しない)
                max_name = max(len(r['name']) for r in records) if records else 4
                max_type = max(len(r['type']) for r in records) if records else 4
                max_data = max(len(str(r['data'])) for r in records) if records else 4

                header = f"  {'ID':<10} {'Name':<{max_name}}   {'Type':<{max_type}}   {'TTL':<6}   {'Data'}"
                print(header)
                print(f"  {'-'*10} {'-'*max_name}   {'-'*max_type}   {'-'*6}   {'-'*max_data}")

                for record in records:
                    short_id = get_short_id(record['uuid'])
                    print(f"  {short_id:<10} {record['name']:<{max_name}}   {record['type']:<{max_type}}   {str(record['ttl']):<6}   {record['data']}")

        except (ValueError, requests.exceptions.RequestException) as e:
            handle_api_error(e) if isinstance(e, requests.exceptions.RequestException) else print(f"エラー: {e}", file=sys.stderr)
        except IOError as e:
            print(f"ファイル書き込みエラー: {e}", file=sys.stderr)

    def add_record(self, identifier: str, name: str, type: str, data: str, ttl: int):
        try:
            domain_id = self.domain_manager.get_domain_id(identifier)
            domain_name = self.domain_manager.get_domain_name_from_id(domain_id)
            normalized_name = normalize_record_name(domain_name, name)
            
            print(f"ドメイン '{domain_name}' にレコード '{normalized_name}' を追加しています...")
            payload = {"name": normalized_name, "type": type, "data": data, "ttl": ttl}
            record = self.client.post(f"/v1/domains/{domain_id}/records", payload)
            short_id = get_short_id(record['uuid'])
            print("レコードが正常に追加されました。")
            print(f"  ID: {short_id}, Name: {record['name']}, Type: {record['type']}, Data: {record['data']}")
        except (ValueError, requests.exceptions.RequestException) as e:
            handle_api_error(e) if isinstance(e, requests.exceptions.RequestException) else print(f"エラー: {e}")

    def delete_record(self, identifier: str, short_record_id: str):
        try:
            domain_id = self.domain_manager.get_domain_id(identifier)
            domain_name = self.domain_manager.get_domain_name_from_id(domain_id)
            all_records = self._get_all_records(domain_id)
            full_record_id = find_full_uuid(all_records, short_record_id)
            
            print(f"ドメイン '{domain_name}' からレコードID '{short_record_id}' (UUID: {full_record_id}) を削除しています...")
            self.client.delete(f"/v1/domains/{domain_id}/records/{full_record_id}")
            print("レコードが正常に削除されました。")
        except (ValueError, requests.exceptions.RequestException) as e:
            handle_api_error(e) if isinstance(e, requests.exceptions.RequestException) else print(f"エラー: {e}")

    def get_record(self, domain_id: str, record_id: str):
        return self.client.get(f"/v1/domains/{domain_id}/records/{record_id}")

    def update_record(self, identifier: str, short_record_id: str, new_name: str = None, new_type: str = None, new_data: str = None, new_ttl: int = None):
        try:
            domain_id = self.domain_manager.get_domain_id(identifier)
            domain_name = self.domain_manager.get_domain_name_from_id(domain_id)
            all_records = self._get_all_records(domain_id)
            full_record_id = find_full_uuid(all_records, short_record_id)
            
            print(f"レコードID '{short_record_id}' (UUID: {full_record_id}) の現在の情報を取得しています...")
            current_record = self.get_record(domain_id, full_record_id)
            
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

            print(f"レコードID '{short_record_id}' を更新しています...")
            updated_record = self.client.put(f"/v1/domains/{domain_id}/records/{full_record_id}", payload)
            
            short_id = get_short_id(updated_record['uuid'])
            print("レコードが正常に更新されました。")
            print(f"  ID: {short_id}, Name: {updated_record['name']}, Type: {updated_record['type']}, Data: {updated_record['data']}, TTL: {updated_record.get('ttl')}")

        except (ValueError, requests.exceptions.RequestException) as e:
            handle_api_error(e) if isinstance(e, requests.exceptions.RequestException) else print(f"エラー: {e}")
