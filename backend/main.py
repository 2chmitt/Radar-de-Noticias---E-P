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

from starlette.responses import Response
from starlette.staticfiles import StaticFiles

class NoCacheStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-store"
        return response

app.mount("/static", NoCacheStaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
def serve_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.get("/fpm")
def serve_fpm():
    return FileResponse(os.path.join(FRONTEND_DIR, "fpm.html"))

@app.get("/sobre")
def serve_sobre():
    return FileResponse(os.path.join(FRONTEND_DIR, "sobre.html"))

# =========================
# CONFIG
# =========================
MIN_RELEVANCIA = 1
TZ_BRASIL = timezone(timedelta(hours=-3))

# =========================
# PUBLISHERS
# =========================
ROYALTIES_PUBLISHERS = [
    "Valor Econômico","Reuters","Agência Brasil","g1","Estadão","Folha",
    "O Globo","CNN Brasil","InfoMoney","Petrobras","ANP",
    "Agência Nacional do Petróleo","IBAMA","Portos e Navios",
    "Brasil Energia","Offshore Energy","BNAmericas","Eixos","epbr",
]

FPM_PUBLISHERS = [
    # originais
    "Agência Brasil","g1","Estadão","Folha","O Globo","UOL",
    "CNN Brasil","InfoMoney","Valor Econômico","Consultor Jurídico",
    "ConJur","CNM","Confederação Nacional de Municípios",
    "IBGE","STF","STJ","TCU","Agência Senado",
    "Câmara dos Deputados","Senado",

    # fortalecimento institucional
    "Portal da Transparência",
    "Ministério da Fazenda",
    "Ministério do Planejamento",
    "Tesouro Nacional",
    "Secretaria do Tesouro Nacional",
    "Gov.br",
    "Planalto",
    "Diário Oficial da União",
    "Diário Oficial",
    "Tribunal de Contas da União",
    "Tribunal de Contas",
    "CNM Notícias",
    "Agência Câmara",
    "Agência Senado Notícias",
]


# =========================
# TERMOS (ORIGINAIS COMPLETOS)
# =========================
ROYALTIES_TERMS = [
    "royalties","royalties de petróleo","royalties do petróleo",
    "royalties gás natural","royalties de gás natural",
    "participação especial","compensação financeira",
    "anp","agência nacional do petróleo","gás natural",
    "exploração de petróleo","exploração de gás natural",
    "processo judicial anp","processo judicial royalties de petróleo",
    "processo judicial royalties gás natural","exploração","produção",
    "perfuração","poço","poço exploratório","sísmica",
    "levantamento sísmico","bloco exploratório","oferta permanente",
    "leilão anp","rodada anp","contrato de concessão",
    "contrato de partilha","campo","campo produtor",
    "entrada em produção","ramp-up","offshore","onshore",
    "plataforma","plataforma de petróleo","fpso","navio-plataforma",
    "sonda","sonda de perfuração","gasoduto","oleoduto",
    "terminal marítimo","escoamento de produção","pré-sal","presal",
    "margem equatorial","bacia da foz do amazonas",
    "bacia de campos","bacia de santos","bacia potiguar",
    "bacia de sergipe-alagoas","bacia do recôncavo",
    "bacia do parnaíba","municípios confrontantes",
    "redistribuição de royalties","lei dos royalties",
    "ação judicial","stf","stj","tcu","vazamento de óleo",
    "derramamento de óleo","incidente em plataforma",
    "paralisação de produção",
]

FPM_TERMS = [
    # termos originais
    "fpm","fundo de participação dos municipios",
    "fundo de participação dos municípios",
    "fundo de participação municipal","ibge","censo",
    "processo judicial fpm","majoração do coeficiente",
    "coeficiente do fpm","coeficiente fpm",
    "coeficiente populacional","repasse fpm",
    "transferência constitucional","revisão do coeficiente",

    # fortalecimento institucional
    "transferências constitucionais",
    "transferência intergovernamental",
    "receita municipal",
    "receitas municipais",
    "arrecadação municipal",
    "finanças municipais",
    "orçamento municipal",
    "orçamento dos municípios",
    "partilha de recursos",
    "redistribuição do fpm",
    "quota do fpm",
    "quota-parte do fpm",

    # IBGE e dados demográficos
    "estimativa populacional",
    "população estimada",
    "dados do ibge",
    "divulgação do censo",
    "revisão populacional",
    "atualização populacional",
    "contagem populacional",
    "projeção populacional",

    # jurídico
    "ação no stf sobre fpm",
    "ação no stj sobre fpm",
    "decisão judicial fpm",
    "liminar fpm",
    "mandado de segurança fpm",
    "controle de constitucionalidade fpm",
    "artigo 159 da constituição",
    "constituição federal art 159",
    "tribunal de contas da união fpm",
    "tcu fpm",

    # CNM / municipalismo
    "confederação nacional de municípios",
    "cnm fpm",
    "movimento municipalista",
    "municipalismo",
    "prefeituras",
    "prefeitos",
    "impacto do fpm",
    "queda do fpm",
    "aumento do fpm",

    # economia pública
    "receita corrente líquida",
    "equilíbrio fiscal municipal",
    "responsabilidade fiscal municípios",
    "lei de responsabilidade fiscal",
    "impacto orçamentário fpm",

    # político-institucional
    "câmara dos deputados fpm",
    "senado fpm",
    "comissão de finanças e tributação",
    "reforma tributária municípios",
    "pacto federativo",
]

# =========================
# FUNÇÕES ORIGINAIS
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

# =========================
# MÉTODO GOOGLE (ORIGINAL)
# =========================
def buscar_google(dias, termos, publishers, queries):
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
# RSS DIRETO
# =========================
RSS_FEEDS_ROYALTIES = [
    "https://g1.globo.com/rss/g1/economia/",
    "https://agenciabrasil.ebc.com.br/rss/economia/feed.xml",
    "https://www.infomoney.com.br/feed/",
]

RSS_FEEDS_FPM = [
    "https://agenciabrasil.ebc.com.br/rss/politica/feed.xml",
    "https://www.cnm.org.br/rss",
]

def buscar_rss(dias, termos, publishers, feeds):
    inicio, fim = janela_datas(dias)
    resultados = []
    vistos = set()

    for feed_url in feeds:
        feed = feedparser.parse(feed_url)

        for entry in feed.entries:
            if not entry.get("published_parsed"):
                continue

            data_utc = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            data_pub = data_utc.astimezone(TZ_BRASIL)

            if not (inicio <= data_pub <= fim):
                continue

            link = getattr(entry, "link", "") or ""
            if not link or link in vistos:
                continue
            vistos.add(link)

            publisher = feed.feed.get("title", "RSS")
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
# BING
# =========================

from urllib.parse import urlparse, urlunparse

def buscar_bing(dias, termos, publishers, queries):
    inicio, fim = janela_datas(dias)
    resultados = []
    vistos = set()

    for q in queries:
        query = urllib.parse.quote(q)
        url = f"https://www.bing.com/news/search?q={query}&format=rss"
        feed = feedparser.parse(url)

        for entry in feed.entries:
            if not entry.get("published_parsed"):
                continue

            data_utc = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            data_pub = data_utc.astimezone(TZ_BRASIL)

            if not (inicio <= data_pub <= fim):
                continue

            link_original = getattr(entry, "link", "") or ""
            if not link_original:
                continue

            # 🔥 NORMALIZA LINK (REMOVE TRACKING DO BING)
            parsed = urlparse(link_original)
            link_limpo = urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))

            # 🔥 CONTROLE DE DUPLICAÇÃO
            if link_limpo in vistos:
                continue
            vistos.add(link_limpo)

            publisher = "Bing News"

            texto = f"{getattr(entry,'title','')} {getattr(entry,'summary','')}"
            relev = calcular_relevancia(texto, termos)
            if relev < MIN_RELEVANCIA:
                continue

            resultados.append({
                "titulo": getattr(entry, "title", ""),
                "link": link_original,  # mantém link original para o usuário
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
def buscar_royalties(
    dias: int = Query(7, ge=1, le=60),
    metodo: str = Query("google")
):

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

    if metodo == "rss":
        resultados = buscar_rss(dias, ROYALTIES_TERMS, ROYALTIES_PUBLISHERS, RSS_FEEDS_ROYALTIES)
    elif metodo == "bing":
        resultados = buscar_bing(dias, ROYALTIES_TERMS, ROYALTIES_PUBLISHERS, queries)
    else:
        resultados = buscar_google(dias, ROYALTIES_TERMS, ROYALTIES_PUBLISHERS, queries)

    return {
        "tipo": "Royalties de Petróleo",
        "periodo": "Hoje" if dias == 1 else f"Últimos {dias} dias",
        "metodo": metodo.capitalize(),
        "quantidade": len(resultados),
        "noticias": resultados
    }

@app.get("/buscar-fpm")
def buscar_fpm(
    dias: int = Query(7, ge=1, le=60),
    metodo: str = Query("google")
):

    queries = [
       # base direta
    "FPM",
    "Fundo de Participação dos Municípios",
    "Fundo de participação municipal",

    # repasses
    "repasse do FPM",
    "repasse FPM municípios",
    "repasse federal municípios",
    "transferência do FPM",
    "transferências constitucionais municípios",
    "Tesouro Nacional FPM",
    "Secretaria do Tesouro Nacional FPM",

    # linguagem jornalística
    "municípios recebem FPM",
    "prefeituras recebem FPM",
    "queda do FPM",
    "aumento do FPM",
    "valor do FPM",
    "terceiro decêndio do FPM",
    "segundo decêndio do FPM",
    "primeiro decêndio do FPM",

    # IBGE e coeficiente
    "coeficiente do FPM IBGE",
    "revisão coeficiente FPM",
    "estimativa populacional IBGE municípios",
    "censo IBGE impacto FPM",
    "majoração coeficiente FPM",

    # legislativo e judicial
    "projeto de lei FPM",
    "STF FPM decisão",
    "STJ FPM decisão",
    "TCU FPM",
    "ação judicial FPM",

    # contexto econômico
    "orçamento municipal FPM",
    "arrecadação municipal FPM",
    "receita municipal FPM",
    "impacto do FPM nos municípios",

    # pacto federativo
    "pacto federativo municípios",
    "reforma tributária municípios FPM",
    ]

    if metodo == "rss":
        resultados = buscar_rss(dias, FPM_TERMS, FPM_PUBLISHERS, RSS_FEEDS_FPM)
    elif metodo == "bing":
        resultados = buscar_bing(dias, FPM_TERMS, FPM_PUBLISHERS, queries)
    else:
        resultados = buscar_google(dias, FPM_TERMS, FPM_PUBLISHERS, queries)

    return {
        "tipo": "FPM",
        "periodo": "Hoje" if dias == 1 else f"Últimos {dias} dias",
        "metodo": metodo.capitalize(),
        "quantidade": len(resultados),
        "noticias": resultados
    }
