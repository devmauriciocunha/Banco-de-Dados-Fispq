#!/usr/bin/env python3
"""
Exemplo de uso do sistema FISPQ com banco de dados
Este arquivo demonstra como usar todas as funcionalidades disponíveis
"""

import os
import json
import logging
from datetime import datetime

# Importar os módulos do sistema
from database_manager import DatabaseManager
from app import FISPQExtractor

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def demonstrar_funcionalidades():
    """Demonstra todas as funcionalidades do sistema"""
    
    print("=" * 60)
    print("🧪 SISTEMA DE GERENCIAMENTO DE FISPQ COM BANCO DE DADOS")
    print("=" * 60)
    
    # Criar instância do extrator
    pasta_trabalho = "./dados_fispq/"
    extrator = FISPQExtractor(pasta_trabalho)
    
    print("\n1. 📊 ESTATÍSTICAS INICIAIS DO BANCO")
    print("-" * 40)
    extrator.exibir_estatisticas_bd()
    
    # Demonstrar busca por ONU
    print("\n2. 🔍 BUSCA POR NÚMERO ONU")
    print("-" * 40)
    numero_onu_exemplo = "1234"  # Substitua por um número real
    produto_onu = extrator.buscar_produto_onu(numero_onu_exemplo)
    
    if produto_onu:
        print(f"   ✅ Encontrado: {produto_onu['substancia']}")
        print(f"   📋 Classe de Risco: {produto_onu['classe_risco']}")
        print(f"   🏷️  Aspecto: {produto_onu['aspecto']}")
    else:
        print(f"   ❌ Número ONU {numero_onu_exemplo} não encontrado")
    
    # Demonstrar busca por substância
    print("\n3. 🔍 BUSCA POR NOME DA SUBSTÂNCIA")
    print("-" * 40)
    nome_substancia = "ácido"  # Exemplo de busca parcial
    produtos_substancia = extrator.buscar_produtos_substancia(nome_substancia)
    
    if produtos_substancia:
        print(f"   📦 Total encontrado: {len(produtos_substancia)} produtos")
        for i, produto in enumerate(produtos_substancia[:3], 1):  # Mostrar apenas os 3 primeiros
            print(f"   {i}. {produto['substancia']} (ONU: {produto['numero_onu']})")
    
    # Demonstrar busca por classe de risco
    print("\n4. 🔍 BUSCA POR CLASSE DE RISCO")
    print("-" * 40)
    classe_risco = "3"  # Exemplo de classe de risco
    produtos_classe = extrator.buscar_produtos_classe_risco(classe_risco)
    
    if produtos_classe:
        print(f"   🔥 Total da classe {classe_risco}: {len(produtos_classe)} produtos")
    
    # Demonstrar exportação
    print("\n5. 📤 EXPORTAÇÃO DE DADOS")
    print("-" * 40)
    arquivo_export = os.path.join(pasta_trabalho, "backup_database.json")
    sucesso_export = extrator.exportar_bd_para_json(arquivo_export)
    
    if sucesso_export:
        print(f"   ✅ Dados exportados para: {arquivo_export}")
        # Verificar tamanho do arquivo
        if os.path.exists(arquivo_export):
            tamanho = os.path.getsize(arquivo_export) / 1024  # KB
            print(f"   📏 Tamanho do arquivo: {tamanho:.1f} KB")
    
    print("\n6. 📊 ESTATÍSTICAS FINAIS")
    print("-" * 40)
    extrator.exibir_estatisticas_bd()

def exemplo_processamento_completo():
    """Exemplo de processamento completo de PDFs"""
    
    print("\n" + "=" * 60)
    print("🔄 EXEMPLO DE PROCESSAMENTO COMPLETO")
    print("=" * 60)
    
    pasta_trabalho = "./dados_fispq_completo/"
    extrator = FISPQExtractor(pasta_trabalho)
    
    # Método 1: Processar PDFs do site
    print("\n📥 MÉTODO 1: Baixar e processar PDFs do site")
    print("Para executar este método, descomente a linha abaixo:")
    print("# extrator.executar()")
    
    # Método 2: Carregar JSON existente
    print("\n📂 MÉTODO 2: Carregar JSON existente para BD")
    print("Para executar este método:")
    print("# extrator.executar(carregar_json_existente=True)")

