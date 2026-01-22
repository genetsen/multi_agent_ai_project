"""Refresh cross-agent master data from the canonical Prisma CSV in GCS.

Reads:
  gs://gs_data_model/prisma/prisma_master_filtered.csv

Writes (default):
  schemas/master_data.json

This is intentionally dependency-light (stdlib only) and uses `gsutil` for GCS IO.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


CANONICAL_GCS_URI = "gs://gs_data_model/prisma/prisma_master_filtered.csv"


def _run(cmd: list[str]) -> str:
    res = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return res.stdout


_slug_re = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    v = (value or "").strip().lower()
    v = _slug_re.sub("_", v).strip("_")
    return v or "unknown"


@dataclass(frozen=True)
class Client:
    client_id: str
    client_name: str
    client_code: Optional[str] = None
    external_keys: Optional[Dict[str, str]] = None
    status: str = "active"


@dataclass(frozen=True)
class Campaign:
    campaign_id: str
    client_id: str
    campaign_name: str
    status: str = "planned"


@dataclass(frozen=True)
class Partner:
    partner_id: str
    partner_name: str
    partner_code: Optional[str] = None
    external_keys: Optional[Dict[str, str]] = None
    status: str = "active"


@dataclass(frozen=True)
class Package:
    package_id: str
    package_name: str
    client_id: Optional[str] = None
    campaign_id: Optional[str] = None
    partner_id: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    external_keys: Optional[Dict[str, str]] = None


def stream_gcs_csv(uri: str) -> Iterable[dict[str, str]]:
    out = _run(["gsutil", "cat", uri])
    reader = csv.DictReader(out.splitlines())
    for row in reader:
        yield {k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()}


def build_master_data(rows: Iterable[dict[str, str]]) -> dict[str, Any]:
    clients_by_key: dict[str, Client] = {}
    campaigns_by_key: dict[tuple[str, str], Campaign] = {}
    partners_by_key: dict[str, Partner] = {}
    packages_by_id: dict[str, Package] = {}

    for r in rows:
        adv_key = r.get("ADVERTISER_BUSINESS_KEY") or ""
        adv_name = r.get("ADVERTISER_NAME") or "Unknown Advertiser"
        adv_short = r.get("ADVERTISER_SHORT_NAME") or None

        client_id = f"cli_{slugify(adv_short or adv_name)}"
        if adv_key and adv_key not in clients_by_key:
            clients_by_key[adv_key] = Client(
                client_id=client_id,
                client_name=adv_name,
                client_code=(adv_short or None),
                external_keys={"prisma_advertiser_business_key": adv_key},
            )
        elif adv_key and adv_key in clients_by_key:
            pass

        camp_name = r.get("CAMPAIGN_NAME") or "Unknown Campaign"
        campaign_id = f"cam_{slugify(adv_short or adv_name)}_{slugify(camp_name)}"
        if adv_key:
            campaigns_by_key.setdefault(
                (adv_key, camp_name),
                Campaign(
                    campaign_id=campaign_id,
                    client_id=client_id,
                    campaign_name=camp_name,
                ),
            )

        sup_key = r.get("SUPPLIER_BUSINESS_KEY") or ""
        sup_name = r.get("SUPPLIER_NAME") or "Unknown Supplier"
        sup_code = r.get("SUPPLIER_CODE") or None

        partner_id = f"par_{slugify(sup_code or sup_name)}"
        if sup_key and sup_key not in partners_by_key:
            partners_by_key[sup_key] = Partner(
                partner_id=partner_id,
                partner_name=sup_name,
                partner_code=sup_code,
                external_keys={"prisma_supplier_business_key": sup_key},
            )

        plc_id = r.get("PACKAGE_HEADER_PLACEMENT_ID") or ""
        plc_name = r.get("PLACEMENT_NAME") or "Unknown Package"

        if plc_id and plc_id not in packages_by_id:
            packages_by_id[plc_id] = Package(
                package_id=plc_id,
                package_name=plc_name,
                client_id=(client_id if adv_key else None),
                campaign_id=(campaign_id if adv_key else None),
                partner_id=(partner_id if sup_key else None),
                start_date=(r.get("PLACEMENT_START_DATE") or None),
                end_date=(r.get("PLACEMENT_END_DATE") or None),
                external_keys={
                    "prisma_package_header_package_id": plc_id,
                    "prisma_external_entity_id": (r.get("EXTERNAL_ENTITY_ID") or ""),
                },
            )

    clients = sorted((c.__dict__ for c in clients_by_key.values()), key=lambda x: x["client_id"])
    campaigns = sorted((c.__dict__ for c in campaigns_by_key.values()), key=lambda x: x["campaign_id"])
    partners = sorted((p.__dict__ for p in partners_by_key.values()), key=lambda x: x["partner_id"])
    placements = sorted((p.__dict__ for p in packages_by_id.values()), key=lambda x: x["package_id"])

    return {
        "schema_version": "1.1.0",
        "source": {
            "type": "gcs_csv",
            "uri": CANONICAL_GCS_URI,
            "refreshed_at": dt.datetime.now(dt.UTC).isoformat(),
        },
        "clients": clients,
        "campaigns": campaigns,
        "partners": partners,
        "packages": placements,
        "project_types": json.load(open(Path("schemas/master_data.json"), "r", encoding="utf-8")).get(
            "project_types", []
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gcs-uri", default=CANONICAL_GCS_URI)
    parser.add_argument("--out", default="schemas/master_data.json")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    rows = stream_gcs_csv(args.gcs_uri)
    if args.limit and args.limit > 0:
        limited = []
        for i, r in enumerate(rows):
            if i >= args.limit:
                break
            limited.append(r)
        rows_iter: Iterable[dict[str, str]] = limited
    else:
        rows_iter = rows

    out_obj = build_master_data(rows_iter)
    out_path = Path(args.out)
    out_path.write_text(json.dumps(out_obj, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
