# Papéis e responsabilidades do METAEXP

O METAEXP é a plataforma interna de experimentação (IDP) do beOn Labs. Este documento define quem participa de um experimento, o que cada papel faz e por qual jornada entra na plataforma. A fonte é `metaexp/papeis.py`, a mesma usada pelo backend e pela rota `GET /api/papeis`.

## Quem entra pela plataforma

A primeira tela pede que a pessoa escolha o papel. Cada papel tem uma jornada própria, com prompt, ferramentas, etapas e encaminhamento diferentes.

| | Solicitante | Desenvolvedor |
|---|---|---|
| Quem é | Procurou o beOn Labs para executar um desafio tecnológico. | Desenvolvedor de qualquer área querendo construir algo. |
| Promessa | Você fala do seu negócio; o laboratório cuida da tecnologia e executa. | Desenho técnico desde o início: baseline, abordagens, avaliação e kit para construir. |
| Tom da conversa | Fluida e cadenciada, linguagem de negócio, nenhum termo técnico | Técnica e profunda desde a primeira pergunta, como uma revisão de design |
| O que o Cientista aprofunda | Frequência e custo do problema, impacto no cliente, quem decide, o que muda se der certo | Stack, fontes de dados, restrições, baseline, abordagens com trade-offs, protocolo de avaliação, arquitetura |
| Etapas | Desafio → Impacto → Objetivo → Hipótese → Amostra → Métricas → Responsáveis → Ficha → Bancada | Problema → Contexto técnico → Objetivo → Baseline → Hipótese → Abordagens → Amostra → Avaliação → Critérios → Responsáveis → Ficha → Kit |
| Tecnologia | Escolhida pelo laboratório e registrada na ficha, sem explicação técnica na conversa | Discutida abertamente: 2 a 4 abordagens com prós, contras, custo, latência e recomendação |
| Ferramentas exclusivas | — | `propor_abordagens`, `registrar_desenho_tecnico`, `apresentar_skills` |
| Encaminhamento | Sempre para a bancada do laboratório | Recebe ficha, desenho técnico e kit; a bancada é opcional |
| Personalização na entrada | Área: Rede, Atendimento, Digital, Financeiro, Suprimentos, Jurídico, RH, Marketing, Operações, Outra<br>Ritmo da conversa: Direto ao ponto, Guiado, com exemplos | Stack principal: Python, TypeScript / Node, Java / Kotlin, SQL e dados<br>Experiência com IA: Começando em IA, Já usei LLMs e APIs, Especialista em ML<br>Onde vai rodar: Sandbox do laboratório, Minha infraestrutura |

As duas jornadas seguem o mesmo método oficial: hipótese começando com "Acreditamos que", critérios de aceite numéricos, nome com até 3 palavras, BO e Sponsor, checklist de qualidade mínima e Gerador de Ficha. O que muda é a profundidade e o vocabulário.

## Todos os papéis

### Solicitante (pessoa)

Traz o desafio de negócio e decide com base no resultado.

- Descrever o problema, o impacto e o objetivo
- Fornecer ou indicar os dados
- Aprovar a ficha
- Validar resultados com conhecimento do domínio
- Aceitar o parecer e decidir o encaminhamento

### Desenvolvedor (pessoa)

Constrói a solução com apoio do método e dos agentes.

- Detalhar contexto técnico, baseline e restrições
- Escolher a abordagem com os trade-offs apresentados
- Definir o protocolo de avaliação
- Construir e executar a solução (ou enviá-la à bancada)
- Reportar resultados para o parecer

### BO (responsável pelo experimento) (pessoa)

Responde pelo experimento do início ao fim.

- Garantir acesso a dados e pessoas
- Acompanhar prazos e gates
- Assinar a ficha e o parecer

### Sponsor (patrocinador) (pessoa)

Patrocina o experimento e decide sobre piloto e escala.

- Priorizar o desafio
- Aprovar recursos
- Decidir piloto e escala a partir do veredito

### Agente Cientista (agente de IA)

Conduz a conversa no método oficial e gera a ficha.

- Adaptar a jornada ao papel
- Validar o checklist de qualidade mínima
- Buscar experimentos semelhantes
- Analisar a amostra enviada
- Gerar a ficha e encaminhar

### Agentes da bancada (agente de IA)

Executam o experimento: Dados, Desenvolvedor, QA e Analista.

- Analisar a amostra (G1)
- Planejar e construir
- Rodar o Ralph Loop até Qk ≥ 0,85 (G2)
- Emitir o parecer com evidências (G3)

### Curador de governança (pessoa)

Mantém o método, os golden paths e os indicadores da esteira.

- Revisar fichas fora do padrão
- Promover novos golden paths
- Acompanhar C, ΔT, A e S

### Especialista revisor (pessoa)

Destrava casos difíceis e garante a qualidade dos resultados.

- Orientar quando o Ralph Loop atinge Kmax
- Fazer revisão cega de pareceres

## Matriz por etapa do ciclo

R = responsável por executar · A = aprova ou decide · C = consultado · I = informado

| Papel | Ficha (G0) | Amostra (G1) | Construção | Qualidade (G2) | Resultado (G3) | Piloto e escala |
|---|---|---|---|---|---|---|
| Solicitante | A | C | I | I | A | C |
| Desenvolvedor | A | R | R | R | C | C |
| BO (responsável pelo experimento) | R | A | I | I | R | R |
| Sponsor (patrocinador) | I | I | I | I | I | A |
| Agente Cientista | R | C | I | I | I | I |
| Agentes da bancada | I | R | R | R | R | I |
| Curador de governança | C | I | I | C | C | I |
| Especialista revisor | I | C | C | A | C | I |

Na jornada do solicitante, as colunas Construção e Qualidade ficam com os agentes da bancada. Na jornada do desenvolvedor, quando ele constrói por conta própria, essas colunas ficam com ele; se escolher a bancada, voltam para os agentes.

## Como mudar

- Papéis, preferências, ferramentas e encaminhamentos: `metaexp/papeis.py`.
- Tom e profundidade de cada jornada: `metaexp/prompts/jornada_solicitante.md` e `metaexp/prompts/jornada_desenvolvedor.md`.
- Regras comuns do método: `metaexp/prompts/cientista.md` e `metaexp/metodo.py`.
- Depois de mudar, regere este documento com `python -m metaexp papeis` e rode `python -m metaexp avaliar --n 5 --sim`.
