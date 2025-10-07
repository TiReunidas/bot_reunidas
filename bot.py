import os
import requests
import logging
from flask import Flask, request
from dotenv import load_dotenv

from utils.whatsapp_utils import send_whatsapp_message, send_whatsapp_template_menu
from apps.glpi import create_glpi_ticket, find_glpi_user_by_phone, get_glpi_ticket_status

load_dotenv()
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
app = Flask(__name__)
user_states = {}

# (As funções 'handle_chamado', 'handle_consulta_chamado' e 'handle_outras_opcoes' não mudam)
def handle_chamado(from_number, message_body, media_url=None, media_content_type=None):
    # ... código completo da função
    state_info = user_states.get(from_number, {})
    current_state = state_info.get("state")
    if not current_state:
        user_id = find_glpi_user_by_phone(from_number)
        if user_id:
            user_states[from_number] = {"flow": "create_ticket", "state": "awaiting_title", "data": {"user_id": user_id}}
            return "Ok, vamos abrir um novo chamado em seu nome. Por favor, qual é o *título* do problema?"
        else:
            default_user_id = os.getenv("GLPI_DEFAULT_USER_ID")
            user_states[from_number] = {"flow": "create_ticket", "state": "awaiting_name", "data": {"user_id": default_user_id}}
            return "Não localizei seu número no GLPI. Para prosseguir, por favor, digite seu *nome completo*."
    elif current_state == "awaiting_name":
        state_info["state"] = "awaiting_title"; state_info["data"]["requester_name"] = message_body
        return f"Obrigado, {message_body.split(' ')[0]}. O chamado será aberto em seu nome.\n\nAgora, por favor, qual é o *título* do problema?"
    elif current_state == "awaiting_title":
        state_info["state"] = "awaiting_description"; state_info["data"]["title"] = message_body
        return f"Entendido. Título: *{message_body}*.\n\nAgora, descreva o problema com detalhes."
    elif current_state == "awaiting_description":
        state_info["state"] = "awaiting_image"; state_info["data"]["description"] = message_body
        return "Descrição recebida. Gostaria de anexar um anexo (imagem, vídeo, documento)? Se sim, *envie o arquivo agora*. Se não, digite `não`."
    elif current_state == "awaiting_image":
        title, desc, user_id, name = state_info["data"]["title"], state_info["data"]["description"], state_info["data"]["user_id"], state_info["data"].get("requester_name")
        media_data, process = None, False
        if media_url and media_content_type:
            send_whatsapp_message(from_number, "Anexo recebido! Processando..."); process = True
            try: 
                media_data = {
                    "content": requests.get(media_url, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)).content,
                    "content_type": media_content_type
                }
            except: pass
        elif message_body.lower() in ['não', 'nao', 'n']:
            send_whatsapp_message(from_number, "Ok, sem anexo. Criando o chamado..."); process = True
        else: return "Não entendi. Por favor, envie um anexo ou digite 'não'."
        
        if process:
            glpi_response = create_glpi_ticket(title, desc, user_id, media_data, name)
            del user_states[from_number]
            return glpi_response
    return "Ocorreu um erro no fluxo. Comece de novo."
def handle_consulta_chamado(from_number, message_body):
    state_info = user_states.get(from_number, {})
    current_state = state_info.get("state")
    if not current_state:
        user_states[from_number] = {"flow": "check_status", "state": "awaiting_ticket_number"}
        return "Entendido. Por favor, digite o *número do chamado* que você deseja consultar (apenas os números)."
    elif current_state == "awaiting_ticket_number":
        ticket_id = message_body.strip()
        if not ticket_id.isdigit():
            return "Por favor, envie apenas o número do chamado."
        del user_states[from_number]
        return get_glpi_ticket_status(ticket_id)
    return "Ocorreu um erro no fluxo de consulta."
def handle_outras_opcoes(from_number, message_body):
    return "A função 'Outras Opções' está em desenvolvimento."

@app.route('/webhook', methods=['POST'])
def webhook():
    incoming_message = request.values.get('Body', '').strip()
    from_number = request.values.get('From', '')
    
    num_media = int(request.values.get('NumMedia', 0))
    media_url = request.values.get('MediaUrl0') if num_media > 0 else None
    media_content_type = request.values.get('MediaContentType0') if num_media > 0 else None
    
    app.logger.info(f"Msg de {from_number}: '{incoming_message}' / Mídia: {media_url} (Tipo: {media_content_type})")
    response_message = ""

    # --- A LÓGICA DE ROTEAMENTO CORRIGIDA ESTÁ AQUI ---
    if from_number in user_states:
        flow = user_states[from_number].get("flow")
        if flow == "create_ticket":
            response_message = handle_chamado(from_number, incoming_message, media_url, media_content_type)
        elif flow == "check_status":
            # A mensagem aqui não terá mídia, então passamos None
            response_message = handle_consulta_chamado(from_number, incoming_message)
        else:
            # Estado inválido, limpa tudo e volta ao menu
            del user_states[from_number]
            send_whatsapp_template_menu(from_number)
            response_message = None
    # --- FIM DA CORREÇÃO ---
    else:
        command = incoming_message.lower()
        if command == 'abrir chamado':
            response_message = handle_chamado(from_number, command, media_url, media_content_type)
        elif command == 'consultar chamado':
             response_message = handle_consulta_chamado(from_number, command)
        elif command == 'outras opções':
             response_message = handle_outras_opcoes(from_number, command)
        else:
             send_whatsapp_template_menu(from_number)
             response_message = None
    
    if from_number and response_message:
        send_whatsapp_message(from_number, response_message)
        
    return "OK", 200

if __name__ == '__main__':
    nova_porta = 8080
    app.run(debug=True, port=nova_porta)