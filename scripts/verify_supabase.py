"""Quick Supabase connectivity check for the GAIA agent."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

load_dotenv()

from supabase_client import get_supabase, is_supabase_configured


def main() -> None:
    if not is_supabase_configured():
        print("Supabase env vars are missing.")
        return

    client = get_supabase()
    print("Supabase client OK:", client.supabase_url)

    try:
        result = client.table("gaia_tasks").select("task_id").limit(1).execute()
        print("gaia_tasks table reachable:", len(result.data), "row(s) sampled")
    except Exception as exc:
        print("gaia_tasks query failed (run supabase/migrations/001_gaia_tasks.sql):", exc)


if __name__ == "__main__":
    main()
