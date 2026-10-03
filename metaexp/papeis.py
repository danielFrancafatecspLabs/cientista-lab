"""Papéis da plataforma e as jornadas de cada um.

Dois papéis entram pela porta da frente e têm jornadas próprias:

- **Solicitante**: procurou o beOn Labs para executar um desafio tecnológico.
  Conversa fluida e cadenciada, com profundidade de negócio e nenhuma parte
  técnica. O laboratório escolhe a técnica e executa na bancada.
- **Desenvolvedor**: de qualquer área, quer construir algo. Jornada técnica e
  profunda desde o início: stack, baseline, abordagens com trade-offs,
  protocolo de avaliação e desenho da solução. Recebe a ficha e o kit; a
  bancada do laboratório é opcional.

Os demais papéis (BO, Sponsor, Curador, Especialista revisor e os agentes)
estão em `RESPONSABILIDADES`, usada pela API e pela documentação.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Papel = Literal["solicitante", "desenvolvedor"]


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
    descricao: str
    promessa: str
    etapas: tuple[str, ...]
    prompt: str                            # arquivo em prompts/
    ferramentas: tuple[str, ...]
    destinos: tuple[str, ...]              # encaminhamentos permitidos
    destino_padrao: str
    perfil_corpus: Literal["negocio", "desenvolvedor"]
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


AREAS = (("rede", "Rede"), ("atendimento", "Atendimento"), ("digital", "Digital"), ("financeiro", "Financeiro"),
         ("suprimentos", "Suprimentos"), ("juridico", "Jurídico"), ("rh", "RH"), ("marketing", "Marketing"),
         ("operacoes", "Operações"), ("outro", "Outra"))

COMUNS = ("atualizar_ficha", "gerar_ficha", "buscar_experimentos_similares", "sugerir_respostas",
          "solicitar_dados", "calcular_tamanho_amostra", "classificar_experimento", "encaminhar")

JORNADAS: dict[str, Jornada] = {
    "solicitante": Jornada(
        papel="solicitante",
        nome="Solicitante",
        descricao="Procurou o beOn Labs para executar um desafio tecnológico.",
        promessa="Você fala do seu negócio; o laboratório cuida da tecnologia e executa.",
        etapas=("Desafio", "Impacto", "Objetivo", "Hipótese", "Amostra", "Métricas", "Responsáveis", "Ficha", "Bancada"),
        prompt="jornada_solicitante",
        ferramentas=COMUNS,
        destinos=("workflow",),
        destino_padrao="workflow",
        perfil_corpus="negocio",
        preferencias=(
            Preferencia("area", "Área:", AREAS, "atendimento"),
            Preferencia("ritmo", "Ritmo da conversa:", (("direto", "Direto ao ponto"), ("guiado", "Guiado, com exemplos")), "guiado"),
        ),
    ),
    "desenvolvedor": Jornada(
        papel="desenvolvedor",
        nome="Desenvolvedor",
        descricao="Desenvolvedor de qualquer área querendo construir algo.",
        promessa="Desenho técnico desde o início: baseline, abordagens, avaliação e kit para construir.",
        etapas=("Problema", "Contexto técnico", "Objetivo", "Baseline", "Hipótese", "Abordagens", "Amostra",
                "Avaliação", "Critérios", "Responsáveis", "Ficha", "Kit"),
        prompt="jornada_desenvolvedor",
        ferramentas=COMUNS + ("propor_abordagens", "registrar_desenho_tecnico", "apresentar_skills"),
        destinos=("desenvolvedor", "workflow"),
        destino_padrao="desenvolvedor",
        perfil_corpus="desenvolvedor",
        preferencias=(
            Preferencia("stack", "Stack principal:", (("python", "Python"), ("typescript", "TypeScript / Node"), ("java", "Java / Kotlin"), ("sql", "SQL e dados")), "python"),
            Preferencia("ia", "Experiência com IA:", (("iniciante", "Começando em IA"), ("intermediario", "Já usei LLMs e APIs"), ("avancado", "Especialista em ML")), "intermediario"),
            Preferencia("ambiente", "Onde vai rodar:", (("sandbox", "Sandbox do laboratório"), ("propria", "Minha infraestrutura")), "sandbox"),
        ),
    ),
}


def jornada(papel: str | None) -> Jornada:
    return JORNADAS.get(papel or "", JORNADAS["solicitante"])


# Matriz de papéis e responsabilidades por etapa (R = responsável, A = aprova,
# C = consultado, I = informado). Fonte da documentação em docs/.
ETAPAS_CICLO = ("Ficha (G0)", "Amostra (G1)", "Construção", "Qualidade (G2)", "Resultado (G3)", "Piloto e escala")

RESPONSABILIDADES: list[dict] = [
    {"papel": "Solicitante", "tipo": "pessoa", "entra_pela_plataforma": True,
     "missao": "Traz o desafio de negócio e decide com base no resultado.",
     "responsabilidades": ["Descrever o problema, o impacto e o objetivo", "Fornecer ou indicar os dados", "Aprovar a ficha",
                           "Validar resultados com conhecimento do domínio", "Aceitar o parecer e decidir o encaminhamento"],
     "raci": ["A", "C", "I", "I", "A", "C"]},
    {"papel": "Desenvolvedor", "tipo": "pessoa", "entra_pela_plataforma": True,
     "missao": "Constrói a solução com apoio do método e dos agentes.",
     "responsabilidades": ["Detalhar contexto técnico, baseline e restrições", "Escolher a abordagem com os trade-offs apresentados",
                           "Definir o protocolo de avaliação", "Construir e executar a solução (ou enviá-la à bancada)",
                           "Reportar resultados para o parecer"],
     "raci": ["A", "R", "R", "R", "C", "C"]},
    {"papel": "BO (responsável pelo experimento)", "tipo": "pessoa", "entra_pela_plataforma": False,
     "missao": "Responde pelo experimento do início ao fim.",
     "responsabilidades": ["Garantir acesso a dados e pessoas", "Acompanhar prazos e gates", "Assinar a ficha e o parecer"],
     "raci": ["R", "A", "I", "I", "R", "R"]},
    {"papel": "Sponsor (patrocinador)", "tipo": "pessoa", "entra_pela_plataforma": False,
     "missao": "Patrocina o experimento e decide sobre piloto e escala.",
     "responsabilidades": ["Priorizar o desafio", "Aprovar recursos", "Decidir piloto e escala a partir do veredito"],
     "raci": ["I", "I", "I", "I", "I", "A"]},
    {"papel": "Agente Cientista", "tipo": "agente", "entra_pela_plataforma": False,
     "missao": "Conduz a conversa no método oficial e gera a ficha.",
     "responsabilidades": ["Adaptar a jornada ao papel", "Validar o checklist de qualidade mínima", "Buscar experimentos semelhantes",
                           "Analisar a amostra enviada", "Gerar a ficha e encaminhar"],
     "raci": ["R", "C", "I", "I", "I", "I"]},
    {"papel": "Agentes da bancada", "tipo": "agente", "entra_pela_plataforma": False,
     "missao": "Executam o experimento: Dados, Desenvolvedor, QA e Analista.",
     "responsabilidades": ["Analisar a amostra (G1)", "Planejar e construir", "Rodar o Ralph Loop até Qk ≥ 0,85 (G2)",
                           "Emitir o parecer com evidências (G3)"],
     "raci": ["I", "R", "R", "R", "R", "I"]},
    {"papel": "Curador de governança", "tipo": "pessoa", "entra_pela_plataforma": False,
     "missao": "Mantém o método, os golden paths e os indicadores da esteira.",
     "responsabilidades": ["Revisar fichas fora do padrão", "Promover novos golden paths", "Acompanhar C, ΔT, A e S"],
     "raci": ["C", "I", "I", "C", "C", "I"]},
    {"papel": "Especialista revisor", "tipo": "pessoa", "entra_pela_plataforma": False,
     "missao": "Destrava casos difíceis e garante a qualidade dos resultados.",
     "responsabilidades": ["Orientar quando o Ralph Loop atinge Kmax", "Fazer revisão cega de pareceres"],
     "raci": ["I", "C", "C", "A", "C", "I"]},
]
