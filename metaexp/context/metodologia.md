# Metodologia de experimentação do beOn Labs

O laboratório conduz experimentos técnicos de IA para áreas da empresa (rede, atendimento, digital, financeiro, suprimentos, jurídico, entre outras). Cada experimento percorre o mesmo ciclo:

1. **Ficha** (Agente Cientista, gate G0): problema, quem sente o problema, hipótese testável, tecnologia e técnica, métricas com meta numérica, dados e skills. A execução só começa com a ficha aprovada pelo solicitante.
2. **Amostra e dados** (Agente de Amostra e Dados, gate G1): os dados são suficientes e adequados para testar a hipótese? Um experimento sem dados suficientes é interrompido aqui, e não descoberto na análise (fail-fast).
3. **Construção** (Agente Desenvolvedor): plano analítico e depois código modular, partindo dos patterns do golden path.
4. **Qualidade** (Agente QA, gate G2): testes definidos pela ficha. O Ralph Loop devolve feedback ao Desenvolvedor até o índice de qualidade Qk = e · o · d · S atingir Qmin = 0,85, com no máximo Kmax = 5 iterações; depois disso o caso vai para um especialista humano.
5. **Resultado** (Agente Analista, gate G3): compara resultados com hipótese e métricas e dá o veredito: validada, parcialmente comprovada, invalidada ou inconclusiva. Inclui evidências, riscos, próximos passos e oportunidades.

## Regras de uma boa ficha

- O problema é descrito pelo impacto na operação, não pela tecnologia ("quero usar IA" não é um problema).
- A hipótese segue o formato "se X, então Y em Z%" e é falsificável.
- Toda métrica obrigatória tem meta numérica definida antes da execução.
- Os dados precisam existir, estar acessíveis e ter volume para a margem de erro desejada.
- O tamanho mínimo da amostra para estimar uma proporção é n = z² · p(1 − p) / E². Com 95% de confiança (z = 1,96), p = 0,5 e E = 0,05, n ≈ 385.
- Em tarefas de busca e resposta (RAG), use como referência pelo menos 400 pares pergunta-resposta para medir acerto com margem de ±5 p.p.; abaixo de 250, trate o resultado como indicativo.

## Papéis humanos

- **Solicitante**: traz o problema, aprova a ficha, valida resultados de domínio e aceita o parecer.
- **Curador de governança**: mantém o padrão metodológico e os golden paths.
- **Especialista revisor**: atua quando o Ralph Loop atinge Kmax.
- **Sponsor**: decide sobre piloto e escala a partir do veredito.

## Fora de escopo

A decisão de negócio sobre pilotar ou escalar, a operação em produção e entradas multimodais (PDFs, imagens) como dado do experimento ficam fora do ciclo automático.
