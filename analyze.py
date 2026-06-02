import json
import csv
import os
import sys
import time
from datetime import datetime
import urllib.parse
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

# Try to import anthropic, we will install it if missing
try:
    import anthropic
except ImportError:
    print("Installing anthropic...")
    os.system("pip install anthropic")
    import anthropic

# Setup Anthropic API Key
api_key = os.environ.get("ANTHROPIC_API_KEY")

# Check for a local .env file
env_path = ".env"
if not api_key and os.path.exists(env_path):
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip() and not line.startswith("#"):
                    key, val = line.strip().split("=", 1)
                    if key.strip() == "ANTHROPIC_API_KEY":
                        api_key = val.strip().strip('"').strip("'")
                        break
    except Exception as e:
        print(f"Erro ao ler o arquivo .env: {e}")

if not api_key:
    print("\n" + "="*70)
    print("Aviso: Chave API da Anthropic não encontrada no arquivo .env ou no sistema.")
    print("Você pode criar um arquivo '.env' na pasta com a linha:")
    print("ANTHROPIC_API_KEY=sua_chave_aqui")
    print("Ou digite-a abaixo agora:")
    api_key = input("Chave API da Anthropic: ").strip()
    print("="*70 + "\n")

if not api_key:
    print("Erro: Chave API necessária para realizar as análises.")
    sys.exit(1)

client = anthropic.Anthropic(api_key=api_key)
MODELS_TO_TRY = [
    "claude-haiku-4-5-20251001",
    "claude-sonnet-4-5-20250929",
    "claude-sonnet-4-6"
]

def get_text_content(page, url):
    domain = urllib.parse.urlparse(url).netloc.lower()
    
    if any(x in domain for x in ["youtube.com", "youtu.be", "instagram.com", "facebook.com", "tiktok.com"]):
        return None, "Rede Social / Bloqueio de Login"
        
    try:
        print(f"Loading {url}...")
        page.goto(url, timeout=15000, wait_until="domcontentloaded")
        time.sleep(2)
        
        html = page.content()
        soup = BeautifulSoup(html, "html.parser")
        
        for script in soup(["script", "style", "noscript", "iframe", "header", "footer", "nav"]):
            script.decompose()
            
        text = soup.get_text(separator=' ')
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        clean_text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return clean_text[:12000], None
    except Exception as e:
        print(f"Error loading {url}: {e}")
        return None, str(e)

