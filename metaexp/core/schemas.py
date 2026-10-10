"""Contratos de dados do METAEXP.

Os mesmos modelos servem a quatro usos: estado da conversa (a ficha sendo
montada), saídas estruturadas dos agentes, registros do corpus de experimentos
(reais e sintéticos) e casos de avaliação.
"""

from __future__ import annotations

from typing import ClassVar, Literal, Optional

from pydantic import BaseModel, Field

Dominio = Literal["rede", "atendimento", "digital", "financeiro", "suprimentos", "juridico", "rh", "marketing", "operacoes", "outro"]
Tecnologia = Literal["ia_generativa", "machine_learning", "estatistica", "visao_computacional", "automacao", "otimizacao", "outro"]
Perfil = Literal["negocio", "desenvolvedor"]
Veredito = Literal["validada", "parcialmente_comprovada", "invalidada", "inconclusiva"]
SituacaoDados = Literal["sem_dados", "amostra_pequena", "amostra_suficiente", "dados_sensiveis"]


# ---------------------------------------------------------------- ficha ----

class Metrica(BaseModel):
    nome: str = Field(description="Nome curto em snake_case, ex.: acuracia")
    descricao: str
    criterio_aceite: str = Field(description="Valor numérico com condição clara de sucesso, ex.: 'Acurácia ≥ 85%'")
    obrigatoria: bool


class Abordagem(BaseModel):
    nome: str
    descricao: str
    pros: list[str]
    contras: list[str]
    custo: str = Field(description="Estimativa de custo, ex.: 'R$ 0,03 por consulta'")
    latencia: str = Field(description="Estimativa de latência, ex.: 'p95 ≈ 1,5 s'")
    complexidade: Literal["baixa", "media", "alta"]
    recomendada: bool


class MetricaTecnica(BaseModel):
    nome: str = Field(description="Ex.: recall@5, f1_macro, latencia_p95_ms, custo_por_consulta")
    alvo: str = Field(description="Meta com condição, ex.: '≥ 0,85' ou '< 2000 ms'")
    baseline: Optional[str] = Field(None, description="Valor de hoje, se conhecido")
    liga_a: Optional[str] = Field(None, description="Métrica de negócio da ficha que ela sustenta")


class ProtocoloAvaliacao(BaseModel):
    """Como o experimento será medido: o contrato que o CI do kit executa a cada mudança."""

    conjunto: str = Field(description="De onde vêm os casos de teste e como são rotulados")
    tamanho: Optional[int] = Field(None, description="Número de casos no conjunto de avaliação")
    divisao: Optional[str] = Field(None, description="Ex.: 'teste congelado de 20%, sem vazamento por cliente'")
    metricas: list[MetricaTecnica] = Field(default_factory=list)
    gate_regressao: Optional[str] = Field(None, description="Quando uma mudança é bloqueada, ex.: 'queda > 2 p.p. em recall@5'")


class DetalhesTecnicos(BaseModel):
    """Desenho técnico, preenchido na jornada do desenvolvedor."""

    stack: Optional[str] = None
    fontes_dados: Optional[str] = Field(None, description="Sistemas, formatos, volume e atualização")
    restricoes: list[str] = Field(default_factory=list, description="Latência, custo, segurança, LGPD")
    baseline: Optional[str] = Field(None, description="O que existe hoje e seu desempenho")
    abordagens: list[Abordagem] = Field(default_factory=list)
    abordagem_escolhida: Optional[str] = None
    avaliacao: Optional[ProtocoloAvaliacao] = None
    arquitetura: list[str] = Field(default_factory=list, description="Componentes da solução")
    riscos_tecnicos: list[str] = Field(default_factory=list)

    def pendencias(self) -> list[str]:
        """O que falta para o desenho virar um kit executável."""
        out = []
        if not self.stack:
            out.append("stack")
        if not self.baseline:
            out.append("baseline")
        if not self.abordagem_escolhida:
            out.append("abordagem escolhida")
        if not self.avaliacao or not self.avaliacao.metricas:
            out.append("protocolo de avaliação com métricas técnicas")
        elif not self.avaliacao.gate_regressao:
            out.append("gate de regressão do protocolo")
        if not self.arquitetura:
            out.append("arquitetura")
        return out


# ------------------------------------------------------- mapa do problema ----

