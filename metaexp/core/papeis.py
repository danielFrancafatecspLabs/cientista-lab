"""Papéis do METAEXP e a jornada de cada um.

Quatro papéis entram pela porta da frente:

- **Solicitante**: área de negócio que trouxe um desafio. Conversa com o
  Cientista sobre o negócio, nunca sobre técnica. O laboratório executa.
- **Desenvolvedor**: quer construir. Conversa técnica desde o início e sai com
  ficha, desenho e um kit executável (experimento como código).
- **Lab**: pesquisadores que revisam e aprovam fichas (gate G0) com apoio do
  Agente Revisor, e acompanham a bancada.
- **Sponsor**: acompanha o portfólio e decide o que escala depois do parecer.

Os dois primeiros conversam com o Cientista; os dois últimos trabalham em
painéis. A matriz completa de responsabilidades está em `RESPONSABILIDADES`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Papel = Literal["solicitante", "desenvolvedor", "lab", "sponsor"]
PapelConversa = Literal["solicitante", "desenvolvedor"]


@dataclass(frozen=True)
class Preferencia:
    id: str
    pergunta: str
    opcoes: tuple[tuple[str, str], ...]     # (id, rótulo)
    padrao: str


@dataclass(frozen=True)
class Jornada:
    papel: Papel
    nome: str
    chamada: str                           # a frase da porta de entrada
    descricao: str
    promessa: str
    tipo: Literal["conversa", "painel"]
    etapas: tuple[str, ...]
    prompt: str = ""                       # arquivo em prompts/ (só papéis de conversa)
    ferramentas: tuple[str, ...] = ()
    destinos: tuple[str, ...] = ()         # encaminhamentos permitidos
    perfil_corpus: Literal["negocio", "desenvolvedor"] = "negocio"
    preferencias: tuple[Preferencia, ...] = field(default_factory=tuple)

    def valida_preferencias(self, prefs: dict | None) -> dict:
        """Mantém só preferências conhecidas com valores válidos; completa com o padrão."""
        prefs = prefs or {}
        out = {}
        for p in self.preferencias:
            validos = {o for o, _ in p.opcoes}
            v = prefs.get(p.id)
            out[p.id] = v if v in validos else p.padrao
        return out

    def descreve_preferencias(self, prefs: dict) -> str:
        linhas = []
        for p in self.preferencias:
            rotulo = dict(p.opcoes).get(prefs.get(p.id, p.padrao), "")
            linhas.append(f"- {p.pergunta} {rotulo}")
        return "\n".join(linhas)


AREAS = (("atendimento", "Atendimento"), ("rede", "Rede"), ("digital", "Digital"), ("financeiro", "Financeiro"),
         ("suprimentos", "Suprimentos"), ("juridico", "Jurídico"), ("rh", "RH"), ("marketing", "Marketing"),
         ("operacoes", "Operações"), ("outro", "Outra"))

COMUNS = ("mapear_problema", "atualizar_ficha", "gerar_ficha", "buscar_experimentos_similares", "sugerir_respostas",
          "solicitar_dados", "calcular_tamanho_amostra", "classificar_experimento", "encaminhar")

JORNADAS: dict[str, Jornada] = {
    "solicitante": Jornada(
        papel="solicitante", nome="Solicitante", tipo="conversa",
        chamada="Tenho um desafio de negócio",
        descricao="Você trouxe um desafio para o beOn Labs resolver com tecnologia.",
        promessa="Você fala do seu negócio. O Cientista transforma isso em um experimento e o laboratório executa.",
        etapas=("Desafio", "Entendimento", "Hipótese", "Sucesso", "Dados", "Responsáveis", "Ficha", "Revisão do Lab", "Bancada"),
        prompt="papel_solicitante", ferramentas=COMUNS, destinos=("workflow",), perfil_corpus="negocio",
        preferencias=(
            Preferencia("area", "Área:", AREAS, "atendimento"),
            Preferencia("ritmo", "Ritmo:", (("direto", "Direto ao ponto"), ("guiado", "Guiado, com exemplos")), "guiado"),
        ),
    ),
    "desenvolvedor": Jornada(
        papel="desenvolvedor", nome="Desenvolvedor", tipo="conversa",
        chamada="Quero construir algo",
        descricao="Você quer construir uma solução e precisa provar que ela funciona.",
        promessa="Desenho técnico com baseline, trade-offs e protocolo de avaliação, e um kit pronto para rodar com CI.",
        etapas=("Problema", "Contexto técnico", "Baseline", "Hipótese", "Abordagens", "Avaliação", "Dados", "Ficha", "Kit"),
        prompt="papel_desenvolvedor",
        ferramentas=COMUNS + ("propor_abordagens", "registrar_desenho_tecnico", "apresentar_skills"),
        destinos=("desenvolvedor", "workflow"), perfil_corpus="desenvolvedor",
        preferencias=(
            Preferencia("stack", "Stack:", (("python", "Python"), ("typescript", "TypeScript / Node"), ("java", "Java / Kotlin"), ("sql", "SQL e dados")), "python"),
            Preferencia("ia", "Experiência com IA:", (("iniciante", "Começando"), ("intermediario", "Já usei LLMs"), ("avancado", "Especialista em ML")), "intermediario"),
            Preferencia("ambiente", "Onde vai rodar:", (("sandbox", "Sandbox do Lab"), ("propria", "Minha infraestrutura")), "sandbox"),
        ),
    ),
    "lab": Jornada(
        papel="lab", nome="Lab", tipo="painel",
        chamada="Reviso e aprovo experimentos",
        descricao="Você garante o rigor do método antes de qualquer execução.",
        promessa="Fila de revisão com pré-análise do Agente Revisor, evidências da conversa e decisão em um clique.",
        etapas=("Fila", "Pré-revisão", "Evidências", "Decisão"),
    ),
    "sponsor": Jornada(
        papel="sponsor", nome="Sponsor", tipo="painel",
        chamada="Acompanho o portfólio",
        descricao="Você patrocina experimentos e decide o que escala.",
        promessa="Portfólio por etapa, indicadores do metaexperimento e as decisões que dependem de você.",
        etapas=("Portfólio", "Indicadores", "Decisões"),
    ),
}

PAPEIS_CONVERSA = tuple(p for p, j in JORNADAS.items() if j.tipo == "conversa")


def jornada(papel: str | None) -> Jornada:
    return JORNADAS.get(papel or "", JORNADAS["solicitante"])


# Matriz de papéis e responsabilidades por etapa (R = responsável, A = aprova,
# C = consultado, I = informado). Fonte da documentação em docs/.
ETAPAS_CICLO = ("Ficha", "Revisão (G0)", "Amostra (G1)", "Construção", "Qualidade (G2)", "Parecer (G3)", "Decisão")

RESPONSABILIDADES: list[dict] = [
    {"papel": "Solicitante", "tipo": "pessoa", "entra_pela_plataforma": True,
     "missao": "Traz o desafio de negócio e decide com base no resultado.",
     "responsabilidades": ["Explicar o problema, o impacto e a decisão em jogo", "Indicar ou fornecer os dados",
                           "Confirmar a ficha", "Validar resultados com conhecimento do domínio", "Aceitar o parecer"],
     "raci": ["R", "I", "C", "I", "I", "A", "C"]},
    {"papel": "Desenvolvedor", "tipo": "pessoa", "entra_pela_plataforma": True,
     "missao": "Constrói a solução com apoio do método e dos agentes.",
     "responsabilidades": ["Detalhar contexto técnico, baseline e restrições", "Escolher a abordagem pelos trade-offs",
                           "Definir o protocolo de avaliação", "Construir com o kit e o CI do experimento", "Reportar resultados"],
     "raci": ["R", "I", "R", "R", "R", "C", "I"]},
    {"papel": "Lab (pesquisa)", "tipo": "pessoa", "entra_pela_plataforma": True,
     "missao": "Garante o rigor do método e destrava casos difíceis.",
     "responsabilidades": ["Revisar e aprovar fichas (G0)", "Confirmar a amostra (G1)", "Orientar quando o Ralph Loop atinge Kmax",
                           "Manter o método e os golden paths", "Fazer revisão cega de pareceres"],
     "raci": ["C", "A", "A", "C", "A", "R", "C"]},
    {"papel": "Sponsor", "tipo": "pessoa", "entra_pela_plataforma": True,
     "missao": "Patrocina o portfólio e decide o que escala.",
     "responsabilidades": ["Priorizar desafios", "Aprovar recursos", "Decidir escalar, iterar ou encerrar após o parecer"],
     "raci": ["I", "I", "I", "I", "I", "I", "A"]},
    {"papel": "BO (responsável pelo experimento)", "tipo": "pessoa", "entra_pela_plataforma": False,
     "missao": "Responde pelo experimento do início ao fim.",
     "responsabilidades": ["Garantir acesso a dados e pessoas", "Acompanhar prazos e gates", "Assinar ficha e parecer"],
     "raci": ["A", "C", "R", "I", "I", "R", "R"]},
    {"papel": "Agente Cientista", "tipo": "agente", "entra_pela_plataforma": False,
     "missao": "Entende o problema a fundo e conduz a ficha no método oficial.",
     "responsabilidades": ["Mapear o problema com perguntas de alto valor", "Ancorar critérios no histórico do Lab",
                           "Validar o checklist de qualidade mínima", "Desenhar a avaliação com o desenvolvedor", "Gerar a ficha e encaminhar"],
     "raci": ["R", "I", "C", "I", "I", "I", "I"]},
    {"papel": "Agente Revisor", "tipo": "agente", "entra_pela_plataforma": False,
     "missao": "Prepara a revisão do Lab com uma pré-análise verificável.",
     "responsabilidades": ["Pontuar a ficha na rubrica do Lab", "Apontar riscos e ajustes concretos", "Citar o trecho que justifica cada nota"],
     "raci": ["I", "R", "I", "I", "I", "I", "I"]},
    {"papel": "Agentes da bancada", "tipo": "agente", "entra_pela_plataforma": False,
     "missao": "Executam o experimento: Dados, Desenvolvedor, QA e Analista.",
     "responsabilidades": ["Analisar a amostra (G1)", "Planejar e construir", "Rodar o Ralph Loop até Qk ≥ 0,85 (G2)",
                           "Emitir o parecer com evidências (G3)"],
     "raci": ["I", "I", "R", "R", "R", "R", "I"]},
]
