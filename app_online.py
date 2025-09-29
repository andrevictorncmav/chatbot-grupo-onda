"""
Chatbot IA para Grupo Onda - Versão Online
Sistema de chat inteligente com base de conhecimento personalizada
"""

import os
import json
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session
import openai
from document_processor_online import DocumentProcessor
from database_manager import DatabaseManager
from google_drive_api import GoogleDriveManager

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicialização da aplicação Flask
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'chatbot-grupo-onda-fallback-key')

# Configuração da OpenAI via variável de ambiente
openai.api_key = os.getenv('OPENAI_API_KEY')

# Inicialização dos componentes
db_manager = DatabaseManager()
drive_manager = GoogleDriveManager()
doc_processor = DocumentProcessor()

# Variáveis globais para cache
documents_cache = {}
last_processed_doc = None

@app.route('/')
def index():
    """Página principal com interface de chat avançada"""
    return render_template('chat_online.html')

@app.route('/history')
def history():
    """Página de histórico de documentos"""
    return render_template('history_online.html')

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
        
        # Salvar no banco de dados
        doc_id = db_manager.save_document(
            filename=file.filename,
            content=chunks,
            metadata={'upload_time': datetime.now().isoformat()}
        )
        
        # Backup no Google Drive (opcional)
        try:
            drive_manager.upload_document(temp_path, file.filename)
        except Exception as e:
            logger.warning(f"Falha no backup Google Drive: {e}")
        
        # Atualizar cache
        global documents_cache, last_processed_doc
        documents_cache[doc_id] = {
            'filename': file.filename,
            'chunks': chunks,
            'processed_at': datetime.now().isoformat()
        }
        last_processed_doc = doc_id
        
        # Limpar arquivo temporário
        os.remove(temp_path)
        
        return jsonify({
            'success': True,
            'message': f'Documento processado com sucesso! {len(chunks)} chunks criados.',
            'doc_id': doc_id,
            'chunks_count': len(chunks),
            'filename': file.filename
        })
        
    except Exception as e:
        logger.error(f"Erro no upload: {e}")
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
        doc_data = documents_cache.get(doc_id) or db_manager.get_document(doc_id)
        
        if not doc_data:
            return jsonify({'error': 'Documento não encontrado'}), 404
        
        # Buscar chunks relevantes
        relevant_chunks = doc_processor.search_relevant_chunks(
            question, 
            doc_data['chunks'] if 'chunks' in doc_data else doc_data['content']
        )
        
        if not relevant_chunks:
            return jsonify({
                'answer': 'Não encontrei informações relevantes sobre sua pergunta no documento carregado.',
                'sources': []
            })
        
        # Preparar contexto para a IA
        context = "\n\n".join([chunk['text'] for chunk in relevant_chunks[:3]])
        
        # Gerar resposta com OpenAI
        try:
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
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@app.route('/api/search', methods=['POST'])
def search_documents():
    """Endpoint para busca sem IA (apenas TF-IDF)"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({'error': 'Query não pode estar vazia'}), 400
        
        if not last_processed_doc and not documents_cache:
            return jsonify({'results': [], 'message': 'Nenhum documento processado'})
        
        # Buscar no último documento processado
        doc_id = last_processed_doc or list(documents_cache.keys())[-1]
        doc_data = documents_cache.get(doc_id) or db_manager.get_document(doc_id)
        
        if not doc_data:
            return jsonify({'error': 'Documento não encontrado'}), 404
        
        # Buscar chunks relevantes
        relevant_chunks = doc_processor.search_relevant_chunks(
            query, 
            doc_data['chunks'] if 'chunks' in doc_data else doc_data['content']
        )
        
        results = [
            {
                'text': chunk['text'],
                'similarity': chunk.get('similarity', 0),
                'chunk_id': i
            }
            for i, chunk in enumerate(relevant_chunks[:5])
        ]
        
        return jsonify({
            'results': results,
            'total_found': len(relevant_chunks),
            'query': query,
            'document': doc_data.get('filename', 'Documento')
        })
        
    except Exception as e:
        logger.error(f"Erro na busca: {e}")
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@app.route('/api/status')
def status():
    """Endpoint de status do sistema"""
    try:
        # Verificar componentes
        openai_status = "Configurado" if openai.api_key else "Não configurado"
        db_status = "Conectado" if db_manager.test_connection() else "Desconectado"
        
        # Estatísticas
        total_docs = len(documents_cache)
        total_chunks = sum(len(doc.get('chunks', [])) for doc in documents_cache.values())
        
        return jsonify({
            'status': 'online',
            'openai': openai_status,
            'database': db_status,
            'documents_loaded': total_docs,
            'total_chunks': total_chunks,
            'last_document': documents_cache.get(last_processed_doc, {}).get('filename') if last_processed_doc else None,
            'timestamp': datetime.now().isoformat()
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
        
        # Documentos do banco (se não estiverem em cache)
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
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint não encontrado'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Erro interno do servidor'}), 500

if __name__ == '__main__':
    # Configuração para produção
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'
    
    logger.info(f"Iniciando aplicação na porta {port}")
    logger.info(f"Modo debug: {debug}")
    logger.info(f"OpenAI configurado: {'Sim' if openai.api_key else 'Não'}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