class DimensaoMapa(BaseModel):
    entendimento: Optional[str] = None
    profundidade: int = Field(0, ge=0, le=3, description="0 vazio · 1 raso · 2 claro · 3 profundo e com evidência")
    evidencia: Optional[str] = Field(None, description="Fala ou dado da pessoa que sustenta o entendimento")


class PerguntaGuia(BaseModel):
    """A pergunta que o Cientista está fazendo agora e por quê: mostrada à pessoa."""

    dimensao: str
    tecnica: str
    por_que: str


class MapaProblema(BaseModel):
    """O que o Cientista entendeu do problema, dimensão a dimensão (ver core/descoberta.py)."""

    dimensoes: dict[str, DimensaoMapa] = Field(default_factory=dict)
    sintese: Optional[str] = None
    sintese_confirmada: bool = False
    pergunta_atual: Optional[PerguntaGuia] = None


class Ficha(BaseModel):
    """Ficha de experimento no padrão beOn Labs (Apêndice A da proposta)."""

    id: Optional[str] = None
    titulo: Optional[str] = Field(None, description="Nome do experimento: no máximo 3 palavras, executivo")
    dominio: Optional[Dominio] = None
    problema: Optional[str] = None
    publico_afetado: Optional[str] = Field(None, description="Impacto: quem sente o problema e quanto custa hoje")
    objetivo: Optional[str] = Field(None, description="O que será realizado (não o que se espera comprovar)")
    hipotese: Optional[str] = Field(None, description="'Acreditamos que [ação] irá gerar [resultado mensurável] para [contexto].' Máximo 2 linhas")
    metodologia: Optional[str] = Field(None, description="Como o experimento será conduzido")
    tecnologia: Optional[Tecnologia] = None
    tecnica: Optional[str] = Field(None, description="Ex.: RAG, classificação supervisionada, agrupamento")
    justificativa_tecnica: Optional[str] = None
    golden_path: Optional[str] = None
    metricas: list[Metrica] = Field(default_factory=list)
    dados: Optional[str] = Field(None, description="Fontes de dados e sensibilidade")
    amostra: Optional[str] = Field(None, description="Tamanho e qualidade da amostra validada")
    bo: Optional[str] = Field(None, description="Responsável pelo experimento (BO)")
    sponsor: Optional[str] = Field(None, description="Patrocinador (SPONSOR)")
    skills: list[str] = Field(default_factory=list)
    execucao: Optional[Literal["laboratorio", "solicitante"]] = None
    riscos: list[str] = Field(default_factory=list)
    detalhes_tecnicos: Optional[DetalhesTecnicos] = None

    CAMPOS_OBRIGATORIOS: ClassVar[tuple[str, ...]] = (
        "titulo", "problema", "publico_afetado", "objetivo", "hipotese", "metodologia", "tecnologia",
        "tecnica", "metricas", "dados", "amostra", "bo", "sponsor", "skills", "execucao",
    )

    def faltantes(self) -> list[str]:
        return [c for c in self.CAMPOS_OBRIGATORIOS if not getattr(self, c)]

    def pendencias(self) -> list[str]:
        """Checklist de qualidade mínima do método (regras de formato incluídas)."""
        from metaexp.core.metodo import pendencias
        return pendencias(self)

    def completa(self) -> bool:
        return not self.faltantes() and not self.pendencias()


# --------------------------------------------------- artefatos da bancada ----

class AnaliseAmostra(BaseModel):
    """Saída do Agente de Amostra e Dados (gate G1)."""

    resumo: str
    registros_validos: int
    tamanho_minimo: int
    suficiente: bool
    qualidade: Literal["boa", "aceitavel", "ruim"]
    achados: list[str] = Field(description="Observações objetivas sobre os dados")
    alertas: list[str] = Field(description="Problemas que o QA deve considerar")
    decisao_g1: Literal["aprovado", "aprovado_com_ressalva", "reprovado"]


class PlanoTecnico(BaseModel):
    """Saída do Agente Desenvolvedor (drafting + estrutura da solução)."""

    abordagem: str
    etapas: list[str]
    componentes: list[str] = Field(description="Módulos/scripts a construir")
    criterios_atendidos: list[str] = Field(description="Quais critérios da ficha cada parte cobre")
    riscos_tecnicos: list[str]


class CriterioAvaliado(BaseModel):
    criterio: str
    atendido: bool
    evidencia: str


