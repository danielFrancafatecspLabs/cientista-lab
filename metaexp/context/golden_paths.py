"""Catálogo de golden paths: caminhos padronizados para experimentos recorrentes."""

from __future__ import annotations

GOLDEN_PATHS: list[dict] = [
    {
        "id": "rag-busca-semantica",
        "nome": "Busca semântica e respostas com fonte (RAG)",
        "tecnologia": "ia_generativa",
        "quando_usar": "Pessoas perdem tempo procurando informação em FAQs, procedimentos, normas ou bases de conhecimento.",
        "dados_tipicos": "FAQ, procedimentos, manuais, base de conhecimento em texto",
        "metricas_padrao": ["respostas corretas", "respostas com fonte citada", "redução do tempo de busca"],
        "skills": ["Python", "Embeddings e banco vetorial", "Engenharia de prompt", "Avaliação de LLM"],
        "amostra_minima": "400 pares pergunta-resposta (250 para resultado indicativo)",
    },
    {
        "id": "texto-livre-voc",
        "nome": "Texto livre e voz do cliente",
        "tecnologia": "ia_generativa",
        "quando_usar": "Classificar, resumir ou extrair temas de manifestações, reclamações, pesquisas e transcrições.",
        "dados_tipicos": "Manifestações, tickets, transcrições de atendimento, respostas abertas",
        "metricas_padrao": ["F1 por classe", "concordância com especialista"],
        "skills": ["Python", "Engenharia de prompt", "Avaliação de LLM", "Taxonomia do domínio"],
        "amostra_minima": "50 exemplos rotulados por classe",
    },
    {
        "id": "classificacao-supervisionada",
        "nome": "Classificação supervisionada",
        "tecnologia": "machine_learning",
        "quando_usar": "Prever propensão, risco, triagem ou roteamento a partir de dados tabulares históricos.",
        "dados_tipicos": "Tabelas históricas com o desfecho rotulado",
        "metricas_padrao": ["AUC", "precisão", "recall"],
        "skills": ["Python", "scikit-learn", "Engenharia de atributos", "Validação temporal"],
        "amostra_minima": "385 eventos positivos rotulados",
    },
    {
        "id": "correlacao-eventos",
        "nome": "Correlação de eventos",
        "tecnologia": "machine_learning",
        "quando_usar": "Agrupar alarmes, incidentes ou logs para reduzir ruído e apontar causa raiz.",
        "dados_tipicos": "Logs de alarmes com timestamp, inventário de topologia",
        "metricas_padrao": ["redução de volume", "recall de incidentes", "precisão de causa raiz"],
        "skills": ["Python", "Séries temporais", "Grafos"],
        "amostra_minima": "385 incidentes rotulados",
    },
    {
        "id": "automacao-documental",
        "nome": "Automação documental",
        "tecnologia": "ia_generativa",
        "quando_usar": "Extrair campos ou cláusulas de editais, contratos, notas e qualificações.",
        "dados_tipicos": "Documentos em PDF ou texto com gabarito de campos",
        "metricas_padrao": ["taxa de extração correta", "tempo por documento"],
        "skills": ["Python", "Engenharia de prompt", "Esquemas de extração"],
        "amostra_minima": "100 documentos com gabarito",
    },
    {
        "id": "visao-computacional",
        "nome": "Visão computacional",
        "tecnologia": "visao_computacional",
        "quando_usar": "Inspecionar ou aceitar remotamente elementos físicos por imagem.",
        "dados_tipicos": "Fotos rotuladas de campo",
        "metricas_padrao": ["acurácia", "taxa de falso aceite"],
        "skills": ["Python", "Visão computacional", "GPU"],
        "amostra_minima": "1.000 imagens rotuladas",
    },
    {
        "id": "previsao-demanda",
        "nome": "Previsão de séries temporais",
        "tecnologia": "estatistica",
        "quando_usar": "Prever volume de chamadas, demanda, consumo ou capacidade.",
        "dados_tipicos": "Séries históricas com pelo menos dois ciclos sazonais",
        "metricas_padrao": ["MAPE", "viés"],
        "skills": ["Python", "Séries temporais"],
        "amostra_minima": "24 meses de histórico",
    },
]

BY_ID = {g["id"]: g for g in GOLDEN_PATHS}
