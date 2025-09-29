"""
Gerenciador de Banco de Dados PostgreSQL para o Chatbot Online
Autor: Sistema Manus
Data: 2025
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.postgresql import JSON

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()

class Document(Base):
    """Modelo para documentos processados"""
    __tablename__ = 'documents'
    
    id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_type = Column(String(50), nullable=False)
    processed_at = Column(DateTime, default=datetime.utcnow)
    chunk_count = Column(Integer, default=0)
    google_drive_id = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    metadata = Column(JSON, nullable=True)

class DocumentChunk(Base):
    """Modelo para chunks de documentos"""
    __tablename__ = 'document_chunks'
    
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    tfidf_vector = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class ChatSession(Base):
    """Modelo para sessões de chat"""
    __tablename__ = 'chat_sessions'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String(255), unique=True, nullable=False)
    user_ip = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

class ChatMessage(Base):
    """Modelo para mensagens do chat"""
    __tablename__ = 'chat_messages'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String(255), nullable=False)
    message_type = Column(String(20), nullable=False)  # 'user' ou 'assistant'
    content = Column(Text, nullable=False)
    sources = Column(JSON, nullable=True)
    response_time = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class DatabaseManager:
    """Gerenciador principal do banco de dados"""
    
    def __init__(self, database_url: str = None):
        """
        Inicializa o gerenciador de banco de dados
        
        Args:
            database_url: URL de conexão com o banco (se None, usa variável de ambiente)
        """
        self.database_url = database_url or os.getenv('DATABASE_URL')
        if not self.database_url:
            # Fallback para SQLite local em desenvolvimento
            self.database_url = 'sqlite:///chatbot_local.db'
            logger.warning("DATABASE_URL não encontrada, usando SQLite local")
        
        # Ajustar URL para PostgreSQL no Render
        if self.database_url.startswith('postgres://'):
            self.database_url = self.database_url.replace('postgres://', 'postgresql://', 1)
        
        self.engine = create_engine(self.database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Criar tabelas
        self.create_tables()
    
    def create_tables(self):
        """Cria todas as tabelas no banco de dados"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Tabelas criadas com sucesso")
        except Exception as e:
            logger.error(f"Erro ao criar tabelas: {e}")
            raise
    
    def get_session(self) -> Session:
        """Retorna uma nova sessão do banco de dados"""
        return self.SessionLocal()
    
    def save_document(self, filename: str, file_path: str, file_size: int, 
                     file_type: str, chunk_count: int = 0, 
                     google_drive_id: str = None, metadata: dict = None) -> int:
        """
        Salva um documento no banco de dados
        
        Returns:
            ID do documento salvo
        """
        session = self.get_session()
        try:
            document = Document(
                filename=filename,
                original_filename=filename,
                file_path=file_path,
                file_size=file_size,
                file_type=file_type,
                chunk_count=chunk_count,
                google_drive_id=google_drive_id,
                metadata=metadata or {}
            )
            
            session.add(document)
            session.commit()
            
            doc_id = document.id
            logger.info(f"Documento salvo: {filename} (ID: {doc_id})")
            return doc_id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Erro ao salvar documento: {e}")
            raise
        finally:
            session.close()
    
    def save_chunks(self, document_id: int, chunks: List[str], tfidf_vectors: List[dict] = None):
        """
        Salva os chunks de um documento
        
        Args:
            document_id: ID do documento
            chunks: Lista de chunks de texto
            tfidf_vectors: Lista de vetores TF-IDF (opcional)
        """
        session = self.get_session()
        try:
            # Remover chunks existentes
            session.query(DocumentChunk).filter_by(document_id=document_id).delete()
            
            # Adicionar novos chunks
            for i, chunk in enumerate(chunks):
                tfidf_vector = tfidf_vectors[i] if tfidf_vectors and i < len(tfidf_vectors) else None
                
                chunk_obj = DocumentChunk(
                    document_id=document_id,
                    chunk_index=i,
                    content=chunk,
                    tfidf_vector=tfidf_vector
                )
                session.add(chunk_obj)
            
            # Atualizar contagem de chunks no documento
            document = session.query(Document).filter_by(id=document_id).first()
            if document:
                document.chunk_count = len(chunks)
            
            session.commit()
            logger.info(f"Salvos {len(chunks)} chunks para documento {document_id}")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Erro ao salvar chunks: {e}")
            raise
        finally:
            session.close()
    
    def get_document_chunks(self, document_id: int) -> List[Dict[str, Any]]:
        """
        Recupera todos os chunks de um documento
        
        Returns:
            Lista de dicionários com dados dos chunks
        """
        session = self.get_session()
        try:
            chunks = session.query(DocumentChunk).filter_by(
                document_id=document_id
            ).order_by(DocumentChunk.chunk_index).all()
            
            result = []
            for chunk in chunks:
                result.append({
                    'index': chunk.chunk_index,
                    'content': chunk.content,
                    'tfidf_vector': chunk.tfidf_vector
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao recuperar chunks: {e}")
            return []
        finally:
            session.close()
    
    def get_active_documents(self) -> List[Dict[str, Any]]:
        """
        Recupera todos os documentos ativos
        
        Returns:
            Lista de dicionários com dados dos documentos
        """
        session = self.get_session()
        try:
            documents = session.query(Document).filter_by(is_active=True).order_by(
                Document.processed_at.desc()
            ).all()
            
            result = []
            for doc in documents:
                result.append({
                    'id': doc.id,
                    'filename': doc.filename,
                    'file_path': doc.file_path,
                    'file_size': doc.file_size,
                    'file_type': doc.file_type,
                    'processed_at': doc.processed_at.isoformat(),
                    'chunk_count': doc.chunk_count,
                    'google_drive_id': doc.google_drive_id,
                    'metadata': doc.metadata
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao recuperar documentos: {e}")
            return []
        finally:
            session.close()
    
    def get_latest_document(self) -> Optional[Dict[str, Any]]:
        """
        Recupera o documento mais recente
        
        Returns:
            Dicionário com dados do documento ou None
        """
        session = self.get_session()
        try:
            document = session.query(Document).filter_by(is_active=True).order_by(
                Document.processed_at.desc()
            ).first()
            
            if not document:
                return None
            
            return {
                'id': document.id,
                'filename': document.filename,
                'file_path': document.file_path,
                'file_size': document.file_size,
                'file_type': document.file_type,
                'processed_at': document.processed_at.isoformat(),
                'chunk_count': document.chunk_count,
                'google_drive_id': document.google_drive_id,
                'metadata': document.metadata
            }
            
        except Exception as e:
            logger.error(f"Erro ao recuperar último documento: {e}")
            return None
        finally:
            session.close()
    
    def save_chat_message(self, session_id: str, message_type: str, content: str, 
                         sources: List[dict] = None, response_time: float = None):
        """
        Salva uma mensagem do chat
        
        Args:
            session_id: ID da sessão
            message_type: 'user' ou 'assistant'
            content: Conteúdo da mensagem
            sources: Fontes consultadas (para respostas da IA)
            response_time: Tempo de resposta em segundos
        """
        session = self.get_session()
        try:
            message = ChatMessage(
                session_id=session_id,
                message_type=message_type,
                content=content,
                sources=sources,
                response_time=response_time
            )
            
            session.add(message)
            session.commit()
            
        except Exception as e:
            session.rollback()
            logger.error(f"Erro ao salvar mensagem: {e}")
        finally:
            session.close()
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Recupera estatísticas do sistema
        
        Returns:
            Dicionário com estatísticas
        """
        session = self.get_session()
        try:
            # Contar documentos
            total_docs = session.query(Document).filter_by(is_active=True).count()
            
            # Contar chunks
            total_chunks = session.query(DocumentChunk).count()
            
            # Calcular tamanho total
            total_size = session.query(Document).filter_by(is_active=True).with_entities(
                func.sum(Document.file_size)
            ).scalar() or 0
            
            # Contar sessões ativas
            active_sessions = session.query(ChatSession).filter_by(is_active=True).count()
            
            # Contar mensagens
            total_messages = session.query(ChatMessage).count()
            
            return {
                'total_documents': total_docs,
                'total_chunks': total_chunks,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'active_sessions': active_sessions,
                'total_messages': total_messages,
                'database_status': 'online'
            }
            
        except Exception as e:
            logger.error(f"Erro ao recuperar estatísticas: {e}")
            return {
                'total_documents': 0,
                'total_chunks': 0,
                'total_size_mb': 0,
                'active_sessions': 0,
                'total_messages': 0,
                'database_status': 'error'
            }
        finally:
            session.close()
    
    def cleanup_old_sessions(self, days: int = 7):
        """
        Remove sessões antigas do banco de dados
        
        Args:
            days: Número de dias para considerar uma sessão como antiga
        """
        session = self.get_session()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Marcar sessões antigas como inativas
            session.query(ChatSession).filter(
                ChatSession.last_activity < cutoff_date
            ).update({'is_active': False})
            
            session.commit()
            logger.info(f"Limpeza de sessões antigas concluída")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Erro na limpeza de sessões: {e}")
        finally:
            session.close()

# Instância global do gerenciador
db_manager = None

def get_db_manager() -> DatabaseManager:
    """Retorna a instância global do gerenciador de banco"""
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager()
    return db_manager

def init_database():
    """Inicializa o banco de dados"""
    try:
        manager = get_db_manager()
        logger.info("Banco de dados inicializado com sucesso")
        return manager
    except Exception as e:
        logger.error(f"Erro ao inicializar banco de dados: {e}")
        raise
