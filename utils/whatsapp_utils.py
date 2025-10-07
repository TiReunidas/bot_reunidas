import os
import logging
import json # Importe a biblioteca JSON
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
twilio_number = os.getenv('TWILIO_WHATSAPP_NUMBER')

client = Client(account_sid, auth_token)

# --- FUNÇÃO 1: PARA TEXTO SIMPLES ---
def send_whatsapp_message(to_number, body_text):
    """Envia uma mensagem de texto simples. (Funcionalidade principal)"""
    try:
        # Esta função NÃO USA content_sid
        message = client.messages.create(
            from_=twilio_number,
            body=body_text,
            to=to_number
        )
        logging.info(f"Mensagem de texto enviada para {to_number}")
        return True
    except Exception as e:
        logging.error(f"Erro ao enviar mensagem de texto: {e}")
        return False

# --- FUNÇÃO 2: PARA O TEMPLATE DE BOTÕES (TESTE) ---
def send_whatsapp_template_menu(to_number):
    """Tenta enviar o template de menu usando a formatação correta de variáveis."""
    try:
        # É AQUI que pegamos o menu_sid
        menu_sid = os.getenv("TWILIO_WHATSAPP_MENU_SID")
        if not menu_sid:
            logging.error("TESTE ERRO: TWILIO_WHATSAPP_MENU_SID não está definido no .env")
            return False

        logging.info(f"TESTE: Tentando enviar template {menu_sid} com content_variables='{{}}'")
        
        # É AQUI que usamos content_sid e content_variables
        message = client.messages.create(
            from_=twilio_number,
            to=to_number,
            content_sid=menu_sid,
            content_variables=json.dumps({}) 
        )

        logging.info(f"TESTE SUCESSO: Template de menu enviado para {to_number}")
        return True
    except Exception as e:
        logging.error(f"TESTE ERRO: Erro ao enviar template de menu: {e}")
        return False