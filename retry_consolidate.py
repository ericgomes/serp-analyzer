import json
import os
import sys
import time
import anthropic

# Setup Anthropic API Key
api_key = os.environ.get("ANTHROPIC_API_KEY")
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
    print("Erro: Chave API da Anthropic não encontrada.")
    sys.exit(1)

client = anthropic.Anthropic(api_key=api_key)
MODEL_NAME = "claude-3-5-haiku-latest"

def main():
    print("Aguardando 10 segundos para liberação da quota de requisições...")
    time.sleep(10)
    
    output_file = "analysis_results.json"
    if not os.path.exists(output_file):
        print(f"Erro: Arquivo '{output_file}' não encontrado.")
        return
        
    with open(output_file, "r", encoding="utf-8") as f:
        analyses = json.load(f)
        
    print(f"Lidos {len(analyses)} registros para a consolidação.")
    
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
    
    max_retries = 3
    retry_delay = 30
    
    for attempt in range(max_retries):
        print(f"Gerando relatório consolidado com a API (Tentativa {attempt+1}/{max_retries})...")
        try:
            response = client.messages.create(
                model=MODEL_NAME,
                max_tokens=1500,
                temperature=0,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            report = response.content[0].text.strip()
            
            # Save markdown report
            with open("consolidated_report.md", "w", encoding="utf-8") as f:
                f.write(report)
            print("Relatório consolidado salvo em consolidated_report.md")
            
            # Save updated javascript file for the webapp
            with open("analysis_data.js", "w", encoding="utf-8") as f:
                f.write("const analysisResults = " + json.dumps(analyses, ensure_ascii=False, indent=4) + ";\n")
                f.write("const consolidatedReport = " + json.dumps(report, ensure_ascii=False) + ";\n")
            print("Dados integrados com sucesso para a Web App em 'analysis_data.js'")
            break
            
        except Exception as e:
            print(f"Erro ao chamar a API: {e}")
            if attempt < max_retries - 1:
                print(f"Aguardando {retry_delay} segundos antes de tentar novamente...")
                time.sleep(retry_delay)

if __name__ == "__main__":
    main()
