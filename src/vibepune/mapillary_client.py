"""Thin client for the Mapillary Graph API (v4).

Docs: https://www.mapillary.com/developer/api-documentation
Auth: pass a free client access token (format "MLY|<app_id>|<token>").
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Iterator

import requests

from .config import get_mapillary_token, load_config


class MapillaryClient:
    def __init__(self, token: str | None = None, cfg: dict | None = None):
        self.cfg = cfg or load_config()
        self.token = token or get_mapillary_token()
        self.api_root = self.cfg["mapillary"]["api_root"]
        self.fields = self.cfg["mapillary"]["image_fields"]
        self.page_limit = int(self.cfg["mapillary"]["page_limit"])
        self.session = requests.Session()

    def _get(self, url: str, params: dict) -> dict:
        params = {**params, "access_token": self.token}
        for attempt in range(4):
            resp = self.session.get(url, params=params, timeout=30)
            if resp.status_code == 429:  # rate limited — back off and retry
                time.sleep(2**attempt)
                continue
            resp.raise_for_status()
            return resp.json()
        resp.raise_for_status()
        return {}

    def images_in_bbox(
        self,
        bbox: tuple[float, float, float, float],
        min_year: int | None = None,
        max_pages: int = 20,
    ) -> Iterator[dict]:
        """Yield image metadata dicts within a (minLon, minLat, maxLon, maxLat) bbox.

        Follows API pagination up to max_pages to avoid runaway requests.
        """
        url = f"{self.api_root}/images"
        params: dict = {
            "fields": self.fields,
            "bbox": ",".join(f"{v:.6f}" for v in bbox),
            "limit": self.page_limit,
        }
        if min_year:
            start = datetime(min_year, 1, 1, tzinfo=timezone.utc)
            params["start_captured_at"] = start.strftime("%Y-%m-%dT%H:%M:%SZ")

        pages = 0
        while pages < max_pages:
            data = self._get(url, params)
            for img in data.get("data", []):
                yield img
            next_url = data.get("paging", {}).get("next")
            if not next_url:
                break
            # 'next' is a fully formed URL including token & params
            url, params = next_url, {}
            pages += 1

    @staticmethod
    def parse_image(img: dict) -> dict:
        """Flatten one API image record into a tidy row."""
        geom = img.get("computed_geometry") or {}
        coords = geom.get("coordinates", [None, None])
        captured_ms = img.get("captured_at")
        captured = (
            datetime.fromtimestamp(captured_ms / 1000, tz=timezone.utc)
            if captured_ms
            else None
        )
        return {
            "image_id": img.get("id"),
            "lon": coords[0],
            "lat": coords[1],
            "captured_at": captured.isoformat() if captured else None,
            "year": captured.year if captured else None,
            "compass_angle": img.get("compass_angle"),
            "is_pano": img.get("is_pano"),
            "sequence": img.get("sequence"),
            "thumb_url": img.get("thumb_1024_url"),
        }
