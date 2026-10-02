# Documentos reais do laboratório

Coloque aqui fichas, relatórios, pareceres e apresentações de experimentos que o beOn Labs já fez. **Nada desta pasta vai para o Git** (só este README).

Formatos aceitos: `.pdf`, `.docx`, `.md`, `.txt` e `.json` (já no formato `Experimento`).

- Um arquivo solto vira um experimento.
- Vários arquivos do mesmo experimento vão numa subpasta e viram um único registro:

```
data/real/
├── EXP-VOC-01/
│   ├── ficha.docx
│   └── relatorio_final.pdf
├── correlacao_alarmes_core.pdf
└── editais_parecer.docx
```

Depois rode `python -m metaexp ingerir`. Os registros estruturados vão para `data/corpus/real/` (também fora do Git) e passam a servir de contexto para o Cientista e de referência para o gerador sintético. Nomes de pessoas são trocados por papéis na ingestão.
