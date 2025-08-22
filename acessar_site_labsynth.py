from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import requests
import os
import time
import pdfplumber
import re
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

# Importar o gerenciador de banco de dados
from database_manager import DatabaseManager

# --- Configurações de logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fispq_extractor.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FISPQExtractor:
    def __init__(self, pasta_download: str = "/home/mauricio-cunha/Documentos/reconhecimento-placas-fispq-main/teste/"):
        self.pasta_download = pasta_download
        self.pasta_json = os.path.join(pasta_download, "json")
        self.json_consolidado = os.path.join(self.pasta_json, "consolidado.json")
        
        # Inicializar gerenciador de banco de dados
        self.db_manager = DatabaseManager(os.path.join(pasta_download, "fispq_database.db"))
        
        # Criar pastas se não existirem
        os.makedirs(self.pasta_download, exist_ok=True)
        os.makedirs(self.pasta_json, exist_ok=True)
    
    @staticmethod
    def normalizar_texto(texto: str) -> str:
        """Normaliza caracteres especiais no texto"""
        if not texto:
            return ""
            
        substituicoes = {
            'Ã§': 'ç', 'Ã¡': 'á', 'Ã©': 'é', 'Ã­': 'í', 'Ã³': 'ó', 'Ãº': 'ú',
            'Ã ': 'à', 'Ãª': 'ê', 'Ã´': 'ô', 'Ã¢': 'â', 'Ãµ': 'õ', 'Ã£': 'ã',
            'Ã‡': 'Ç', 'Ã': 'Á', 'Ã‰': 'É', 'Ã': 'Í', 'Ã"': 'Ó', 'Ãš': 'Ú',
            'Ã€': 'À', 'ÃŠ': 'Ê', 'Ã"': 'Ô', 'Ã‚': 'Â', 'Ã•': 'Õ', 'Ãƒ': 'Ã'
        }
        
        for old, new in substituicoes.items():
            texto = texto.replace(old, new)
        
        return texto.strip()
    
    @staticmethod
    def match(padrao: str, texto: str, flags=re.IGNORECASE | re.DOTALL) -> Optional[str]:
        """Função auxiliar para regex com normalização"""
        if not texto:
            return None
            
        m = re.search(padrao, texto, flags)
        if m:
            resultado = m.group(1).strip()
            return FISPQExtractor.normalizar_texto(resultado) if resultado else None
        return None
    
    def extrair_primeiros_socorros(self, texto: str) -> Dict[str, str]:
        """Extrai informações estruturadas de primeiros socorros"""
        secao_primeiros_socorros = self.match(
            r"(?:4\.\s*(?:PRIMEIROS SOCORROS|Medidas de primeiros socorros)|PRIMEIROS SOCORROS)(.*?)(?=\d+\.\s*[A-Z]|\Z)", 
            texto
        )
        
        if not secao_primeiros_socorros:
            return {}
        
        primeiros_socorros = {
            "inalacao": self.match(r"(?:Inalação|INALAÇÃO)[:\-]?\s*([^-•\n]*(?:\n[^-•]*)*?)(?=(?:Contato|CONTATO|Ingestão|INGESTÃO|\n\s*-|\n\s*•)|$)", secao_primeiros_socorros),
            "contato_pele": self.match(r"(?:Contato com a pele|CONTATO COM A PELE)[:\-]?\s*([^-•\n]*(?:\n[^-•]*)*?)(?=(?:Contato com os olhos|CONTATO COM OS OLHOS|Ingestão|INGESTÃO|\n\s*-|\n\s*•)|$)", secao_primeiros_socorros),
            "contato_olhos": self.match(r"(?:Contato com os olhos|CONTATO COM OS OLHOS)[:\-]?\s*([^-•\n]*(?:\n[^-•]*)*?)(?=(?:Ingestão|INGESTÃO|\n\s*-|\n\s*•)|$)", secao_primeiros_socorros),
            "ingestao": self.match(r"(?:Ingestão|INGESTÃO)[:\-]?\s*([^-•\n]*(?:\n[^-•]*)*?)(?=(?:\n\s*4\.|Sintomas|SINTOMAS|\n\s*-|\n\s*•)|$)", secao_primeiros_socorros),
            "sintomas": self.match(r"(?:Sintomas e efeitos|SINTOMAS E EFEITOS)[^:]*[:\-]?\s*([^\n]*(?:\n[^4]*)*?)(?=(?:4\.\d|\n\s*Notas para o médico|NOTAS PARA O MÉDICO)|$)", secao_primeiros_socorros),
            "notas_medico": self.match(r"(?:Notas para o médico|NOTAS PARA O MÉDICO)[^:]*[:\-]?\s*([^\n]*(?:\n[^5]*)*?)(?=(?:5\.\d|MEDIDAS DE COMBATE)|$)", secao_primeiros_socorros)
        }
        
        # Remove valores vazios
        return {k: v for k, v in primeiros_socorros.items() if v and v.strip()}
    
    def extrair_combate_incendio(self, texto: str) -> Dict[str, str]:
        """Extrai informações estruturadas de combate a incêndio"""
        secao_incendio = self.match(
            r"(?:5\.\s*(?:MEDIDAS DE COMBATE A INCÊNDIO|COMBATE A INCÊNDIO)|COMBATE A INCÊNDIO)(.*?)(?=\d+\.\s*[A-Z]|\Z)", 
            texto
        )
        
        if not secao_incendio:
            return {}
        
        combate_incendio = {
            "meios_extincao": self.match(r"(?:Meios de extinção|MEIOS DE EXTINÇÃO)[^:]*[:\-]?\s*([^\n]*(?:\n[^5]*)*?)(?=(?:5\.\d|Perigos específicos|PERIGOS ESPECÍFICOS)|$)", secao_incendio),
            "perigos_especificos": self.match(r"(?:Perigos específicos|PERIGOS ESPECÍFICOS)[^:]*[:\-]?\s*([^\n]*(?:\n[^5]*)*?)(?=(?:5\.\d|Medidas de proteção|MEDIDAS DE PROTEÇÃO)|$)", secao_incendio),
            "protecao_equipe": self.match(r"(?:Medidas de proteção da equipe|MEDIDAS DE PROTEÇÃO DA EQUIPE)[^:]*[:\-]?\s*([^\n]*(?:\n[^6]*)*?)(?=(?:6\.\d|MEDIDAS DE CONTROLE)|$)", secao_incendio)
        }
        
        # Remove valores vazios
        return {k: v for k, v in combate_incendio.items() if v and v.strip()}
    
    def extrair_propriedades_fisico_quimicas(self, texto: str) -> Dict[str, str]:
        """Extrai propriedades físico-químicas"""
        secao_propriedades = self.match(
            r"(?:9\.\s*(?:PROPRIEDADES FÍSICO|Propriedades físico).*?)(.*?)(?=\d+\.\s*[A-Z]|\Z)", 
            texto
        )
        
        if not secao_propriedades:
            return {}
        
        propriedades = {
            "aspecto": self.match(r"(?:Aspecto|ASPECTO)[:\-]?\s*([^\n]+)", secao_propriedades),
            "odor": self.match(r"(?:Odor|ODOR)[:\-]?\s*([^\n]+)", secao_propriedades),
            "ph": self.match(r"(?:pH|PH)[:\-]?\s*([^\n]+)", secao_propriedades),
            "ponto_fusao": self.match(r"(?:Ponto de fusão|PONTO DE FUSÃO)[^:]*[:\-]?\s*([^\n]+)", secao_propriedades),
            "ponto_ebulicao": self.match(r"(?:Ponto de ebulição|PONTO DE EBULIÇÃO)[^:]*[:\-]?\s*([^\n]+)", secao_propriedades),
            "ponto_fulgor": self.match(r"(?:Ponto de fulgor|PONTO DE FULGOR)[^:]*[:\-]?\s*([^\n]+)", secao_propriedades),
            "densidade": self.match(r"(?:Densidade|DENSIDADE)[^:]*[:\-]?\s*([^\n]+)", secao_propriedades),
            "solubilidade": self.match(r"(?:Solubilidade|SOLUBILIDADE)[^:]*[:\-]?\s*([^\n]*(?:\n[^\n-]*)*?)(?=(?:-|•|\n\s*[A-Z])|$)", secao_propriedades)
        }
        
        # Remove valores vazios
        return {k: v for k, v in propriedades.items() if v and v.strip()}
    
    def extrair_dados_pdf(self, caminho_pdf: str, nome_arquivo: str) -> Dict:
        """Extrai todos os dados de um PDF"""
        try:
            with pdfplumber.open(caminho_pdf) as pdf:
                texto_completo = ""
                for pagina in pdf.pages:
                    texto_pagina = pagina.extract_text()
                    if texto_pagina:
                        texto_completo += texto_pagina + "\n"
                
                # Normalizar o texto completo
                texto_completo = self.normalizar_texto(texto_completo)
                
                # Extrair dados estruturados
                dados_pdf = {
                    "arquivo": nome_arquivo,
                    "data_processamento": datetime.now().isoformat(),
                    "identificacao": {
                        "substancia": self.match(r"(?:Nome do produto|Substância|NOME DO PRODUTO)[:\-]?\s*([^\n:]+)", texto_completo),
                        "numero_onu": self.match(r"(?:Número ONU|ONU|NÚMERO ONU)[:\-]?\s*(\d{4,5})", texto_completo),
                        "classe_risco": self.match(r"(?:Classe|CLASSE)\s*[\/\\]?\s*(?:subclasse\s*)?(?:de\s*)?(?:risco\s*)?(?:principal\s*)?(?:e\s*subsidiário\s*)?[:\-]?\s*(\d+(?:\.\d+)?)", texto_completo),
                        "numero_risco": self.match(r"(?:Número de Risco|Risco|NÚMERO DE RISCO)[:\-]?\s*(\d+)", texto_completo),
                        "risco_subsidiario": self.match(r"(?:Risco Subsidiário|Subsidiário|RISCO SUBSIDIÁRIO)[:\-]?\s*([^\n]+)", texto_completo)
                    },
                    "emergencia": {
                        "primeiros_socorros": self.extrair_primeiros_socorros(texto_completo),
                        "combate_incendio": self.extrair_combate_incendio(texto_completo)
                    },
                    "propriedades": self.extrair_propriedades_fisico_quimicas(texto_completo),
                    "manuseio_armazenamento": {
                        "precaucoes_manuseio": self.match(r"(?:Precauções para o manuseio seguro|PRECAUÇÕES PARA O MANUSEIO)[^:]*[:\-]?\s*([^\n]*(?:\n[^7]*)*?)(?=(?:7\.\d|Condições de armazenamento)|$)", texto_completo),
                        "condicoes_armazenamento": self.match(r"(?:Condições de armazenamento|CONDIÇÕES DE ARMAZENAMENTO)[^:]*[:\-]?\s*([^\n]*(?:\n[^8]*)*?)(?=(?:8\.\d|CONTROLE DE EXPOSIÇÃO)|$)", texto_completo)
                    }
                }
                
                # Remove seções vazias
                dados_pdf = self.remover_campos_vazios(dados_pdf)
                
                logger.info(f"✅ Dados extraídos com sucesso: {nome_arquivo}")
                return dados_pdf
                
        except Exception as e:
            logger.error(f"❌ Erro ao processar {nome_arquivo}: {str(e)}")
            return {
                "arquivo": nome_arquivo,
                "erro": str(e),
                "data_processamento": datetime.now().isoformat()
            }
    def salvar_txt(self, caminho_pdf: str, nome_arquivo: str):
        try:
            texto_completo = ""
            with pdfplumber.open(caminho_pdf) as pdf:
                for pagina in pdf.pages:
                    texto = pagina.extract_text()
                    if texto:
                        texto_completo += texto + "\n"

            nome_txt = os.path.splitext(nome_arquivo)[0] + ".txt"
            caminho_txt = os.path.join(self.pasta_download, nome_txt)

            with open(caminho_txt, "w", encoding="utf-8") as f:
                f.write(texto_completo)

            logger.info(f"📝 TXT salvo: {caminho_txt}")
            return caminho_txt

        except Exception as e:
            logger.error(f"❌ Erro ao salvar TXT de {nome_arquivo}: {e}")
            return None
        
    def remover_campos_vazios(self, dados: Dict) -> Dict:
        
        if isinstance(dados, dict):
            return {k: self.remover_campos_vazios(v) for k, v in dados.items() 
                   if v is not None and v != "" and v != {}}
        elif isinstance(dados, list):
            return [self.remover_campos_vazios(item) for item in dados if item]
        else:
            return dados
    
    def baixar_pdfs(self, url: str = "https://www.labsynth.com.br/fispq/") -> List[str]:
        """Baixa PDFs do site usando Selenium"""
        chrome_options = Options()
        chrome_options.add_experimental_option("prefs", {
            "download.default_directory": self.pasta_download,
            "download.prompt_for_download": False,
            "plugins.always_open_pdf_externally": True
        })
        
        navegador = None
        try:
            navegador = webdriver.Chrome(options=chrome_options)
            navegador.get(url)
            navegador.maximize_window()
            time.sleep(2)
            
            # Encontrar links de PDFs
            links = navegador.find_elements(By.XPATH, '//a[contains(@href, ".pdf")]')
            logger.info(f"Encontrados {len(links)} PDFs.")
            
            arquivos_baixados = []
            
            for i, link in enumerate(links, start=1):
                try:
                    url_pdf = link.get_attribute('href')
                    nome_arquivo = f"arquivo_{i}.pdf"
                    caminho_arquivo = os.path.join(self.pasta_download, nome_arquivo)
                    
                    response = requests.get(url_pdf, timeout=30)
                    response.raise_for_status()
                    
                    with open(caminho_arquivo, "wb") as f:
                        f.write(response.content)
                    
                    arquivos_baixados.append(nome_arquivo)
                    logger.info(f"📥 PDF {i} baixado: {nome_arquivo}")
                    
                except Exception as e:
                    logger.error(f"❌ Erro ao baixar PDF {i}: {str(e)}")
            
            return arquivos_baixados
            
        except Exception as e:
            logger.error(f"❌ Erro durante download: {str(e)}")
            return []
        finally:
            if navegador:
                navegador.quit()
    
    def processar_pdfs(self, arquivos_pdf: List[str]) -> List[Dict]:
        """Processa lista de PDFs e retorna dados extraídos"""
        todos_registros = []
        
        for pdf_file in arquivos_pdf:
            caminho_pdf = os.path.join(self.pasta_download, pdf_file)
            
            if os.path.exists(caminho_pdf):
                dados_pdf = self.extrair_dados_pdf(caminho_pdf, pdf_file)
                
                # Salvar JSON individual
                nome_json = os.path.join(self.pasta_json, pdf_file.replace(".pdf", ".json"))
                try:
                    with open(nome_json, "w", encoding="utf-8") as f:
                        json.dump(dados_pdf, f, ensure_ascii=False, indent=2)
                    logger.info(f"📄 JSON salvo: {nome_json}")
                except Exception as e:
                    logger.error(f"❌ Erro ao salvar JSON {nome_json}: {str(e)}")
                
                # Salvar TXT individual
                try:
                    self.salvar_txt(caminho_pdf, pdf_file)
                except Exception as e:
                    logger.error(f"❌ Erro ao salvar TXT {pdf_file}: {str(e)}")
                
                # Verificar se tem dados válidos para inserir no BD
                if (dados_pdf.get("identificacao", {}).get("numero_onu") and 
                    not dados_pdf.get("erro")):
                    
                    # Inserir no banco de dados
                    produto_id = self.db_manager.inserir_produto(dados_pdf)
                    if produto_id:
                        dados_pdf["produto_id"] = produto_id
                    
                    todos_registros.append(dados_pdf)
                else:
                    logger.warning(f"⚠️ Produto sem ONU ou com erro não será inserido no BD: {pdf_file}")
                
                # Remover PDF após processamento
                try:
                    os.remove(caminho_pdf)
                    logger.info(f"🗑️ PDF removido: {caminho_pdf}")
                except Exception as e:
                    logger.error(f"❌ Erro ao remover PDF {caminho_pdf}: {str(e)}")
        
        return todos_registros

    
    def salvar_consolidado(self, registros: List[Dict]):
        """Salva arquivo JSON consolidado"""
        try:
            with open(self.json_consolidado, "w", encoding="utf-8") as f:
                json.dump(registros, f, ensure_ascii=False, indent=2)
            logger.info(f"📦 JSON consolidado salvo: {self.json_consolidado}")
            logger.info(f"📊 Total de registros válidos: {len(registros)}")
        except Exception as e:
            logger.error(f"❌ Erro ao salvar consolidado: {str(e)}")
    
    def carregar_json_existente_para_bd(self, caminho_json: str = None):
        """Carrega dados de um JSON existente para o banco de dados"""
        if caminho_json is None:
            caminho_json = self.json_consolidado
            
        if os.path.exists(caminho_json):
            logger.info(f"📂 Carregando JSON existente para BD: {caminho_json}")
            resultado = self.db_manager.carregar_json_consolidado(caminho_json)
            logger.info(f"💾 Resultado da carga: {resultado['sucessos']} sucessos, {resultado['erros']} erros")
        else:
            logger.warning(f"⚠️ Arquivo JSON não encontrado: {caminho_json}")
    
    def executar(self, carregar_json_existente: bool = False):
        """Executa o processo completo"""
        logger.info("🚀 Iniciando extração de FISPQs...")
        
        # Opção para carregar JSON existente sem baixar novos PDFs
        if carregar_json_existente:
            logger.info("📂 Modo: Carregando JSON existente para BD")
            self.carregar_json_existente_para_bd()
            self.exibir_estatisticas_bd()
            return
        
        # 1. Baixar PDFs
        arquivos_pdf = self.baixar_pdfs()
        if not arquivos_pdf:
            logger.error("❌ Nenhum PDF foi baixado. Encerrando.")
            return
        
        # 2. Processar PDFs (já inclui inserção no BD)
        registros_validos = self.processar_pdfs(arquivos_pdf)
        
        # 3. Salvar consolidado
        self.salvar_consolidado(registros_validos)
        
        # 4. Limpar JSONs inválidos
        self.limpar_jsons_invalidos()
        
        # 5. Exibir estatísticas do banco de dados
        self.exibir_estatisticas_bd()
        
        logger.info("✅ Processo concluído com sucesso!")
    
    def limpar_jsons_invalidos(self):
        """Remove JSONs que não têm número ONU e seus respectivos TXT"""
        removidos = 0
        for json_file in os.listdir(self.pasta_json):
            if json_file.endswith(".json") and json_file != "consolidado.json":
                caminho_json = os.path.join(self.pasta_json, json_file)
                nome_pdf_equivalente = os.path.splitext(json_file)[0] + ".pdf"
                nome_txt_equivalente = os.path.splitext(json_file)[0] + ".txt"
                caminho_txt = os.path.join(self.pasta_download, nome_txt_equivalente)
                
                try:
                    with open(caminho_json, "r", encoding="utf-8") as f:
                        dados = json.load(f)
                    
                    if not dados.get("identificacao", {}).get("numero_onu"):
                        # Remove JSON inválido
                        os.remove(caminho_json)
                        removidos += 1
                        logger.info(f"🗑️ JSON inválido removido: {json_file}")
                        
                        # Remove TXT correspondente se existir
                        if os.path.exists(caminho_txt):
                            os.remove(caminho_txt)
                            logger.info(f"🗑️ TXT correspondente removido: {nome_txt_equivalente}")
                        
                except Exception as e:
                    logger.error(f"❌ Erro ao verificar JSON {json_file}: {str(e)}")
        
        logger.info(f"🧹 {removidos} JSONs inválidos removidos (com TXT correspondente)")

    
    def exibir_estatisticas_bd(self):
        """Exibe estatísticas do banco de dados"""
        logger.info("📊 === ESTATÍSTICAS DO BANCO DE DADOS ===")
        stats = self.db_manager.obter_estatisticas()
        
        if stats:
            logger.info(f"📦 Total de produtos: {stats.get('total_produtos', 0)}")
            
            # Produtos por classe de risco
            por_classe = stats.get('por_classe_risco', {})
            if por_classe:
                logger.info("🔥 Produtos por classe de risco:")
                for classe, qtd in por_classe.items():
                    logger.info(f"   • Classe {classe}: {qtd} produtos")
            
            # Produtos mais recentes
            mais_recentes = stats.get('mais_recentes', [])
            if mais_recentes:
                logger.info("🕐 Produtos mais recentes:")
                for produto in mais_recentes[:3]:
                    logger.info(f"   • {produto['substancia']} (ONU: {produto['onu']})")
        
        logger.info("=" * 45)
    
    # Métodos para consultas no banco de dados
    def buscar_produto_onu(self, numero_onu: str):
        """Busca produto por número ONU"""
        produto = self.db_manager.buscar_por_onu(numero_onu)
        if produto:
            logger.info(f"✅ Produto encontrado - ONU {numero_onu}: {produto['substancia']}")
            return produto
        else:
            logger.info(f"❌ Produto ONU {numero_onu} não encontrado")
            return None
    
    def buscar_produtos_substancia(self, nome_substancia: str):
        """Busca produtos por nome da substância"""
        produtos = self.db_manager.buscar_por_substancia(nome_substancia)
        logger.info(f"🔍 Encontrados {len(produtos)} produtos para '{nome_substancia}'")
        
        for produto in produtos:
            logger.info(f"   • {produto['substancia']} (ONU: {produto['numero_onu']}, Classe: {produto['classe_risco']})")
        
        return produtos
    
    def buscar_produtos_classe_risco(self, classe_risco: str):
        """Busca produtos por classe de risco"""
        produtos = self.db_manager.buscar_por_classe_risco(classe_risco)
        logger.info(f"🔥 Encontrados {len(produtos)} produtos da classe {classe_risco}")
        
        for produto in produtos:
            logger.info(f"   • {produto['substancia']} (ONU: {produto['numero_onu']})")
        
        return produtos
    
    def exportar_bd_para_json(self, caminho_saida: str = None):
        """Exporta dados do banco para JSON"""
        if caminho_saida is None:
            caminho_saida = os.path.join(self.pasta_json, "export_database.json")
        
        sucesso = self.db_manager.exportar_para_json(caminho_saida)
        if sucesso:
            logger.info(f"📤 Dados exportados com sucesso para: {caminho_saida}")
        return sucesso

