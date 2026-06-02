import os
import re
import json
import csv
import time
import asyncio
import threading
import urllib.parse
from datetime import datetime
from typing import Dict, List, Set, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import anthropic

app = FastAPI(title="Reputação Digital - Marcelo Baptista de Oliveira")

# Enable CORS for frontend flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables to track the current task progress
analysis_task = {
    "is_running": False,
    "progress": 0,
    "total": 100,
    "current_status": "Idle",
    "logs": []
}

# WebSocket Manager to broadcast progress logs to frontend in real-time
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        # Send current state upon connection
        await websocket.send_json({
            "type": "state",
            "data": analysis_task
        })

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

def add_log(msg: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_line = f"[{timestamp}] {msg}"
    print(log_line)
    analysis_task["logs"].append(log_line)
    # limit log array size
    if len(analysis_task["logs"]) > 200:
        analysis_task["logs"].pop(0)
    
    # Run async broadcast in synchronous context using loop helper
    asyncio.run(manager.broadcast({
        "type": "log",
        "message": log_line,
        "state": analysis_task
    }))

# Next-gen models supported by user account
MODELS_TO_TRY = [
    "claude-haiku-4-5-20251001",
    "claude-sonnet-4-5-20250929",
    "claude-sonnet-4-6"
]

def load_env_api_key():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key and os.path.exists(".env"):
        try:
            with open(".env", "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip() and not line.startswith("#"):
                        parts = line.strip().split("=", 1)
                        if len(parts) == 2 and parts[0].strip() == "ANTHROPIC_API_KEY":
                            api_key = parts[1].strip().strip('"').strip("'")
                            break
        except Exception:
            pass
    return api_key

def check_captcha_and_wait(page):
    if "google.com/recaptcha" in page.url or page.locator("#captcha-form").count() > 0:
        add_log("⚠️ GOOGLE CAPTCHA DETECTADO! Por favor, resolva o CAPTCHA no navegador visível que se abriu na sua tela.")
        # Wait up to 90 seconds for captcha resolution
        for i in range(90):
            if not ("google.com/recaptcha" in page.url or page.locator("#captcha-form").count() > 0):
                add_log("✅ CAPTCHA resolvido com sucesso! Continuando...")
                break
            time.sleep(1)
        page.wait_for_load_state("networkidle")

def handle_consent_if_needed(page):
    try:
        consent_selectors = [
            "button:has-text('Rejeitar tudo')",
            "button:has-text('Aceitar tudo')",
            "button:has-text('Accept all')",
            "button:has-text('Reject all')",
            "#L2AGLb"
        ]
        for selector in consent_selectors:
            btn = page.locator(selector)
            if btn.count() > 0 and btn.is_visible():
                btn.click()
                page.wait_for_load_state("networkidle")
                break
    except Exception:
        pass

def scrape_google_search(page, query: str, results_needed: int = 100) -> List[dict]:
    all_results = []
    start_index = 0
    pages_checked = 0
    
    while len(all_results) < results_needed and pages_checked < 15:
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://www.google.com/search?q={encoded_query}&start={start_index}"
        add_log(f"Pesquisando no Google: buscando a partir do resultado {start_index}...")
        
        page.goto(url)
        page.wait_for_load_state("domcontentloaded")
        
        handle_consent_if_needed(page)
        check_captcha_and_wait(page)
        
        time.sleep(2)
        html = page.content()
        soup = BeautifulSoup(html, "html.parser")
        
        # Parse search blocks
        search_blocks = soup.find_all("div", class_="g")
        links_with_h3 = []
        for a in soup.find_all("a", href=True):
            h3 = a.find("h3")
            if h3:
                href = a["href"]
                if href.startswith("/search?") or "google.com" in href and "search?" in href:
                    continue
                links_with_h3.append((a, h3))
                
        page_results = []
        if not search_blocks and links_with_h3:
            for a, h3 in links_with_h3:
                title = h3.get_text().strip()
                link = a["href"]
                if link.startswith("/url?q="):
                    link = link.split("/url?q=")[1].split("&")[0]
                    link = urllib.parse.unquote(link)
                if not link.startswith("http") or "google.com" in link:
                    continue
                page_results.append({"title": title, "url": link, "snippet": ""})
        else:
            for block in search_blocks:
                a_tag = block.find("a", href=True)
                h3_tag = block.find("h3")
                if not a_tag or not h3_tag:
                    continue
                title = h3_tag.get_text().strip()
                link = a_tag["href"]
                if link.startswith("/url?q="):
                    link = link.split("/url?q=")[1].split("&")[0]
                    link = urllib.parse.unquote(link)
                if not link.startswith("http") or "google.com" in link:
                    continue
                
                snippet = ""
                snippet_elem = block.find("div", class_="VwiC3b") or block.find("span", class_="aCOpRe")
                if snippet_elem:
                    snippet = snippet_elem.get_text().strip()
                
                page_results.append({"title": title, "url": link, "snippet": snippet})
                
        if not page_results:
            add_log("⚠️ Google retornou uma página vazia. Bloqueio suspeito. Aguardando 10 segundos antes de tentar novamente...")
            time.sleep(10)
            break
            
        for pr in page_results:
            if not any(ar["url"] == pr["url"] for ar in all_results):
                pr["rank"] = len(all_results) + 1
                all_results.append(pr)
                
        add_log(f"Encontrados {len(page_results)} resultados nesta página. Total coletado: {len(all_results)}/100")
        
        if len(all_results) >= results_needed:
            all_results = all_results[:results_needed]
            break
            
        start_index += 10
        pages_checked += 1
        time.sleep(2.5)
        
    return all_results

def get_text_content(page, url: str):
    domain = urllib.parse.urlparse(url).netloc.lower()
    is_social = any(x in domain for x in ["youtube.com", "youtu.be", "instagram.com", "facebook.com", "tiktok.com", "linkedin.com"])
    
    try:
        if is_social:
            add_log(f"🔑 [Login/Interação] Abrindo rede social ({domain}). Aguardando 15 segundos para você interagir/fazer login se necessário...")
            page.goto(url, timeout=30000, wait_until="load")
            # Wait 15 seconds to allow manual interaction/login
            for i in range(15):
                time.sleep(1)
        else:
            page.goto(url, timeout=15000, wait_until="domcontentloaded")
            time.sleep(1.5)
        
        html = page.content()
        soup = BeautifulSoup(html, "html.parser")
        for s in soup(["script", "style", "noscript", "iframe", "header", "footer", "nav"]):
            s.decompose()
            
        text = soup.get_text(separator=' ')
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        clean_text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return clean_text[:12000], None
    except Exception as e:
        return None, str(e)

def analyze_content_with_claude(client, url, title, text):
    prompt = f"""
    Analise o seguinte conteúdo textual extraído da página web:
    URL: {url}
    Título da página: {title}
    
    Texto da página:
    ---
    {text}
    ---
    
    Extraia as seguintes informações em formato JSON. Responda APENAS o JSON puro, sem explicações extras, sem formatação markdown (sem ```json):
    {{
        "categoria": "Categoria da página (Ex: Biografia Empresarial, Agronegócio, Legal, Imprensa, Perfil Profissional, etc.)",
        "tema": "Tema principal tratado (Ex: História do Grupo Protege, Criação de Cavalos, Processos Judiciais, etc.)",
        "resumo": "Um resumo em português de 2 a 4 linhas sobre o conteúdo da página relacionado a Marcelo Baptista de Oliveira.",
        "destaques_negativos": "Principais pontos ou menções negativas encontradas (se houver). Se não houver, escreva 'Nenhum destaque negativo identificado.'",
        "destaques_positivos": "Principais pontos ou menções positivas (Ex: liderança, prêmios, conquistas, hobbies enriquecedores). Se não houver, escreva 'Nenhum destaque positivo identificado.'"
    }}
    """
    for model_name in MODELS_TO_TRY:
        try:
            response = client.messages.create(
                model=model_name,
                max_tokens=1000,
                temperature=0,
                messages=[{"role": "user", "content": prompt}]
            )
            response_text = response.content[0].text.strip()
            if response_text.startswith("```json"):
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif response_text.startswith("```"):
                response_text = response_text.split("```")[1].split("```")[0].strip()
            return json.loads(response_text)
        except Exception as e:
            error_str = str(e)
            if "404" in error_str:
                continue
            time.sleep(2)
            
    return {
        "categoria": "Erro de Análise",
        "tema": "Erro no Processamento da IA",
        "resumo": "Não foi possível analisar o conteúdo desta página com a IA da Anthropic.",
        "destaques_negativos": "Erro de processamento da IA.",
        "destaques_positivos": "Erro de processamento da IA."
    }

def get_error_analysis(url, error_type):
    domain = urllib.parse.urlparse(url).netloc.lower()
    
    if "youtube.com" in domain or "youtu.be" in domain:
        return {
            "categoria": "Mídia Social",
            "tema": "Conteúdo de Vídeo",
            "resumo": "A URL fornecida refere-se a um vídeo no YouTube e não pôde ser analisada diretamente sem a reprodução do vídeo.",
            "destaques_negativos": "Não é possível determinar destaques negativos sem acesso ao conteúdo de vídeo.",
            "destaques_positivos": "O link indica a presença de conteúdo de vídeo relacionado ao executivo."
        }
    elif "instagram.com" in domain:
        return {
            "categoria": "Mídia Social",
            "tema": "Conteúdo de Instagram",
            "resumo": "A URL fornecida é um link para uma postagem ou Reel no Instagram. O conteúdo não pôde ser analisado devido às restrições de login da plataforma.",
            "destaques_negativos": "Não é possível determinar destaques negativos sem acesso direto ao conteúdo da mídia social.",
            "destaques_positivos": "Não é possível determinar destaques positivos sem acesso direto ao conteúdo da mídia social."
        }
    elif "facebook.com" in domain:
        return {
            "categoria": "Mídia Social",
            "tema": "Conteúdo de Facebook",
            "resumo": "A URL fornecida é um link do Facebook. O acesso direto foi bloqueado pelas políticas de login ou segurança da plataforma.",
            "destaques_negativos": "Nenhum destaque negativo pôde ser identificado a partir dos metadados básicos obtidos.",
            "destaques_positivos": "Presença ativa em redes sociais indicando relevância de marca pessoal."
        }
    else:
        return {
            "categoria": "Erro de Acesso",
            "tema": "Falha de Conexão",
            "resumo": f"Esta página não pôde ser carregada pelo servidor para análise do conteúdo devido à restrição do site ou queda de conexão ({error_type}).",
            "destaques_negativos": "Acesso bloqueado ou indisponível devido a restrições do servidor de destino.",
            "destaques_positivos": "Nenhum destaque positivo verificado devido à indisponibilidade do site."
        }

def run_background_analysis(query: str, limit: int):
    global analysis_task
    api_key = load_env_api_key()
    if not api_key:
        add_log("❌ ERRO: Chave ANTHROPIC_API_KEY não foi encontrada no arquivo .env!")
        analysis_task["is_running"] = False
        analysis_task["current_status"] = "Erro: API Key não configurada"
        return
        
    client = anthropic.Anthropic(api_key=api_key)
    analysis_task["is_running"] = True
    analysis_task["progress"] = 0
    analysis_task["logs"] = []
    
    add_log(f"🚀 Iniciando motor de coleta e análise para termo: '{query}' (limite de {limit} links)...")
    
    try:
        with sync_playwright() as p:
            # We open headful mode locally to allow manual Captcha / Social Login interaction
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )
            page = context.new_page()
            
            # Enforce phrase search by wrapping in double quotes
            clean_query = query.strip().strip('"').strip("'")
            quoted_query = f'"{clean_query}"'
            
            # Step 1: Scrape Google
            analysis_task["current_status"] = f"Raspando resultados do Google para: {quoted_query}..."
            search_results = scrape_google_search(page, quoted_query, limit)
            
            if not search_results:
                add_log("❌ ERRO: Nenhuma URL pôde ser extraída do Google.")
                analysis_task["is_running"] = False
                analysis_task["current_status"] = "Falha na raspagem do Google"
                browser.close()
                return
                
            add_log(f"✅ Coleta finalizada. Salvando resultados. Iniciando análise das {len(search_results)} URLs...")
            
            # Step 2: Loop through each URL
            analyses = []
            analysis_task["total"] = len(search_results)
            
            for idx, result in enumerate(search_results):
                url = result["url"]
                analysis_task["progress"] = idx + 1
                analysis_task["current_status"] = f"Analisando URL {idx+1}/{len(search_results)}..."
                add_log(f"[{idx+1}/{len(search_results)}] Carregando: {url}")
                

                
                text, error = get_text_content(page, url)
                analysis_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                if error:
                    add_log(f"⚠️ Erro ao carregar ({error}). Aplicando fallback.")
                    analysis = get_error_analysis(url, error)
                else:
                    add_log("🧠 Enviando texto extraído para o Claude...")
                    analysis = analyze_content_with_claude(client, url, result["title"], text)
                    
                analysis["url"] = url
                analysis["title"] = result["title"]
                analysis["rank"] = result["rank"]
                analysis["data_hora"] = analysis_time
                
                analyses.append(analysis)
                
                # Broadcast the newly analyzed URL to all websockets in real-time
                asyncio.run(manager.broadcast({
                    "type": "result",
                    "item": analysis,
                    "state": analysis_task
                }))
                
                time.sleep(2)
                
            browser.close()
            
            # Step 3: Write outputs locally for fallback backup
            with open("analysis_results.json", "w", encoding="utf-8") as f:
                json.dump(analyses, f, ensure_ascii=False, indent=4)
                
            add_log("🎉 Todas as análises foram concluídas! Iniciando consolidação de dados...")
            
    except Exception as e:
        add_log(f"❌ Erro fatal durante a automação: {e}")
        analysis_task["is_running"] = False
        analysis_task["current_status"] = f"Erro fatal: {e}"
        return

    # Step 4: Call Claude to generate the consolidated report
    analysis_task["current_status"] = "Gerando Relatório Consolidado Geral..."
    try:
        summaries_text = ""
        # Read the first 40 records to build the consolidated report summaries prompt
        for item in analyses[:40]:
            # skip errors to build a cleaner overview
            if "erro" not in item.get("categoria", "").lower():
                summaries_text += f"- URL: {item['url']}\n  Categoria: {item['categoria']}\n  Resumo: {item['resumo']}\n  Positivos: {item['destaques_positivos']}\n  Negativos: {item['destaques_negativos']}\n\n"
                
        prompt = f"""
        A partir das seguintes análises individuais de páginas encontradas na pesquisa sobre "{query}", elabore um relatório consolidado geral estruturado.
        O principal objetivo é destacar o que é NEGATIVO e o que é POSITIVO.
        
        Resumos Individuais:
        ---
        {summaries_text}
        ---
        
        Escreva um relatório em português estruturado em Markdown com as seguintes seções:
        1. # Relatório Consolidado de Reputação Digital - {query}
        2. ## Visão Geral da Presença Online (Resumo geral dos tipos de sites e temas dominantes encontrados na pesquisa)
        3. ## Destaques Positivos (Consolidação de conquistas, prêmios, liderança de mercado, empreendedorismo, menções favoráveis)
        4. ## Destaques Negativos e Áreas de Risco (Processos judiciais, trabalhistas ou cíveis comuns, conflitos ou menções desfavoráveis)
        5. ## Conclusão Geral e Índice de Sentimento (Classifique a reputação online geral como Predominantemente Positiva, Neutra ou Negativa, justificando a resposta com base nos dados analisados).
        """
        
        report = "Erro ao consolidar"
        for model_name in MODELS_TO_TRY:
            try:
                response = client.messages.create(
                    model=model_name,
                    max_tokens=1500,
                    temperature=0,
                    messages=[{"role": "user", "content": prompt}]
                )
                report = response.content[0].text.strip()
                break
            except Exception:
                continue
                
        # Save output locally
        with open("consolidated_report.md", "w", encoding="utf-8") as f:
            f.write(report)
            
        # Write updated js file locally
        with open("analysis_data.js", "w", encoding="utf-8") as f:
            f.write("const analysisResults = " + json.dumps(analyses, ensure_ascii=False, indent=4) + ";\n")
            f.write("const consolidatedReport = " + json.dumps(report, ensure_ascii=False) + ";\n")
            f.write(f"const consolidatedReportTime = '{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}';\n")
            
        add_log("✅ Relatório consolidado e arquivos de dados criados com sucesso!")
        
        # Broadcast final success state
        analysis_task["is_running"] = False
        analysis_task["current_status"] = "Concluído"
        asyncio.run(manager.broadcast({
            "type": "finished",
            "report": report,
            "results": analyses,
            "state": analysis_task
        }))
        
    except Exception as e:
        add_log(f"⚠️ Erro ao consolidar relatório: {e}")
        analysis_task["is_running"] = False
        analysis_task["current_status"] = "Concluído com falha no relatório"

@app.websocket("/ws/progress")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/api/start")
async def start_analysis(query: str = "Marcelo Baptista de Oliveira", limit: int = 100):
    if analysis_task["is_running"]:
        return {"status": "already_running", "message": "A análise já está em execução."}
        
    # Start analysis in a separate thread so FastAPI event loop is unblocked
    threading.Thread(target=run_background_analysis, args=(query, limit), daemon=True).start()
    return {"status": "started", "message": "Análise iniciada."}

@app.get("/api/state")
async def get_state():
    return analysis_task

# Mount local frontend files (static files)
# If main.py is in the workspace folder, it serves index.html, style.css, app.js and static data
app.mount("/", StaticFiles(directory=".", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    print("Iniciando servidor de desenvolvimento FastAPI...")
    uvicorn.run(app, host="127.0.0.1", port=8090)
