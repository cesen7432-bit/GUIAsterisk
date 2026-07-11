import re


def render(text: str, variables: dict) -> str:
    """Reemplaza {{variable}} en el texto. Lanza ValueError si falta alguna."""
    missing = set(re.findall(r"\{\{(\w+)\}\}", text)) - set(variables)
    if missing:
        raise ValueError(f"Variables faltantes en plantilla: {missing}")
    return re.sub(r"\{\{(\w+)\}\}", lambda m: str(variables[m.group(1)]), text)
