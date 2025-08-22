from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import requests
import os
import time
import pdfplumber
import re
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse
import tempfile

from database_manager import DatabaseManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fispq_extractor.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FISPQExtractorMelhorado:
    def __init__(self, pasta_download: str = "/home/mauricio-cunha/Documentos/reconhecimento-placas-fispq-main/arquivos_extraidos/"):
        self.pasta_download = pasta_download
        self.pasta_json = os.path.join(pasta_download, "json")
        self.json_consolidado = os.path.join(self.pasta_json, "consolidado.json")
        
        self.db_manager = DatabaseManager(os.path.join(pasta_download, "fispq_database.db"))
        
        os.makedirs(self.pasta_download, exist_ok=True)
        os.makedirs(self.pasta_json, exist_ok=True)
        
        self.chrome_options = Options()
        self.chrome_options.add_experimental_option("prefs", {
            "download.default_directory": self.pasta_download,
            "download.prompt_for_download": False,
            "plugins.always_open_pdf_externally": True,
            "profile.default_content_settings.popups": 0,
            "profile.default_content_setting_values.notifications": 2
        })
        self.chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        self.chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.chrome_options.add_experimental_option('useAutomationExtension', False)
    
    @staticmethod
    def normalizar_texto(texto: str) -> str:
        if not texto:
            return ""
            
        substituicoes = {
            'Ã§': 'ç', 'Ã¡': 'á', 'Ã©': 'é', 'Ã­': 'í', 'Ã³': 'ó', 'Ãº': 'ú',
            'Ã ': 'à', 'Ãª': 'ê', 'Ã´': 'ô', 'Ã¢': 'â', 'Ãµ': 'õ', 'Ã£': 'ã',
            'Ã‡': 'Ç', 'Ã': 'Á', 'Ã‰': 'É', 'Ã': 'Í', 'Ã"': 'Ó', 'Ãš': 'Ú',
            'Ã€': 'À', 'ÃŠ': 'Ê', 'Ã"': 'Ô', 'Ã‚': 'Â', 'Ã•': 'Õ', 'Ãƒ': 'Ã',
            'â€™': "'", 'â€œ': '"', 'â€': '"', 'â€"': '-', 'â€"': '–'
        }
        
        for old, new in substituicoes.items():
            texto = texto.replace(old, new)
        
        return texto.strip()
    
    @staticmethod
    def match(padrao: str, texto: str, flags=re.IGNORECASE | re.DOTALL) -> Optional[str]:
        if not texto:
            return None
            
        m = re.search(padrao, texto, flags)
        if m:
            resultado = m.group(1).strip() if m.group(1) else None
            return FISPQExtractorMelhorado.normalizar_texto(resultado) if resultado else None
        return None
    
    def debug_texto(self, texto: str, nome_arquivo: str):
        debug_path = os.path.join(self.pasta_json, f"debug_{nome_arquivo}.txt")
        try:
            with open(debug_path, "w", encoding="utf-8") as f:
                f.write(texto)
            logger.info(f"🐛 Debug text saved: {debug_path}")
        except Exception as e:
            logger.error(f"❌ Erro ao salvar debug: {e}")
    
    def extrair_identificacao_melhorada(self, texto: str) -> Dict[str, str]:
        identificacao = {}
        texto_normalizado = re.sub(r'\s+', ' ', texto)
        
        # Nome do produto - padrões mais específicos
        padroes_nome = [
            r'(?:Nome do produto\s*[:]\s*)([^\n\r]+?)(?=\n|Referência|$)',
            r'(?:NOME DO PRODUTO\s*[:]\s*)([^\n\r]+?)(?=\n|REFERÊNCIA|$)',
            r'(?:Product name\s*[:]\s*)([^\n\r]+?)(?=\n|Product|$)',
            r'(?:1\.1[^:]*[:]\s*)([^\n\r]+?)(?=\n|1\.2|$)',
            r'(?:^|\n)([A-ZÁÉÍÓÚÇÃÕ][A-ZÁÉÍÓÚÇÃÕ\s-]{5,50})(?:\s*\n|\s*Referência)',
        ]
        
        for padrao in padroes_nome:
            nome = self.match(padrao, texto_normalizado)
            if nome and len(nome.strip()) > 3:
                nome = re.sub(r'\s*\n.*', '', nome).strip()
                nome = re.sub(r'(ficha|fispq|safety|data|sheet|msds).*', '', nome, flags=re.IGNORECASE).strip()
                if len(nome) > 3 and not re.match(r'^(Referência|Marca|Companhia)', nome):
                    identificacao["substancia"] = nome
                    logger.info(f"✅ Substância encontrada: {nome}")
                    break
        
        # Número ONU - padrões mais específicos para seção 14
        numero_onu = self.extrair_numero_onu_melhorado(texto)
        if numero_onu:
            identificacao["numero_onu"] = numero_onu
        
        # Classe de risco
        padroes_classe = [
            r'Classe\s*[:]\s*(\d+(?:\.\d+)?)',
            r'Class\s*[:]\s*(\d+(?:\.\d+)?)',
            r'(?:14\.3|seção\s+14)[^:]*classe[:\s-]*(\d+(?:\.\d+)?)',
            r'ADR/RID[^:]*Classe\s*[:]\s*(\d+)',
            r'IMDG[^:]*Classe\s*[:]\s*(\d+)',
            r'IATA[^:]*Classe\s*[:]\s*(\d+)',
        ]
        
        for padrao in padroes_classe:
            classe = self.match(padrao, texto_normalizado)
            if classe and re.match(r'^\d+(\.\d+)?$', classe):
                identificacao["classe_risco"] = classe
                logger.info(f"✅ Classe de risco encontrada: {classe}")
                break
        
        # Número de risco
        padroes_numero_risco = [
            r'Número de risco\s*[:]\s*(\d+)',
            r'Risk number\s*[:]\s*(\d+)',
            r'Kemler\s*[:]\s*(\d+)',
        ]
        
        for padrao in padroes_numero_risco:
            numero_risco = self.match(padrao, texto_normalizado)
            if numero_risco:
                identificacao["numero_risco"] = numero_risco
                logger.info(f"✅ Número de risco encontrado: {numero_risco}")
                break
        
        # Risco subsidiário
        padroes_risco_sub = [
            r'Risco subsidiário\s*[:]\s*(\d+(?:\.\d+)?)',
            r'Subsidiary risk\s*[:]\s*(\d+(?:\.\d+)?)',
            r'Sub\. Risk\s*[:]\s*(\d+(?:\.\d+)?)',
        ]
        
        for padrao in padroes_risco_sub:
            risco_sub = self.match(padrao, texto_normalizado)
            if risco_sub:
                identificacao["risco_subsidiario"] = risco_sub
                logger.info(f"✅ Risco subsidiário encontrado: {risco_sub}")
                break
        
        # Códigos H
        codigos_h = re.findall(r'\bH\d{3}\b', texto, re.IGNORECASE)
        if codigos_h:
            identificacao["codigos_h"] = list(set(codigos_h))
            logger.info(f"✅ Códigos H encontrados: {codigos_h}")
        
        return identificacao
    
    def extrair_numero_onu_melhorado(self, texto: str) -> Optional[str]:
        texto_normalizado = re.sub(r'\s+', ' ', texto)
        
        # Buscar especificamente na seção 14
        secao_14_match = re.search(r'14\..*?(?=15\.|$)', texto_normalizado, re.IGNORECASE | re.DOTALL)
        if secao_14_match:
            secao_14 = secao_14_match.group(0)
            
            padroes_onu_secao14 = [
                r'Número ONU\s*[:]\s*(\d{4})',
                r'UN number\s*[:]\s*(\d{4})',
                r'ONU\s*[:]\s*(\d{4})',
                r'UN\s*[:]\s*(\d{4})',
                r'ADR/RID[^:]*Número ONU\s*[:]\s*(\d{4})',
                r'IMDG[^:]*Número ONU\s*[:]\s*(\d{4})',
                r'IATA[^:]*Número ONU\s*[:]\s*(\d{4})',
            ]
            
            for padrao in padroes_onu_secao14:
                match = re.search(padrao, secao_14, re.IGNORECASE)
                if match:
                    numero = match.group(1)
                    if numero.isdigit() and len(numero) == 4:
                        num = int(numero)
                        if 1000 <= num <= 9999:
                            logger.info(f"✅ ONU encontrado na seção 14: {numero}")
                            return numero
        
        # Padrões gerais como fallback
        padroes_onu_gerais = [
            r'(?:número\s+onu|no\s+onu|n°\s+onu|onu)\s*[:]\s*(\d{4})',
            r'(?:un\s+number|un\s+no)\s*[:]\s*(\d{4})',
        ]
        
        for padrao in padroes_onu_gerais:
            matches = re.findall(padrao, texto_normalizado, re.IGNORECASE)
            for match in matches:
                if match.isdigit() and len(match) == 4:
                    num = int(match)
                    if 1000 <= num <= 9999:
                        logger.info(f"✅ ONU encontrado: {match}")
                        return match
        
        logger.warning("⚠️ Número ONU não encontrado")
        return None
    
    def extrair_primeiros_socorros_melhorado(self, texto: str) -> Dict[str, str]:
        # Buscar seção 4 completa
        secao_4_match = re.search(r'4\..*?(?=5\.|$)', texto, re.IGNORECASE | re.DOTALL)
        if not secao_4_match:
            logger.warning("⚠️ Seção 4 (Primeiros Socorros) não encontrada")
            return {}
        
        secao_4 = secao_4_match.group(0)
        logger.info("✅ Seção 4 encontrada")
        
        primeiros_socorros = {}
        
        # Padrões melhorados para cada tipo de exposição
        padroes = {
            "inalacao": [
                r'(?:Se for inalado|If inhaled|Inalação|Inhalation)[^:]*[:]\s*([^.]+(?:\.[^.]*){0,3})\.',
                r'(?:4\.1|Por inalação)[^:]*[:]\s*([^.]+(?:\.[^.]*){0,3})\.',
                r'(?:Se for respirado)[^:]*[:]\s*([^.]+(?:\.[^.]*){0,3})\.',
            ],
            "contato_pele": [
                r'(?:No caso dum contacto com a pele|Skin contact|Contato com a pele)[^:]*[:]\s*([^.]+(?:\.[^.]*){0,3})\.',
                r'(?:4\.2|Em caso de contato com a pele)[^:]*[:]\s*([^.]+(?:\.[^.]*){0,3})\.',
            ],
            "contato_olhos": [
                r'(?:No caso dum contacto com os olhos|Eye contact|Contato com os olhos)[^:]*[:]\s*([^.]+(?:\.[^.]*){0,3})\.',
                r'(?:4\.3|Em caso de contato com os olhos)[^:]*[:]\s*([^.]+(?:\.[^.]*){0,3})\.',
            ],
            "ingestao": [
                r'(?:Se for engolido|If swallowed|Ingestão|Ingestion)[^:]*[:]\s*([^.]+(?:\.[^.]*){0,3})\.',
                r'(?:4\.4|Em caso de ingestão)[^:]*[:]\s*([^.]+(?:\.[^.]*){0,3})\.',
            ]
        }
        
        for tipo, patterns in padroes.items():
            for pattern in patterns:
                resultado = self.match(pattern, secao_4)
                if resultado and len(resultado.strip()) > 10:
                    resultado_limpo = re.sub(r'\s+', ' ', resultado).strip()
                    primeiros_socorros[tipo] = resultado_limpo
                    logger.info(f"✅ {tipo} encontrado: {resultado_limpo[:50]}...")
                    break
        
        # Buscar sintomas se disponível
        sintomas_match = re.search(r'(?:Sintomas|Symptoms)[^:]*[:]\s*([^.]+(?:\.[^.]*){0,5})\.', secao_4, re.IGNORECASE)
        if sintomas_match:
            sintomas = re.sub(r'\s+', ' ', sintomas_match.group(1)).strip()
            primeiros_socorros["sintomas"] = sintomas
            logger.info(f"✅ Sintomas encontrados: {sintomas[:50]}...")
        
        return primeiros_socorros
    
    def extrair_combate_incendio(self, texto: str) -> Dict[str, str]:
        secao_5_match = re.search(r'5\..*?(?=6\.|$)', texto, re.IGNORECASE | re.DOTALL)
        if not secao_5_match:
            return {}
        
        secao_5 = secao_5_match.group(0)
        combate_incendio = {}
        
        # Meios de extinção
        meios_match = re.search(r'(?:Meios adequados de extinção|Extinguishing media)[^:]*[:]\s*([^.]+(?:\.[^.]*){0,2})\.', secao_5, re.IGNORECASE)
        if meios_match:
            meios = re.sub(r'\s+', ' ', meios_match.group(1)).strip()
            combate_incendio["meios_extincao"] = meios
            logger.info(f"✅ Meios de extinção encontrados: {meios}")
        
        # Perigos específicos
        perigos_match = re.search(r'(?:Perigos específicos|Specific hazards)[^:]*[:]\s*([^.]+(?:\.[^.]*){0,2})\.', secao_5, re.IGNORECASE)
        if perigos_match:
            perigos = re.sub(r'\s+', ' ', perigos_match.group(1)).strip()
            combate_incendio["perigos_especificos"] = perigos
            logger.info(f"✅ Perigos específicos encontrados: {perigos}")
        
        # Equipamento de proteção
        protecao_match = re.search(r'(?:Equipamento especial de proteção|Protective equipment)[^:]*[:]\s*([^.]+(?:\.[^.]*){0,2})\.', secao_5, re.IGNORECASE)
        if protecao_match:
            protecao = re.sub(r'\s+', ' ', protecao_match.group(1)).strip()
            combate_incendio["protecao_equipe"] = protecao
            logger.info(f"✅ Proteção da equipe encontrada: {protecao}")
        
        return combate_incendio
    
    def extrair_manuseio_armazenamento(self, texto: str) -> Dict[str, str]:
        secao_7_match = re.search(r'7\..*?(?=8\.|$)', texto, re.IGNORECASE | re.DOTALL)
        if not secao_7_match:
            return {}
        
        secao_7 = secao_7_match.group(0)
        manuseio = {}
        
        # Precauções para manuseio
        manuseio_match = re.search(r'(?:Precauções para um manuseio seguro|Handling precautions)[^:]*[:]\s*([^.]+(?:\.[^.]*){0,3})\.', secao_7, re.IGNORECASE)
        if manuseio_match:
            precaucoes = re.sub(r'\s+', ' ', manuseio_match.group(1)).strip()
            manuseio["precaucoes_manuseio"] = precaucoes
            logger.info(f"✅ Precauções de manuseio encontradas: {precaucoes[:50]}...")
        
        # Condições de armazenamento
        armazenamento_match = re.search(r'(?:Condições para uma armazenagem segura|Storage conditions)[^:]*[:]\s*([^.]+(?:\.[^.]*){0,3})\.', secao_7, re.IGNORECASE)
        if armazenamento_match:
            condicoes = re.sub(r'\s+', ' ', armazenamento_match.group(1)).strip()
            manuseio["condicoes_armazenamento"] = condicoes
            logger.info(f"✅ Condições de armazenamento encontradas: {condicoes[:50]}...")
        
        return manuseio
    
    def extrair_propriedades_fisico_quimicas(self, texto: str) -> Dict[str, str]:
        secao_9_match = re.search(r'9\..*?(?=10\.|$)', texto, re.IGNORECASE | re.DOTALL)
        if not secao_9_match:
            return {}
        
        secao_9 = secao_9_match.group(0)
        propriedades = {}
        
        padroes_propriedades = {
            "aspecto": r'(?:Aspecto|Appearance|Estado físico)[^:]*[:]\s*([^\n\r]+)',
            "cor": r'(?:Cor|Color|Colour)[^:]*[:]\s*([^\n\r]+)',
            "odor": r'(?:Odor|Odour|Smell)[^:]*[:]\s*([^\n\r]+)',
            "ph": r'(?:pH)[^:]*[:]\s*([^\n\r]+)',
            "ponto_fusao": r'(?:Ponto de fusão|Melting point)[^:]*[:]\s*([^\n\r]+)',
            "ponto_ebulicao": r'(?:Ponto de ebulição|Boiling point)[^:]*[:]\s*([^\n\r]+)',
            "ponto_fulgor": r'(?:Ponto de fulgor|Flash point)[^:]*[:]\s*([^\n\r]+)',
            "densidade": r'(?:Densidade|Density)[^:]*[:]\s*([^\n\r]+)',
            "solubilidade": r'(?:Hidrossolubilidade|Solubility|Water solubility)[^:]*[:]\s*([^\n\r]+)'
        }
        
        for campo, padrao in padroes_propriedades.items():
            valor = self.match(padrao, secao_9)
            if valor and len(valor.strip()) > 1:
                valor_limpo = re.sub(r'\s+', ' ', valor).strip()
                propriedades[campo] = valor_limpo
                logger.info(f"✅ {campo} encontrado: {valor_limpo}")
        
        return propriedades
    
    def extrair_informacoes_transporte(self, texto: str) -> Dict[str, str]:
        secao_14_match = re.search(r'14\..*?(?=15\.|$)', texto, re.IGNORECASE | re.DOTALL)
        if not secao_14_match:
            return {}
        
        secao_14 = secao_14_match.group(0)
        transporte = {}
        
        # Número ONU
        numero_onu = self.extrair_numero_onu_melhorado(texto)
        if numero_onu:
            transporte["numero_onu"] = numero_onu
        
        # Outros dados de transporte
        padroes_transporte = {
            "classe": r'Classe\s*[:]\s*(\d+(?:\.\d+)?)',
            "grupo_embalagem": r'Grupo de embalagem\s*[:]\s*(I{1,3})',
            "designacao_oficial": r'(?:Denominação de expedição correcta|Proper shipping name)\s*[:]\s*([^\n\r]{10,100})',
            "nome_tecnico": r'(?:Nome técnico|Technical name)\s*[:]\s*([^\n\r]{10,100})'
        }
        
        for campo, padrao in padroes_transporte.items():
            valor = self.match(padrao, secao_14)
            if valor:
                transporte[campo] = valor
                logger.info(f"✅ {campo} de transporte encontrado: {valor}")
        
        return transporte
    
    def remover_campos_vazios(self, dados: Dict) -> Dict:
        if isinstance(dados, dict):
            return {k: self.remover_campos_vazios(v) for k, v in dados.items() 
                   if v is not None and v != "" and v != {} and v != []}
        elif isinstance(dados, list):
            return [self.remover_campos_vazios(item) for item in dados if item]
        else:
            return dados
    
    def extrair_dados_pdf_melhorado(self, caminho_pdf: str, nome_arquivo: str) -> Dict:
        logger.info(f"🔍 Processando PDF: {nome_arquivo}")
        
        try:
            with pdfplumber.open(caminho_pdf) as pdf:
                texto_completo = ""
                metadados_pdf = pdf.metadata or {}
                
                for i, pagina in enumerate(pdf.pages):
                    texto_pagina = pagina.extract_text()
                    if texto_pagina:
                        texto_completo += f"\n--- PÁGINA {i+1} ---\n" + texto_pagina
                
                texto_completo = self.normalizar_texto(texto_completo)
                self.debug_texto(texto_completo, nome_arquivo.replace('.pdf', ''))
                
                logger.info(f"📄 Texto extraído: {len(texto_completo)} caracteres")
                
                identificacao = self.extrair_identificacao_melhorada(texto_completo)
                logger.info(f"🔍 Identificação extraída: {identificacao}")
                
                primeiros_socorros = self.extrair_primeiros_socorros_melhorado(texto_completo)
                logger.info(f"🚑 Primeiros socorros extraídos: {len(primeiros_socorros)} itens")
                
                combate_incendio = self.extrair_combate_incendio(texto_completo)
                logger.info(f"🔥 Combate a incêndio extraído: {len(combate_incendio)} itens")
                
                dados_pdf = {
                    "arquivo": nome_arquivo,
                    "data_processamento": datetime.now().isoformat(),
                    "identificacao": identificacao,
                    "emergencia": {
                        "primeiros_socorros": primeiros_socorros,
                        "combate_incendio": combate_incendio
                    },
                    "manuseio_armazenamento": self.extrair_manuseio_armazenamento(texto_completo)
                }
                
                # Só adicionar propriedades se houver dados
                propriedades = self.extrair_propriedades_fisico_quimicas(texto_completo)
                if propriedades:
                    dados_pdf["propriedades"] = propriedades
                
                # Só adicionar informações de transporte se houver dados
                info_transporte = self.extrair_informacoes_transporte(texto_completo)
                if info_transporte:
                    dados_pdf["informacoes_transporte"] = info_transporte
                
                dados_pdf = self.remover_campos_vazios(dados_pdf)
                
                total_campos = sum([
                    len(dados_pdf.get("identificacao", {})),
                    len(dados_pdf.get("emergencia", {}).get("primeiros_socorros", {})),
                    len(dados_pdf.get("emergencia", {}).get("combate_incendio", {})),
                    len(dados_pdf.get("manuseio_armazenamento", {}))
                ])
                
                logger.info(f"✅ PDF processado: {nome_arquivo} - {total_campos} campos extraídos")
                return dados_pdf
                
        except Exception as e:
            logger.error(f"❌ Erro ao processar {nome_arquivo}: {str(e)}")
            return {
                "arquivo": nome_arquivo,
                "erro": str(e),
                "data_processamento": datetime.now().isoformat()
            }
    
    def baixar_pdfs_navegacao_adaptada(self, url: str = "https://sites.usp.br/cipa-ffclrp/fispq/") -> List[str]:
        navegador = None
        try:
            navegador = webdriver.Chrome(options=self.chrome_options)
            navegador.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            navegador.get(url)
            navegador.maximize_window()
            
            wait = WebDriverWait(navegador, 10)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            logger.info("📄 Página principal carregada, procurando links...")
            
            links_encontrados = []
            logger.info("🔍 Procurando PDFs na sequência específica do site USP...")
            
            for i in range(1, 415):
                xpath_sequencial = f'//*[@id="content"]/article/div/div/section[2]/div/div/div/div/div/p/a[{i}]'
                
                try:
                    elemento = navegador.find_element(By.XPATH, xpath_sequencial)
                    href = elemento.get_attribute('href')
                    texto = elemento.text.strip()
                    
                    if href and (href.endswith('.pdf') or 'pdf' in href.lower() or 'fispq' in href.lower()):
                        links_encontrados.append({
                            'elemento': elemento,
                            'href': href,
                            'texto': texto
                        })
                        logger.info(f"📎 Link {i} encontrado: {texto[:50]}... -> {href}")
                    
                except NoSuchElementException:
                    logger.info(f"🔚 Fim da sequência detectado no índice {i}. Total encontrado: {len(links_encontrados)}")
                    break
                except Exception as e:
                    logger.debug(f"Erro ao processar link {i}: {e}")
                    continue
            
            arquivos_baixados = []
            
            logger.info(f"📊 Total de links encontrados: {len(links_encontrados)}")
            
            for i, link_info in enumerate(links_encontrados, start=1):
                try:
                    url_pdf = link_info['href']
                    nome_arquivo = f"fispq_{i:03d}_{link_info['texto'][:20].replace(' ', '_')}.pdf"
                    nome_arquivo = re.sub(r'[^\w\-_.]', '', nome_arquivo)
                    
                    caminho_arquivo = os.path.join(self.pasta_download, nome_arquivo)
                    
                    logger.info(f"📥 Baixando PDF {i}: {url_pdf}")
                    
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                    }
                    
                    response = requests.get(url_pdf, timeout=30, headers=headers)
                    response.raise_for_status()
                    
                    with open(caminho_arquivo, "wb") as f:
                        f.write(response.content)
                    
                    arquivos_baixados.append(nome_arquivo)
                    logger.info(f"✅ PDF {i} baixado: {nome_arquivo}")
                    
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"❌ Erro ao baixar PDF {i}: {str(e)}")
                    continue
            
            logger.info(f"📊 Total de PDFs baixados: {len(arquivos_baixados)}")
            return arquivos_baixados
            
        except Exception as e:
            logger.error(f"❌ Erro durante navegação: {str(e)}")
            return []
        finally:
            if navegador:
                try:
                    navegador.quit()
                except:
                    pass
    
    def baixar_pdfs(self, url: str = "https://sites.usp.br/cipa-ffclrp/fispq/") -> List[str]:
        return self.baixar_pdfs_navegacao_adaptada(url)
    
    def processar_pdfs(self, arquivos_pdf: List[str]) -> List[Dict]:
        todos_registros = []
        
        logger.info(f"📁 Processando {len(arquivos_pdf)} PDFs...")
        
        for i, pdf_file in enumerate(arquivos_pdf, 1):
            caminho_pdf = os.path.join(self.pasta_download, pdf_file)
            
            if os.path.exists(caminho_pdf):
                logger.info(f"📄 [{i}/{len(arquivos_pdf)}] Processando: {pdf_file}")
                
                dados_pdf = self.extrair_dados_pdf_melhorado(caminho_pdf, pdf_file)
                
                nome_json = os.path.join(self.pasta_json, pdf_file.replace(".pdf", ".json"))
                try:
                    with open(nome_json, "w", encoding="utf-8") as f:
                        json.dump(dados_pdf, f, ensure_ascii=False, indent=2)
                    logger.info(f"📄 JSON salvo: {os.path.basename(nome_json)}")
                except Exception as e:
                    logger.error(f"❌ Erro ao salvar JSON {nome_json}: {str(e)}")
                
                identificacao = dados_pdf.get("identificacao", {})
                tem_onu = identificacao.get("numero_onu")
                tem_substancia = identificacao.get("substancia")
                sem_erro = not dados_pdf.get("erro")
                
                if (tem_onu or tem_substancia) and sem_erro:
                    try:
                        produto_id = self.db_manager.inserir_produto(dados_pdf)
                        if produto_id:
                            dados_pdf["produto_id"] = produto_id
                            logger.info(f"💾 Produto inserido no BD com ID: {produto_id}")
                        
                        todos_registros.append(dados_pdf)
                    except Exception as e:
                        logger.error(f"❌ Erro ao inserir no BD: {str(e)}")
                else:
                    logger.warning(f"⚠️ Produto sem dados mínimos não será inserido no BD: {pdf_file}")
                    logger.info(f"   - ONU: {tem_onu}, Substância: {tem_substancia}, Sem erro: {sem_erro}")
                
                try:
                    os.remove(caminho_pdf)
                    logger.info(f"🗑️ PDF removido: {os.path.basename(caminho_pdf)}")
                except Exception as e:
                    logger.error(f"❌ Erro ao remover PDF {caminho_pdf}: {str(e)}")
            else:
                logger.error(f"❌ Arquivo não encontrado: {caminho_pdf}")
        
        return todos_registros
    
    def salvar_consolidado(self, registros: List[Dict]):
        try:
            resumo = {
                "data_consolidacao": datetime.now().isoformat(),
                "total_registros": len(registros),
                "registros_com_onu": len([r for r in registros if r.get("identificacao", {}).get("numero_onu")]),
                "registros": registros
            }
            
            with open(self.json_consolidado, "w", encoding="utf-8") as f:
                json.dump(resumo, f, ensure_ascii=False, indent=2)
            
            logger.info(f"📦 JSON consolidado salvo: {os.path.basename(self.json_consolidado)}")
            logger.info(f"📊 Total de registros válidos: {len(registros)}")
            logger.info(f"🏷️ Registros com número ONU: {resumo['registros_com_onu']}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar consolidado: {str(e)}")
    
    def carregar_json_existente_para_bd(self, caminho_json: str = None):
        if caminho_json is None:
            caminho_json = self.json_consolidado
            
        if os.path.exists(caminho_json):
            logger.info(f"📂 Carregando JSON existente para BD: {caminho_json}")
            resultado = self.db_manager.carregar_json_consolidado(caminho_json)
            logger.info(f"💾 Resultado da carga: {resultado['sucessos']} sucessos, {resultado['erros']} erros")
        else:
            logger.warning(f"⚠️ Arquivo JSON não encontrado: {caminho_json}")
    
    def executar(self, carregar_json_existente: bool = False, limite_pdfs: int = None):
        logger.info("🚀 Iniciando extração de FISPQs...")
        
        if carregar_json_existente:
            logger.info("📂 Modo: Carregando JSON existente para BD")
            self.carregar_json_existente_para_bd()
            self.exibir_estatisticas_bd()
            return
        
        logger.info("📥 Iniciando download de PDFs...")
        arquivos_pdf = self.baixar_pdfs()
        
        if not arquivos_pdf:
            logger.error("❌ Nenhum PDF foi baixado. Encerrando.")
            return
        
        if limite_pdfs and limite_pdfs > 0:
            arquivos_pdf = arquivos_pdf[:limite_pdfs]
            logger.info(f"📊 Processamento limitado a {limite_pdfs} PDFs")
        
        logger.info("🔄 Iniciando processamento de PDFs...")
        registros_validos = self.processar_pdfs(arquivos_pdf)
        
        logger.info("💾 Salvando dados consolidados...")
        self.salvar_consolidado(registros_validos)
        
        logger.info("🧹 Limpando arquivos desnecessários...")
        self.limpar_jsons_invalidos()
        
        self.exibir_estatisticas_bd()
        
        logger.info("✅ Processo concluído com sucesso!")
        logger.info(f"📊 Resumo: {len(registros_validos)} produtos processados com sucesso")
    
    def limpar_jsons_invalidos(self):
        removidos = 0
        for json_file in os.listdir(self.pasta_json):
            if json_file.endswith(".json") and json_file != "consolidado.json" and not json_file.startswith("debug_"):
                caminho_json = os.path.join(self.pasta_json, json_file)
                try:
                    with open(caminho_json, "r", encoding="utf-8") as f:
                        dados = json.load(f)
                    
                    identificacao = dados.get("identificacao", {})
                    tem_dados_minimos = (
                        identificacao.get("numero_onu") or 
                        identificacao.get("substancia") or
                        len(identificacao) > 0
                    )
                    
                    if not tem_dados_minimos:
                        os.remove(caminho_json)
                        removidos += 1
                        logger.info(f"🗑️ JSON sem dados mínimos removido: {json_file}")
                        
                except Exception as e:
                    logger.error(f"❌ Erro ao verificar JSON {json_file}: {str(e)}")
        
        logger.info(f"🧹 {removidos} JSONs inválidos removidos.")
    
    def exibir_estatisticas_bd(self):
        logger.info("📊 === ESTATÍSTICAS DO BANCO DE DADOS ===")
        try:
            stats = self.db_manager.obter_estatisticas()
            
            if stats:
                logger.info(f"📦 Total de produtos: {stats.get('total_produtos', 0)}")
                
                por_classe = stats.get('por_classe_risco', {})
                if por_classe:
                    logger.info("🔥 Produtos por classe de risco:")
                    for classe, qtd in por_classe.items():
                        logger.info(f"   • Classe {classe}: {qtd} produtos")
                
                mais_recentes = stats.get('mais_recentes', [])
                if mais_recentes:
                    logger.info("🕐 Produtos mais recentes:")
                    for produto in mais_recentes[:5]:
                        logger.info(f"   • {produto.get('substancia', 'N/A')} (ONU: {produto.get('onu', 'N/A')})")
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter estatísticas: {str(e)}")
        
        logger.info("=" * 45)
    
    def buscar_produto_onu(self, numero_onu: str):
        try:
            produto = self.db_manager.buscar_por_onu(numero_onu)
            if produto:
                logger.info(f"✅ Produto encontrado - ONU {numero_onu}: {produto.get('substancia', 'N/A')}")
                return produto
            else:
                logger.info(f"❌ Produto ONU {numero_onu} não encontrado")
                return None
        except Exception as e:
            logger.error(f"❌ Erro na busca por ONU: {str(e)}")
            return None
    
    def buscar_produtos_substancia(self, nome_substancia: str):
        try:
            produtos = self.db_manager.buscar_por_substancia(nome_substancia)
            logger.info(f"🔍 Encontrados {len(produtos)} produtos para '{nome_substancia}'")
            
            for produto in produtos:
                logger.info(f"   • {produto.get('substancia', 'N/A')} (ONU: {produto.get('numero_onu', 'N/A')}, Classe: {produto.get('classe_risco', 'N/A')})")
            
            return produtos
        except Exception as e:
            logger.error(f"❌ Erro na busca por substância: {str(e)}")
            return []
    
    def buscar_produtos_classe_risco(self, classe_risco: str):
        try:
            produtos = self.db_manager.buscar_por_classe_risco(classe_risco)
            logger.info(f"🔥 Encontrados {len(produtos)} produtos da classe {classe_risco}")
            
            for produto in produtos:
                logger.info(f"   • {produto.get('substancia', 'N/A')} (ONU: {produto.get('numero_onu', 'N/A')})")
            
            return produtos
        except Exception as e:
            logger.error(f"❌ Erro na busca por classe: {str(e)}")
            return []
    
    def exportar_bd_para_json(self, caminho_saida: str = None):
        if caminho_saida is None:
            caminho_saida = os.path.join(self.pasta_json, "export_database.json")
        
        try:
            sucesso = self.db_manager.exportar_para_json(caminho_saida)
            if sucesso:
                logger.info(f"📤 Dados exportados com sucesso para: {caminho_saida}")
            return sucesso
        except Exception as e:
            logger.error(f"❌ Erro na exportação: {str(e)}")
            return False
    
    def testar_extração(self, arquivo_pdf: str = None):
        if arquivo_pdf:
            if not os.path.exists(arquivo_pdf):
                logger.error(f"❌ Arquivo não encontrado: {arquivo_pdf}")
                return
            
            logger.info(f"🧪 Testando extração em: {arquivo_pdf}")
            dados = self.extrair_dados_pdf_melhorado(arquivo_pdf, os.path.basename(arquivo_pdf))
            
            nome_teste = os.path.join(self.pasta_json, f"teste_{os.path.basename(arquivo_pdf).replace('.pdf', '.json')}")
            with open(nome_teste, "w", encoding="utf-8") as f:
                json.dump(dados, f, ensure_ascii=False, indent=2)
            
            logger.info(f"📄 Resultado do teste salvo em: {nome_teste}")
            
            identificacao = dados.get("identificacao", {})
            logger.info("📋 RESUMO DA EXTRAÇÃO:")
            logger.info(f"   • Substância: {identificacao.get('substancia', 'NÃO ENCONTRADA')}")
            logger.info(f"   • Número ONU: {identificacao.get('numero_onu', 'NÃO ENCONTRADO')}")
            logger.info(f"   • Classe de Risco: {identificacao.get('classe_risco', 'NÃO ENCONTRADA')}")
            logger.info(f"   • Primeiros Socorros: {len(dados.get('emergencia', {}).get('primeiros_socorros', {}))} itens")
            logger.info(f"   • Combate Incêndio: {len(dados.get('emergencia', {}).get('combate_incendio', {}))} itens")
            
        else:
            logger.info("🧪 Para testar, forneça o caminho do arquivo PDF")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Extrator de FISPQs com banco de dados - Versão Melhorada')
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
    parser.add_argument('--limite-pdfs', type=int, default=None,
                       help='Limita o número de PDFs a processar (para teste)')
    parser.add_argument('--testar', type=str, nargs='?', const='',
                       help='Testa extração em um PDF específico')
    parser.add_argument('--debug', action='store_true',
                       help='Ativa modo debug com mais informações')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("🐛 Modo debug ativado")
    
    extrator = FISPQExtractorMelhorado()
    
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
    elif args.testar is not None:
        extrator.testar_extração(args.testar if args.testar else None)
    else:
        extrator.executar(limite_pdfs=args.limite_pdfs)