from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

_BACKEND_DIR = Path(__file__).resolve().parent
_CLIENT_PATH = _BACKEND_DIR / "supabase" / "supabase_client.py"
_SPEC = importlib.util.spec_from_file_location("glp_supabase_client", _CLIENT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Cannot load Supabase client from {_CLIENT_PATH}")

_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

get_student_profile: Any = _MODULE.get_student_profile
get_supabase_client: Any = _MODULE.get_supabase_client
