import os
import requests
from dotenv import load_dotenv

# Carrega as variáveis do seu arquivo .env
load_dotenv()
GLPI_URL = os.getenv("GLPI_URL")
GLPI_APP_TOKEN = os.getenv("GLPI_APP_TOKEN")

# --- DADOS PARA O TESTE ---
# !! IMPORTANTE: Substitua '123' pelo ID de um usuário requisitante válido do seu GLPI !!
TEST_REQUESTER_USER_ID = 2
TEST_TICKET_TITLE = "Teste de API - Upload de Documento"
TEST_TICKET_DESCRIPTION = "Este é um chamado de teste gerado por um script para depurar o anexo de arquivos."
TEST_IMAGE_PATH = "test.jpg"
# -------------------------

def run_test():
    """Executa o teste completo de criação e anexo de chamado no GLPI."""
    
    session_token = None
    ticket_id = None

    print("--- INICIANDO TESTE DE UPLOAD PARA O GLPI ---")

    # 1. Iniciar Sessão
    print("\n[PASSO 1/3] Tentando iniciar sessão no GLPI...")
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"user_token {GLPI_APP_TOKEN}"
        }
        response = requests.get(f"{GLPI_URL}/initSession", headers=headers)
        response.raise_for_status()
        session_token = response.json().get("session_token")
        print(f"SUCESSO! Session-Token obtido: {session_token[:10]}...")
    except requests.exceptions.RequestException as e:
        print(f"!!! ERRO ao iniciar sessão: {e}")
        if e.response is not None:
            print(f"Resposta do servidor: {e.response.text}")
        return

    # 2. Criar o Chamado
    print("\n[PASSO 2/3] Tentando criar um chamado de teste...")
    try:
        ticket_data = {"input": {"name": TEST_TICKET_TITLE, "content": TEST_TICKET_DESCRIPTION, "_users_id_requester": TEST_REQUESTER_USER_ID}}
        headers = {"Content-Type": "application/json", "Session-Token": session_token}
        response = requests.post(f"{GLPI_URL}/Ticket", headers=headers, json=ticket_data)
        response.raise_for_status()
        ticket_id = response.json().get("id")
        print(f"SUCESSO! Chamado #{ticket_id} criado.")
    except requests.exceptions.RequestException as e:
        print(f"!!! ERRO ao criar o chamado: {e}")
        if e.response is not None:
            print(f"Resposta do servidor: {e.response.text}")
        # Encerra a sessão mesmo se a criação do ticket falhar
        requests.get(f"{GLPI_URL}/killSession", headers={"Session-Token": session_token})
        return
    # [PASSO 3/3] Anexar o Documento
    print(f"\n[PASSO 3/3] Tentando anexar o arquivo '{TEST_IMAGE_PATH}' ao chamado #{ticket_id}...")
    try:
        with open(TEST_IMAGE_PATH, 'rb') as image_file:
            image_data = image_file.read()

        headers = { "Session-Token": session_token }
        
        manifest_json = f'{{"input": {{"itemtype": "Ticket", "items_id": {ticket_id}, "name": "{TEST_IMAGE_PATH}", "_filename": ["{TEST_IMAGE_PATH}"]}}}}'
        
        # ## <-- A SOLUÇÃO DEFINITIVA ESTÁ AQUI ##
        # Adicionamos 'application/json' como o Content-Type para o campo uploadManifest,
        # exatamente como a nova documentação mostrou.
        files = {
            'uploadManifest': (None, manifest_json, 'application/json'),
            'filename[0]': (TEST_IMAGE_PATH, image_data, 'image/jpeg')
        }
        
        response = requests.post(f"{GLPI_URL}/Document", headers=headers, files=files)
        # ## FIM DA CORREÇÃO ##
        
        response.raise_for_status()
        
        print("🎉 SUCESSO! Resposta da API de Upload foi recebida sem erros.")
        print("Resposta do servidor:", response.json())
        print(f"\n>>> POR FAVOR, VERIFIQUE AGORA O CHAMADO #{ticket_id} no GLPI para confirmar se o anexo apareceu na aba 'Documentos'.")

    except FileNotFoundError:
        print(f"!!! ERRO: Arquivo de teste '{TEST_IMAGE_PATH}' não encontrado.")
    except requests.exceptions.RequestException as e:
        print(f"!!! ERRO CRÍTICO ao fazer upload: {e}")
        if e.response is not None:
            print(f"Código de Status: {e.response.status_code}")
            print(f"Resposta do servidor (UPLOAD): {e.response.text}")
    finally:
        if session_token:
            print("\nEncerrando sessão GLPI...")
            requests.get(f"{GLPI_URL}/killSession", headers={"Session-Token": session_token})
            print("Sessão encerrada.")

if __name__ == "__main__":
    run_test()
