import requests
import math

BASE_URL = "http://64.188.74.2:8000"
API_PASSWORD = "7#wY9&rQ4@kM2!pX"
HEADERS = {"X-API-Key": API_PASSWORD}

session = requests.Session()
session.headers.update(HEADERS)

_cached_products = []
_cached_sales = []
_cached_timestamp = 0.0


def get_last_update() -> float:
    try:
        resp = session.get(f"{BASE_URL}/last-update", timeout=3)
        if resp.status_code == 200:
            return float(resp.json().get("timestamp", 0.0))
    except:
        pass
    return 0.0


def load_all_data_if_needed(force_refresh=False) -> tuple:
    global _cached_products, _cached_sales, _cached_timestamp

    remote_ts = _cached_timestamp
    if not force_refresh:
        try:
            remote_ts = get_last_update()
        except:
            pass

    has_db_updates = (remote_ts - _cached_timestamp) > 0.05

    if force_refresh or has_db_updates or not _cached_products or not _cached_sales:
        success_products = False
        success_sales = False

        try:
            resp_p = session.get(f"{BASE_URL}/products", timeout=10)
            if resp_p.status_code == 200:
                _cached_products = resp_p.json()
                success_products = True
        except:
            pass

        try:
            resp_s = session.get(f"{BASE_URL}/sales", timeout=10)
            if resp_s.status_code == 200:
                _cached_sales = resp_s.json()
                success_sales = True
        except:
            pass

        if success_products and success_sales:
            try:
                _cached_timestamp = get_last_update()
            except:
                _cached_timestamp = remote_ts
        else:
            _cached_timestamp = 0.0

    return _cached_products, _cached_sales, _cached_timestamp


def get_products(force_refresh=False) -> list:
    prods, _, _ = load_all_data_if_needed(force_refresh)
    return prods


def get_sales(force_refresh=False) -> list:
    _, sales, _ = load_all_data_if_needed(force_refresh)
    return sales


def create_product(data: dict):
    try:
        resp = session.post(f"{BASE_URL}/products", json=data, timeout=5)
        if resp.status_code in (200, 201):
            return resp.json()
    except:
        pass
    return None


def update_product(product_id: str, data: dict):
    try:
        resp = session.patch(f"{BASE_URL}/products/{product_id}", json=data, timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return None


def delete_product(product_id: str) -> bool:
    try:
        resp = session.delete(f"{BASE_URL}/products/{product_id}", timeout=5)
        return resp.status_code == 204
    except:
        pass
    return False


def create_sale(data: dict):
    try:
        resp = session.post(f"{BASE_URL}/sales", json=data, timeout=5)
        if resp.status_code in (200, 201):
            return resp.json()
    except:
        pass
    return None


def get_query_vector(query: str) -> list:
    try:
        resp = session.get(
            f"{BASE_URL}/embeddings/query",
            params={"q": query},
            timeout=5,
        )
        if resp.status_code == 200:
            return resp.json().get("vector", [])
    except:
        pass
    return []


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
        emb_raw = p.get("embedding")
        emb = []
        if isinstance(emb_raw, list):
            emb = emb_raw
        elif isinstance(emb_raw, str):
            try:
                import json

                parsed = json.loads(emb_raw)
                if isinstance(parsed, list):
                    emb = parsed
            except:
                try:
                    emb = [float(x.strip()) for x in emb_raw.split(",") if x.strip()]
                except:
                    pass

        if emb and len(emb) == len(query_vector):
            dot_product = sum(a * b for a, b in zip(query_vector, emb))
            magnitude_v1 = math.sqrt(sum(a * a for a in query_vector))
            magnitude_v2 = math.sqrt(sum(b * b for b in emb))
            sim = (
                dot_product / (magnitude_v1 * magnitude_v2)
                if magnitude_v1 > 0 and magnitude_v2 > 0
                else 0.0
            )
            p["_similarity"] = sim
        else:
            p["_similarity"] = -1.0
        scored_products.append(p)

    scored_products.sort(key=lambda x: x.get("_similarity", -1.0), reverse=True)
    return scored_products
