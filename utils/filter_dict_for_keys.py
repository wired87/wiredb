def filter_dicts_by_keys(data: list[dict], valid_keys: list[str]) -> list[dict]:
    """
    Filtert jeden dict in der Liste `admin_data`, sodass nur Schlüssel aus `valid_keys` erhalten bleiben.
    """
    return [{k: d[k] for k in valid_keys if k in d} for d in data]