def analyze_content_with_claude(url, title, text):
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
    
    max_retries = 3
    retry_delay = 5
    
    for model_name in MODELS_TO_TRY:
        for attempt in range(max_retries):
            try:
                response = client.messages.create(
                    model=model_name,
                    max_tokens=1000,
                    temperature=0,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                response_text = response.content[0].text.strip()
                
                # Clean markdown wrapper if Claude returns it
                if response_text.startswith("```json"):
                    response_text = response_text.split("```json")[1].split("```")[0].strip()
                elif response_text.startswith("```"):
                    response_text = response_text.split("```")[1].split("```")[0].strip()
                    
                return json.loads(response_text)
            except Exception as e:
                error_str = str(e)
                if "404" in error_str:
                    print(f"Modelo {model_name} não encontrado (404). Tentando o próximo modelo...")
                    break # Break inner loop to try next model
                elif "429" in error_str or "rate_limit" in error_str.lower() or "overloaded" in error_str.lower():
                    print(f"Limite de requisições ou sobrecarga na Anthropic. Aguardando {retry_delay} segundos antes de tentar novamente (Tentativa {attempt+1}/{max_retries})...")
                    time.sleep(retry_delay)
                    continue
                    
                print(f"Error calling Anthropic API with {model_name}: {e}")
                break # Try next model
                
    return {
        "categoria": "Erro de Análise",
        "tema": "Erro no Processamento da IA",
        "resumo": "Não foi possível analisar o conteúdo desta página com nenhum dos modelos Claude disponíveis.",
        "destaques_negativos": "Erro ao processar destaques.",
        "destaques_positivos": "Erro ao processar destaques."
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
    elif "jusbrasil.com.br" in domain:
        return {
            "categoria": "Legal",
            "tema": "Processos Judiciais",
            "resumo": "A URL fornecida refere-se a uma página do Jusbrasil que lista processos judiciais associados ao nome Marcelo Baptista de Oliveira.",
            "destaques_negativos": "A página pode conter informações sobre processos judiciais que podem incluir disputas legais ou questões pendentes.",
            "destaques_positivos": "Não há informações positivas específicas disponíveis nesta URL, tratando-se de indexação pública de processos."
        }
    else:
        return {
            "categoria": "Erro de Acesso",
            "tema": "Bloqueio de Rede" if "403" in error_type or "429" in error_type else "Problema de Conexão",
            "resumo": f"A URL fornecida não pôde ser acessada devido a um problema de carregamento ou restrição (Erro: {error_type}).",
            "destaques_negativos": "Acesso bloqueado ou indisponível devido a restrições do servidor de destino.",
            "destaques_positivos": "Nenhum destaque positivo pôde ser verificado devido à indisponibilidade da página."
        }

def generate_consolidated_report(analyses):
    print("Generating consolidated general analysis with Claude...")
    
    summaries_text = ""
    for item in analyses[:40]:
        summaries_text += f"- URL: {item['url']}\n  Categoria: {item['categoria']}\n  Resumo: {item['resumo']}\n  Positivos: {item['destaques_positivos']}\n  Negativos: {item['destaques_negativos']}\n\n"
        
    prompt = f"""
    A partir das seguintes análises individuais de páginas encontradas na pesquisa sobre "Marcelo Baptista de Oliveira" (fundador do Grupo Protege e Agro Maripá), elabore um relatório consolidado geral estruturado.
    
    O principal objetivo é destacar o que é NEGATIVO e o que é POSITIVO.
    
    Resumos Individuais:
    ---
    {summaries_text}
    ---
    
    Escreva um relatório em português estruturado em Markdown com as seguintes seções:
    1. # Relatório Consolidado de Reputação Digital - Marcelo Baptista de Oliveira
    2. ## Visão Geral da Presença Online (Resumo geral dos tipos de sites e temas dominantes, ex: segurança com o Grupo Protege, agronegócio e criação de cavalos com a Agro Maripá)
    3. ## Destaques Positivos (Consolidação de conquistas, prêmios, cidadão paulistano, liderança de mercado, empreendedorismo, esporte equestre)
    4. ## Destaques Negativos e Áreas de Risco (Processos judiciais em sites como Jusbrasil/Escavador, processos trabalhistas ou cíveis comuns a grandes corporações, conflitos ou menções desfavoráveis)
    5. ## Conclusão Geral e Índice de Sentimento (Classifique a reputação online geral como Predominantemente Positiva, Neutra ou Negativa, justificando a resposta com base nos dados analisados).
    """
    
    for model_name in MODELS_TO_TRY:
        try:
            response = client.messages.create(
                model=model_name,
                max_tokens=1500,
                temperature=0,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return response.content[0].text.strip()
        except Exception as e:
            error_str = str(e)
            if "404" in error_str:
                print(f"Modelo {model_name} não encontrado (404) para consolidação. Tentando o próximo...")
                continue
            print(f"Error generating consolidated report with {model_name}: {e}")
            
    return f"# Relatório Consolidado\nErro ao gerar a consolidação com todos os modelos Claude disponíveis da Anthropic."

def main():
    input_file = "results.json"
    output_file = "analysis_results.json"
    
    if not os.path.exists(input_file):
        print(f"Erro: Arquivo '{input_file}' não encontrado.")
        return
        
    with open(input_file, "r", encoding="utf-8") as f:
        search_results = json.load(f)
        
    analyses = []
    if os.path.exists(output_file):
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                analyses = json.load(f)
                print(f"Carregados {len(analyses)} registros já analisados. Continuando...")
        except Exception:
            pass
            
    analyzed_urls = {item["url"] for item in analyses if item.get("categoria") != "Erro de Análise"}
    analyses = [item for item in analyses if item.get("categoria") != "Erro de Análise"]
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        for idx, result in enumerate(search_results):
            url = result["url"]
            if url in analyzed_urls:
                continue
                
            print(f"\n[{idx+1}/{len(search_results)}] Analisando: {url}")
            text, error = get_text_content(page, url)
            analysis_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            if error:
                print(f"Fallback para erro: {error}")
                analysis = get_error_analysis(url, error)
            else:
                print("Enviando texto extraído para o Claude...")
                analysis = analyze_content_with_claude(url, result["title"], text)
                
            analysis["url"] = url
            analysis["title"] = result["title"]
            analysis["rank"] = result["rank"]
            analysis["data_hora"] = analysis_time
            
            analyses.append(analysis)
            
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(analyses, f, ensure_ascii=False, indent=4)
                
            time.sleep(2)
            
        browser.close()
        
    print("\nProcessamento de URLs individuais finalizado.")
    
    report = generate_consolidated_report(analyses)
    
    report_filename = "consolidated_report.md"
    with open(report_filename, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Relatório consolidado salvo em {report_filename}")
    
    csv_filename = "analysis_results.csv"
    with open(csv_filename, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["rank", "url", "title", "categoria", "tema", "resumo", "destaques_negativos", "destaques_positivos", "data_hora"])
        writer.writeheader()
        for item in analyses:
            writer.writerow({
                "rank": item.get("rank", 0),
                "url": item.get("url", ""),
                "title": item.get("title", ""),
                "categoria": item.get("categoria", ""),
                "tema": item.get("tema", ""),
                "resumo": item.get("resumo", ""),
                "destaques_negativos": item.get("destaques_negativos", ""),
                "destaques_positivos": item.get("destaques_positivos", ""),
                "data_hora": item.get("data_hora", "")
            })
    print(f"Tabela de análises salva em {csv_filename}")
    
    with open("analysis_data.js", "w", encoding="utf-8") as f:
        f.write("const analysisResults = " + json.dumps(analyses, ensure_ascii=False, indent=4) + ";\n")
        f.write("const consolidatedReport = " + json.dumps(report, ensure_ascii=False) + ";\n")
    print("Dados integrados para a Web App em 'analysis_data.js'")

if __name__ == "__main__":
    main()
