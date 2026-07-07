from __future__ import annotations


def friendly_openai_error(exc: BaseException) -> str:
    msg = str(exc)
    lower = msg.lower()
    if "insufficient_quota" in lower or "exceeded your current quota" in lower:
        return (
            "A chave OpenAI não tem saldo/quota disponível. "
            "Verifica em platform.openai.com → Billing e adiciona créditos."
        )
    if "invalid_api_key" in lower or "incorrect api key" in lower:
        return (
            "OPENAI_API_KEY inválida em backend/.env. "
            "Gera uma chave nova em platform.openai.com e reinicia o backend."
        )
    if "rate_limit" in lower or "429" in lower:
        return (
            "Limite de pedidos OpenAI atingido. Espera um minuto e tenta outra vez."
        )
    if "OPENAI_API_KEY" in msg or "ConfigurationError" in type(exc).__name__:
        return (
            "OPENAI_API_KEY em falta em backend/.env. "
            "Cola a chave, guarda e reinicia com ARRANCAR.cmd."
        )
    return "Ocorreu um erro ao processar o pedido. Tenta novamente ou contacta o administrador."
