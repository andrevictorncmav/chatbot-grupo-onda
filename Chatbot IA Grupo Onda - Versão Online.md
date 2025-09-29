# Chatbot IA Grupo Onda - Versão Online

Sistema de chatbot inteligente para o Grupo Onda, otimizado para produção online com suporte a múltiplos usuários simultâneos.

## 🚀 Características

### Funcionalidades Principais
- **Upload de Documentos**: Suporte a PDF e CSV (até 16MB)
- **Processamento Inteligente**: Algoritmo TF-IDF para busca por similaridade
- **Chat com IA**: Integração com OpenAI GPT-3.5-turbo
- **Multi-usuário**: Suporte a múltiplos usuários simultâneos
- **Persistência**: Banco de dados PostgreSQL para armazenamento permanente
- **Google Drive**: Backup automático na nuvem
- **Interface Responsiva**: Funciona em desktop e mobile

### Tecnologias Utilizadas
- **Backend**: Flask (Python)
- **Banco de Dados**: PostgreSQL
- **IA**: OpenAI GPT-3.5-turbo
- **Armazenamento**: Google Drive API
- **Deploy**: Render (gratuito)
- **Frontend**: HTML5, CSS3, JavaScript

## 📋 Pré-requisitos

### Para Deploy no Render
- Conta no [Render](https://render.com)
- Conta no [OpenAI](https://platform.openai.com)
- Conta no [Google Cloud](https://console.cloud.google.com) (opcional)

### Para Desenvolvimento Local
- Python 3.11+
- PostgreSQL (ou SQLite para testes)

## 🛠️ Instalação e Deploy

### 1. Deploy Automático no Render

1. **Fork/Clone este repositório**
2. **Conecte ao Render**:
   - Acesse [Render Dashboard](https://dashboard.render.com)
   - Clique em "New" → "Web Service"
   - Conecte seu repositório GitHub

3. **Configure as Variáveis de Ambiente**:
   ```
   OPENAI_API_KEY=sk-proj-sua-chave-aqui
   FLASK_ENV=production
   SECRET_KEY=sua-chave-secreta-aqui
   ```

4. **Configure o Banco de Dados**:
   - No Render, crie um "PostgreSQL Database"
   - A variável `DATABASE_URL` será configurada automaticamente

5. **Deploy**:
   - O Render fará o deploy automaticamente
   - Acesse sua URL: `https://seu-app.onrender.com`

### 2. Desenvolvimento Local

```bash
# Clone o repositório
git clone <url-do-repositorio>
cd chatbot_online

# Instale as dependências
pip install -r requirements.txt

# Configure as variáveis de ambiente
export OPENAI_API_KEY="sk-proj-sua-chave-aqui"
export DATABASE_URL="sqlite:///local.db"  # Para desenvolvimento
export FLASK_ENV="development"

# Execute a aplicação
python app_online.py
```

## ⚙️ Configuração

### Variáveis de Ambiente

| Variável | Descrição | Obrigatória |
|----------|-----------|-------------|
| `OPENAI_API_KEY` | Chave da API OpenAI | ✅ |
| `DATABASE_URL` | URL do banco PostgreSQL | ✅ |
| `SECRET_KEY` | Chave secreta do Flask | ✅ |
| `GOOGLE_DRIVE_CREDENTIALS` | Credenciais do Google Drive | ❌ |
| `FLASK_ENV` | Ambiente (production/development) | ❌ |
| `PORT` | Porta do servidor (padrão: 5000) | ❌ |

### Google Drive (Opcional)

Para habilitar backup no Google Drive:

1. **Crie um projeto no Google Cloud Console**
2. **Ative a Google Drive API**
3. **Crie credenciais de Service Account**
4. **Configure a variável `GOOGLE_DRIVE_CREDENTIALS`** com o JSON das credenciais

## 📖 Como Usar

### 1. Acesso ao Sistema
- Acesse a URL do seu deploy
- A interface principal será carregada automaticamente

### 2. Upload de Documento
- Clique em "Selecionar Arquivo" ou arraste um arquivo
- Suporte: PDF e CSV (máximo 16MB)
- O sistema processará automaticamente

### 3. Chat com IA
- Após o upload, faça perguntas sobre o documento
- A IA responderá baseada no conteúdo processado
- Fontes consultadas são exibidas automaticamente

### 4. Histórico
- Acesse "/history" para ver documentos processados
- Carregue documentos anteriores com um clique
- Filtre e ordene por diferentes critérios

## 🏗️ Arquitetura

```
chatbot_online/
├── app_online.py              # Aplicação Flask principal
├── database_manager.py        # Gerenciador do PostgreSQL
├── google_drive_api.py        # Integração com Google Drive
├── document_processor_online.py # Processamento de documentos
├── requirements.txt           # Dependências Python
├── render.yaml               # Configuração do Render
├── templates/
│   ├── chat_online.html      # Interface principal
│   └── history_online.html   # Página de histórico
└── README.md                 # Este arquivo
```

### Fluxo de Dados

1. **Upload**: Usuário faz upload → Arquivo salvo temporariamente
2. **Processamento**: Texto extraído → Dividido em chunks → TF-IDF calculado
3. **Armazenamento**: Dados salvos no PostgreSQL + Google Drive (backup)
4. **Chat**: Query do usuário → Busca por similaridade → Resposta da IA
5. **Histórico**: Documentos listados → Carregamento sob demanda

## 🔧 Endpoints da API

### Principais Endpoints

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/` | GET | Interface principal |
| `/history` | GET | Página de histórico |
| `/api/upload` | POST | Upload de documentos |
| `/api/chat` | POST | Chat com IA |
| `/api/history` | GET | Listar documentos |
| `/api/load_document` | POST | Carregar documento específico |
| `/status` | GET | Status do sistema |
| `/health` | GET | Health check |

### Exemplo de Uso da API

```javascript
// Upload de documento
const formData = new FormData();
formData.append('file', fileInput.files[0]);

const response = await fetch('/api/upload', {
    method: 'POST',
    body: formData
});

// Chat com IA
const chatResponse = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: 'Sua pergunta aqui' })
});
```

## 📊 Monitoramento

### Health Check
- **URL**: `/health`
- **Verifica**: Banco de dados, OpenAI, Google Drive
- **Retorna**: Status HTTP 200 (saudável) ou 503 (degradado)

### Status Detalhado
- **URL**: `/status`
- **Informações**: Estatísticas completas do sistema
- **Uso**: Monitoramento e debugging

## 🔒 Segurança

### Medidas Implementadas
- **Validação de Arquivos**: Tipos e tamanhos permitidos
- **Sanitização**: Nomes de arquivos seguros
- **Sessões**: IDs únicos por usuário
- **Rate Limiting**: Prevenção de spam (implementar se necessário)
- **HTTPS**: Obrigatório em produção

### Recomendações
- Use chaves de API com permissões mínimas
- Configure firewall no banco de dados
- Monitore logs de acesso
- Implemente backup regular

## 🚨 Solução de Problemas

### Problemas Comuns

**1. Erro de Conexão com Banco**
```
Solução: Verifique a variável DATABASE_URL
```

**2. OpenAI não responde**
```
Solução: Verifique a chave OPENAI_API_KEY e créditos
```

**3. Upload falha**
```
Solução: Verifique tamanho (máx 16MB) e tipo do arquivo
```

**4. Google Drive não funciona**
```
Solução: Configuração opcional, sistema funciona sem
```

### Logs e Debug

```bash
# Ver logs no Render
render logs -s seu-servico-id

