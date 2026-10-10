# Papéis e responsabilidades do METAEXP

O METAEXP é a plataforma interna de experimentação (IDP) do beOn Labs. Este documento define quem participa de um experimento, o que cada papel faz e por qual porta entra na plataforma. A fonte é `metaexp/core/papeis.py`, a mesma usada pelo backend (`GET /api/papeis`) e pelo app.

## As quatro portas de entrada

A primeira tela pede que a pessoa escolha o papel. Solicitante e Desenvolvedor conversam com o Cientista; Lab e Sponsor trabalham em painéis.

| Papel | Porta | Quem é | O que recebe | Etapas |
|---|---|---|---|---|
| **Solicitante** | Tenho um desafio de negócio | Você trouxe um desafio para o beOn Labs resolver com tecnologia. | Você fala do seu negócio. O Cientista transforma isso em um experimento e o laboratório executa. | Desafio → Entendimento → Hipótese → Sucesso → Dados → Responsáveis → Ficha → Revisão do Lab → Bancada |
| **Desenvolvedor** | Quero construir algo | Você quer construir uma solução e precisa provar que ela funciona. | Desenho técnico com baseline, trade-offs e protocolo de avaliação, e um kit pronto para rodar com CI. | Problema → Contexto técnico → Baseline → Hipótese → Abordagens → Avaliação → Dados → Ficha → Kit |
| **Lab** | Reviso e aprovo experimentos | Você garante o rigor do método antes de qualquer execução. | Fila de revisão com pré-análise do Agente Revisor, evidências da conversa e decisão em um clique. | Fila → Pré-revisão → Evidências → Decisão |
| **Sponsor** | Acompanho o portfólio | Você patrocina experimentos e decide o que escala. | Portfólio por etapa, indicadores do metaexperimento e as decisões que dependem de você. | Portfólio → Indicadores → Decisões |

## As duas conversas com o Cientista

| | Solicitante | Desenvolvedor |
|---|---|---|
| Tom | Reunião com quem conhece o próprio negócio: linguagem de negócio, nenhum termo técnico | Revisão de design com um tech lead: técnico, direto, trade-offs explícitos |
| Descoberta do problema | Longa e profunda: casos concretos, quantificação, decisão em jogo | Curta e afiada: quem sofre, tamanho, decisão, sinal de sucesso |
| Depois da descoberta | Objetivo, hipótese, sucesso em termos de negócio, dados, responsáveis | Contexto técnico, baseline, abordagens, protocolo de avaliação, arquitetura |
| Ferramentas exclusivas | — | `propor_abordagens`, `registrar_desenho_tecnico`, `apresentar_skills` |
| Ao final | Ficha vai para a revisão do Lab e depois para a bancada | Ficha, desenho e kit (avaliador + CI); bancada opcional |
| Personalização | Área: Atendimento, Rede, Digital, Financeiro, Suprimentos, Jurídico, RH, Marketing, Operações, Outra<br>Ritmo: Direto ao ponto, Guiado, com exemplos | Stack: Python, TypeScript / Node, Java / Kotlin, SQL e dados<br>Experiência com IA: Começando, Já usei LLMs, Especialista em ML<br>Onde vai rodar: Sandbox do Lab, Minha infraestrutura |

Nas duas, o Cientista mantém um **mapa do problema** com dez dimensões e mostra à pessoa por que cada pergunta importa:

- **O que acontece**: o que se observa hoje, descrito em fatos e não em soluções.
- **Quem sente**: quem é afetado, quantas pessoas e em que momento do trabalho.
- **Tamanho do problema**: frequência, volume e custo em números, mesmo que aproximados.
- **Um caso real**: o último exemplo real, com o que aconteceu passo a passo.
- **Por que acontece**: as causas prováveis, separando sintoma de causa raiz.
- **Como se resolve hoje**: o contorno atual e por que ele não basta.
- **Decisão em jogo**: que decisão o resultado vai destravar e quem a toma.
- **Como saberemos**: o sinal observável de sucesso, que vira métrica e critério.
- **Restrições**: prazo, regras, dados disponíveis, orçamento e riscos que limitam a solução.
- **Premissa mais arriscada**: o que precisa ser verdade para valer a pena, e ainda não sabemos.

