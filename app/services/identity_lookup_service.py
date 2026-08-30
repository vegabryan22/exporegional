import json
import re
import time
from threading import Lock
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


GOMETA_URL = "https://apis.gometa.org/cedulas/{identity}"
HACIENDA_URL = "https://api.hacienda.go.cr/fe/ae"
REQUEST_TIMEOUT = 8
CACHE_TTL_SECONDS = 24 * 60 * 60

_cache = {}
_cache_lock = Lock()


class IdentityLookupError(Exception):
    pass


def normalize_identity(value) -> str:
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) == 8:
        digits = "0" + digits
    if not 9 <= len(digits) <= 12:
        raise IdentityLookupError("La cédula debe contener entre 9 y 12 dígitos.")
    return digits


def _read_json(url: str) -> dict:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "ExpoTecnicaRegional/1.0"})
    with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def _gometa(identity: str):
    payload = _read_json(GOMETA_URL.format(identity=identity))
    results = payload.get("results") or []
    if not results:
        return None
    person = results[0]
    return " ".join(
        filter(None, (person.get("firstname"), person.get("lastname1"), person.get("lastname2")))
    ).strip() or person.get("fullname")


def _hacienda(identity: str):
    payload = _read_json(f"{HACIENDA_URL}?{urlencode({'identificacion': identity})}")
    return (payload.get("nombre") or "").strip() or None


def _natural_name(value: str) -> str:
    particles = {"DE", "DEL", "LA", "LAS", "LOS", "Y"}
    words = []
    for index, word in enumerate(re.split(r"\s+", str(value or "").strip())):
        if index and word.upper() in particles:
            words.append(word.lower())
        else:
            words.append("-".join(part[:1].upper() + part[1:].lower() for part in word.split("-")))
    return " ".join(words)


def lookup_identity_name(identity_value) -> dict:
    identity = normalize_identity(identity_value)
    now = time.time()
    with _cache_lock:
        cached = _cache.get(identity)
        if cached and now - cached[0] < CACHE_TTL_SECONDS:
            return {"identity": identity, "name": cached[1], "source": cached[2]}

    service_responded = False
    raw_name = None
    source = None
    for provider, provider_name in ((_gometa, "GoMeta"), (_hacienda, "Hacienda")):
        try:
            raw_name = provider(identity)
            service_responded = True
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError):
            continue
        if raw_name:
            source = provider_name
            break

    if not raw_name:
        if service_responded:
            raise IdentityLookupError("No se encontró un nombre para esta cédula.")
        raise IdentityLookupError("No fue posible consultar los servicios de cédulas en este momento.")

    name = _natural_name(raw_name)
    with _cache_lock:
        _cache[identity] = (now, name, source)
    return {"identity": identity, "name": name, "source": source}
