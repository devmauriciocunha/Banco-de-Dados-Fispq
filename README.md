# 🧪 Sistema de Extração e Gerenciamento de FISPQs

Este sistema extrai dados de FISPQs (Fichas de Informações de Segurança de Produtos Químicos) de PDFs e armazena as informações estruturadas em um banco de dados SQLite para consultas rápidas e eficientes.

## 📋 Funcionalidades

- ✅ **Extração automática** de dados de PDFs do site Labsynth
- ✅ **Banco de dados SQLite** para armazenamento estruturado
- ✅ **Normalização** de texto com caracteres especiais
- ✅ **Busca avançada** por ONU, substância e classe de risco
- ✅ **Exportação** de dados para JSON
- ✅ **Estatísticas** detalhadas do banco
- ✅ **Interface de linha de comando** completa
- ✅ **Logging** detalhado de todas as operações

## 📁 Estrutura do Projeto

```
projeto/
├── app.py                   # Extrator principal com BD integrado
├── database_manager.py      # Gerenciador do banco de dados
├── consulta.py              # Exemplos de uso do sistema
├── README.md                # Este arquivo
└── dados_fispq/             # Pasta de trabalho (criada automaticamente)
    ├── json/                # JSONs individuais e consolidado
    ├── fispq_database.db    # Banco de dados SQLite
    └── fispq_extractor.log  # Log das operações
```

## 🚀 Instalação

### Pré-requisitos

```bash
pip install selenium requests pdfplumber
```

### Configuração do ChromeDriver

1. Baixe o ChromeDriver compatível com sua versão do Chrome
2. Adicione o ChromeDriver ao PATH do sistema
3. Ou coloque o executável na pasta do projeto

## 💻 Como Usar

### 1. Extração Completa (Baixar + Processar)

```bash
# Baixa PDFs do site e processa tudo automaticamente
python app_extrair_com_bd.py
```

### 2. Carregar JSON Existente para BD

```bash
# Carrega um arquivo consolidado.json existente para o banco
python app_extrair_com_bd.py --carregar-json
```

### 3. Consultas no Banco de Dados

```bash
# Buscar produto por número ONU
python app_extrair_com_bd.py --buscar-onu 1830

# Buscar produtos por nome da substância (busca parcial)
python app_extrair_com_bd.py --buscar-substancia "ácido"

# Buscar produtos por classe de risco
python app_extrair_com_bd.py --buscar-classe 3

# Ver apenas estatísticas do banco
python app_extrair_com_bd.py --stats
```

### 4. Exportação de Dados

```bash
# Exportar todo o banco para JSON
python app_extrair_com_bd.py --exportar backup.json

# Exportar com nome padrão
python app_extrair_com_bd.py --exportar
```

## 🗄️ Estrutura do Banco de Dados

### Tabela: `produtos_quimicos`
- **Identificação**: substância, número ONU, classe de risco, número de risco
- **Propriedades**: aspecto, odor, pH, pontos de fusão/ebulição/fulgor, densidade, solubilidade
- **Manuseio**: precauções de manuseio, condições de armazenamento

### Tabela: `primeiros_socorros`
- Procedimentos para: inalação, contato com pele, contato com olhos, ingestão
- Sintomas e efeitos
- Notas para o médico

### Tabela: `combate_incendio`
- Meios de extinção apropriados
- Perigos específicos do produto
- Medidas de proteção da equipe

## 📊 Dados Extraídos

O sistema extrai automaticamente os seguintes campos dos PDFs:

### 🏷️ Identificação do Produto
- Nome da substância/produto
- Número ONU (UN Number)
- Classe de risco principal
- Número de risco
- Risco subsidiário

### 🆘 Informações de Emergência
- **Primeiros Socorros**:
  - Inalação
  - Contato com a pele
  - Contato com os olhos
  - Ingestão
  - Sintomas e efeitos
  - Notas para o médico

- **Combate a Incêndio**:
  - Meios de extinção
  - Perigos específicos
  - Proteção da equipe

### 🧪 Propriedades Físico-Químicas
- Aspecto físico
- Odor
- pH
- Ponto de fusão
- Ponto de ebulição
- Ponto de fulgor
- Densidade
- Solubilidade

### 🛡️ Manuseio e Armazenamento
- Precauções para manuseio seguro
- Condições de armazenamento

## 🔍 Exemplos de Consulta

### Usando Python

```python
from database_manager import DatabaseManager
from app_extrair_com_bd import FISPQExtractor

# Inicializar
extrator = FISPQExtractor()

# Buscar por ONU
produto = extrator.buscar_produto_onu("1830")

# Buscar por substância
produtos = extrator.buscar_produtos_substancia("ácido")

# Buscar por classe de risco
produtos_classe = extrator.buscar_produtos_classe_risco("8")

# Ver estatísticas
extrator.exibir_estatisticas_bd()
```

### Usando Diretamente o DatabaseManager

