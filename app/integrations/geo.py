from typing import Any

import httpx

from app.core.config import settings


class GeoEnricher:
    def __init__(self, client: httpx.AsyncClient | None = None):
        self.client = client

    async def enrich(self, ip: str | None) -> dict[str, Any]:
        if not ip or ip in {"127.0.0.1", "::1"}:
            return {}
        client = self.client or httpx.AsyncClient(timeout=settings.geo_timeout_seconds)
        close = self.client is None
        try:
            try:
                response = await client.get(f"https://ip-api.com/json/{ip}")
                response.raise_for_status()
                data = response.json()
                if data.get("status") == "success":
                    return {"country": data.get("country"), "country_code": data.get("countryCode"), "city": data.get("city"), "region": data.get("regionName"), "geo_provider": "ip-api"}
            except (httpx.HTTPError, ValueError, TypeError):
                pass
            try:
                response = await client.get(f"https://ipapi.co/{ip}/json/")
                response.raise_for_status()
                data = response.json()
                if data.get("country_name"):
                    return {"country": data.get("country_name"), "country_code": data.get("country_code"), "city": data.get("city"), "region": data.get("region"), "geo_provider": "ipapi.co"}
            except (httpx.HTTPError, ValueError, TypeError):
                pass
            return {}
        finally:
            if close:
                await client.aclose()
