"""
Chatbot IA para Grupo Onda - Versão de Produção
Sistema completo com todas as funcionalidades otimizado para Render
"""

import os
import json
import logging
import traceback
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session
import openai

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicialização da aplicação Flask
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'chatbot-grupo-onda-fallback-key')

# Configuração da OpenAI via variável de ambiente
openai.api_key = os.getenv('OPENAI_API_KEY')

# Importações condicionais para evitar erros de dependência
try:
    from document_processor_production import DocumentProcessor
    doc_processor = DocumentProcessor()
    logger.info("DocumentProcessor carregado com sucesso")
except ImportError as e:
    logger.warning(f"DocumentProcessor não disponível: {e}")
    doc_processor = None

try:
    from database_manager_production import DatabaseManager
    db_manager = DatabaseManager()
    logger.info("DatabaseManager carregado com sucesso")
except ImportError as e:
    logger.warning(f"DatabaseManager não disponível: {e}")
    db_manager = None

try:
    from google_drive_api_production import GoogleDriveManager
    drive_manager = GoogleDriveManager()
    logger.info("GoogleDriveManager carregado com sucesso")
except ImportError as e:
    logger.warning(f"GoogleDriveManager não disponível: {e}")
    drive_manager = None

# Cache em memória como fallback
documents_cache = {}
last_processed_doc = None

# Processador de documentos simples como fallback
class SimpleDocumentProcessor:
    def __init__(self):
        self.documents = {}
    
    def process_document(self, file_path):
        """Processamento básico de documentos"""
        try:
            import PyPDF2
            
            if file_path.endswith('.pdf'):
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text() + "\n"
                
                # Dividir em chunks
                chunks = self._split_text(text)
                return [{'text': chunk, 'metadata': {}} for chunk in chunks]
            
            elif file_path.endswith('.txt'):
                with open(file_path, 'r', encoding='utf-8') as file:
                    text = file.read()
                chunks = self._split_text(text)
                return [{'text': chunk, 'metadata': {}} for chunk in chunks]
            
            return []
            
        except Exception as e:
            logger.error(f"Erro no processamento simples: {e}")
            return []
    
    def _split_text(self, text, chunk_size=1000):
        """Dividir texto em chunks"""
        words = text.split()
        chunks = []
        current_chunk = []
        current_size = 0
        
        for word in words:
            current_chunk.append(word)
            current_size += len(word) + 1
            
            if current_size >= chunk_size:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_size = 0
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks
    
    def search_relevant_chunks(self, query, chunks):
        """Busca simples por palavras-chave"""
        if not chunks or not query:
            return []
        
        query_words = query.lower().split()
        scored_chunks = []
        
        for chunk in chunks:
            chunk_text = chunk.get('text', '') if isinstance(chunk, dict) else str(chunk)
            chunk_lower = chunk_text.lower()
            score = 0
            
            for word in query_words:
                if word in chunk_lower:
                    score += chunk_lower.count(word)
            
            if score > 0:
                scored_chunks.append({
                    'text': chunk_text,
                    'similarity': score / len(query_words),
                    'metadata': chunk.get('metadata', {}) if isinstance(chunk, dict) else {}
                })
        
        scored_chunks.sort(key=lambda x: x['similarity'], reverse=True)
        return scored_chunks[:5]

# Usar processador simples como fallback
if not doc_processor:
    doc_processor = SimpleDocumentProcessor()
    logger.info("Usando SimpleDocumentProcessor como fallback")

@app.route('/')
def index():
    """Página principal com interface de chat avançada"""
    return render_template('chat_production.html')

@app.route('/history')
def history():
    """Página de histórico de documentos"""
    return render_template('history_production.html')

