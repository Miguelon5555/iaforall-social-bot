"""
build_temas.py
Reconstruye temas.json antes de cada ejecución del bot social, combinando:
  1) Una noticia fresca sacada de los mismos feeds RSS que usa app.js del blog
  2) Una rotación aleatoria de tutoriales/apps/prompts estáticos (copiados de app.js)

Ejecútalo como paso previo a generate.py en el workflow de GitHub Actions.
"""

import json
import random
import urllib.request
import urllib.parse

# Mismos feeds que RSS_FEEDS en app.js del blog
RSS_FEEDS = [
    {"name": "Genbeta", "url": "https://feeds.weblogssl.com/genbeta"},
    {"name": "Hipertextual", "url": "https://hipertextual.com/feed"},
    {"name": "Wired en Español", "url": "https://es.wired.com/feed"},
    {
        "name": "Google News IA",
        "url": "https://news.google.com/rss/search?q=inteligencia+artificial+IA&hl=es&gl=ES&ceid=ES:es",
    },
]

# Copiado de TUTORIALS en app.js (solo los títulos, para mantenerlo corto)
TUTORIALES = [
    "Los Mejores Cursos de IA para 2026",
    "Cómo aprender IA desde cero en 2026",
    "Crear imágenes con FLUX AI - Tutorial",
    "Crear videos con Kling AI - Guía completa",
    "Automatización con Make y N8N",
    "Ingeniería de Prompts - Guía definitiva",
    "Como Estar al Día con la IA en 2026",
    "Crear GPTs personalizados - Tutorial",
    "Mejores Bootcamps de IA 2026",
]

# Copiado de APPS en app.js
APPS = [
    "ChatGPT: el asistente de IA más popular para conversar y resolver dudas",
    "Midjourney: genera imágenes increíbles a partir de descripciones de texto",
    "Claude: IA conversacional avanzada de Anthropic, gran alternativa a ChatGPT",
    "Canva IA: diseño gráfico potenciado con inteligencia artificial",
    "Grammarly: corrección y mejora de textos usando IA",
]

# Copiado de PROMPTS en app.js
PROMPTS = [
    "Prompt para resumir textos largos en 3 puntos clave",
    "Prompt para generar 10 ideas de contenido creativo",
    "Prompt para traducir texto manteniendo tono y estilo",
    "Prompt para explicar conceptos complejos como si tuvieras 10 años",
    "Prompt para generar código con comentarios explicativos",
    "Prompt para mejorar emails profesionales",
]


def obtener_noticia_fresca():
    """Intenta traer el titular más reciente de alguno de los feeds, en orden,
    hasta que uno responda. Si todos fallan, devuelve None."""
    random.shuffle(RSS_FEEDS)  # para no depender siempre de la misma fuente
    for feed in RSS_FEEDS:
        try:
            proxy_url = (
                "https://api.rss2json.com/v1/api.json?rss_url="
                + urllib.parse.quote(feed["url"])
            )
            with urllib.request.urlopen(proxy_url, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            if data.get("status") == "ok" and data.get("items"):
                titulo = data["items"][0]["title"]
                return f"Noticia: {titulo} (fuente: {feed['name']})"
        except Exception as e:
            print(f"⚠️ No se pudo leer {feed['name']}: {e}")
            continue
    return None


def construir_temas():
    temas = []

    noticia = obtener_noticia_fresca()
    if noticia:
        temas.append(noticia)
    else:
        print("⚠️ Ningún feed respondió, se omite la noticia de hoy")

    # Un tutorial, una app y un prompt al azar para variar cada ejecución
    temas.append("Tutorial: " + random.choice(TUTORIALES))
    temas.append("App recomendada: " + random.choice(APPS))
    temas.append("Prompt útil: " + random.choice(PROMPTS))

    salida = {
        "temas": temas,
        "plataformas_cta": [
            "instagram",
            "pinterest",
            "twitter",
            "tiktok_idea",
            "youtube_short",
            "linkedin",
        ],
    }

    with open("temas.json", "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)

    print(f"✅ temas.json actualizado con {len(temas)} temas")


if __name__ == "__main__":
    construir_temas()
