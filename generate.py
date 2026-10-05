import os
import json
import random
from datetime import datetime
import anthropic
import requests

# --- Config ---
SYSTEM_PROMPT = open("system_prompt.txt", "r", encoding="utf-8").read()

with open("temas.json", "r", encoding="utf-8") as f:
    config = json.load(f)

tema_hoy = random.choice(config["temas"])
plataforma_cta = random.choice(config["plataformas_cta"])

user_prompt = f"""Genera contenido para el día de hoy con este enfoque específico: {tema_hoy}

Plataforma a priorizar hoy con link real: {plataforma_cta}"""

# --- Llamada a Claude ---
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=2000,
    system=SYSTEM_PROMPT,
    messages=[{"role": "user", "content": user_prompt}]
)

raw_text = response.content[0].text.strip()
raw_text = raw_text.replace("```json", "").replace("```", "").strip()

try:
    data = json.loads(raw_text)
except json.JSONDecodeError as e:
    print("Error parseando JSON:", e)
    print("Contenido recibido:", raw_text)
    raise

# --- Crear un Issue en GitHub con el contenido para revisar ---
fecha = datetime.now().strftime("%Y-%m-%d")

yt = data.get("youtube_short", {})
guion_yt = yt.get("guion_voz_en_off") or "— (formato timelapse silencioso, sin voz)"

cuerpo = f"""## Tema del día: {tema_hoy}
**Plataforma con CTA hoy:** {plataforma_cta}

### 📸 Instagram
**Caption:**
{data['instagram']['caption']}

**Hashtags:** {', '.join(data['instagram']['hashtags'])}

**Idea de imagen:** {data['instagram']['image_idea']}

---

### 📌 Pinterest
**Título:** {data['pinterest']['title']}

**Descripción:** {data['pinterest']['description']}

**Idea de imagen:** {data['pinterest']['image_idea']}

---

### 🐦 X / Twitter
{data['twitter']['text']}

**Idea de imagen:** {data['twitter']['image_idea']}

---

### 🎵 TikTok (idea)
**Concepto:** {data['tiktok_idea']['concept']}

**Audio sugerido:** {data['tiktok_idea']['audio_suggestion']}

**Texto en pantalla:** {data['tiktok_idea']['text_overlay']}

---

### 🎥 YouTube Short ({yt.get('format', 'no especificado')})
**Duración estimada:** {yt.get('duracion_estimada', '-')}

**Guion voz en off:**
{guion_yt}

**Texto en pantalla:** {yt.get('texto_pantalla', '-')}

**Audio/música:** {yt.get('sugerencia_audio', '-')}

**Descripción del vídeo:** {yt.get('cta_descripcion', '-')}

---

### 💼 LinkedIn
{data['linkedin']['text']}

**Idea de imagen:** {data['linkedin']['image_idea']}
"""

repo = os.environ["GITHUB_REPOSITORY"]  # viene automático en Actions, formato "usuario/repo"
token = os.environ["GITHUB_TOKEN"]

url = f"https://api.github.com/repos/{repo}/issues"
headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github+json"
}
payload = {
    "title": f"📱 Posts del {fecha} — {tema_hoy}",
    "body": cuerpo,
    "labels": ["contenido-pendiente"]
}

resp = requests.post(url, headers=headers, json=payload)
resp.raise_for_status()

print(f"Issue creado correctamente: {resp.json()['html_url']}")
