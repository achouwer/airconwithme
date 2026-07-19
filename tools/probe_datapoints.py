"""Read-only Airconwithme datapoint probe.

This script only sends read commands:
- login
- getinfo
- getavailabledatapoints
- getdatapointvalue with uid="all"
- optionally getdatapointvalue for explicit candidate uids

It never sends setdatapointvalue.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import dataclass
from typing import Any

import aiohttp


CONTENT_TYPE = "application/json; charset=utf-8"
DEFAULT_CANDIDATES = (3, 6, 7, 8, 11, 16, 17, 18, 19, 20)


@dataclass(frozen=True)
class ProbeConfig:
    """Runtime configuration for the probe."""

    host: str
    username: str
    password: str
    timeout: int
    candidates: tuple[int, ...]
    read_candidates: bool


def normalize_host(host: str) -> str:
    """Normalize host, URL, or api.cgi input into a bare host."""
    normalized = host.strip().removeprefix("http://").removeprefix("https://").rstrip("/")
    if normalized.endswith("/api.cgi"):
        normalized = normalized[: -len("/api.cgi")]
    return normalized


class ProbeClient:
    """Small read-only client for Airconwithme api.cgi."""

    def __init__(self, config: ProbeConfig) -> None:
        self.config = config
        self.session_id: str | None = None
        self.timeout = aiohttp.ClientTimeout(total=config.timeout)

    @property
    def url(self) -> str:
        """Return API endpoint URL."""
        return f"http://{self.config.host}/api.cgi"

    async def request(
        self,
        session: aiohttp.ClientSession,
        command: str,
        data: dict[str, Any] | None = None,
        *,
        authenticated: bool = True,
    ) -> dict[str, Any]:
        """Send one API request."""
        payload_data = dict(data or {})
        if authenticated:
            if not self.session_id:
                raise RuntimeError("Authenticated request before login")
            payload_data["sessionID"] = self.session_id

        async with session.post(
            self.url,
            json={"command": command, "data": payload_data},
            headers={"Content-Type": CONTENT_TYPE},
            timeout=self.timeout,
        ) as response:
            body = await response.json(content_type=None)
            if not isinstance(body, dict):
                return {
                    "success": False,
                    "error": {"code": "invalid_json", "http_status": response.status},
                }
            body.setdefault("_http_status", response.status)
            return body

    async def login(self, session: aiohttp.ClientSession) -> None:
        """Log in and store session id."""
        result = await self.request(
            session,
            "login",
            {
                "username": self.config.username,
                "password": self.config.password,
            },
            authenticated=False,
        )
        if result.get("success") is not True:
            raise RuntimeError(f"Login failed: {json.dumps(result, sort_keys=True)}")

        session_id = result.get("data", {}).get("id", {}).get("sessionID")
        if not isinstance(session_id, str) or not session_id:
            raise RuntimeError("Login succeeded but response did not contain sessionID")
        self.session_id = session_id


def metadata_rows(metadata: list[dict[str, Any]], values_by_uid: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    """Combine metadata and values into stable table rows."""
    rows: list[dict[str, Any]] = []
    for item in sorted(metadata, key=lambda row: int(row.get("uid", 0))):
        uid = int(item["uid"])
        value_item = values_by_uid.get(uid, {})
        rows.append(
            {
                "uid": uid,
                "value": value_item.get("value"),
                "status": value_item.get("status"),
                "rw": item.get("rw"),
                "type": item.get("type"),
                "descr": item.get("descr"),
            }
        )
    return rows


def print_table(rows: list[dict[str, Any]]) -> None:
    """Print a compact datapoint table."""
    print("uid  value  status  rw  type  descr")
    print("---  -----  ------  --  ----  -----")
    for row in rows:
        print(
            f"{row['uid']:>3}  "
            f"{str(row.get('value', '')):<5}  "
            f"{str(row.get('status', '')):<6}  "
            f"{str(row.get('rw', '')):<2}  "
            f"{str(row.get('type', '')):<4}  "
            f"{row.get('descr', '')}"
        )


async def run_probe(config: ProbeConfig) -> dict[str, Any]:
    """Run the read-only probe and return structured output."""
    client = ProbeClient(config)
    async with aiohttp.ClientSession() as session:
        await client.login(session)

        info = await client.request(session, "getinfo")
        metadata_result = await client.request(session, "getavailabledatapoints")
        values_result = await client.request(session, "getdatapointvalue", {"uid": "all"})

        metadata = metadata_result.get("data", {}).get("dp", {}).get("datapoints", [])
        if not isinstance(metadata, list):
            metadata = []

        values = values_result.get("data", {}).get("dpval", [])
        if not isinstance(values, list):
            values = []

        values_by_uid = {
            int(item["uid"]): item
            for item in values
            if isinstance(item, dict) and "uid" in item
        }
        metadata_uids = {
            int(item["uid"])
            for item in metadata
            if isinstance(item, dict) and "uid" in item
        }

        candidate_reads: dict[int, dict[str, Any]] = {}
        if config.read_candidates:
            for uid in config.candidates:
                candidate_reads[uid] = await client.request(
                    session,
                    "getdatapointvalue",
                    {"uid": uid},
                )

        return {
            "host": config.host,
            "info": info,
            "datapoints": metadata_rows(metadata, values_by_uid),
            "candidate_summary": [
                {
                    "uid": uid,
                    "present_in_metadata": uid in metadata_uids,
                    "present_in_all_values": uid in values_by_uid,
                    "read_result": candidate_reads.get(uid),
                }
                for uid in config.candidates
            ],
        }


def parse_args() -> ProbeConfig:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Read-only Airconwithme datapoint probe")
    parser.add_argument("host", help="Device IP/host, URL, or http://<host>/api.cgi")
    parser.add_argument("--username", default="Admin")
    parser.add_argument("--password", default="admin")
    parser.add_argument("--timeout", type=int, default=10)
    parser.add_argument(
        "--candidates",
        default=",".join(str(uid) for uid in DEFAULT_CANDIDATES),
        help="Comma-separated candidate uids to check in metadata",
    )
    parser.add_argument(
        "--read-candidates",
        action="store_true",
        help="Also send read-only getdatapointvalue requests for candidate uids",
    )

    args = parser.parse_args()
    candidates = tuple(
        int(part.strip())
        for part in args.candidates.split(",")
        if part.strip()
    )
    return ProbeConfig(
        host=normalize_host(args.host),
        username=args.username,
        password=args.password,
        timeout=args.timeout,
        candidates=candidates,
        read_candidates=args.read_candidates,
    )


async def main() -> None:
    """Run script."""
    result = await run_probe(parse_args())
    print_table(result["datapoints"])
    print()
    print("Candidate summary")
    print(json.dumps(result["candidate_summary"], indent=2, sort_keys=True))
    print()
    print("Full JSON")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    asyncio.run(main())
