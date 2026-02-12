from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import feedparser
from datetime import datetime, timedelta
import os
import urllib.parse
import time

app = FastAPI()

# =========================
# CORS (Render-safe)
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # depois pode restringir
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# CAMINHOS (IMPORTANTE PARA RENDER)
# =========================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")

# =========================
# SERVIR ARQUIVOS ESTÁTICOS
# =========================

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/")
def serve_frontend():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

# =========================
# FONTES PERMITIDAS
# =========================

ALLOWED_PUBLISHERS = [
    "Valor Econômico",
    "Reuters",
    "Agência Brasil",
    "g1",
    "Estadão",
    "Folha",
    "O Globo",
    "CNN Brasil",
    "InfoMoney",
    "Petrobras",
    "ANP",
    "IBAMA",
    "Portos e Navios",
    "Brasil Energia",
    "Offshore Energy",
    "BNAmericas",
    "Eixos",
    "epbr"
]

# =========================
# TERMOS E&P
# =========================

KEY_TERMS = [
    "petróleo", "óleo", "petrobras", "anp",
    "exploração", "perfuração", "produção",
    "pré-sal", "presal", "offshore",
    "bacia", "campo", "plataforma", "fpso",
    "contrato", "licitação", "leilão",
    "royalties", "capex",
    "margem equatorial",
    "bacia de campos", "bacia de santos"
]

MIN_RELEVANCIA = 2

# =========================
# FUNÇÕES
# =========================

def normalizar(txt):
    return (txt or "").lower()

def calcular_relevancia(texto):
    score = 0
    t = normalizar(texto)
    for termo in KEY_TERMS:
        if termo in t:
            score += 1
    return score

def publisher_valido(publisher):
    if not publisher:
        return False
    return any(p.lower() in publisher.lower() for p in ALLOWED_PUBLISHERS)

def get_publisher(entry):
    if " - " in entry.title:
        return entry.title.rsplit(" - ", 1)[-1]
    return ""

# =========================
# ROTA PRINCIPAL
# =========================

@app.get("/buscar-noticias")
def buscar_noticias(dias: int = Query(7, ge=1, le=90)):

    hoje = datetime.now()
    limite = hoje - timedelta(days=dias)

    resultados = []
    vistos = set()

    queries = [
        "petróleo Brasil",
        "exploração de petróleo Brasil",
        "produção de petróleo Brasil",
        "ANP leilão petróleo",
        "perfuração offshore Brasil",
        "pré-sal produção Brasil",
        "bacia de campos produção",
        "bacia de santos pré-sal",
        "margem equatorial petróleo"
    ]

    for q in queries:

        query = urllib.parse.quote(q)

        url = (
            "https://news.google.com/rss/search?"
            f"q={query}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
        )

        feed = feedparser.parse(url)

        for entry in feed.entries:

            data_publicacao = None

            if entry.get("published_parsed"):
                data_publicacao = datetime.fromtimestamp(
                    time.mktime(entry.published_parsed)
                )

            if not data_publicacao or data_publicacao < limite:
                continue

            publisher = get_publisher(entry)

            if not publisher_valido(publisher):
                continue

            texto_completo = f"{entry.title} {entry.get('summary','')}"
            nivel_relevancia = calcular_relevancia(texto_completo)

            if nivel_relevancia < MIN_RELEVANCIA:
                continue

            if entry.link in vistos:
                continue

            vistos.add(entry.link)

            resultados.append({
                "titulo": entry.title,
                "link": entry.link,
                "data": data_publicacao.strftime("%d/%m/%Y"),
                "fonte": publisher,
                "relevancia": nivel_relevancia
            })

    resultados.sort(
        key=lambda x: (x["relevancia"], x["data"]),
        reverse=True
    )

    return {
        "periodo": f"Últimos {dias} dias",
        "quantidade": len(resultados),
        "noticias": resultados
    }