O método oficial vale para todos: hipótese começando com "Acreditamos que", critérios de aceite numéricos, nome com até 3 palavras, BO e Sponsor, checklist de qualidade mínima e Gerador de Ficha.

## Todos os papéis

### Solicitante (pessoa)

Traz o desafio de negócio e decide com base no resultado.

- Explicar o problema, o impacto e a decisão em jogo
- Indicar ou fornecer os dados
- Confirmar a ficha
- Validar resultados com conhecimento do domínio
- Aceitar o parecer

### Desenvolvedor (pessoa)

Constrói a solução com apoio do método e dos agentes.

- Detalhar contexto técnico, baseline e restrições
- Escolher a abordagem pelos trade-offs
- Definir o protocolo de avaliação
- Construir com o kit e o CI do experimento
- Reportar resultados

### Lab (pesquisa) (pessoa)

Garante o rigor do método e destrava casos difíceis.

- Revisar e aprovar fichas (G0)
- Confirmar a amostra (G1)
- Orientar quando o Ralph Loop atinge Kmax
- Manter o método e os golden paths
- Fazer revisão cega de pareceres

### Sponsor (pessoa)

Patrocina o portfólio e decide o que escala.

- Priorizar desafios
- Aprovar recursos
- Decidir escalar, iterar ou encerrar após o parecer

### BO (responsável pelo experimento) (pessoa)

Responde pelo experimento do início ao fim.

- Garantir acesso a dados e pessoas
- Acompanhar prazos e gates
- Assinar ficha e parecer

### Agente Cientista (agente de IA)

Entende o problema a fundo e conduz a ficha no método oficial.

- Mapear o problema com perguntas de alto valor
- Ancorar critérios no histórico do Lab
- Validar o checklist de qualidade mínima
- Desenhar a avaliação com o desenvolvedor
- Gerar a ficha e encaminhar

### Agente Revisor (agente de IA)

Prepara a revisão do Lab com uma pré-análise verificável.

- Pontuar a ficha na rubrica do Lab
- Apontar riscos e ajustes concretos
- Citar o trecho que justifica cada nota

### Agentes da bancada (agente de IA)

Executam o experimento: Dados, Desenvolvedor, QA e Analista.

- Analisar a amostra (G1)
- Planejar e construir
- Rodar o Ralph Loop até Qk ≥ 0,85 (G2)
- Emitir o parecer com evidências (G3)

## Matriz por etapa do ciclo

R = responsável por executar · A = aprova ou decide · C = consultado · I = informado

| Papel | Ficha | Revisão (G0) | Amostra (G1) | Construção | Qualidade (G2) | Parecer (G3) | Decisão |
|---|---|---|---|---|---|---|---|
| Solicitante | R | I | C | I | I | A | C |
| Desenvolvedor | R | I | R | R | R | C | I |
| Lab (pesquisa) | C | A | A | C | A | R | C |
| Sponsor | I | I | I | I | I | I | A |
| BO (responsável pelo experimento) | A | C | R | I | I | R | R |
| Agente Cientista | R | I | C | I | I | I | I |
| Agente Revisor | I | R | I | I | I | I | I |
| Agentes da bancada | I | I | R | R | R | R | I |

Quando o desenvolvedor constrói por conta própria, Construção e Qualidade ficam com ele (o CI do kit faz o papel do QA); se escolher a bancada, voltam para os agentes.

## Como mudar

- Papéis, preferências, ferramentas e encaminhamentos: `metaexp/core/papeis.py`.
- Dimensões do mapa do problema e técnicas de pergunta: `metaexp/core/descoberta.py`.
- Tom de cada jornada: `metaexp/prompts/papel_solicitante.md` e `metaexp/prompts/papel_desenvolvedor.md`.
- Regras comuns do método: `metaexp/prompts/cientista.md` e `metaexp/core/metodo.py`.
- Depois de mudar, regere este documento com `python -m metaexp papeis` e rode `python -m metaexp avaliar --n 5 --sim`.
