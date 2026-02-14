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
# FRONTEND (static)
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/")
def serve_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.get("/fpm")
def serve_fpm():
    return FileResponse(os.path.join(FRONTEND_DIR, "fpm.html"))

# =========================
# CONFIG
# =========================
MIN_RELEVANCIA = 1  # mantém filtro mínimo (lógica original), só aumentamos termos/queries
TZ_BRASIL = timezone(timedelta(hours=-3))

# =========================
# PUBLISHERS
# =========================
ROYALTIES_PUBLISHERS = [
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
    "Agência Nacional do Petróleo",
    "IBAMA",
    "Portos e Navios",
    "Brasil Energia",
    "Offshore Energy",
    "BNAmericas",
    "Eixos",
    "epbr",
]

FPM_PUBLISHERS = [
    "Agência Brasil",
    "g1",
    "Estadão",
    "Folha",
    "O Globo",
    "UOL",
    "CNN Brasil",
    "InfoMoney",
    "Valor Econômico",
    "Consultor Jurídico",
    "ConJur",
    "CNM",
    "Confederação Nacional de Municípios",
    "IBGE",
    "STF",
    "STJ",
    "TCU",
    "Agência Senado",
    "Câmara dos Deputados",
    "Senado",
]

# =========================
# TERMOS (RELEVÂNCIA)
# =========================
ROYALTIES_TERMS = [
    # royalties base
    "royalties", "royalties de petróleo", "royalties do petróleo",
    "royalties gás natural", "royalties de gás natural",
    "participação especial", "compensação financeira",

    # termos adicionais (seu pedido)
    "royalties de petróleo",
    "anp",
    "agência nacional do petróleo",
    "gás natural",
    "exploração de petróleo",
    "exploração de gás natural",
    "processo judicial anp",
    "processo judicial royalties de petróleo",
    "processo judicial royalties gás natural",

    # exploração & produção
    "exploração", "produção", "perfuração", "poço", "poço exploratório",
    "sísmica", "levantamento sísmico",
    "bloco exploratório", "oferta permanente", "leilão anp", "rodada anp",
    "contrato de concessão", "contrato de partilha",
    "campo", "campo produtor", "entrada em produção", "ramp-up",

    # offshore/infra
    "offshore", "onshore", "plataforma", "plataforma de petróleo",
    "fpso", "navio-plataforma", "sonda", "sonda de perfuração",
    "gasoduto", "oleoduto", "terminal marítimo", "escoamento de produção",

    # bacias / regiões estratégicas
    "pré-sal", "presal",
    "margem equatorial",
    "bacia da foz do amazonas",
    "bacia de campos",
    "bacia de santos",
    "bacia potiguar",
    "bacia de sergipe-alagoas",
    "bacia do recôncavo",
    "bacia do parnaíba",

    # municipal/jurídico
    "municípios confrontantes",
    "redistribuição de royalties",
    "lei dos royalties",
    "ação judicial",
    "stf",
    "stj",
    "tcu",

    # incidentes
    "vazamento de óleo",
    "derramamento de óleo",
    "incidente em plataforma",
    "paralisação de produção",
]

FPM_TERMS = [
    # termos base e os seus (com variações)
    "fpm",
    "fundo de participação dos municipios",
    "fundo de participação dos municípios",
    "fundo de participação municipal",
    "ibge",
    "censo",
    "processo judicial fpm",
    "majoração do coeficiente",
    "coeficiente do fpm",
    "coeficiente fpm",
    "coeficiente populacional",
    "repasse fpm",
    "transferência constitucional",
    "revisão do coeficiente",
]

# =========================
# FUNÇÕES (LÓGICA ORIGINAL)
# =========================
def calcular_relevancia(texto: str, termos) -> int:
    t = (texto or "").lower()
    score = 0
    for termo in termos:
        if termo.lower() in t:
            score += 1
    return score

def get_publisher(entry) -> str:
    title = getattr(entry, "title", "") or ""
    if " - " in title:
        return title.rsplit(" - ", 1)[-1].strip()
    return ""

def publisher_valido(publisher: str, lista) -> bool:
    if not publisher:
        return False
    p = publisher.lower()
    return any(item.lower() in p for item in lista)

def janela_datas(dias: int):
    agora = datetime.now(TZ_BRASIL)
    if dias == 1:
        inicio = agora.replace(hour=0, minute=0, second=0, microsecond=0)
        fim = agora.replace(hour=23, minute=59, second=59, microsecond=999999)
    else:
        inicio = agora - timedelta(days=dias)
        fim = agora
    return inicio, fim

def buscar_generico(dias: int, termos, publishers, queries):
    inicio, fim = janela_datas(dias)

    resultados = []
    vistos = set()

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

            # UTC -> Brasil (correto)
            data_utc = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            data_pub = data_utc.astimezone(TZ_BRASIL)

            if not (inicio <= data_pub <= fim):
                continue

            link = getattr(entry, "link", "") or ""
            if not link or link in vistos:
                continue
            vistos.add(link)

            publisher = get_publisher(entry)
            if not publisher_valido(publisher, publishers):
                continue

            texto = f"{getattr(entry,'title','')} {getattr(entry,'summary','')}"
            relev = calcular_relevancia(texto, termos)
            if relev < MIN_RELEVANCIA:
                continue

            resultados.append({
                "titulo": getattr(entry, "title", ""),
                "link": link,
                "data": data_pub.strftime("%d/%m/%Y"),
                "fonte": publisher,
                "relevancia": relev
            })

    resultados.sort(key=lambda x: (x["relevancia"], x["data"]), reverse=True)
    return resultados

# =========================
# ENDPOINTS
# =========================
@app.get("/buscar-royalties")
def buscar_royalties(dias: int = Query(7, ge=1, le=60)):
    # Multi-queries robustas (mantém lógica; só ampliamos)
    queries = [
        "royalties de petróleo Brasil",
        "royalties gás natural Brasil",
        "ANP royalties",
        "Agência Nacional do Petróleo royalties",
        "exploração de petróleo Brasil",
        "exploração de gás natural Brasil",
        "processo judicial ANP",
        "processo judicial royalties de petróleo",
        "processo judicial royalties gás natural",
        "participação especial petróleo municípios",
        "margem equatorial petróleo",
        "bacia da foz do amazonas petróleo",
        "produção de petróleo offshore Brasil",
        "oferta permanente ANP blocos",
        "leilão ANP petróleo gás",
    ]

    resultados = buscar_generico(dias, ROYALTIES_TERMS, ROYALTIES_PUBLISHERS, queries)
    return {
        "tipo": "Royalties de Petróleo",
        "periodo": "Hoje" if dias == 1 else f"Últimos {dias} dias",
        "quantidade": len(resultados),
        "noticias": resultados
    }

@app.get("/buscar-fpm")
def buscar_fpm(dias: int = Query(7, ge=1, le=60)):
    queries = [
        "FPM",
        "Fundo de Participação dos Municípios",
        "Fundo de participação municipal",
        "IBGE censo FPM",
        "coeficiente do FPM",
        "coeficiente FPM IBGE",
        "majoração do coeficiente FPM",
        "processo judicial FPM",
        "revisão coeficiente FPM",
        "repasse FPM municípios",
    ]

    resultados = buscar_generico(dias, FPM_TERMS, FPM_PUBLISHERS, queries)
    return {
        "tipo": "FPM",
        "periodo": "Hoje" if dias == 1 else f"Últimos {dias} dias",
        "quantidade": len(resultados),
        "noticias": resultados
    }
