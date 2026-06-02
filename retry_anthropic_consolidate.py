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

# We will try these models in order of priority
MODELS_TO_TRY = [
    "claude-3-5-sonnet-20240620",
    "claude-3-haiku-20240307",
    "claude-3-5-sonnet-latest"
]

def main():
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
    
    success = False
    for model_name in MODELS_TO_TRY:
        print(f"Tentando gerar com o modelo: {model_name}...")
        try:
            response = client.messages.create(
                model=model_name,
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
            print(f"Sucesso! Relatório consolidado salvo em consolidated_report.md (usou {model_name})")
            
            # Save updated javascript file for the webapp
            with open("analysis_data.js", "w", encoding="utf-8") as f:
                f.write("const analysisResults = " + json.dumps(analyses, ensure_ascii=False, indent=4) + ";\n")
                f.write("const consolidatedReport = " + json.dumps(report, ensure_ascii=False) + ";\n")
            print("Dados integrados com sucesso para a Web App em 'analysis_data.js'")
            success = True
            break
            
        except Exception as e:
            print(f"Erro ao usar o modelo {model_name}: {e}")
            time.sleep(2)
            
    if not success:
        print("Erro: Todos os modelos disponíveis na lista falharam.")

if __name__ == "__main__":
    main()
