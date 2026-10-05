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


def generar_contenido(system_prompt, tema):
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    mensaje = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": f"Tema de hoy: {tema}\n\nGenera el contenido en el formato JSON indicado en las instrucciones.",
            }
        ],
    )

    texto = mensaje.content[0].text.strip()

    # Por si Claude envuelve la respuesta en backticks de markdown pese a las instrucciones
    if texto.startswith("```"):
        texto = texto.split("```")[1]
        if texto.startswith("json"):
            texto = texto[4:]
        texto = texto.strip()

    contenido = json.loads(texto)

    faltantes = [k for k in REQUIRED_KEYS if k not in contenido]
    if faltantes:
        raise ValueError(f"Respuesta incompleta, faltan claves: {faltantes}")

    return contenido


def crear_issue(tema, contenido):
    repo = os.environ["GITHUB_REPOSITORY"]
    token = os.environ["GITHUB_TOKEN"]

    url = f"https://api.github.com/repos/{repo}/issues"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }

    cuerpo = f"## Tema: {tema}\n\n"
    for plataforma in REQUIRED_KEYS:
        cuerpo += f"### {plataforma}\n{contenido[plataforma]}\n\n"

    payload = {
        "title": f"Contenido social — {tema[:60]}",
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