# --- Execução do script ---
if __name__ == "__main__":
    import argparse
    
    # Argumentos da linha de comando
    parser = argparse.ArgumentParser(description='Extrator de FISPQs com banco de dados')
    parser.add_argument('--carregar-json', action='store_true', 
                       help='Carrega JSON consolidado existente para o banco de dados')
    parser.add_argument('--buscar-onu', type=str, 
                       help='Busca produto por número ONU')
    parser.add_argument('--buscar-substancia', type=str, 
                       help='Busca produtos por nome da substância')
    parser.add_argument('--buscar-classe', type=str, 
                       help='Busca produtos por classe de risco')
    parser.add_argument('--exportar', type=str, nargs='?', const='default',
                       help='Exporta banco de dados para JSON')
    parser.add_argument('--stats', action='store_true', 
                       help='Exibe apenas as estatísticas do banco')
    
    args = parser.parse_args()
    
    # Criar instância do extrator
    extrator = FISPQExtractor()
    
    # Executar baseado nos argumentos
    if args.stats:
        extrator.exibir_estatisticas_bd()
    elif args.carregar_json:
        extrator.executar(carregar_json_existente=True)
    elif args.buscar_onu:
        extrator.buscar_produto_onu(args.buscar_onu)
    elif args.buscar_substancia:
        extrator.buscar_produtos_substancia(args.buscar_substancia)
    elif args.buscar_classe:
        extrator.buscar_produtos_classe_risco(args.buscar_classe)
    elif args.exportar:
        caminho = None if args.exportar == 'default' else args.exportar
        extrator.exportar_bd_para_json(caminho)
    else:
        # Execução padrão - baixar e processar PDFs
        extrator.executar()