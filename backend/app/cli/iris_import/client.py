"""Read-only client for the DFIR IRIS v2.4 REST API.

Only GET requests are made; nothing in IRIS is changed. The API key needs
access to every case to be migrated (an IRIS administrator's key does).
"""
import httpx

PAGE_SIZE = 100


class IrisError(RuntimeError):
    """IRIS returned an error or something that isn't the expected JSON."""


class IrisClient:
    def __init__(self, base_url: str, api_key: str, *, verify: bool = True, timeout: float = 60.0,
                 transport: httpx.AsyncBaseTransport | None = None):
        self.base_url = base_url.rstrip("/")
        self._http = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
            verify=verify,
            timeout=timeout,
            transport=transport,
        )

    async def __aenter__(self) -> "IrisClient":
        return self

    async def __aexit__(self, *exc) -> None:
        await self._http.aclose()

    async def _get(self, path: str, *, cid: int | None = None, params: dict | None = None):
        query = dict(params or {})
        if cid is not None:
            query["cid"] = cid
        try:
            response = await self._http.get(path, params=query)
        except httpx.HTTPError as exc:
            raise IrisError(f"GET {path}: {exc}") from exc
        try:
            body = response.json()
        except ValueError as exc:
            raise IrisError(f"GET {path}: HTTP {response.status_code}, response is not JSON") from exc
        if response.status_code >= 400 or not isinstance(body, dict) or body.get("status") != "success":
            message = body.get("message") if isinstance(body, dict) else None
            raise IrisError(f"GET {path}: HTTP {response.status_code} {message or ''}".strip())
        return body.get("data")

    async def version(self) -> str:
        data = await self._get("/api/versions")
        return (data or {}).get("iris_current", "unknown")

    async def list_cases(self, case_ids: list[int] | None = None) -> list[dict]:
        """Every case visible to the API key (open and closed), oldest first."""
        params: dict = {"per_page": PAGE_SIZE, "sort_dir": "asc", "order_by": "case_id"}
        if case_ids:
            params["case_ids"] = ",".join(str(c) for c in case_ids)
        cases: list[dict] = []
        page = 1
        while True:
            data = await self._get("/manage/cases/filter", params={**params, "page": page})
            batch = (data or {}).get("cases") or []
            cases.extend(batch)
            total = (data or {}).get("total") or 0
            if not batch or len(cases) >= total:
                break
            page += 1
        return sorted(cases, key=lambda c: c["case_id"])

    async def fetch_children(self, case_id: int) -> dict:
        """Everything the importer needs from inside one case."""
        directories = await self._get("/case/notes/directories/filter", cid=case_id) or []
        notes: dict[int, dict] = {}
        for directory in directories:
            for ref in directory.get("notes") or []:
                if ref["id"] not in notes:
                    notes[ref["id"]] = await self._get(f"/case/notes/{ref['id']}", cid=case_id)

        listed = (await self._get("/case/timeline/events/list", cid=case_id) or {}).get("timeline") or []
        events = []
        for item in listed:
            # The list has the category name; the detail has the source, raw
            # text and the ids of linked assets and IOCs.
            detail = await self._get(f"/case/timeline/events/{item['event_id']}", cid=case_id) or {}
            events.append({**item, **detail, "category_name": item.get("category_name")})

        assets = (await self._get("/case/assets/list", cid=case_id) or {}).get("assets") or []
        iocs = (await self._get("/case/ioc/list", cid=case_id) or {}).get("ioc") or []
        return {"directories": directories, "notes": notes, "events": events, "assets": assets, "iocs": iocs}
