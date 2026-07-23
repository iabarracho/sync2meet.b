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
        "name": "Ata da Reunião",
        "type": TemplateType.minutes,
        "source": TemplateSource.builtin,
        "content": MINUTES_TEMPLATE,
        "is_default": True,
        "structure": {
            "sections": ["header", "participants", "notes", "action_items_table"],
            "placeholders": ["NOME CLIENTE", "DATA", "PARTICIPANTES"],
            "tables": ["action_items"],
        },
    },
]
