"""
Processador de Documentos Online - Versão Otimizada para Produção
Autor: Sistema Manus
Data: 2025
"""

import os
import re
import math
import logging
from typing import List, Dict, Tuple, Any, Optional
from collections import Counter, defaultdict
import PyPDF2
import pandas as pd
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentProcessorOnline:
    """Processador de documentos otimizado para ambiente online"""
    
    def __init__(self):
        """Inicializa o processador de documentos"""
        self.documents = {}
        self.chunks = []
        self.tfidf_matrix = []
        self.vocabulary = {}
        self.idf_scores = {}
        self.document_stats = {
            'total_documents': 0,
            'total_chunks': 0,
            'total_words': 0,
            'vocabulary_size': 0,
            'last_processed': None
        }
        
        # Palavras de parada em português
        self.stop_words = {
            'a', 'ao', 'aos', 'as', 'à', 'às', 'ante', 'após', 'até', 'com', 'contra', 'de', 'desde',
            'em', 'entre', 'para', 'per', 'perante', 'por', 'sem', 'sob', 'sobre', 'trás', 'e', 'mas',
            'nem', 'ou', 'logo', 'pois', 'porém', 'contudo', 'todavia', 'entretanto', 'senão', 'que',
            'se', 'como', 'quando', 'onde', 'porque', 'porquê', 'qual', 'quais', 'quanto', 'quantos',
            'quanta', 'quantas', 'quem', 'o', 'os', 'a', 'as', 'um', 'uma', 'uns', 'umas', 'este',
            'esta', 'estes', 'estas', 'esse', 'essa', 'esses', 'essas', 'aquele', 'aquela', 'aqueles',
            'aquelas', 'isto', 'isso', 'aquilo', 'eu', 'tu', 'ele', 'ela', 'nós', 'vós', 'eles', 'elas',
            'me', 'mim', 'comigo', 'te', 'ti', 'contigo', 'se', 'si', 'consigo', 'nos', 'conosco',
            'vos', 'convosco', 'lhe', 'lhes', 'meu', 'minha', 'meus', 'minhas', 'teu', 'tua', 'teus',
            'tuas', 'seu', 'sua', 'seus', 'suas', 'nosso', 'nossa', 'nossos', 'nossas', 'vosso',
            'vossa', 'vossos', 'vossas', 'do', 'da', 'dos', 'das', 'no', 'na', 'nos', 'nas', 'pelo',
            'pela', 'pelos', 'pelas', 'num', 'numa', 'nuns', 'numas', 'dum', 'duma', 'duns', 'dumas',
            'ser', 'estar', 'ter', 'haver', 'ir', 'vir', 'dar', 'fazer', 'dizer', 'ver', 'saber',
            'poder', 'querer', 'ficar', 'parecer', 'deixar', 'passar', 'chegar', 'trazer', 'levar',
            'encontrar', 'sentir', 'continuar', 'começar', 'acabar', 'entrar', 'sair', 'voltar',
            'muito', 'mais', 'menos', 'bem', 'mal', 'melhor', 'pior', 'maior', 'menor', 'grande',
            'pequeno', 'novo', 'velho', 'primeiro', 'último', 'outro', 'mesmo', 'todo', 'cada',
            'algum', 'nenhum', 'qualquer', 'certo', 'tanto', 'quanto', 'pouco', 'bastante', 'demais',
            'já', 'ainda', 'sempre', 'nunca', 'hoje', 'ontem', 'amanhã', 'agora', 'depois', 'antes',
            'aqui', 'ali', 'lá', 'aí', 'cá', 'dentro', 'fora', 'cima', 'baixo', 'perto', 'longe',
            'sim', 'não', 'talvez', 'também', 'só', 'apenas', 'inclusive', 'até', 'mesmo'
        }
    
    def extract_text_from_pdf(self, file_path: str) -> str:
        """
        Extrai texto de um arquivo PDF
        
        Args:
            file_path: Caminho para o arquivo PDF
            
        Returns:
            Texto extraído do PDF
        """
        try:
            text = ""
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text() + "\n"
            
            logger.info(f"Texto extraído do PDF: {len(text)} caracteres")
            return text
            
        except Exception as e:
            logger.error(f"Erro ao extrair texto do PDF: {e}")
            return ""
    
    def extract_text_from_csv(self, file_path: str) -> str:
        """
        Extrai texto de um arquivo CSV
        
        Args:
            file_path: Caminho para o arquivo CSV
            
        Returns:
            Texto extraído do CSV
        """
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
            
            # Converter todas as colunas para string e concatenar
            text_parts = []
            for column in df.columns:
                text_parts.append(f"Coluna {column}:")
                text_parts.extend(df[column].astype(str).tolist())
            
            text = " ".join(text_parts)
            logger.info(f"Texto extraído do CSV: {len(text)} caracteres")
            return text
            
        except Exception as e:
            logger.error(f"Erro ao extrair texto do CSV: {e}")
            return ""
    
    def clean_text(self, text: str) -> str:
        """
        Limpa e normaliza o texto
        
        Args:
            text: Texto bruto
            
        Returns:
            Texto limpo e normalizado
        """
        # Remover caracteres especiais e normalizar espaços
        text = re.sub(r'[^\w\s\-\.\,\;\:\!\?\(\)]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        
        # Remover linhas muito curtas (provavelmente ruído)
        lines = text.split('\n')
        cleaned_lines = [line.strip() for line in lines if len(line.strip()) > 10]
        
        return '\n'.join(cleaned_lines).strip()
    
    def split_into_chunks(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """
        Divide o texto em chunks com sobreposição
        
        Args:
            text: Texto para dividir
            chunk_size: Tamanho máximo do chunk em palavras
            overlap: Número de palavras de sobreposição
            
        Returns:
            Lista de chunks de texto
        """
        words = text.split()
        chunks = []
        
        if len(words) <= chunk_size:
            return [text]
        
        start = 0
        while start < len(words):
            end = min(start + chunk_size, len(words))
            chunk = ' '.join(words[start:end])
            
            # Adicionar apenas chunks com conteúdo significativo
            if len(chunk.strip()) > 50:
                chunks.append(chunk.strip())
            
            # Mover para o próximo chunk com sobreposição
            start = end - overlap
            if start >= len(words):
                break
        
        return chunks
    
    def tokenize(self, text: str) -> List[str]:
        """
        Tokeniza o texto em palavras
        
        Args:
            text: Texto para tokenizar
            
        Returns:
            Lista de tokens (palavras)
        """
        # Converter para minúsculas e dividir em palavras
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Filtrar palavras muito curtas e stop words
        filtered_words = [
            word for word in words 
            if len(word) > 2 and word not in self.stop_words
        ]
        
        return filtered_words
    
    def calculate_tf(self, tokens: List[str]) -> Dict[str, float]:
        """
        Calcula a frequência de termos (TF)
        
        Args:
            tokens: Lista de tokens
            
        Returns:
            Dicionário com scores TF
        """
        tf_scores = {}
        total_tokens = len(tokens)
        
        if total_tokens == 0:
            return tf_scores
        
        token_counts = Counter(tokens)
        
        for token, count in token_counts.items():
            tf_scores[token] = count / total_tokens
        
        return tf_scores
    
    def calculate_idf(self, all_chunks_tokens: List[List[str]]) -> Dict[str, float]:
        """
        Calcula a frequência inversa de documentos (IDF)
        
        Args:
            all_chunks_tokens: Lista de listas de tokens de todos os chunks
            
        Returns:
            Dicionário com scores IDF
        """
        idf_scores = {}
        total_chunks = len(all_chunks_tokens)
        
        if total_chunks == 0:
            return idf_scores
        
        # Contar em quantos chunks cada termo aparece
        term_chunk_count = defaultdict(int)
        
        for chunk_tokens in all_chunks_tokens:
            unique_tokens = set(chunk_tokens)
            for token in unique_tokens:
                term_chunk_count[token] += 1
        
        # Calcular IDF
        for term, chunk_count in term_chunk_count.items():
            idf_scores[term] = math.log(total_chunks / chunk_count)
        
        return idf_scores
    
    def calculate_tfidf_matrix(self, chunks: List[str]) -> Tuple[List[Dict[str, float]], Dict[str, int]]:
        """
        Calcula a matriz TF-IDF para todos os chunks
        
        Args:
            chunks: Lista de chunks de texto
            
        Returns:
            Tupla com (matriz TF-IDF, vocabulário)
        """
        # Tokenizar todos os chunks
        all_chunks_tokens = [self.tokenize(chunk) for chunk in chunks]
        
        # Calcular IDF
        self.idf_scores = self.calculate_idf(all_chunks_tokens)
        
        # Construir vocabulário
        vocabulary = {}
        vocab_index = 0
        for chunk_tokens in all_chunks_tokens:
            for token in set(chunk_tokens):
                if token not in vocabulary:
                    vocabulary[token] = vocab_index
                    vocab_index += 1
        
        # Calcular TF-IDF para cada chunk
        tfidf_matrix = []
        for chunk_tokens in all_chunks_tokens:
            tf_scores = self.calculate_tf(chunk_tokens)
            tfidf_vector = {}
            
            for token, tf_score in tf_scores.items():
                if token in self.idf_scores:
                    tfidf_score = tf_score * self.idf_scores[token]
                    tfidf_vector[token] = tfidf_score
            
            tfidf_matrix.append(tfidf_vector)
        
        return tfidf_matrix, vocabulary
    
    def cosine_similarity(self, vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
        """
        Calcula a similaridade de cosseno entre dois vetores TF-IDF
        
        Args:
            vec1: Primeiro vetor TF-IDF
            vec2: Segundo vetor TF-IDF
            
        Returns:
            Score de similaridade (0-1)
        """
        # Encontrar termos em comum
        common_terms = set(vec1.keys()) & set(vec2.keys())
        
        if not common_terms:
            return 0.0
        
        # Calcular produto escalar
        dot_product = sum(vec1[term] * vec2[term] for term in common_terms)
        
        # Calcular normas
        norm1 = math.sqrt(sum(score ** 2 for score in vec1.values()))
        norm2 = math.sqrt(sum(score ** 2 for score in vec2.values()))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def process_document(self, file_path: str, filename: str) -> Dict[str, Any]:
        """
        Processa um documento completo
        
        Args:
            file_path: Caminho para o arquivo
            filename: Nome do arquivo
            
        Returns:
            Dicionário com resultados do processamento
        """
        try:
            logger.info(f"Processando documento: {filename}")
            
            # Extrair texto baseado no tipo de arquivo
            file_extension = os.path.splitext(filename)[1].lower()
            
            if file_extension == '.pdf':
                raw_text = self.extract_text_from_pdf(file_path)
            elif file_extension == '.csv':
                raw_text = self.extract_text_from_csv(file_path)
            else:
                raise ValueError(f"Tipo de arquivo não suportado: {file_extension}")
            
            if not raw_text.strip():
                raise ValueError("Nenhum texto foi extraído do documento")
            
            # Limpar texto
            cleaned_text = self.clean_text(raw_text)
            
            # Dividir em chunks
            chunks = self.split_into_chunks(cleaned_text)
            
            if not chunks:
                raise ValueError("Nenhum chunk foi gerado do documento")
            
            # Calcular TF-IDF
            tfidf_matrix, vocabulary = self.calculate_tfidf_matrix(chunks)
            
            # Salvar dados
            self.chunks = chunks
            self.tfidf_matrix = tfidf_matrix
            self.vocabulary = vocabulary
            
            # Atualizar estatísticas
            self.document_stats.update({
                'total_documents': 1,
                'total_chunks': len(chunks),
                'total_words': len(cleaned_text.split()),
                'vocabulary_size': len(vocabulary),
                'last_processed': datetime.now().isoformat()
            })
            
            # Salvar informações do documento
            self.documents[filename] = {
                'filename': filename,
                'file_path': file_path,
                'processed_at': datetime.now().isoformat(),
                'chunk_count': len(chunks),
                'file_size': os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                'file_type': file_extension
            }
            
            result = {
                'success': True,
                'filename': filename,
                'chunks_count': len(chunks),
                'vocabulary_size': len(vocabulary),
                'file_size': self.documents[filename]['file_size'],
                'processing_time': 'completed'
            }
            
            logger.info(f"Documento processado com sucesso: {len(chunks)} chunks criados")
            return result
            
        except Exception as e:
            logger.error(f"Erro ao processar documento {filename}: {e}")
            return {
                'success': False,
                'error': str(e),
                'filename': filename
            }
    
    def search_similar_chunks(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Busca chunks similares à consulta
        
        Args:
            query: Texto da consulta
            top_k: Número de chunks mais similares para retornar
            
        Returns:
            Lista de chunks com scores de similaridade
        """
        try:
            if not self.chunks or not self.tfidf_matrix:
                logger.warning("Nenhum documento processado para busca")
                return []
            
            # Tokenizar query
            query_tokens = self.tokenize(query)
            
            if not query_tokens:
                logger.warning("Query vazia após tokenização")
                return []
            
            # Calcular TF-IDF da query
            query_tf = self.calculate_tf(query_tokens)
            query_tfidf = {}
            
            for token, tf_score in query_tf.items():
                if token in self.idf_scores:
                    query_tfidf[token] = tf_score * self.idf_scores[token]
            
            if not query_tfidf:
                logger.warning("Query não possui termos conhecidos")
                return []
            
            # Calcular similaridade com todos os chunks
            similarities = []
            for i, chunk_tfidf in enumerate(self.tfidf_matrix):
                similarity = self.cosine_similarity(query_tfidf, chunk_tfidf)
                
                if similarity > 0:
                    similarities.append({
                        'chunk_index': i,
                        'content': self.chunks[i],
                        'similarity': similarity
                    })
            
            # Ordenar por similaridade e retornar top_k
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            
            result = similarities[:top_k]
            logger.info(f"Busca realizada: {len(result)} chunks encontrados")
            
            return result
            
        except Exception as e:
            logger.error(f"Erro na busca por similaridade: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Retorna estatísticas do processador
        
        Returns:
            Dicionário com estatísticas
        """
        return {
            'document_stats': self.document_stats.copy(),
            'chunks_loaded': len(self.chunks),
            'vocabulary_size': len(self.vocabulary),
            'tfidf_matrix_size': len(self.tfidf_matrix),
            'status': 'active' if self.chunks else 'empty'
        }
    
    def export_data(self) -> Dict[str, Any]:
        """
        Exporta todos os dados processados
        
        Returns:
            Dicionário com todos os dados
        """
        return {
            'documents': self.documents,
            'chunks': self.chunks,
            'tfidf_matrix': self.tfidf_matrix,
            'vocabulary': self.vocabulary,
            'idf_scores': self.idf_scores,
            'document_stats': self.document_stats,
            'exported_at': datetime.now().isoformat()
        }
    
    def import_data(self, data: Dict[str, Any]) -> bool:
        """
        Importa dados processados
        
        Args:
            data: Dicionário com dados para importar
            
        Returns:
            True se sucesso, False se falhar
        """
        try:
            self.documents = data.get('documents', {})
            self.chunks = data.get('chunks', [])
            self.tfidf_matrix = data.get('tfidf_matrix', [])
            self.vocabulary = data.get('vocabulary', {})
            self.idf_scores = data.get('idf_scores', {})
            self.document_stats = data.get('document_stats', {
                'total_documents': 0,
                'total_chunks': 0,
                'total_words': 0,
                'vocabulary_size': 0,
                'last_processed': None
            })
            
            logger.info(f"Dados importados: {len(self.chunks)} chunks carregados")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao importar dados: {e}")
            return False
    
    def clear_data(self):
        """Limpa todos os dados processados"""
        self.documents = {}
        self.chunks = []
        self.tfidf_matrix = []
        self.vocabulary = {}
        self.idf_scores = {}
        self.document_stats = {
            'total_documents': 0,
            'total_chunks': 0,
            'total_words': 0,
            'vocabulary_size': 0,
            'last_processed': None
        }
        logger.info("Dados do processador limpos")

# Instância global do processador
document_processor = None

def get_document_processor() -> DocumentProcessorOnline:
    """Retorna a instância global do processador de documentos"""
    global document_processor
    if document_processor is None:
        document_processor = DocumentProcessorOnline()
    return document_processor
