from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import feedparser
from datetime import datetime, timedelta, timezone
import os
import urllib.parse

app = FastAPI()

# =========================
# CORS
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# CAMINHOS
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")

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
# TERMOS EXPLORAÇÃO & PRODUÇÃO
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
# FUNÇÕES AUXILIARES
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

    # 🔥 TIMEZONE BRASIL
    tz_brasil = timezone(timedelta(hours=-3))
    agora = datetime.now(tz_brasil)

    if dias == 1:
        # Apenas o dia atual
        limite_inferior = agora.replace(hour=0, minute=0, second=0, microsecond=0)
        limite_superior = agora.replace(hour=23, minute=59, second=59, microsecond=999999)
    else:
        limite_inferior = agora - timedelta(days=dias)
        limite_superior = agora

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

            if not entry.get("published_parsed"):
                continue

            # 🔥 CONVERSÃO CORRETA UTC → BRASIL
            data_utc = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            data_publicacao = data_utc.astimezone(tz_brasil)

            if not (limite_inferior <= data_publicacao <= limite_superior):
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
        "periodo": "Hoje" if dias == 1 else f"Últimos {dias} dias",
        "quantidade": len(resultados),
        "noticias": resultados
    }
