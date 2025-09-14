import xxhash

def get_short_id(uuid: str) -> str:
    """UUIDから短いハッシュIDを生成する"""
    return xxhash.xxh64(uuid).hexdigest()[:8] # 8文字に短縮

def find_full_uuid(items: list, short_id: str) -> str:
    """アイテムのリストからshort_idに一致する完全なUUIDを見つける"""
    for item in items:
        if get_short_id(item['uuid']) == short_id:
            return item['uuid']
    raise ValueError(f"指定されたID '{short_id}' に一致するアイテムが見つかりませんでした。")
