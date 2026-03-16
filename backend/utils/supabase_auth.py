import os
import requests
from typing import Optional, Dict, Any


class SupabaseAuthError(Exception):
    pass


def _supabase_config():
    url = (os.getenv("SUPABASE_URL") or "").rstrip("/")
    anon_key = os.getenv("SUPABASE_ANON_KEY") or ""
    if not url or not anon_key:
        raise SupabaseAuthError("Missing SUPABASE_URL / SUPABASE_ANON_KEY in environment.")
    return url, anon_key


def _headers(anon_key: str):
    return {
        "apikey": anon_key,
        "Authorization": f"Bearer {anon_key}",
        "Content-Type": "application/json",
    }


def sign_up(email: str, password: str, user_metadata: Optional[Dict[str, Any]] = None):
    url, anon_key = _supabase_config()
    payload = {
        "email": email,
        "password": password,
        "data": user_metadata or {},
    }
    r = requests.post(f"{url}/auth/v1/signup", json=payload, headers=_headers(anon_key), timeout=25)
    try:
        data = r.json()
    except Exception:
        data = {"error": r.text[:200]}
    if r.status_code >= 400:
        msg = data.get("msg") or data.get("error_description") or data.get("error") or "Signup failed"
        raise SupabaseAuthError(str(msg))
    return data


def sign_in_with_password(email: str, password: str):
    url, anon_key = _supabase_config()
    payload = {"email": email, "password": password}
    r = requests.post(
        f"{url}/auth/v1/token?grant_type=password",
        json=payload,
        headers=_headers(anon_key),
        timeout=25,
    )
    try:
        data = r.json()
    except Exception:
        data = {"error": r.text[:200]}
    if r.status_code >= 400:
        msg = data.get("msg") or data.get("error_description") or data.get("error") or "Login failed"
        raise SupabaseAuthError(str(msg))
    return data
