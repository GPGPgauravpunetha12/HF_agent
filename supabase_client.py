"""Supabase client helper for the GAIA agent."""

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()

GAIA_FILES_BUCKET = os.getenv("SUPABASE_GAIA_BUCKET", "gaia-files")


def is_supabase_configured() -> bool:
    url = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    key = (
        os.getenv("SUPABASE_KEY")
        or os.getenv("SUPABASE_PUBLISHABLE_KEY")
        or os.getenv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY")
    )
    return bool(url and key)


@lru_cache(maxsize=1)
def get_supabase():
    """Return a cached Supabase client, or raise if env vars are missing."""
    from supabase import create_client

    url = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    key = (
        os.getenv("SUPABASE_KEY")
        or os.getenv("SUPABASE_PUBLISHABLE_KEY")
        or os.getenv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY")
    )

    if not url or not key:
        raise ValueError(
            "Supabase is not configured. Set SUPABASE_URL and SUPABASE_KEY "
            "(or NEXT_PUBLIC_SUPABASE_URL / NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY)."
        )

    return create_client(url, key)
