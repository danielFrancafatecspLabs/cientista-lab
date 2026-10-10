// Roteiros do modo demonstração: conversas que mostram a descoberta do problema
// (perguntas de alto valor, "por que pergunto", síntese) e o método oficial.
import type { CardKind, Desenho, Ficha } from "../types";

export interface Passo {
  texto: string;
  mapa?: [string, string, number, string?][];
  porque?: [string, string, string];
  ficha?: Partial<Ficha>;
  desenho?: Partial<Desenho>;
  cards?: { kind: CardKind; data: any }[];
  chips?: string[];
  upload?: { descricao: string; formatos: string[] };
  sintese?: string;
  confirma?: boolean;
  gerar?: boolean;
  encaminhar?: "workflow" | "desenvolvedor";
}

const SIMILARES = [
  { id: "EXP-ATD-03", titulo: "Busca na base", veredito: "validada", origem: "real", relevancia: 0.82,
    nota: "Reduziu o tempo de atendimento em 27% com 400 perguntas reais." },
  { id: "EXP-JUR-02", titulo: "Pareceres jurídicos", veredito: "parcialmente_comprovada", origem: "real", relevancia: 0.61,
    nota: "Acerto de 78%: a base estava desatualizada. Vale checar a FAQ antes." },
];

export function roteiroSolicitante(nome: string): Passo[] {
  return [
    {
      texto: `Oi, ${nome}! Sou o Cientista do beOn Labs. Vamos transformar o seu desafio em um experimento que o Lab consiga testar e que ajude você a decidir.\n\n**O que está acontecendo hoje que fez você procurar o Lab?**`,
      porque: ["sintoma", "caso_concreto", "Começo pelo que acontece de fato, antes de pensar em qualquer solução."],
      chips: ["Os analistas demoram para achar respostas na FAQ", "Queremos um chatbot no atendimento", "Muitos chamados voltam por informação errada"],
    },
    {
      texto: "Entendi: a informação existe, mas encontrá-la custa tempo.\n\n**Pense no último atendimento em que isso aconteceu: o que o analista fez quando não achou a resposta?**",
      mapa: [["sintoma", "Analistas não encontram respostas na FAQ durante o atendimento.", 1, "os analistas demoram para achar respostas"]],
      porque: ["caso_concreto", "caso_concreto", "Um caso real mostra onde o tempo se perde, melhor do que uma média."],
      chips: ["Abriu 3 ou 4 documentos e chamou o supervisor", "Deixou o cliente esperando na linha", "Respondeu de memória e errou"],
    },
    {
      texto: "Então o contorno de hoje é o supervisor, e isso ocupa duas pessoas por atendimento.\n\n**Quantas vezes por dia algo assim acontece, mais ou menos? Uma faixa já ajuda.**",
      mapa: [["caso_concreto", "Analista abre vários documentos, não acha e escala para o supervisor com o cliente na linha.", 2, "abriu 3 ou 4 documentos e chamou o supervisor"],
        ["sintoma", "Busca lenta na FAQ trava o atendimento e escala para o supervisor.", 2],
        ["solucao_atual", "Escalar para o supervisor, que responde de memória.", 1]],
      porque: ["tamanho", "quantificar", "O tamanho do problema diz se o experimento vale o investimento."],
      chips: ["Umas 300 vezes por dia", "Entre 50 e 100", "Não sei, mas é todo dia"],
    },
    {
      texto: "300 por dia é bastante. Se cada busca leva uns 6 minutos (estimativa minha, corrija se estiver longe), são cerca de 30 horas da equipe por dia.\n\n**Quem sente isso mais: os analistas novos, os experientes ou o cliente na linha?**",
      mapa: [["tamanho", "Cerca de 300 ocorrências por dia; ~30 h/dia da equipe (estimativa a confirmar).", 2, "umas 300 vezes por dia"]],
      porque: ["quem_sofre", "quem_mais", "Saber quem mais sofre define onde medir o ganho."],
      chips: ["Os novos, que ainda não conhecem a base", "Todos igualmente", "O cliente, que espera em média 6 minutos"],
    },
    {
      texto: "Isso combina com dois experimentos do histórico do Lab: no **EXP-ATD-03**, uma busca na base de conhecimento reduziu o tempo de atendimento em 27%.\n\n**Se isso estivesse resolvido amanhã, que decisão você tomaria diferente?**",
      mapa: [["quem_sofre", "Analistas novos (menos de 3 meses), que dependem do supervisor; o cliente espera na linha.", 2, "os novos, que ainda não conhecem a base"],
        ["causas", "A FAQ é longa e organizada por produto, não pela dúvida do cliente.", 1]],
      cards: [{ kind: "similares", data: SIMILARES }],
      porque: ["decisao", "decisao", "Um experimento só vale a pena se o resultado muda uma decisão real."],
      chips: ["Reduziria o treinamento dos novos de 30 para 15 dias", "Levaria a solução para o 2º nível", "Deixaria de contratar 5 temporários"],
    },
    {
      texto: "É uma decisão concreta e mensurável, ótimo.\n\n**Que resultado faria você desistir da ideia? Por exemplo: se o tempo de busca caísse menos de quanto?**",
      mapa: [["decisao", "Reduzir o treinamento dos novos de 30 para 15 dias. Decide a coordenação do atendimento.", 2, "reduziria o treinamento de 30 para 15 dias"],
        ["sucesso", "Tempo de busca menor sem piorar a resposta ao cliente.", 1]],
      porque: ["sucesso", "criterio_de_parada", "Saber quando desistir ajuda a fixar uma meta de sucesso honesta."],
      chips: ["Se cair menos de 10%, não compensa", "Menos de 20% não vale", "Se errar mais que hoje"],
    },
    {
      texto: "Deixa eu confirmar o que entendi antes de propor a hipótese.",
      mapa: [["sucesso", "Tempo de busca cai pelo menos 10% sem aumentar respostas erradas; abaixo disso, não compensa.", 2, "se cair menos de 10%, não compensa"],
        ["premissa_critica", "A resposta certa existe na FAQ; o problema é encontrá-la.", 1]],
      sintese: "Hoje, quando a FAQ não responde rápido, o analista abre vários documentos e chama o supervisor, com o cliente na linha. Isso acontece cerca de 300 vezes por dia e pesa mais nos analistas novos. Se resolvido, você reduziria o treinamento de 30 para 15 dias; com ganho abaixo de 10%, não compensa.",
      chips: ["Isso mesmo", "Quase: vou ajustar um ponto"],
    },
    {
      texto: "Perfeito. Coloquei na ficha uma proposta de hipótese:\n\n> Acreditamos que uma busca inteligente na FAQ irá reduzir em 20% o tempo de busca dos analistas no atendimento.\n\n**Faz sentido para você, ou o número deveria ser outro?**",
      confirma: true,
      ficha: {
        dominio: "atendimento",
        problema: "Analistas não encontram respostas na FAQ e escalam para o supervisor com o cliente na linha (~300 vezes por dia).",
        publico_afetado: "Analistas novos do atendimento e clientes em espera; ~30 h/dia da equipe.",
        objetivo: "Testar uma busca inteligente na FAQ com perguntas reais do atendimento.",
        hipotese: "Acreditamos que uma busca inteligente na FAQ irá reduzir em 20% o tempo de busca dos analistas no atendimento.",
        metodologia: "Comparar tempo de busca e acerto antes e depois, com perguntas reais do último mês.",
        tecnologia: "ia_generativa", tecnica: "RAG", golden_path: "rag-busca-semantica",
      },
      porque: ["sucesso", "contrafactual", "A meta precisa ser ambiciosa, mas possível de medir no tempo do experimento."],
      chips: ["Faz sentido", "Acho que dá para 30%"],
    },
    {
      texto: "Combinado. Duas métricas obrigatórias na ficha: **tempo de busca (redução ≥ 20%)** e **respostas corretas (≥ 85%)**, a mesma referência que o Lab aprovou no EXP-ATD-03.\n\n**Você consegue me enviar a FAQ e uma amostra das perguntas que chegaram no último mês?**",
      ficha: { metricas: [
        { nome: "tempo_de_busca", descricao: "Tempo médio para encontrar a resposta", criterio_aceite: "Redução ≥ 20%", obrigatoria: true },
        { nome: "respostas_corretas", descricao: "Respostas certas segundo o supervisor", criterio_aceite: "Acerto ≥ 85%", obrigatoria: true }] },
      upload: { descricao: "FAQ e perguntas reais do último mês", formatos: ["xlsx", "csv"] },
      chips: ["Vou anexar a planilha", "Não tenho as perguntas reais"],
    },
    {
      texto: "Recebi, e está bem organizado. Para medir acerto com margem de ±5 p.p. o Lab usa 400 perguntas (cálculo de tamanho de amostra, não estimativa).\n\n**Consegue mais perguntas em uma semana, ou seguimos com resultado indicativo?**",
      porque: ["restricoes", "restricao", "Com menos dados o experimento ainda roda, mas o resultado vira indicativo; a escolha é sua."],
      chips: ["Consigo mais em 1 semana", "Seguimos com o que temos"],
    },
    {
      texto: "Ótimo. Só faltam os responsáveis.\n\n**Quem responde pelo experimento (BO) e quem patrocina (Sponsor)?**",
      ficha: { amostra: "230 perguntas reais + FAQ; meta de 400 em uma semana", dados: "FAQ do atendimento e perguntas do último mês" },
      mapa: [["restricoes", "Amostra atual de 230 perguntas; 400 em uma semana.", 2]],
      chips: ["Eu sou a BO; o sponsor é o Diretor de Atendimento", "BO: Coordenação de Qualidade; Sponsor: VP de Operações"],
    },
    {
      texto: "Ficha pronta e validada no checklist do método. Ela vai agora para a **revisão do Lab (G0)**; assim que aprovarem, a bancada começa e você acompanha tudo por aqui.",
      ficha: { titulo: "Busca na FAQ", bo: "Coordenadora de atendimento", sponsor: "Diretor de atendimento" },
      gerar: true, encaminhar: "workflow",
    },
  ];
}

