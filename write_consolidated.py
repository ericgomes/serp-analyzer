import json
from datetime import datetime

report_content = """# Relatório Consolidado de Reputação Digital - Marcelo Baptista de Oliveira

## Visão Geral da Presença Online
A presença digital de Marcelo Baptista de Oliveira é predominantemente institucional, corporativa e ligada a suas atividades de liderança empresarial e de agronegócio de elite. Os resultados de busca concentram-se em três pilares fundamentais:
1. **Liderança e Segurança Privada:** Informações sobre sua atuação como fundador e presidente do **Grupo Protege**, uma das maiores holdings de segurança e logística de valores do Brasil.
2. **Agronegócio e Criação de Cavalos:** Reportagens e conteúdos sobre a **Agro Maripá**, marca referência na seleção genética e promoção nacional e internacional da raça Mangalarga Marchador.
3. **Reconhecimento Cívico e Cultural:** Menções ao Título de Cidadão Paulistano recebido em 2017 e seu papel como incentivador e patrocinador de artes e projetos culturais (cinema, teatro e parcerias com o GRAACC).

## Destaques Positivos
- **Liderança e Geração de Empregos:** Fundador e presidente de uma corporação bilionária (Grupo Protege) que emprega de 12 mil a 20 mil colaboradores no país, sendo referência global no setor de transporte de valores.
- **Reconhecimento Público de Prestígio:** Homenagem formal com a entrega do **Título de Cidadão Paulistano** na Câmara Municipal de São Paulo, reconhecendo seu papel social, cultural e de fomento econômico na capital.
- **Pioneirismo Tecnológico e Sustentabilidade:** Fomento a soluções de sustentabilidade e vanguarda, como o desenvolvimento do primeiro carro-forte 100% elétrico do Brasil e a introdução de novas tecnologias visuais (3D) no mercado de cinema nacional.
- **Responsabilidade Social Ativa:** Parcerias duradouras da Protege com instituições renomadas de combate ao câncer infantil, como o **GRAACC**.
- **Destaque no Agronegócio Equestre:** Reconhecimento no meio de criadores como criador experiente (Mangalarga Marchador) há mais de 40 anos e promotor da genética nacional na Europa.

## Destaques Negativos e Áreas de Risco
- **Litígios Judiciais (Jusbrasil / Escavador):** O nome Marcelo Baptista de Oliveira está indexado em um volume de processos de busca jurídica (cerca de 650 registros). No entanto, a análise detalhada revela que esses processos são, em sua grande maioria, de natureza trabalhista ou cível decorrentes da operação normal das empresas sob sua gestão (como o Grupo Protege), ou onde ele atua em representação legal/corporativa.
- **Nenhuma Ocorrência de Escândalos Pessoais:** Não foram encontradas notícias ou denúncias de fraudes, crimes financeiros ou envolvimento pessoal em condutas desabonadoras ou ilícitas. A exposição de processos judiciais nas plataformas públicas representa o principal ponto a ser monitorado do ponto de vista de SEO.
- **Indisponibilidade de Mídias Sociais (YouTube / Instagram / Facebook):** Algumas URLs de redes sociais não puderam ser totalmente analisadas diretamente pelo navegador devido a bloqueios normais de requisição de login e segurança destas plataformas.

## Conclusão Geral e Índice de Sentimento
**Índice de Sentimento Geral: Predominantemente Positivo (com baixo risco reputacional)**

A reputação online de Marcelo Baptista de Oliveira é altamente sólida e positiva. Os resultados de busca são consistentes com o perfil de um grande líder industrial e filantropo. Embora haja a indexação automática de processos judiciais de natureza corporativa (comum a executivos de grandes holdings), o peso das menções positivas — que incluem homenagens públicas, impacto no agronegócio e pioneirismo tecnológico — domina amplamente o cenário de sua imagem digital.
"""

def main():
    # Load analyses
    with open("analysis_results.json", "r", encoding="utf-8") as f:
        analyses = json.load(f)
        
    analysis_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Append report generation timestamp
    final_report = report_content + f"\n\n---\n*Análise consolidada gerada em: {analysis_time}*"
    
    # Write consolidated markdown
    with open("consolidated_report.md", "w", encoding="utf-8") as f:
        f.write(final_report)
    print("Salvo consolidated_report.md")
        
    # Write js data file
    with open("analysis_data.js", "w", encoding="utf-8") as f:
        f.write("const analysisResults = " + json.dumps(analyses, ensure_ascii=False, indent=4) + ";\n")
        f.write("const consolidatedReport = " + json.dumps(final_report, ensure_ascii=False) + ";\n")
        f.write(f"const consolidatedReportTime = '{analysis_time}';\n")
    print("Salvo analysis_data.js")

if __name__ == "__main__":
    main()
