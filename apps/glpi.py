import os
import re
import requests
import logging
from dotenv import load_dotenv

load_dotenv()

GLPI_URL = os.getenv("GLPI_URL")
GLPI_APP_TOKEN = os.getenv("GLPI_APP_TOKEN")

# (As funções _get_session_token, _kill_session, find_glpi_user_by_phone e get_glpi_ticket_status não mudam)
def _get_session_token():
    try:
        headers = {"Content-Type": "application/json", "Authorization": f"user_token {GLPI_APP_TOKEN}"}
        response = requests.get(f"{GLPI_URL}/initSession", headers=headers)
        response.raise_for_status()
        return response.json().get("session_token"), None
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro ao iniciar sessão no GLPI: {e}"); return None, "Erro de comunicação ao tentar iniciar sessão no GLPI."
def _kill_session(session_token):
    if session_token:
        headers = {"Session-Token": session_token}
        requests.get(f"{GLPI_URL}/killSession", headers=headers)
GLPI_STATUS_MAP = {1: "Novo", 2: "Processando (atribuído)", 3: "Processando (planejado)", 4: "Pendente", 5: "Solucionado", 6: "Fechado"}
def get_glpi_ticket_status(ticket_id):
    session_token, error = _get_session_token()
    if error: return error
    try:
        headers = {"Session-Token": session_token}
        response = requests.get(f"{GLPI_URL}/Ticket/{ticket_id}", headers=headers)
        if response.status_code == 404: return f"O chamado de número *#{ticket_id}* não foi encontrado."
        response.raise_for_status()
        ticket_data = response.json()
        ticket_title = ticket_data.get("name", "Sem Título")
        status_id = ticket_data.get("status")
        status_text = GLPI_STATUS_MAP.get(status_id, f"Desconhecido (ID: {status_id})")
        return f"O chamado *#{ticket_id}*: '{ticket_title}' está com o status: *{status_text}*."
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro ao consultar chamado no GLPI: {e}")
        return "Ocorreu um erro ao tentar consultar o chamado. Verifique o número e tente novamente."
    finally: _kill_session(session_token)
def find_glpi_user_by_phone(whatsapp_number):
    cleaned_number = re.sub(r'\D', '', whatsapp_number)
    session_token, error = _get_session_token()
    if error: print(error); return None
    try:
        headers = {"Session-Token": session_token}
        params = {"searchText[phonenumber]": cleaned_number}
        response = requests.get(f"{GLPI_URL}/User", headers=headers, params=params)
        users = response.json()
        if users: return users[0].get("id")
        params = {"searchText[mobile]": cleaned_number}
        response = requests.get(f"{GLPI_URL}/User", headers=headers, params=params)
        users = response.json()
        if users: return users[0].get("id")
        return None
    except: return None
    finally: _kill_session(session_token)

# --- MUDANÇA AQUI ---
def _upload_document(session_token, ticket_id, media_data, filename="anexo_whatsapp"):
     try:
         headers = { "Session-Token": session_token }
         
         extension = media_data['content_type'].split('/')[-1]
         final_filename = f"{filename}.{extension}"

         # ## <-- TENTATIVA FINAL: Simplificação Radical do Manifesto ##
         # Removemos o parâmetro '_filename' para ver se o GLPI o infere do upload.
         manifest_json = f'{{"input": {{"itemtype": "Ticket", "items_id": {ticket_id}, "name": "{final_filename}"}}}}'
         
         # Voltamos a usar 'filename[0]' que é o padrão dos exemplos
         files = {
             'uploadManifest': (None, manifest_json, 'application/json'),
             'filename[0]': (final_filename, media_data['content'], media_data['content_type'])
         }
         # ## FIM DA ALTERAÇÃO ##
         
         response = requests.post(f"{GLPI_URL}/Document", headers=headers, files=files)
         response.raise_for_status()
         logging.info(f"Anexo associado ao ticket {ticket_id} com sucesso.")
         return True
     except Exception as e:
         logging.error(f"Erro ao fazer upload do documento para o GLPI: {e}")
         if hasattr(e, 'response') and e.response is not None: 
             logging.error(f"Resposta do servidor GLPI (upload): {e.response.text}")
         return False


def create_glpi_ticket(title, description, requester_user_id, media_data=None, requester_name=None):
    session_token, error = _get_session_token()
    if error: return error
    final_description = f"**Requisitante (informado via WhatsApp):** {requester_name}\n\n---\n\n{description}" if requester_name else description
    try:
        # (Lógica de criação do ticket não muda)
        ticket_data = { "input": { "name": title, "content": final_description, "_users_id_requester": requester_user_id, "itilcategories_id": 0 } }
        headers = {"Content-Type": "application/json", "Session-Token": session_token}
        response = requests.post(f"{GLPI_URL}/Ticket", headers=headers, json=ticket_data)
        response.raise_for_status()
        ticket_info = response.json()
        ticket_id = ticket_info.get("id")
        success_message = f"Obrigado, {requester_name.split(' ')[0]}. Seu chamado *#{ticket_id}* foi aberto com sucesso." if requester_name else f"Pronto! O chamado de número *#{ticket_id}* foi aberto com sucesso em seu nome."
        
        # --- MUDANÇA AQUI ---
        if media_data and ticket_id:
            upload_success = _upload_document(session_token, ticket_id, media_data)
            success_message += "\nO anexo foi enviado com sucesso." if upload_success else "\n*Atenção:* O chamado foi criado, mas houve uma falha ao enviar o anexo."
        # --- FIM DA MUDANÇA ---
            
        return success_message
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro ao criar chamado no GLPI: {e}"); return "Erro de comunicação ao tentar criar o chamado no GLPI."
    finally: _kill_session(session_token)