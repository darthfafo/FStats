import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import PORTALES
from warehouse.db import get_connection, initialize
from warehouse.ingest_facebook import ingest_facebook
from warehouse.ingest_instagram import ingest_instagram
from datetime import datetime

PENDIENTE = ("PENDIENTE", "", None)


def _is_active(portal):
    if portal.get("ig_only"):
        return (portal.get("access_token") not in PENDIENTE and
                portal.get("instagram_id") not in PENDIENTE)
    return (portal.get("access_token") not in PENDIENTE and
            portal.get("facebook_page_id") not in PENDIENTE)


def run():
    print(f"{'='*60}")
    print(f"FStats Ingestion - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    con = get_connection()
    initialize(con)
    con.close()

    results = {"ok": 0, "skipped": 0, "errors": []}

    for portal in PORTALES:
        nombre = portal["nombre"]
        if not _is_active(portal):
            print(f"\n[{nombre}] -- Skipped (PENDIENTE credentials)")
            results["skipped"] += 1
            continue

        print(f"\n{'─'*40}")
        print(f"[{nombre}] Starting ingestion...")

        try:
            if not portal.get("ig_only"):
                ingest_facebook(portal)
            ingest_instagram(portal)
            results["ok"] += 1
            print(f"[{nombre}] ✓ Complete")
        except Exception as e:
            print(f"[{nombre}] ✗ Failed: {e}")
            results["errors"].append((nombre, str(e)))

    print(f"\n{'='*60}")
    print(f"Done - OK: {results['ok']}, Skipped: {results['skipped']}, Errors: {len(results['errors'])}")
    for nombre, err in results["errors"]:
        print(f"  ✗ {nombre}: {err}")
    print(f"{'='*60}")

    return results


if __name__ == "__main__":
    run()