# Debug local
export FLASK_ENV=development
python app_online.py
```

## 📈 Performance

### Otimizações Implementadas
- **Cache de TF-IDF**: Evita recálculos desnecessários
- **Chunks otimizados**: Tamanho balanceado para performance
- **Conexões de banco**: Pool de conexões automático
- **Compressão**: Assets comprimidos automaticamente

### Limites Atuais
- **Arquivo**: 16MB máximo
- **Concurrent Users**: Limitado pelo plano do Render
- **Banco de dados**: 1GB no plano gratuito
- **OpenAI**: Limitado pelos créditos da conta

## 🔄 Atualizações

### Deploy Automático
- Push para branch principal → Deploy automático no Render
- Migrations de banco executadas automaticamente
- Zero downtime deployment

### Versionamento
- Use tags Git para releases
- Mantenha CHANGELOG.md atualizado
- Teste em ambiente de staging primeiro

## 🤝 Contribuição

### Como Contribuir
1. Fork o repositório
2. Crie uma branch para sua feature
3. Faça commit das mudanças
4. Abra um Pull Request

### Padrões de Código
- PEP 8 para Python
- Docstrings em funções importantes
- Testes unitários para novas features
- Comentários em português

## 📞 Suporte

### Contato
- **Email**: suporte@grupoonda.com.br
- **Issues**: Use o GitHub Issues
- **Documentação**: Este README

### Status do Sistema
- **Monitoramento**: `/health` endpoint
- **Logs**: Disponíveis no dashboard do Render
- **Métricas**: `/status` endpoint

---

**Desenvolvido para o Grupo Onda** 🌊  
*Sistema de Chatbot Inteligente - Versão Online 2025*
