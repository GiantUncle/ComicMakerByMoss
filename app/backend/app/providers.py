"""Model providers — the app talks to any OpenAI-compatible endpoint directly.

Four named slots ship ready to fill — **Google API, OpenCode GO, NVIDIA, Custom** —
each holding a base URL, a key and the last model list fetched from it.

OpenCode GO is OpenCode's subscription provider (key from the OpenCode Zen console),
OpenAI-compatible at `https://opencode.ai/zen/go/v1` — `/models` lists, and
`/chat/completions` or `/messages` calls. A model the user picks is remembered
**per provider**, and favourites are remembered too.

    ~/.comicmaker/providers.json   base url, key, cached model ids
    ~/.comicmaker/models.json      favourites, last model per provider, active

`chat()` is the only thing the stage runner needs. `_post`/`_get` are module-level
so a test can replace them.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

CONFIG = Path(os.environ.get("CM_CONFIG", Path.home() / ".comicmaker"))
PROVIDERS = CONFIG / "providers.json"
MODELS = CONFIG / "models.json"

TIMEOUT = float(os.environ.get("CM_TIMEOUT", "600"))

# The four slots the UI always shows. `base_url` is a starting point, editable.
SLOTS: tuple[dict[str, str], ...] = (
    {"id": "google", "label": "Google API",
     "base_url": "https://generativelanguage.googleapis.com/v1beta/openai"},
    {"id": "opencode-go", "label": "OpenCode GO",
     "base_url": "https://opencode.ai/zen/go/v1"},
    {"id": "nvidia", "label": "NVIDIA",
     "base_url": "https://integrate.api.nvidia.com/v1"},
    {"id": "custom", "label": "Custom", "base_url": ""},
)
SLOT_IDS = tuple(s["id"] for s in SLOTS)


class ProviderError(RuntimeError):
    """Raised when no provider is usable, or the endpoint refuses."""


# --------------------------------------------------------------------- config
def _read() -> dict:
    if PROVIDERS.is_file():
        try:
            return json.loads(PROVIDERS.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"providers": []}
    return {"providers": []}


def _write(data: dict) -> None:
    CONFIG.mkdir(parents=True, exist_ok=True)
    PROVIDERS.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _read_models() -> dict:
    if MODELS.is_file():
        try:
            return json.loads(MODELS.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"favorites": {}, "selected": {}, "active": {}}


def _write_models(data: dict) -> None:
    CONFIG.mkdir(parents=True, exist_ok=True)
    MODELS.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _entry(providers: list[dict], pid: str) -> dict | None:
    return next((p for p in providers if p.get("id") == pid), None)


def public() -> list[dict]:
    """Every slot (always four) plus any extra provider, keys stripped."""
    providers = _read().get("providers", [])
    out: list[dict] = []
    seen = set()
    for slot in SLOTS:
        stored = _entry(providers, slot["id"]) or {}
        out.append({
            "id": slot["id"],
            "label": slot.get("label", slot["id"]),
            "base_url": stored.get("base_url") or slot["base_url"],
            "api_key_set": bool(stored.get("api_key")),
            "models": stored.get("models") or {},
            "models_cache": stored.get("models_cache") or [],
            "models_fetched": stored.get("models_fetched"),
            "supports_json_mode": stored.get("supports_json_mode", True),
        })
        seen.add(slot["id"])
    for p in providers:
        if p.get("id") in seen:
            continue
        p = dict(p)
        p["api_key_set"] = bool(p.pop("api_key", None))
        out.append(p)
    return out


def upsert(body: dict) -> dict:
    data = _read()
    existing = _entry(data.get("providers", []), body.get("id")) or {}
    entry = dict(existing)
    entry.update({k: v for k, v in body.items() if v is not None})
    if not body.get("api_key"):
        entry["api_key"] = existing.get("api_key")
    entry["id"] = body.get("id")
    others = [p for p in data.get("providers", []) if p.get("id") != body.get("id")]
    _write({"providers": others + [entry]})
    return {"id": entry["id"], "saved": True}


# ------------------------------------------------------------------ the model
def fetch_models(provider: dict) -> list[str]:
    """Read the provider's model list. Google is tried both ways."""
    base = str(provider.get("base_url", "")).rstrip("/")
    key = provider.get("api_key") or ""
    headers = {"Accept": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"

    urls = ([f"{base}/models"] if base else [])
    if provider.get("id") == "google" or "generativelanguage" in base:
        native = "https://generativelanguage.googleapis.com/v1beta/models"
        urls.append(f"{native}?key={key}" if key else native)

    last: Exception | None = None
    for url in urls:
        try:
            data = _get(url, headers)
        except ProviderError as e:
            last = e
            continue
        ids = _model_ids(data)
        if ids:
            return ids
    raise ProviderError(str(last) if last else "the provider returned no models")


def _model_ids(data: Any) -> list[str]:
    if not isinstance(data, dict):
        return []
    raw = data.get("data") or data.get("models") or []
    out = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        mid = item.get("id") or item.get("name") or ""
        mid = str(mid).strip()
        if mid.startswith("models/"):
            mid = mid[len("models/"):]
        if mid:
            out.append(mid)
    return sorted(set(out))


def refresh(provider_id: str | None = None) -> dict:
    """Fetch and cache the model list for one provider, or for all configured."""
    data = _read()
    providers = data.get("providers", [])
    targets = [p for p in providers if provider_id in (None, p.get("id"))]
    if provider_id and not targets:
        targets = [{"id": provider_id}]
    results: dict[str, Any] = {}
    for p in targets:
        if not p.get("base_url"):
            results[p["id"]] = {"ok": False, "error": "no base url"}
            continue
        try:
            ids = fetch_models(p)
        except ProviderError as e:
            results[p["id"]] = {"ok": False, "error": str(e)}
            continue
        p["models_cache"] = ids
        p["models_fetched"] = datetime.now().isoformat(timespec="seconds")
        results[p["id"]] = {"ok": True, "count": len(ids)}
    _write({"providers": providers})
    return {"results": results}


# ------------------------------------------------- favorites and selection
def state() -> dict:
    return _read_models()


def toggle_favorite(provider: str, model: str, on: bool | None = None) -> dict:
    data = _read_models()
    favs = data.setdefault("favorites", {})
    current = favs.setdefault(provider, [])
    if on is None:
        on = model not in current
    if on and model not in current:
        current.append(model)
    elif not on and model in current:
        current.remove(model)
    _write_models(data)
    return data


def select_model(provider: str, model: str) -> dict:
    data = _read_models()
    data.setdefault("selected", {})[provider] = model
    data["active"] = {"provider": provider, "model": model}
    _write_models(data)
    return data


def catalog(provider_id: str | None = None) -> dict:
    """Everything the header menu needs: models, favourites, the active choice."""
    providers = _read().get("providers", [])
    state = _read_models()
    favs = state.get("favorites", {})
    selected = state.get("selected", {})
    groups = []
    for slot in SLOTS:
        stored = _entry(providers, slot["id"]) or {}
        cache = stored.get("models_cache") or []
        groups.append({
            "provider": slot["id"],
            "label": slot.get("label", slot["id"]),
            "configured": bool(stored.get("api_key")) or slot["id"] == "custom",
            "fetched": stored.get("models_fetched"),
            "models": cache,
            "favorites": [m for m in favs.get(slot["id"], []) if m in cache],
            "selected": selected.get(slot["id"]),
        })
    for p in providers:
        if p.get("id") in SLOT_IDS:
            continue
        cache = p.get("models_cache") or []
        groups.append({
            "provider": p.get("id"),
            "label": p.get("label", p.get("id")),
            "configured": bool(p.get("api_key")),
            "fetched": p.get("models_fetched"),
            "models": cache,
            "favorites": [m for m in favs.get(p.get("id"), []) if m in cache],
            "selected": selected.get(p.get("id")),
        })
    if provider_id:
        groups = [g for g in groups if g["provider"] == provider_id]
    return {"groups": groups, "active": state.get("active", {})}


def resolve(provider_id: str | None = None) -> dict:
    providers = _read().get("providers", [])
    usable = [p for p in providers if p.get("base_url")]
    if provider_id:
        found = _entry(providers, provider_id)
        if found:
            return found
        raise ProviderError(f"no provider with id {provider_id!r}")
    active = _read_models().get("active", {}).get("provider")
    if active:
        found = _entry(providers, active)
        if found and found.get("base_url"):
            return found
    if usable:
        return usable[0]
    raise ProviderError("no provider configured — add a key in the provider screen")


def model_for(provider: dict, stage: str | None) -> str:
    models = provider.get("models") or {}
    if stage and models.get(stage):
        return models[stage]
    if models.get("default"):
        return models["default"]

    state = _read_models()
    active = state.get("active", {})
    if active.get("provider") == provider.get("id") and active.get("model"):
        return active["model"]
    chosen = state.get("selected", {}).get(provider.get("id"))
    if chosen:
        return chosen
    cache = provider.get("models_cache") or []
    if cache:
        return cache[0]
    if isinstance(models, dict) and len(models) == 1:
        return next(iter(models.values()))
    raise ProviderError(f"provider {provider.get('id')!r} names no model — pick one")


# ----------------------------------------------------------------------- call
def _post(url: str, headers: dict, payload: dict) -> dict:
    with httpx.Client(timeout=TIMEOUT) as client:
        r = client.post(url, headers=headers, json=payload)
    if r.status_code >= 400:
        raise ProviderError(f"{r.status_code} from {url}: {r.text[:400]}")
    return r.json()


def _get(url: str, headers: dict) -> dict:
    with httpx.Client(timeout=30) as client:
        r = client.get(url, headers=headers)
    if r.status_code >= 400:
        raise ProviderError(f"{r.status_code} from {url}: {r.text[:200]}")
    return r.json()


def _extract(data: dict) -> str:
    if "choices" in data and data["choices"]:
        choice = data["choices"][0]
        message = choice.get("message") or {}
        content = message.get("content")
        if isinstance(content, list):
            content = "".join(part.get("text", "") for part in content)
        if content:
            return content
        if choice.get("text"):
            return choice["text"]
    if "content" in data and isinstance(data["content"], str):
        return data["content"]
    raise ProviderError("the endpoint returned no assistant text")


def chat(
    messages: list[dict],
    *,
    stage: str | None = None,
    provider_id: str | None = None,
    model: str | None = None,
    temperature: float = 0.7,
    json_mode: bool = False,
) -> str:
    provider = resolve(provider_id)
    chosen = model or model_for(provider, stage)
    payload: dict[str, Any] = {
        "model": chosen,
        "messages": messages,
        "temperature": temperature,
    }
    if json_mode and provider.get("supports_json_mode", True):
        payload["response_format"] = {"type": "json_object"}

    url = str(provider.get("base_url", "")).rstrip("/") + "/chat/completions"
    headers = {"Content-Type": "application/json"}
    if provider.get("api_key"):
        headers["Authorization"] = f"Bearer {provider['api_key']}"

    data = _post(url, headers, payload)
    return _extract(data)


def parse_json(text: str) -> Any:
    """Read a JSON value out of a model reply.

    Models wrap JSON in code fences or add a sentence before it, so take the
    first balanced object or array.
    """
    raw = text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw
        if raw.rstrip().endswith("```"):
            raw = raw.rstrip()[:-3]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    for opener, closer in (("{", "}"), ("[", "]")):
        start = raw.find(opener)
        if start < 0:
            continue
        depth, in_string, escape = 0, False, False
        for i in range(start, len(raw)):
            ch = raw[i]
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
            elif ch == opener:
                depth += 1
            elif ch == closer:
                depth -= 1
                if depth == 0:
                    return json.loads(raw[start : i + 1])
    raise ProviderError("the reply carried no JSON")