@app.route('/api/upload', methods=['POST'])
def upload_document():
    """Endpoint para upload e processamento de documentos"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Nenhum arquivo enviado'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Nome de arquivo inválido'}), 400
        
        # Validação de tipo de arquivo
        allowed_extensions = {'.pdf', '.csv', '.txt'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        if file_ext not in allowed_extensions:
            return jsonify({'error': f'Tipo de arquivo não suportado: {file_ext}'}), 400
        
        # Salvar arquivo temporariamente
        temp_path = f"/tmp/{file.filename}"
        file.save(temp_path)
        
        # Processar documento
        logger.info(f"Processando documento: {file.filename}")
        chunks = doc_processor.process_document(temp_path)
        
        if not chunks:
            return jsonify({'error': 'Não foi possível extrair conteúdo do documento'}), 400
        
        # Salvar no banco de dados (se disponível)
        doc_id = None
        if db_manager:
            try:
                doc_id = db_manager.save_document(
                    filename=file.filename,
                    content=chunks,
                    metadata={'upload_time': datetime.now().isoformat()}
                )
                logger.info(f"Documento salvo no banco: {doc_id}")
            except Exception as e:
                logger.warning(f"Falha ao salvar no banco: {e}")
        
        # Backup no Google Drive (se disponível)
        if drive_manager:
            try:
                drive_manager.upload_document(temp_path, file.filename)
                logger.info(f"Backup no Google Drive realizado")
            except Exception as e:
                logger.warning(f"Falha no backup Google Drive: {e}")
        
        # Atualizar cache
        global documents_cache, last_processed_doc
        if not doc_id:
            doc_id = f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        documents_cache[doc_id] = {
            'filename': file.filename,
            'chunks': chunks,
            'processed_at': datetime.now().isoformat()
        }
        last_processed_doc = doc_id
        
        # Limpar arquivo temporário
        try:
            os.remove(temp_path)
        except:
            pass
        
        return jsonify({
            'success': True,
            'message': f'Documento processado com sucesso! {len(chunks)} chunks criados.',
            'doc_id': doc_id,
            'chunks_count': len(chunks),
            'filename': file.filename
        })
        
    except Exception as e:
        logger.error(f"Erro no upload: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    """Endpoint principal para chat com IA"""
    try:
        data = request.get_json()
        question = data.get('question', '').strip()
        
        if not question:
            return jsonify({'error': 'Pergunta não pode estar vazia'}), 400
        
        # Verificar se há documentos processados
        if not last_processed_doc and not documents_cache:
            return jsonify({
                'error': 'Nenhum documento foi processado ainda. Faça upload de um documento primeiro.'
            }), 400
        
        # Buscar contexto relevante
        doc_id = last_processed_doc or list(documents_cache.keys())[-1]
        doc_data = documents_cache.get(doc_id)
        
        if not doc_data and db_manager:
            try:
                doc_data = db_manager.get_document(doc_id)
            except Exception as e:
                logger.warning(f"Erro ao buscar documento no banco: {e}")
        
        if not doc_data:
            return jsonify({'error': 'Documento não encontrado'}), 404
        
        # Buscar chunks relevantes
        chunks = doc_data.get('chunks', [])
        if 'content' in doc_data:
            chunks = doc_data['content']
        
        relevant_chunks = doc_processor.search_relevant_chunks(question, chunks)
        
        if not relevant_chunks:
            return jsonify({
                'answer': 'Não encontrei informações relevantes sobre sua pergunta no documento carregado.',
                'sources': []
            })
        
        # Preparar contexto para a IA
        context = "\n\n".join([chunk['text'] for chunk in relevant_chunks[:3]])
        
        # Gerar resposta com OpenAI
        try:
            if not openai.api_key:
                return jsonify({'error': 'OpenAI não configurada'}), 500
            
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "Você é um assistente inteligente especializado em responder perguntas baseadas em documentos fornecidos. Responda de forma clara, concisa e sempre baseada no contexto fornecido. Se a informação não estiver no contexto, diga que não encontrou a informação no documento."
                    },
                    {
                        "role": "user",
                        "content": f"Contexto do documento:\n{context}\n\nPergunta: {question}\n\nResponda baseado apenas no contexto fornecido:"
                    }
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            answer = response.choices[0].message.content.strip()
            
            # Preparar fontes
            sources = [
                {
                    'text': chunk['text'][:200] + '...' if len(chunk['text']) > 200 else chunk['text'],
                    'similarity': chunk.get('similarity', 0),
                    'chunk_id': i
                }
                for i, chunk in enumerate(relevant_chunks[:3])
            ]
            
            return jsonify({
                'answer': answer,
                'sources': sources,
                'document': doc_data.get('filename', 'Documento'),
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Erro na OpenAI: {e}")
            return jsonify({'error': f'Erro na geração da resposta: {str(e)}'}), 500
        
    except Exception as e:
        logger.error(f"Erro no chat: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@app.route('/api/status')
def status():
    """Endpoint de status do sistema"""
    try:
        openai_status = "Configurado" if openai.api_key else "Não configurado"
        db_status = "Conectado" if db_manager and db_manager.test_connection() else "Cache local"
        drive_status = "Disponível" if drive_manager else "Não disponível"
        
        total_docs = len(documents_cache)
        total_chunks = sum(len(doc.get('chunks', [])) for doc in documents_cache.values())
        
        return jsonify({
            'status': 'online',
            'openai': openai_status,
            'database': db_status,
            'google_drive': drive_status,
            'documents_loaded': total_docs,
            'total_chunks': total_chunks,
            'last_document': documents_cache.get(last_processed_doc, {}).get('filename') if last_processed_doc else None,
            'timestamp': datetime.now().isoformat(),
            'components': {
                'doc_processor': type(doc_processor).__name__,
                'db_manager': type(db_manager).__name__ if db_manager else 'None',
                'drive_manager': type(drive_manager).__name__ if drive_manager else 'None'
            }
        })
        
    except Exception as e:
        logger.error(f"Erro no status: {e}")
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@app.route('/api/documents')
def list_documents():
    """Listar documentos processados"""
    try:
        documents = []
        
        # Documentos em cache
        for doc_id, doc_data in documents_cache.items():
            documents.append({
                'id': doc_id,
                'filename': doc_data.get('filename', 'Desconhecido'),
                'chunks_count': len(doc_data.get('chunks', [])),
                'processed_at': doc_data.get('processed_at'),
                'source': 'cache'
            })
        
        # Documentos do banco (se disponível)
        if db_manager:
            try:
                db_docs = db_manager.list_documents()
                for doc in db_docs:
                    if doc['id'] not in documents_cache:
                        documents.append({
                            'id': doc['id'],
                            'filename': doc.get('filename', 'Desconhecido'),
                            'chunks_count': len(doc.get('content', [])),
                            'processed_at': doc.get('created_at'),
                            'source': 'database'
                        })
            except Exception as e:
                logger.warning(f"Erro ao listar documentos do banco: {e}")
        
        return jsonify({
            'documents': documents,
            'total': len(documents)
        })
        
    except Exception as e:
        logger.error(f"Erro ao listar documentos: {e}")
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@app.route('/healthz')
def health_check():
    """Health check para o Render"""
    return jsonify({
        'status': 'healthy', 
        'timestamp': datetime.now().isoformat(),
        'openai_configured': bool(openai.api_key)
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint não encontrado'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Erro 500: {error}")
    return jsonify({'error': 'Erro interno do servidor'}), 500

if __name__ == '__main__':
    # Configuração para produção
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'
    
    logger.info(f"Iniciando aplicação na porta {port}")
    logger.info(f"Modo debug: {debug}")
    logger.info(f"OpenAI configurado: {'Sim' if openai.api_key else 'Não'}")
    logger.info(f"Componentes carregados:")
    logger.info(f"  - DocumentProcessor: {type(doc_processor).__name__}")
    logger.info(f"  - DatabaseManager: {type(db_manager).__name__ if db_manager else 'None'}")
    logger.info(f"  - GoogleDriveManager: {type(drive_manager).__name__ if drive_manager else 'None'}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
