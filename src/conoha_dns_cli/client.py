import os
import requests
import json
from functools import lru_cache
from .utils import handle_api_error

class ConohaDNSClient:
    def __init__(self):
        self.api_base_url = os.getenv("CONOHA_DNS_API_URL", "https://dns-service.c3j1.conoha.io")
        self.token = self._get_api_token()

    def _get_api_token(self):
        token = os.getenv("CONOHA_TOKEN") or os.getenv("API_TOKEN")
        if token:
            return token

        user_id = os.getenv("CONOHA_USER_ID")
        password = os.getenv("CONOHA_PASSWORD")
        project_id = os.getenv("TENANT_ID")

        if not all([user_id, password, project_id]):
            raise ValueError("APIトークンが見つからず、認証情報 (.envの CONOHA_USER_ID, CONOHA_PASSWORD, TENANT_ID) も不完全です。")

        auth_base_url = os.getenv("CONOHA_AUTH_URL", "https://identity.c3j1.conoha.io")
        auth_url = f"{auth_base_url.rstrip('/')}/v3/auth/tokens"

        payload = {
            "auth": {
                "identity": {
                    "methods": ["password"],
                    "password": {
                        "user": {"id": user_id, "password": password}
                    }
                },
                "scope": {"project": {"id": project_id}}
            }
        }
        headers = {"Accept": "application/json", "Content-Type": "application/json"}

        print("APIトークンが見つからないため、認証して新しいトークンを取得します...")
        try:
            response = requests.post(auth_url, headers=headers, json=payload)
            new_token = response.headers.get("X-Subject-Token")

            if response.status_code == 201 and new_token:
                print("新しいAPIトークンを取得しました。")
                try:
                    with open(".env", "a") as f:
                        f.write(f"\nCONOHA_TOKEN={new_token}\n")
                    print(".envファイルにCONOHA_TOKENを追記しました。")
                except IOError as e:
                    print(f"警告: .envファイルへの書き込みに失敗しました。手動でトークンを保存してください。エラー: {e}")
                os.environ['CONOHA_TOKEN'] = new_token
                return new_token
            else:
                error_message = f"APIトークンの取得に失敗しました。ステータスコード: {response.status_code}"
                try:
                    error_details = response.json()
                    error_message += f"\nレスポンス: {json.dumps(error_details, indent=2, ensure_ascii=False)}"
                except json.JSONDecodeError:
                    error_message += f"\nレスポンス: {response.text}"
                raise ValueError(error_message)
        except requests.exceptions.RequestException as e:
            handle_api_error(e)
            raise ValueError("APIトークン取得リクエスト中にエラーが発生しました。")

    @lru_cache(maxsize=None)
    def get_headers(self):
        return {"Accept": "application/json", "X-Auth-Token": self.token}

    def get(self, path):
        url = f"{self.api_base_url}{path}"
        response = requests.get(url, headers=self.get_headers())
        response.raise_for_status()
        return response.json()

    def post(self, path, payload):
        url = f"{self.api_base_url}{path}"
        response = requests.post(url, headers=self.get_headers(), json=payload)
        response.raise_for_status()
        return response.json()

    def delete(self, path):
        url = f"{self.api_base_url}{path}"
        response = requests.delete(url, headers=self.get_headers())
        response.raise_for_status()
        # DELETEはボディが空のことがある
        if response.status_code == 204:
            return None
        return response.json()

    def put(self, path, payload):
        url = f"{self.api_base_url}{path}"
        response = requests.put(url, headers=self.get_headers(), json=payload)
        response.raise_for_status()
        return response.json()
