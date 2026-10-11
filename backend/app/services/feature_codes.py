"""Catálogo de códigos especiales (feature codes) que se habilitan por extensión."""

FEATURE_CODES = [
    {
        "key": "voicemail_own",
        "code": "*97",
        "name": "Mi buzón de voz",
        "description": "Escuchar los mensajes del buzón propio",
        "default": True,
        "dialplan": [
            "Answer()",
            "VoiceMailMain(${CALLERID(num)}@default)",
        ],
    },
    {
        "key": "voicemail_any",
        "code": "*98",
        "name": "Buzón de voz (cualquiera)",
        "description": "Acceder a cualquier buzón pidiendo número y clave",
        "default": False,
        "dialplan": [
            "Answer()",
            "VoiceMailMain(@default)",
        ],
    },
    {
        "key": "park",
        "code": "700",
        "name": "Parqueo de llamadas",
        "description": "Parquear la llamada en curso",
        "default": True,
        "dialplan": [
            "Park()",
        ],
    },
    {
        "key": "spy",
        "code": "555",
        # 555 + extensión, p.ej. 555300 escucha la llamada activa de la 300
        "pattern": "_555X.",
        "label": "555 + ext",
        "name": "Espiar llamada",
        "description": "Escuchar sin ser oído la llamada activa de otra extensión (555 + extensión)",
        "default": False,
        "dialplan": [
            "Answer()",
            # el '-' final evita que 555300 también espíe a la 3001 (PJSIP/3001-xxxx)
            "ChanSpy(PJSIP/${EXTEN:3}-,qE)",
        ],
    },
    {
        "key": "pickup",
        "code": "**",
        # ** + extensión, p.ej. **300 contesta la llamada que está timbrando en la 300
        "pattern": "_**X.",
        "label": "** + ext",
        "name": "Capturar llamada",
        "description": "Contestar desde aquí la llamada que timbra en otra extensión (** + extensión)",
        "default": True,
        "dialplan": [
            "PickupChan(PJSIP/${EXTEN:2}-,p)",
        ],
    },
    {
        "key": "transfer",
        "code": "##",
        "label": "## / *2",
        "name": "Transferir llamada",
        "description": "Durante la llamada: ## transferencia ciega, *2 atendida (o el botón Transferir del teléfono)",
        "default": True,
        # se marca en plena llamada (features.conf), no tiene dialplan propio
        "in_call": True,
    },
    {
        "key": "say_extension",
        "code": "*65",
        "name": "Decir mi extensión",
        "description": "Reproduce el número de la extensión que llama",
        "default": False,
        "dialplan": [
            "Answer()",
            "Wait(1)",
            "SayDigits(${CALLERID(num)})",
        ],
    },
    {
        "key": "say_time",
        "code": "*60",
        "name": "Hora actual",
        "description": "Reproduce la fecha y hora del servidor",
        "default": False,
        "dialplan": [
            "Answer()",
            "Wait(1)",
            "SayUnixTime(,,ABdY 'digits/at' IMp)",
        ],
    },
]

FEATURE_KEYS = {fc["key"] for fc in FEATURE_CODES}
FEATURE_NUMBERS = {fc["code"] for fc in FEATURE_CODES}
FEATURE_PREFIXES = {fc["code"] for fc in FEATURE_CODES if "pattern" in fc}
DIALED_CODES = [fc for fc in FEATURE_CODES if not fc.get("in_call")]
DEFAULT_ENABLED = [fc["key"] for fc in FEATURE_CODES if fc["default"]]


def exten(fc: dict) -> str:
    return fc.get("pattern", fc["code"])


def is_reserved(number: str) -> bool:
    """Un número de extensión no puede chocar con un código ni quedar tapado por un patrón."""
    return number in FEATURE_NUMBERS or any(number.startswith(p) for p in FEATURE_PREFIXES)


def parse(value: str | None) -> list[str]:
    """Columna de BD → lista de keys. NULL significa 'valores por defecto'."""
    if value is None:
        return list(DEFAULT_ENABLED)
    return [k for k in value.split(",") if k in FEATURE_KEYS]


def serialize(keys: list[str]) -> str:
    return ",".join(k for k in keys if k in FEATURE_KEYS)


def public_catalog() -> list[dict]:
    return [
        {**{k: v for k, v in fc.items() if k not in ("dialplan", "pattern", "in_call")},
         "label": fc.get("label", fc["code"])}
        for fc in FEATURE_CODES
    ]