class AvaliacaoQA(BaseModel):
    """Saída do Agente QA em uma iteração do Ralph Loop."""

    executa_sem_erro: bool = Field(description="e: a solução roda sem erro crítico")
    outputs_existem: bool = Field(description="o: todos os outputs esperados existem")
    dados_validos: bool = Field(description="d: outputs não vazios e com estrutura correta")
    criterios: list[CriterioAvaliado]
    feedback: list[str] = Field(description="Correções concretas para a próxima iteração")

    def aderencia(self) -> float:
        if not self.criterios:
            return 0.0
        return sum(c.atendido for c in self.criterios) / len(self.criterios)

    def qualidade(self) -> float:
        """Qk = e · o · d · S (Eq. 5 da proposta)."""
        return float(self.executa_sem_erro) * float(self.outputs_existem) * float(self.dados_validos) * self.aderencia()


class ResultadoMetrica(BaseModel):
    metrica: str
    meta: str
    resultado: str
    atendida: bool


class Resultados(BaseModel):
    """Resultados de execução. `simulado=True` quando vêm do executor simulado."""

    simulado: bool
    metricas: list[ResultadoMetrica]
    observacoes: list[str]


class Parecer(BaseModel):
    """Saída do Agente Analista (gate G3)."""

    veredito: Veredito
    titulo: str = Field(description="Frase-manchete do resultado, para a área de negócio")
    resumo: str
    evidencias: list[str]
    riscos: list[str]
    proximos_passos: list[str]
    oportunidades: list[str]


# ------------------------------------------------ revisão do Lab e decisão ----

CriterioRubrica = Literal["problema", "hipotese", "criterios", "dados", "viabilidade"]


class NotaRubrica(BaseModel):
    criterio: CriterioRubrica
    nota: int = Field(ge=1, le=5)
    justificativa: str = Field(description="Uma frase objetiva, citando o trecho da ficha")


class PreRevisao(BaseModel):
    """Saída do Agente Revisor: prepara a revisão humana do Lab (gate G0)."""

    resumo: str = Field(description="Duas frases: o que o experimento testa e se está pronto")
    notas: list[NotaRubrica]
    pontos_fortes: list[str]
    riscos: list[str]
    ajustes_sugeridos: list[str] = Field(description="Mudanças concretas na ficha, se houver")
    recomendacao: Literal["aprovar", "aprovar_com_ajustes", "devolver"]


class Revisao(BaseModel):
    """Decisão humana do Lab sobre a ficha."""

    decisao: Literal["aprovar", "devolver"]
    comentario: str = ""
    revisor: str = "Lab"
    versao_ficha: int = 1
    em: str = ""


class DecisaoSponsor(BaseModel):
    decisao: Literal["escalar", "iterar", "encerrar"]
    comentario: str = ""
    em: str = ""


# ------------------------------------------------- corpus de experimentos ----

class Turno(BaseModel):
    papel: Literal["cientista", "solicitante"]
    texto: str


class Experimento(BaseModel):
    """Registro do corpus: um experimento completo, real ou sintético.

    É a unidade usada para busca de casos semelhantes (contexto do Cientista),
    para few-shot na geração sintética e para montar casos de avaliação.
    """

    id: str
    origem: Literal["real", "sintetico"]
    semente: Optional[str] = Field(None, description="Id do experimento real que inspirou o sintético")
    dominio: Dominio
    perfil_solicitante: Perfil
    situacao_dados: SituacaoDados
    ficha: Ficha
    descricao_amostra: str
    plano: Optional[PlanoTecnico] = None
    resultados: Optional[Resultados] = None
    parecer: Optional[Parecer] = None
    conversa: list[Turno] = Field(default_factory=list, description="Diálogo de elaboração da ficha")
    lead_time_dias: Optional[int] = None
    tags: list[str] = Field(default_factory=list)

    def texto_busca(self) -> str:
        f = self.ficha
        partes = [f.titulo, f.problema, f.publico_afetado, f.objetivo, f.hipotese, f.metodologia, f.tecnica, f.justificativa_tecnica,
                  f.golden_path, f.dados, self.descricao_amostra, " ".join(self.tags)]
        partes += [m.descricao for m in f.metricas]
        if self.parecer:
            partes += [self.parecer.titulo, self.parecer.resumo, *self.parecer.riscos]
        return " ".join(p for p in partes if p)
