import requests
import json
import math

BASE_URL = "http://64.188.74.2:8000"

_cached_products = []
_cached_sales = []
_cached_prod_timestamp = 0.0
_cached_sales_timestamp = 0.0


def get_last_update() -> float:
    try:
        resp = requests.get(f"{BASE_URL}/last-update")
        if resp.status_code == 200:
            return float(resp.json().get("timestamp", 0.0))
    except:
        pass
    return 0.0


def get_products(force_refresh=False) -> list:
    global _cached_products, _cached_prod_timestamp
    current_ts = get_last_update()

    if force_refresh or not _cached_products or current_ts > _cached_prod_timestamp:
        try:
            resp = requests.get(f"{BASE_URL}/products")
            if resp.status_code == 200:
                _cached_products = resp.json()
                _cached_prod_timestamp = current_ts
        except:
            pass
    return _cached_products


def create_product(data: dict) -> bool:
    global _cached_prod_timestamp
    try:
        resp = requests.post(f"{BASE_URL}/products", json=data)
        if resp.status_code in (200, 201):
            _cached_prod_timestamp = 0.0
            return True
    except:
        return False
    return False


def update_product(product_id: int, data: dict) -> bool:
    global _cached_prod_timestamp
    try:
        resp = requests.patch(f"{BASE_URL}/products/{product_id}", json=data)
        if resp.status_code == 200:
            _cached_prod_timestamp = 0.0
            return True
    except:
        return False
    return False


def delete_product(product_id: int) -> bool:
    global _cached_prod_timestamp
    try:
        resp = requests.delete(f"{BASE_URL}/products/{product_id}")
        if resp.status_code == 204:
            _cached_prod_timestamp = 0.0
            return True
    except:
        return False
    return False


def get_sales(force_refresh=False) -> list:
    global _cached_sales, _cached_sales_timestamp
    current_ts = get_last_update()

    if force_refresh or not _cached_sales or current_ts > _cached_sales_timestamp:
        try:
            resp = requests.get(f"{BASE_URL}/sales")
            if resp.status_code == 200:
                _cached_sales = resp.json()
                _cached_sales_timestamp = current_ts
        except:
            pass
    return _cached_sales


def create_sale(data: dict) -> bool:
    global _cached_sales_timestamp
    try:
        resp = requests.post(f"{BASE_URL}/sales", json=data)
        if resp.status_code in (200, 201):
            _cached_sales_timestamp = 0.0
            return True
    except:
        return False
    return False


def get_query_vector(query: str) -> list:
    try:
        resp = requests.get(f"{BASE_URL}/embeddings/query", params={"q": query})
        if resp.status_code == 200:
            return resp.json().get("vector", [])
    except:
        pass
    return []


def parse_embedding(emb_val) -> list:
    if isinstance(emb_val, list):
        return emb_val
    if isinstance(emb_val, str):
        try:
            parsed = json.loads(emb_val)
            if isinstance(parsed, list):
                return parsed
        except:
            pass
        try:
            return [float(x.strip()) for x in emb_val.split(",") if x.strip()]
        except:
            pass
    return []


def cosine_similarity(v1: list, v2: list) -> float:
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot_product = sum(a * b for a, b in zip(v1, v2))
    magnitude_v1 = math.sqrt(sum(a * a for a in v1))
    magnitude_v2 = math.sqrt(sum(b * b for b in v2))
    if magnitude_v1 == 0.0 or magnitude_v2 == 0.0:
        return 0.0
    return dot_product / (magnitude_v1 * magnitude_v2)


def search_products(query_text: str) -> list:
    if not query_text.strip():
        return get_products()

    query_vector = get_query_vector(query_text)
    all_products = get_products()

    if not query_vector:
        return [
            p for p in all_products if query_text.lower() in p.get("name", "").lower()
        ]

    scored_products = []
    for p in all_products:
        emb = parse_embedding(p.get("embedding"))
        if emb:
            sim = cosine_similarity(query_vector, emb)
            p["_similarity"] = sim
        else:
            p["_similarity"] = -1.0
        scored_products.append(p)

    scored_products.sort(key=lambda x: x.get("_similarity", -1.0), reverse=True)
    return scored_products