export function roteiroDesenvolvedor(nome: string): Passo[] {
  return [
    {
      texto: `Olá, ${nome}! Vamos desenhar um experimento que você consiga provar com números e rodar com CI desde o primeiro commit.\n\n**Qual problema você quer resolver, e para quem?**`,
      porque: ["sintoma", "caso_concreto", "Antes da solução, quero a dor e quem a sente: é isso que vira a métrica."],
      chips: ["Classificar chamados do suporte automaticamente", "Busca semântica na base de conhecimento", "Prever churn de clientes"],
    },
    {
      texto: "Classificação de chamados: bom ponto de partida para medir.\n\n**Como a triagem acontece hoje, e quanto custa um chamado na fila errada?**",
      mapa: [["sintoma", "Chamados do suporte caem na fila errada e voltam.", 1]],
      porque: ["tamanho", "quantificar", "O custo do erro define qual métrica técnica importa de verdade."],
      chips: ["Regras por palavra-chave; ~25% erram de fila", "Manual, 4 pessoas; 18% voltam para a fila"],
    },
    {
      texto: "Então já existe baseline: regras com cerca de 25% de erro.\n\n**Onde estão os dados, e quantos chamados têm a fila final correta registrada?**",
      mapa: [["sintoma", "Triagem por regras manda ~25% dos chamados para a fila errada.", 2, "regras por palavra-chave; ~25% erram de fila"],
        ["tamanho", "~25% de erro de fila; cada erro gera retrabalho e atraso no N1.", 2],
        ["solucao_atual", "Regras por palavra-chave mantidas à mão.", 2], ["quem_sofre", "Analistas do N1 e clientes com SLA atrasado.", 2]],
      desenho: { baseline: "Regras por palavra-chave: ~25% de chamados na fila errada (F1 macro ≈ 0,71)." },
      porque: ["restricoes", "restricao", "Volume e qualidade dos rótulos decidem entre um classificador e um LLM."],
      chips: ["Zendesk: 40 mil chamados com fila final", "Só 2 mil rotulados"],
    },
    {
      texto: "40 mil rótulos é ótimo: dá para treinar e ainda congelar um teste honesto.\n\n**Qual a sua stack e a restrição mais dura: latência, custo ou privacidade?**",
      mapa: [["restricoes", "40 mil chamados com fila final no Zendesk.", 2, "40 mil chamados com fila final"]],
      desenho: { fontes_dados: "Zendesk: 40 mil chamados com fila final (2025–2026), texto + metadados." },
      porque: ["restricoes", "restricao", "A restrição mais dura elimina abordagens antes de testarmos."],
      chips: ["Python; p95 < 300 ms e os dados não saem da nossa nuvem", "Node; custo baixo é o principal"],
    },
    {
      texto: "Com 40 mil rótulos, p95 < 300 ms e dados dentro da nuvem, comparei três caminhos (custos e latências são estimativas). Recomendo o encoder ajustado; a opção mais simples entra como segundo baseline.\n\n**Qual você quer seguir?**",
      desenho: { stack: "Python 3.12, FastAPI, scikit-learn / transformers", restricoes: ["Latência p95 < 300 ms", "Dados não saem da nuvem corporativa"] },
      cards: [{ kind: "abordagens", data: { recomendada: "Encoder PT-BR ajustado", justificativa_recomendacao: "Melhor F1 esperado dentro da latência, sem enviar dados para fora.",
        abordagens: [
          { nome: "TF-IDF + regressão logística", descricao: "Baseline forte e barato.", pros: ["Treina em minutos", "Fácil de explicar"], contras: ["Perde sinônimos e contexto"], custo: "≈ R$ 0", latencia: "p95 ≈ 15 ms", complexidade: "baixa", recomendada: false },
          { nome: "Encoder PT-BR ajustado", descricao: "Modelo de linguagem pequeno ajustado nas filas.", pros: ["Entende contexto", "Roda na sua nuvem"], contras: ["Precisa de GPU para treinar"], custo: "≈ R$ 40 por treino", latencia: "p95 ≈ 80 ms", complexidade: "media", recomendada: true },
          { nome: "LLM com exemplos (few-shot)", descricao: "Classifica com instruções e exemplos.", pros: ["Sem treino", "Lida com filas novas"], contras: ["Latência alta", "Dados saem da nuvem"], custo: "≈ R$ 0,004 por chamado", latencia: "p95 ≈ 1,2 s", complexidade: "baixa", recomendada: false },
        ] } }],
      porque: ["decisao", "decisao", "Cada abordagem muda custo, prazo e risco; a escolha é sua."],
      chips: ["Encoder ajustado", "Começar pelo TF-IDF"],
    },
    {
      texto: "Fechado: encoder ajustado, com TF-IDF como segundo baseline.\n\n**Que decisão o resultado destrava? Por exemplo: desligar as regras e realocar pessoas da triagem.**",
      desenho: { abordagem_escolhida: "Encoder PT-BR ajustado (TF-IDF + LR como segundo baseline)" },
      ficha: { tecnologia: "machine_learning", tecnica: "Classificação supervisionada", golden_path: "classificacao-supervisionada" },
      cards: [{ kind: "tecnologia", data: { tecnologia: "machine_learning", tecnica: "Classificação supervisionada", justificativa: "Há 40 mil rótulos e restrição de latência.", golden_path_nome: "Classificação supervisionada" } }],
      porque: ["decisao", "decisao", "Sem uma decisão em jogo, um bom F1 não muda nada no negócio."],
      chips: ["Desligar as regras e realocar 2 pessoas da triagem", "Levar para o canal de e-mail também"],
    },
    {
      texto: "Proposta de protocolo de avaliação, já no desenho: teste congelado por mês para evitar vazamento e gate de regressão no CI.\n\n**Concorda com bloquear qualquer mudança que derrube o F1 macro em mais de 2 p.p.?**",
      mapa: [["decisao", "Desligar as regras e realocar 2 pessoas da triagem.", 2, "desligar as regras e realocar 2 pessoas"],
        ["sucesso", "Fila errada cai de 25% para 10% ou menos.", 2], ["caso_concreto", "Chamado de portabilidade classificado como cobrança.", 1], ["causas", "Regras não captam variações de escrita.", 1], ["premissa_critica", "A fila final registrada é um rótulo confiável.", 1]],
      ficha: {
        dominio: "operacoes",
        problema: "A triagem por regras manda ~25% dos chamados do suporte para a fila errada.",
        publico_afetado: "Analistas do N1 (retrabalho) e clientes com SLA atrasado.",
        objetivo: "Treinar e avaliar um classificador de filas com chamados históricos rotulados.",
        hipotese: "Acreditamos que um classificador ajustado irá reduzir de 25% para 10% os chamados na fila errada no suporte N1.",
        metodologia: "Treino com chamados de 2025, teste congelado de jan–mar/2026, comparação com regras e TF-IDF.",
        metricas: [
          { nome: "fila_errada", descricao: "Chamados encaminhados para a fila errada", criterio_aceite: "≤ 10%", obrigatoria: true },
          { nome: "latencia_p95", descricao: "Latência da classificação", criterio_aceite: "p95 < 300 ms", obrigatoria: true }],
        amostra: "40 mil chamados rotulados; teste congelado de 4 mil",
        dados: "Zendesk, chamados com fila final",
      },
      desenho: { avaliacao: { conjunto: "Chamados de jan–mar/2026 com a fila final como rótulo", tamanho: 4000, divisao: "Teste congelado por mês, sem vazamento de cliente",
        metricas: [{ nome: "f1_macro", alvo: "≥ 0,85", baseline: "0,71", liga_a: "fila_errada" }, { nome: "acuracia", alvo: "≥ 0,90", baseline: "0,75", liga_a: "fila_errada" },
          { nome: "latencia_p95_ms", alvo: "< 300", baseline: "—", liga_a: "latencia_p95" }],
        gate_regressao: "queda > 2 p.p. em f1_macro" },
        arquitetura: ["Coleta Zendesk", "Pré-processamento", "Encoder ajustado", "API de classificação", "Avaliador + CI"],
        riscos_tecnicos: ["Filas novas sem histórico", "Rótulo da fila final pode ter ruído"] },
      cards: [{ kind: "avaliacao", data: { conjunto: "Chamados de jan–mar/2026 com a fila final como rótulo", tamanho: 4000, divisao: "Teste congelado por mês, sem vazamento de cliente", baseline: "Regras: F1 0,71",
        metricas: [{ nome: "f1_macro", alvo: "≥ 0,85", baseline: "0,71", liga_a: "fila_errada" }, { nome: "acuracia", alvo: "≥ 0,90", baseline: "0,75", liga_a: "fila_errada" },
          { nome: "latencia_p95_ms", alvo: "< 300", baseline: "—", liga_a: "latencia_p95" }], gate_regressao: "queda > 2 p.p. em f1_macro" } }],
      porque: ["sucesso", "criterio_de_parada", "O gate de regressão é o que impede uma melhoria de hoje virar um problema amanhã."],
      chips: ["Concordo", "Prefiro 1 p.p."],
    },
    {
      texto: "Protocolo fechado. Para concluir a ficha:\n\n**Quem é o BO do experimento e quem patrocina?**",
      chips: ["BO: eu; Sponsor: Gerente de Suporte", "BO: Tech lead do suporte; Sponsor: Head de Operações"],
    },
    {
      texto: "Ficha gerada. Pela sua experiência, a lacuna provável é o ajuste fino do encoder; o resto você domina.\n\n**Vai construir com o kit ou prefere a bancada do Lab?**",
      ficha: { titulo: "Triagem de chamados", bo: "Tech lead do suporte", sponsor: "Gerente de Suporte", skills: ["Python", "Ajuste fino de encoders", "Avaliação de classificadores", "FastAPI"] },
      cards: [{ kind: "skills", data: { skills: [{ nome: "Ajuste fino de encoders", para_que: "Treinar o classificador", nivel: 3 }, { nome: "Avaliação de classificadores", para_que: "F1, matriz de confusão", nivel: 2 }, { nome: "FastAPI", para_que: "Servir com p95 < 300 ms", nivel: 2 }],
        estimativa_solicitante: "2 a 3 semanas", estimativa_laboratorio: "1 semana na bancada" } }],
      gerar: true,
      chips: ["Vou construir com o kit", "Prefiro a bancada"],
    },
    {
      texto: "Kit pronto: avaliador, metas e CI que bloqueia regressões. A ficha segue para a **revisão do Lab (G0)**; você pode começar a montar o conjunto de teste enquanto isso.",
      encaminhar: "desenvolvedor",
    },
  ];
}
