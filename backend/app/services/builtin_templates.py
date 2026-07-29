from ..models import TemplateSource, TemplateType

AGENDA_TEMPLATE = """# Agenda reunião [NOME CLIENTE]

**Data:** [DATA]

## Pontos do lado da Empresa

*(O que ficou combinado na última reunião e o estado atual de cada ponto)*

- XX — [FEITO / EM CURSO / PENDENTE / A ENVIAR HOJE]

## Pontos do lado do Cliente

*(O que dependemos do cliente para avançar ou validar)*

- XX

## Temas novos a abordar em reunião

*(Assuntos adicionais ou novas propostas a discutir)*

- XX
"""

MINUTES_TEMPLATE = """# Ata — [NOME CLIENTE]

**Data:** [DATA]

**Participantes:** [PARTICIPANTES]

## Notas da reunião

### TEMA

- Conteúdo

## Action items

| Task | Pessoa Alocada | Timing |
| :--- | :------------- | :----- |
| | | |
"""

FULL_SUMMARY_TEMPLATE = """# Resumo completo — [NOME CLIENTE]

**Data:** [DATA]

**Participantes:** [PARTICIPANTES]

## Resumo executivo

[RESUMO — 1 a 3 parágrafos com o essencial de toda a reunião]

## Objetivo da reunião

[OBJETIVO]

## Temas discutidos

### [TEMA 1]

- O que foi dito / acordado neste tema

### [TEMA 2]

- O que foi dito / acordado neste tema

## Decisões

- [DECISÃO]

## Action items

| Task | Pessoa Alocada | Timing |
| :--- | :------------- | :----- |
| | | |

## Riscos e bloqueios

- [RISCO OU BLOQUEIO]

## Perguntas em aberto

- [PERGUNTA]

## Próximos passos

- [PRÓXIMO PASSO]
"""

BUILTIN_TEMPLATES = [
    {
        "name": "Agenda de Reunião",
        "type": TemplateType.agenda,
        "source": TemplateSource.builtin,
        "content": AGENDA_TEMPLATE,
        "is_default": True,
        "structure": {
            "sections": [
                "header",
                "company_points",
                "client_points",
                "new_topics",
            ],
            "placeholders": ["NOME CLIENTE", "DATA"],
        },
    },
    {
        "name": "Resumo completo da reunião",
        "type": TemplateType.minutes,
        "source": TemplateSource.builtin,
        "content": FULL_SUMMARY_TEMPLATE,
        "is_default": False,
        "structure": {
            "mode": "full_summary",
            "sections": [
                "header",
                "executive_summary",
                "objective",
                "topics",
                "decisions",
                "action_items_table",
                "risks",
                "open_questions",
                "next_steps",
            ],
            "placeholders": ["NOME CLIENTE", "DATA", "PARTICIPANTES"],
            "tables": ["action_items"],
        },
    },
    {
        "name": "Ata da Reunião",
        "type": TemplateType.minutes,
        "source": TemplateSource.builtin,
        "content": MINUTES_TEMPLATE,
        "is_default": True,
        "structure": {
            "mode": "strict_minutes",
            "sections": ["header", "participants", "notes", "action_items_table"],
            "placeholders": ["NOME CLIENTE", "DATA", "PARTICIPANTES"],
            "tables": ["action_items"],
        },
    },
]
