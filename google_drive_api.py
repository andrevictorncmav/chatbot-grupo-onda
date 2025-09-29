"""
Gerenciador da Google Drive API para o Chatbot Online
Autor: Sistema Manus
Data: 2025
"""

import os
import json
import logging
import tempfile
from typing import List, Dict, Optional, Any, BinaryIO
from datetime import datetime
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError
import io

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Escopos necessários para o Google Drive
SCOPES = ['https://www.googleapis.com/auth/drive.file']

class GoogleDriveManager:
    """Gerenciador para operações com Google Drive API"""
    
    def __init__(self, credentials_json: str = None):
        """
        Inicializa o gerenciador do Google Drive
        
        Args:
            credentials_json: JSON com credenciais do Google (se None, usa variável de ambiente)
        """
        self.credentials_json = credentials_json or os.getenv('GOOGLE_DRIVE_CREDENTIALS')
        self.service = None
        self.folder_id = None
        self._authenticate()
    
    def _authenticate(self):
        """Autentica com a API do Google Drive"""
        try:
            if not self.credentials_json:
                logger.warning("Credenciais do Google Drive não encontradas")
                return False
            
            # Parse das credenciais
            if isinstance(self.credentials_json, str):
                try:
                    creds_data = json.loads(self.credentials_json)
                except json.JSONDecodeError:
                    logger.error("Formato inválido das credenciais do Google Drive")
                    return False
            else:
                creds_data = self.credentials_json
            
            # Criar credenciais
            creds = None
            
            # Verificar se existem credenciais salvas
            token_path = '/tmp/token.json'
            if os.path.exists(token_path):
                creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            
            # Se não há credenciais válidas, fazer o fluxo de autorização
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    # Para produção, usar service account ao invés de OAuth
                    # Este é um exemplo simplificado
                    logger.error("Credenciais do Google Drive expiradas ou inválidas")
                    return False
                
                # Salvar credenciais para próxima execução
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
            
            # Construir serviço
            self.service = build('drive', 'v3', credentials=creds)
            
            # Criar/encontrar pasta do projeto
            self._setup_project_folder()
            
            logger.info("Autenticação com Google Drive realizada com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro na autenticação com Google Drive: {e}")
            return False
    
    def _setup_project_folder(self):
        """Cria ou encontra a pasta do projeto no Google Drive"""
        try:
            if not self.service:
                return
            
            folder_name = "Chatbot Grupo Onda"
            
            # Procurar pasta existente
            results = self.service.files().list(
                q=f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'",
                fields="files(id, name)"
            ).execute()
            
            folders = results.get('files', [])
            
            if folders:
                self.folder_id = folders[0]['id']
                logger.info(f"Pasta do projeto encontrada: {self.folder_id}")
            else:
                # Criar nova pasta
                folder_metadata = {
                    'name': folder_name,
                    'mimeType': 'application/vnd.google-apps.folder'
                }
                
                folder = self.service.files().create(
                    body=folder_metadata,
                    fields='id'
                ).execute()
                
                self.folder_id = folder.get('id')
                logger.info(f"Nova pasta criada: {self.folder_id}")
                
        except Exception as e:
            logger.error(f"Erro ao configurar pasta do projeto: {e}")
    
    def is_available(self) -> bool:
        """Verifica se o Google Drive está disponível"""
        return self.service is not None and self.folder_id is not None
    
    def upload_file(self, file_path: str, filename: str = None, 
                   description: str = None) -> Optional[str]:
        """
        Faz upload de um arquivo para o Google Drive
        
        Args:
            file_path: Caminho do arquivo local
            filename: Nome do arquivo no Drive (se None, usa o nome original)
            description: Descrição do arquivo
            
        Returns:
            ID do arquivo no Google Drive ou None se falhar
        """
        try:
            if not self.is_available():
                logger.warning("Google Drive não disponível para upload")
                return None
            
            if not os.path.exists(file_path):
                logger.error(f"Arquivo não encontrado: {file_path}")
                return None
            
            # Preparar metadados
            file_metadata = {
                'name': filename or os.path.basename(file_path),
                'parents': [self.folder_id]
            }
            
            if description:
                file_metadata['description'] = description
            
            # Preparar mídia
            media = MediaFileUpload(file_path, resumable=True)
            
            # Fazer upload
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            file_id = file.get('id')
            logger.info(f"Arquivo enviado para Google Drive: {filename} (ID: {file_id})")
            return file_id
            
        except Exception as e:
            logger.error(f"Erro no upload para Google Drive: {e}")
            return None
    
    def download_file(self, file_id: str, local_path: str) -> bool:
        """
        Baixa um arquivo do Google Drive
        
        Args:
            file_id: ID do arquivo no Google Drive
            local_path: Caminho local para salvar o arquivo
            
        Returns:
            True se sucesso, False se falhar
        """
        try:
            if not self.is_available():
                logger.warning("Google Drive não disponível para download")
                return False
            
            # Fazer download
            request = self.service.files().get_media(fileId=file_id)
            
            # Criar diretório se não existir
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            with open(local_path, 'wb') as fh:
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
            
            logger.info(f"Arquivo baixado do Google Drive: {local_path}")
            return True
            
        except Exception as e:
            logger.error(f"Erro no download do Google Drive: {e}")
            return False
    
    def save_json_data(self, data: dict, filename: str) -> Optional[str]:
        """
        Salva dados JSON no Google Drive
        
        Args:
            data: Dados para salvar
            filename: Nome do arquivo
            
        Returns:
            ID do arquivo no Google Drive ou None se falhar
        """
        try:
            if not self.is_available():
                logger.warning("Google Drive não disponível para salvar JSON")
                return None
            
            # Criar arquivo temporário
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                json.dump(data, temp_file, indent=2, ensure_ascii=False)
                temp_path = temp_file.name
            
            try:
                # Fazer upload
                file_id = self.upload_file(
                    temp_path, 
                    filename,
                    f"Dados processados em {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                return file_id
                
            finally:
                # Remover arquivo temporário
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except Exception as e:
            logger.error(f"Erro ao salvar JSON no Google Drive: {e}")
            return None
    
    def load_json_data(self, file_id: str) -> Optional[dict]:
        """
        Carrega dados JSON do Google Drive
        
        Args:
            file_id: ID do arquivo no Google Drive
            
        Returns:
            Dicionário com os dados ou None se falhar
        """
        try:
            if not self.is_available():
                logger.warning("Google Drive não disponível para carregar JSON")
                return None
            
            # Criar arquivo temporário
            with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as temp_file:
                temp_path = temp_file.name
            
            try:
                # Baixar arquivo
                if self.download_file(file_id, temp_path):
                    with open(temp_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    return data
                else:
                    return None
                    
            finally:
                # Remover arquivo temporário
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except Exception as e:
            logger.error(f"Erro ao carregar JSON do Google Drive: {e}")
            return None
    
    def list_files(self, file_type: str = None) -> List[Dict[str, Any]]:
        """
        Lista arquivos na pasta do projeto
        
        Args:
            file_type: Filtrar por tipo de arquivo (ex: 'pdf', 'json')
            
        Returns:
            Lista de dicionários com informações dos arquivos
        """
        try:
            if not self.is_available():
                logger.warning("Google Drive não disponível para listar arquivos")
                return []
            
            # Construir query
            query = f"'{self.folder_id}' in parents and trashed=false"
            if file_type:
                if file_type == 'pdf':
                    query += " and mimeType='application/pdf'"
                elif file_type == 'json':
                    query += " and mimeType='application/json'"
            
            # Listar arquivos
            results = self.service.files().list(
                q=query,
                fields="files(id, name, size, createdTime, modifiedTime, mimeType)",
                orderBy="modifiedTime desc"
            ).execute()
            
            files = results.get('files', [])
            
            # Formatar resultados
            formatted_files = []
            for file in files:
                formatted_files.append({
                    'id': file['id'],
                    'name': file['name'],
                    'size': int(file.get('size', 0)),
                    'created_at': file['createdTime'],
                    'modified_at': file['modifiedTime'],
                    'mime_type': file['mimeType']
                })
            
            return formatted_files
            
        except Exception as e:
            logger.error(f"Erro ao listar arquivos do Google Drive: {e}")
            return []
    
    def delete_file(self, file_id: str) -> bool:
        """
        Remove um arquivo do Google Drive
        
        Args:
            file_id: ID do arquivo no Google Drive
            
        Returns:
            True se sucesso, False se falhar
        """
        try:
            if not self.is_available():
                logger.warning("Google Drive não disponível para deletar arquivo")
                return False
            
            self.service.files().delete(fileId=file_id).execute()
            logger.info(f"Arquivo removido do Google Drive: {file_id}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao deletar arquivo do Google Drive: {e}")
            return False
    
    def get_storage_info(self) -> Dict[str, Any]:
        """
        Obtém informações sobre o armazenamento
        
        Returns:
            Dicionário com informações de armazenamento
        """
        try:
            if not self.is_available():
                return {
                    'status': 'offline',
                    'total_files': 0,
                    'total_size_mb': 0
                }
            
            # Listar todos os arquivos
            files = self.list_files()
            
            total_size = sum(file.get('size', 0) for file in files)
            
            return {
                'status': 'online',
                'total_files': len(files),
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'folder_id': self.folder_id
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter informações de armazenamento: {e}")
            return {
                'status': 'error',
                'total_files': 0,
                'total_size_mb': 0
            }

# Instância global do gerenciador
drive_manager = None

def get_drive_manager() -> GoogleDriveManager:
    """Retorna a instância global do gerenciador do Google Drive"""
    global drive_manager
    if drive_manager is None:
        drive_manager = GoogleDriveManager()
    return drive_manager

def init_google_drive():
    """Inicializa o Google Drive"""
    try:
        manager = get_drive_manager()
        if manager.is_available():
            logger.info("Google Drive inicializado com sucesso")
        else:
            logger.warning("Google Drive não disponível")
        return manager
    except Exception as e:
        logger.error(f"Erro ao inicializar Google Drive: {e}")
        return GoogleDriveManager()  # Retorna instância sem autenticação
