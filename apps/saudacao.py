# Em: apps/saudacao.py
def handle_saudacao():
    """Exibe um menu de boas-vindas com opções numeradas."""
    menu_text = (
        "Olá! 👋 Sou o assistente virtual do Grupo Reunidas.\n\n"
        "Como posso ajudar hoje?\n\n"
        "Digite o *número* da opção desejada:\n"
        "*1.* Abrir um chamado no GLPI\n"
        "*2.* Consultar Chamado\n"
        "*3.* Outras Opções"
    )
    return menu_text