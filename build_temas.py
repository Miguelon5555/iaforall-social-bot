"""
build_temas.py
Reconstruye temas.json antes de cada ejecución del bot social, combinando:
  1) Una noticia fresca sacada de los mismos feeds RSS que usa app.js del blog
  2) Una rotación aleatoria de tutoriales/apps/prompts estáticos (copiados de app.js)

Ejecútalo como paso previo a generate.py en el workflow de GitHub Actions.
"""

import html
import json
import os
import random
import re
import time
import urllib.request
import urllib.parse

# Guías originales publicadas en el blog (las genera el repo ia-para-todos)
SITE = "https://iaforall.netlify.app"
GUIAS_JSON_URL = "https://raw.githubusercontent.com/Miguelon5555/ia-para-todos/refs/heads/main/guias.json"
GUIA_PAGINA_URL = "https://raw.githubusercontent.com/Miguelon5555/ia-para-todos/refs/heads/main/prompts/{slug}/index.html"
# True = el bot solo promociona guías publicadas (el único contenido propio al que puede enviar con honestidad).
# Cuando el blog tenga páginas propias de noticias/tutoriales/apps, cámbialo a False.
SOLO_GUIAS = True
CADA_N_NO_GUIA = 3  # Solo se usa con SOLO_GUIAS = False: 2 de cada 3 ejecuciones promocionan una guía

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


def descargar(url, timeout=15, intentos=3):
    req = urllib.request.Request(url, headers={"User-Agent": "iaforall-social-bot/1.0"})
    ultimo_error = None
    for n in range(intentos):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8")
        except Exception as e:
            ultimo_error = e
            if n < intentos - 1:
                time.sleep(2)
    raise ultimo_error


def obtener_guias():
    """Lista de guías publicadas (guias.json del blog). Si falla, devuelve []."""
    try:
        guias = json.loads(descargar(GUIAS_JSON_URL))
        return [g for g in guias if re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", g.get("slug", ""))]
    except Exception as e:
        print(f"⚠️ No se pudo leer guias.json: {e}")
        return []


def limpiar_html(fragmento):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragmento)).split())


def leer_detalle_guia(slug):
    """Devuelve (resumen, prompt, incluye) leyendo la página real de la guía."""
    try:
        pagina = descargar(GUIA_PAGINA_URL.format(slug=slug))
    except Exception as e:
        print(f"⚠️ No se pudo leer la guía {slug}: {e}")
        return None, None, None
    resumen = re.search(r'<p class="resumen">(.*?)</p>', pagina, re.S)
    prompt = re.search(r'<pre id="prompt-principal"[^>]*>(.*?)</pre>', pagina, re.S)

    # Qué contiene realmente la guía (para que los posts no prometan de más)
    secciones = [limpiar_html(x) for x in re.findall(r"<h2>(.*?)</h2>", pagina, re.S)]
    secciones = [x for x in secciones if x and x != "Más guías"]
    incluye = ", ".join(secciones)
    m = re.search(r"<h2>Variantes[^<]*</h2>(.*?)<h2>", pagina, re.S)
    if m:
        variantes = [limpiar_html(x) for x in re.findall(r"<h3>(.*?)</h3>", m.group(1), re.S)]
        if variantes:
            incluye += ". Variantes del prompt: " + "; ".join(variantes)

    return (
        limpiar_html(resumen.group(1)) if resumen else None,
        html.unescape(prompt.group(1)).strip() if prompt else None,
        incluye or None,
    )


def tema_de_guia_para_hoy():
    """Elige una guía (rotando entre todas) y la convierte en tema. None si hoy toca otra cosa."""
    guias = obtener_guias()
    if not guias:
        return None

    run = int(os.environ.get("GITHUB_RUN_NUMBER", "1"))
    if SOLO_GUIAS:
        guia = guias[run % len(guias)]
    else:
        if run % CADA_N_NO_GUIA == 0:
            print("ℹ️ Hoy toca hablar de otra cosa que no sea una guía")
            return None
        guia = guias[(run - run // CADA_N_NO_GUIA) % len(guias)]
    resumen, prompt, incluye = leer_detalle_guia(guia["slug"])
    if not resumen:  # sin el contenido real de la guía, no se inventa nada
        return None

    url = f"{SITE}/prompts/{guia['slug']}/"
    lineas = [
        f"Guía del blog: «{guia['titulo']}»",
        f"URL de la guía (usa EXACTAMENTE esta dirección en los enlaces): {url}",
        f"Categoría: {guia.get('categoria', '')}",
        f"Resumen de la guía: {resumen}",
    ]
    if incluye:
        lineas.append(f"Qué incluye la guía (descríbela solo con esto): {incluye}")
    if prompt:
        lineas.append(f"Prompt de la guía (puedes citarlo tal cual):\n{prompt}")
    print(f"📘 Se promociona la guía: {guia['slug']}")
    return "\n".join(lineas)


def construir_temas():
    temas = []

    tema_guia = tema_de_guia_para_hoy()
    if tema_guia:
        temas.append(tema_guia)
    elif SOLO_GUIAS:
        raise SystemExit(
            "❌ No se pudo leer ninguna guía del blog (guias.json o la página de la guía). "
            "No se genera contenido para no prometer páginas que no existen. Vuelve a lanzar el workflow."
        )
    else:
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