```python
from database_manager import DatabaseManager

db = DatabaseManager()

# Buscar produto específico
produto = db.buscar_por_onu("1830")
if produto:
    print(f"Substância: {produto['substancia']}")
    print(f"Primeiros socorros (inalação): {produto['inalacao']}")

# Estatísticas
stats = db.obter_estatisticas()
print(f"Total de produtos: {stats['total_produtos']}")
```

## 🔧 Integração com Outros Sistemas

### API Flask Exemplo

```python
from flask import Flask, jsonify
from database_manager import DatabaseManager

app = Flask(__name__)
db = DatabaseManager()

@app.route('/api/produto/<numero_onu>')
def get_produto(numero_onu):
    produto = db.buscar_por_onu(numero_onu)
    return jsonify(produto) if produto else jsonify({"erro": "Não encontrado"}), 404

@app.route('/api/produtos/substancia/<nome>')
def get_produtos_substancia(nome):
    produtos = db.buscar_por_substancia(nome)
    return jsonify(produtos)

if __name__ == '__main__':
    app.run()
```

## 📈 Monitoramento e Logs

O sistema gera logs detalhados em `fispq_extractor.log`:

```
2025-01-18 10:30:15 - INFO - 🚀 Iniciando extração de FISPQs...
2025-01-18 10:30:20 - INFO - 📥 PDF 1 baixado: arquivo_1.pdf
2025-01-18 10:30:25 - INFO - ✅ Dados extraídos com sucesso: arquivo_1.pdf
2025-01-18 10:30:26 - INFO - ✅ Produto inserido no BD - ID: 1, Substância: Ácido Sulfúrico
2025-01-18 10:30:30 - INFO - 📊 Total de produtos: 1
```

## ⚠️ Tratamento de Erros

O sistema possui tratamento robusto de erros:

- **PDFs corrompidos**: Log do erro, continua processando outros
- **Dados incompletos**: Produtos sem ONU não são inseridos no BD
- **Falhas de conexão**: Retry automático com timeout
- **Caracteres especiais**: Normalização automática de encoding

## 🎯 Casos de Uso

### 1. **Consulta Rápida de Emergência**
```bash
# Buscar procedimentos de emergência para um produto específico
python app_extrair_com_bd.py --buscar-onu 1830
```

### 2. **Análise de Inventário Químico**
```bash
# Listar todos os produtos de uma classe de risco
python app_extrair_com_bd.py --buscar-classe 8
```

### 3. **Backup e Migração**
```bash
# Exportar dados para backup
python app_extrair_com_bd.py --exportar backup_$(date +%Y%m%d).json
```

### 4. **Atualização Periódica**
```bash
# Script para atualização automatizada (crontab)
#!/bin/bash
cd /caminho/para/projeto
python app_extrair_com_bd.py >> log_cron.txt 2>&1
```

## 🛠️ Personalização

### Modificar Local de Download
```python
# No arquivo app_extrair_com_bd.py
extrator = FISPQExtractor("/seu/caminho/personalizado/")
```

### Adicionar Novos Campos
1. Modifique o método `extrair_dados_pdf()` para novos campos
2. Atualize o schema do banco em `database_manager.py`
3. Adicione os campos na inserção

### Diferentes Fontes de PDFs
```python
# Modificar URL no método baixar_pdfs()
arquivos = extrator.baixar_pdfs("https://outro-site.com/fispq/")
```

## 🔐 Segurança e Privacidade

- ✅ **Dados locais**: Tudo armazenado localmente
- ✅ **Sem credenciais**: Não requer login ou senhas
- ✅ **Logs seguros**: Sem informações sensíveis nos logs
- ✅ **Validação**: Dados validados antes da inserção

## 📞 Troubleshooting

### Erro: ChromeDriver não encontrado
```bash
# Solução 1: Instalar via package manager
sudo apt-get install chromium-chromedriver  # Ubuntu/Debian
brew install chromedriver                   # macOS

# Solução 2: Download manual
# Baixar de https://chromedriver.chromium.org/
# Adicionar ao PATH
```

### Erro: PDF não pode ser lido
- Verificar se o PDF não está corrompido
- Verificar permissões de arquivo
- PDF pode estar protegido por senha

### Banco de dados travado
```python
# Resetar banco (cuidado: remove todos os dados)
from database_manager import DatabaseManager
db = DatabaseManager()
db.limpar_banco()
```

### Encoding de caracteres
```python
# O sistema já trata automaticamente, mas se houver problemas:
# Verificar encoding do sistema
import locale
print(locale.getpreferredencoding())
```

## 🤝 Contribuição

Para contribuir com o projeto:

1. Faça um fork do repositório
2. Crie uma branch para sua feature
3. Teste suas modificações
4. Submeta um pull request

## 📄 Licença

Este projeto é fornecido como está, para fins educacionais e de pesquisa.

## 📧 Suporte

Para dúvidas ou problemas:
1. Consulte os logs em `fispq_extractor.log`
2. Execute `python exemplo_uso_banco.py` para testes
3. Verifique se todas as dependências estão instaladas

---

**⚡ Dica**: Execute `python exemplo_uso_banco.py` para ver uma demonstração completa de todas as funcionalidades!
