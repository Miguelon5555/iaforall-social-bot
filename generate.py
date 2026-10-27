import os
import json
import random
import requests
from anthropic import Anthropic

REQUIRED_KEYS = ["instagram", "pinterest", "twitter", "tiktok_idea", "youtube_short", "linkedin"]


def leer_tema():
    with open("system_prompt.txt", "r", encoding="utf-8") as f:
        system_prompt = f.read()

    with open("temas.json", "r", encoding="utf-8") as f:
        temas_data = json.load(f)

    tema = random.choice(temas_data["temas"])
    return system_prompt, tema


def extraer_json(texto):
    texto = texto.strip()
    inicio, fin = texto.find("{"), texto.rfind("}")
    if inicio == -1 or fin == -1:
        raise ValueError("La respuesta no contiene un objeto JSON")
    # strict=False tolera saltos de línea reales dentro de los textos
    return json.loads(texto[inicio : fin + 1], strict=False)


def generar_contenido(system_prompt, tema, intentos=3):
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    ultimo_error = None

    for n in range(1, intentos + 1):
        mensaje = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4500,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": f"Tema de hoy: {tema}\n\nGenera el contenido en el formato JSON indicado en las instrucciones.",
                }
            ],
        )
        texto = mensaje.content[0].text

        try:
            if mensaje.stop_reason == "max_tokens":
                raise ValueError("La respuesta se cortó por longitud (max_tokens)")
            contenido = extraer_json(texto)

            faltantes = [k for k in REQUIRED_KEYS if k not in contenido]
            if faltantes:
                raise ValueError(f"Respuesta incompleta, faltan claves: {faltantes}")

            # Si alguna pieza llega como lista (p. ej. los tweets), se une en texto
            for k in REQUIRED_KEYS:
                v = contenido[k]
                if isinstance(v, list):
                    contenido[k] = "\n\n".join(str(x) for x in v)
                elif not isinstance(v, str):
                    contenido[k] = str(v)
            return contenido
        except Exception as e:
            ultimo_error = e
            print(f"⚠️ Intento {n}/{intentos} no válido: {e}")
            print(f"   stop_reason={mensaje.stop_reason}; inicio de la respuesta: {texto[:300]!r}")

    raise RuntimeError(f"No se pudo generar contenido válido: {ultimo_error}")


def crear_issue(tema, contenido):
    repo = os.environ["GITHUB_REPOSITORY"]
    token = os.environ["GITHUB_TOKEN"]

    url = f"https://api.github.com/repos/{repo}/issues"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }

    lineas_tema = tema.splitlines() or [tema]
    cabecera = lineas_tema[0]
    detalle = "\n".join(lineas_tema[1:]).strip()

    cuerpo = f"## Tema: {cabecera}\n\n"
    if detalle:
        cuerpo += f"<details><summary>Datos del tema</summary>\n\n{detalle}\n\n</details>\n\n"
    for plataforma in REQUIRED_KEYS:
        cuerpo += f"### {plataforma}\n{contenido[plataforma]}\n\n"

    payload = {
        "title": f"Contenido social — {cabecera[:60]}",
        "body": cuerpo,
        "labels": ["contenido-social", "revision-pendiente"],
    }

    resp = requests.post(url, headers=headers, json=payload)
    resp.raise_for_status()
    print(f"✅ Issue creado: {resp.json()['html_url']}")


def main():
    system_prompt, tema = leer_tema()
    print(f"📝 Tema elegido: {tema}")
    contenido = generar_contenido(system_prompt, tema)
    crear_issue(tema, contenido)


if __name__ == "__main__":
    main()
