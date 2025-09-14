import json
import requests

def normalize_domain(domain_name: str) -> str:
    """ドメイン名の末尾にドットを追加する"""
    if not domain_name.endswith('.'):
        return domain_name + '.'
    return domain_name

def normalize_record_name(domain_name: str, record_name: str) -> str:
    """レコード名を正規化する"""
    if record_name == '@':
        return normalize_domain(domain_name)

    clean_domain_name = domain_name.rstrip('.')
    if not record_name.endswith(clean_domain_name):
        record_name = f"{record_name}.{clean_domain_name}"

    return normalize_domain(record_name)

def handle_api_error(e):
    """APIエラーを処理し、情報を出力する"""
    print(f"エラー: 要求に失敗しました。")
    if isinstance(e, requests.exceptions.RequestException):
        if hasattr(e, 'response') and e.response is not None:
            print(f"ステータスコード: {e.response.status_code}")
            try:
                print(f"レスポンス: {json.dumps(e.response.json(), indent=2, ensure_ascii=False)}")
            except json.JSONDecodeError:
                print(f"レスポンス: {e.response.text}")
        else:
            print(e)
    else:
        print(e)