def exemplo_uso_direto_database():
    """Exemplo de uso direto do DatabaseManager"""
    
    print("\n" + "=" * 60)
    print("🗄️  EXEMPLO DE USO DIRETO DO DATABASE MANAGER")
    print("=" * 60)
    
    # Criar instância do gerenciador de BD
    db = DatabaseManager("exemplo_fispq.db")
    
    # Criar um produto de exemplo
    produto_exemplo = {
        "arquivo": "exemplo_teste.pdf",
        "data_processamento": datetime.now().isoformat(),
        "identificacao": {
            "substancia": "Ácido Sulfúrico",
            "numero_onu": "1830",
            "classe_risco": "8",
            "numero_risco": "80"
        },
        "propriedades": {
            "aspecto": "Líquido incolor",
            "odor": "Inodoro",
            "ph": "<1",
            "densidade": "1,84 g/cm³"
        },
        "emergencia": {
            "primeiros_socorros": {
                "inalacao": "Remover para local arejado",
                "contato_pele": "Lavar abundantemente com água",
                "contato_olhos": "Lavar imediatamente com água por 15 minutos",
                "ingestao": "Não induzir vômito. Procurar assistência médica"
            },
            "combate_incendio": {
                "meios_extincao": "Água em forma de neblina",
                "perigos_especificos": "Pode gerar vapores tóxicos"
            }
        },
        "manuseio_armazenamento": {
            "precaucoes_manuseio": "Usar EPI adequado",
            "condicoes_armazenamento": "Local seco e ventilado"
        }
    }
    
    print("\n📝 Inserindo produto de exemplo...")
    produto_id = db.inserir_produto(produto_exemplo)
    
    if produto_id:
        print(f"   ✅ Produto inserido com ID: {produto_id}")
        
        # Buscar o produto inserido
        print("\n🔍 Buscando produto por ONU 1830...")
        produto_encontrado = db.buscar_por_onu("1830")
        
        if produto_encontrado:
            print(f"   ✅ Produto encontrado: {produto_encontrado['substancia']}")
            print(f"   📋 Densidade: {produto_encontrado['densidade']}")
            print(f"   🔧 Manuseio: {produto_encontrado['precaucoes_manuseio']}")
    
    # Exibir estatísticas
    print("\n📊 Estatísticas do banco:")
    stats = db.obter_estatisticas()
    print(json.dumps(stats, indent=2, ensure_ascii=False))

def exemplo_linha_comando():
    """Mostra exemplos de uso via linha de comando"""
    
    print("\n" + "=" * 60)
    print("⌨️  EXEMPLOS DE USO VIA LINHA DE COMANDO")
    print("=" * 60)
    
    exemplos = [
        ("Executar extração completa", "python app_extrair_com_bd.py"),
        ("Carregar JSON existente", "python app_extrair_com_bd.py --carregar-json"),
        ("Buscar por ONU", "python app_extrair_com_bd.py --buscar-onu 1830"),
        ("Buscar por substância", "python app_extrair_com_bd.py --buscar-substancia 'ácido'"),
        ("Buscar por classe de risco", "python app_extrair_com_bd.py --buscar-classe 3"),
        ("Exportar banco para JSON", "python app_extrair_com_bd.py --exportar backup.json"),
        ("Ver apenas estatísticas", "python app_extrair_com_bd.py --stats")
    ]
    
    for descricao, comando in exemplos:
        print(f"\n📌 {descricao}:")
        print(f"   {comando}")

def exemplo_integracao_sistema():
    """Exemplo de como integrar com outros sistemas"""
    
    print("\n" + "=" * 60)
    print("🔗 EXEMPLO DE INTEGRAÇÃO COM OUTROS SISTEMAS")
    print("=" * 60)
    
    codigo_exemplo = '''
# Exemplo de integração com Flask API
from flask import Flask, jsonify, request
from database_manager import DatabaseManager

app = Flask(__name__)
db = DatabaseManager()

@app.route('/api/produto/<numero_onu>')
def get_produto_onu(numero_onu):
    produto = db.buscar_por_onu(numero_onu)
    if produto:
        return jsonify(produto)
    return jsonify({"erro": "Produto não encontrado"}), 404

@app.route('/api/produtos/substancia/<nome>')
def get_produtos_substancia(nome):
    produtos = db.buscar_por_substancia(nome)
    return jsonify(produtos)

@app.route('/api/estatisticas')
def get_estatisticas():
    stats = db.obter_estatisticas()
    return jsonify(stats)

if __name__ == '__main__':
    app.run(debug=True)
    '''
    
    print("💡 Exemplo de API Flask:")
    print(codigo_exemplo)
    
    print("\n💡 Exemplo de uso em outros scripts Python:")
    exemplo_script = '''
# meu_sistema.py
from database_manager import DatabaseManager

# Conectar ao banco
db = DatabaseManager("meu_banco_fispq.db")

# Buscar informações de segurança para um produto
def obter_info_seguranca(numero_onu):
    produto = db.buscar_por_onu(numero_onu)
    if produto:
        return {
            "primeiros_socorros": produto.get("inalacao", ""),
            "combate_incendio": produto.get("meios_extincao", ""),
            "classe_risco": produto.get("classe_risco", "")
        }
    return None

# Exemplo de uso
info = obter_info_seguranca("1830")
if info:
    print(f"Classe de risco: {info['classe_risco']}")
    '''
    
    print(exemplo_script)

def main():
    """Função principal que executa todas as demonstrações"""
    
    print("🚀 Iniciando demonstração do sistema FISPQ...")
    
    try:
        # 1. Demonstrar funcionalidades básicas
        demonstrar_funcionalidades()
        
        # 2. Exemplo de processamento
        exemplo_processamento_completo()
        
        # 3. Exemplo de uso direto do BD
        exemplo_uso_direto_database()
        
        # 4. Exemplos de linha de comando
        exemplo_linha_comando()
        
        # 5. Exemplos de integração
        exemplo_integracao_sistema()
        
        print("\n" + "=" * 60)
        print("✅ DEMONSTRAÇÃO CONCLUÍDA COM SUCESSO!")
        print("=" * 60)
        print("\n📚 Para mais informações, consulte:")
        print("   • database_manager.py - Gerenciamento do banco")
        print("   • app_extrair_com_bd.py - Extração com BD")
        print("   • Este arquivo - Exemplos de uso")
        
    except Exception as e:
        logger.error(f"❌ Erro durante demonstração: {str(e)}")
        print(f"\n⚠️  Erro: {str(e)}")
        print("💡 Certifique-se de que os arquivos necessários estão no diretório correto.")

if __name__ == "__main__":
    main()