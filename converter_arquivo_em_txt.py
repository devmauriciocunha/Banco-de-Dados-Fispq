import os
import sys
import re
from pathlib import Path
import logging

# Configurar logging detalhado
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('pdf_conversion.log')
    ]
)
logger = logging.getLogger(__name__)

class PDFToTxtConverter:
    def __init__(self):
        """Inicializa o conversor com múltiplas bibliotecas"""
        self.available_methods = []
        self.setup_libraries()
    
    def setup_libraries(self):
        """Configura as bibliotecas disponíveis"""
        
        # PyPDF2
        try:
            import PyPDF2
            self.PyPDF2 = PyPDF2
            self.available_methods.append('pypdf2')
            logger.info("✓ PyPDF2 disponível")
        except ImportError:
            logger.warning("PyPDF2 não encontrado")
        
        # pdfplumber
        try:
            import pdfplumber
            self.pdfplumber = pdfplumber
            self.available_methods.append('pdfplumber')
            logger.info("✓ pdfplumber disponível")
        except ImportError:
            logger.warning("pdfplumber não encontrado")
        
        # PyMuPDF
        try:
            import fitz
            self.fitz = fitz
            self.available_methods.append('pymupdf')
            logger.info("✓ PyMuPDF disponível")
        except ImportError:
            logger.warning("PyMuPDF não encontrado")
        
        # pdfminer
        try:
            from pdfminer.high_level import extract_text
            from pdfminer.layout import LAParams
            self.pdfminer_extract = extract_text
            self.LAParams = LAParams
            self.available_methods.append('pdfminer')
            logger.info("✓ pdfminer disponível")
        except ImportError:
            logger.warning("pdfminer não encontrado")
        
        if not self.available_methods:
            logger.error("ERRO: Nenhuma biblioteca de PDF encontrada!")
            logger.error("Instale com: pip install PyPDF2 pdfplumber pymupdf pdfminer.six")
            sys.exit(1)
        
        logger.info(f"Métodos disponíveis: {', '.join(self.available_methods)}")

    def clean_text(self, text):
        """Limpa e normaliza o texto extraído"""
        if not text:
            return ""
        
        # Remover caracteres de controle
        text = text.replace('\x00', '')
        text = text.replace('\r\n', '\n')
        text = text.replace('\r', '\n')
        
        # Normalizar espaços
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Corrigir encoding
        replacements = {
            'â€™': "'", 'â€œ': '"', 'â€': '"',
            'Ã¡': 'á', 'Ã©': 'é', 'Ã­': 'í', 'Ã³': 'ó', 'Ãº': 'ú',
            'Ã£': 'ã', 'Ãµ': 'õ', 'Ã§': 'ç'
        }
        
        for wrong, correct in replacements.items():
            text = text.replace(wrong, correct)
        
        return text.strip()

    def extract_with_pypdf2(self, pdf_path):
        """Extrai texto com PyPDF2"""
        try:
            text = ""
            with open(pdf_path, 'rb') as file:
                pdf_reader = self.PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            return self.clean_text(text)
        except Exception as e:
            logger.error(f"Erro PyPDF2: {str(e)}")
            return None

    def extract_with_pdfplumber(self, pdf_path):
        """Extrai texto com pdfplumber"""
        try:
            text = ""
            with self.pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    # Extrair tabelas
                    tables = page.extract_tables()
                    if tables:
                        for table in tables:
                            for row in table:
                                if row:
                                    text += " | ".join([cell or "" for cell in row]) + "\n"
                    
                    # Extrair texto normal
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            
            return self.clean_text(text)
        except Exception as e:
            logger.error(f"Erro pdfplumber: {str(e)}")
            return None

    def extract_with_pymupdf(self, pdf_path):
        """Extrai texto com PyMuPDF"""
        try:
            text = ""
            pdf_document = self.fitz.open(pdf_path)
            
            for page_num in range(pdf_document.page_count):
                page = pdf_document[page_num]
                text += page.get_text() + "\n"
            
            pdf_document.close()
            return self.clean_text(text)
        except Exception as e:
            logger.error(f"Erro PyMuPDF: {str(e)}")
            return None

    def extract_with_pdfminer(self, pdf_path):
        """Extrai texto com pdfminer"""
        try:
            laparams = self.LAParams(
                boxes_flow=0.5,
                word_margin=0.1,
                char_margin=2.0,
                line_margin=0.5
            )
            
            text = self.pdfminer_extract(pdf_path, laparams=laparams)
            return self.clean_text(text)
        except Exception as e:
            logger.error(f"Erro pdfminer: {str(e)}")
            return None

    def convert_single_pdf(self, pdf_path, output_path=None, method='auto'):
        """Converte um PDF para TXT"""
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            logger.error(f"Arquivo não encontrado: {pdf_path}")
            return False
        
        if output_path is None:
            output_path = pdf_path.with_suffix('.txt')
        else:
            output_path = Path(output_path)
        
        logger.info(f"Convertendo: {pdf_path.name}")
        
        # Determinar métodos a tentar
        if method == 'auto':
            methods_order = ['pdfplumber', 'pymupdf', 'pdfminer', 'pypdf2']
            methods_to_try = [m for m in methods_order if m in self.available_methods]
        else:
            if method in self.available_methods:
                methods_to_try = [method]
            else:
                logger.error(f"Método {method} não disponível")
                return False
        
        # Tentar cada método
        extracted_text = None
        successful_method = None
        
        for method_name in methods_to_try:
            logger.info(f"  Tentando {method_name}...")
            
            if method_name == 'pypdf2':
                extracted_text = self.extract_with_pypdf2(pdf_path)
            elif method_name == 'pdfplumber':
                extracted_text = self.extract_with_pdfplumber(pdf_path)
            elif method_name == 'pymupdf':
                extracted_text = self.extract_with_pymupdf(pdf_path)
            elif method_name == 'pdfminer':
                extracted_text = self.extract_with_pdfminer(pdf_path)
            
            if extracted_text and len(extracted_text.strip()) > 100:
                successful_method = method_name
                break
            else:
                logger.warning(f"    {method_name} extraiu pouco texto")
        
        if not extracted_text or len(extracted_text.strip()) < 50:
            logger.error(f"  ✗ Falha na extração de {pdf_path.name}")
            return False
        
        # Salvar arquivo
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(extracted_text)
            
            logger.info(f"  ✓ Sucesso com {successful_method}: {len(extracted_text)} chars")
            return True
            
        except Exception as e:
            logger.error(f"  ✗ Erro ao salvar: {str(e)}")
            return False

def main():
    """Função principal"""
    
    # Diretórios
    pdf_dir = Path("/home/mauricio-cunha/Documentos/reconhecimento-placas-fispq-main/arquivos_pdf")
    txt_dir = Path("/home/mauricio-cunha/Documentos/reconhecimento-placas-fispq-main/arquivos_txt")
    
    logger.info("=== CONVERSÃO DE FISPQ PDFs PARA TXT ===")
    logger.info(f"PDFs: {pdf_dir}")
    logger.info(f"TXTs: {txt_dir}")
    
    # Verificar diretórios
    if not pdf_dir.exists():
        logger.error(f"Diretório de PDFs não existe: {pdf_dir}")
        pdf_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Diretório criado. Adicione PDFs e execute novamente.")
        return
    
    txt_dir.mkdir(parents=True, exist_ok=True)
    
    # Encontrar PDFs
    pdf_files = list(pdf_dir.glob("*.pdf")) + list(pdf_dir.glob("*.PDF"))
    if not pdf_files:
        logger.warning(f"Nenhum PDF encontrado em {pdf_dir}")
        return
    
    logger.info(f"Encontrados {len(pdf_files)} PDFs")
    
    # Inicializar conversor
    try:
        converter = PDFToTxtConverter()
    except SystemExit:
        return
    
    # Converter arquivos
    stats = {'total': len(pdf_files), 'success': 0, 'failed': 0, 'skipped': 0}
    
    for pdf_file in pdf_files:
        txt_file = txt_dir / f"{pdf_file.stem}.txt"
        
        # Pular se já existe
        if txt_file.exists() and txt_file.stat().st_size > 100:
            logger.info(f"⏭️  Pulando {pdf_file.name} (já existe)")
            stats['skipped'] += 1
            continue
        
        # Converter
        if converter.convert_single_pdf(pdf_file, txt_file):
            stats['success'] += 1
        else:
            stats['failed'] += 1
    
    # Relatório
    logger.info(f"\n=== RELATÓRIO FINAL ===")
    logger.info(f"Total: {stats['total']}")
    logger.info(f"Convertidos: {stats['success']}")
    logger.info(f"Pulados: {stats['skipped']}")
    logger.info(f"Falharam: {stats['failed']}")
    
    if stats['total'] > 0:
        success_rate = (stats['success'] / stats['total']) * 100
        logger.info(f"Taxa de sucesso: {success_rate:.1f}%")
    
    # Verificar resultado
    txt_files = list(txt_dir.glob("*.txt"))
    logger.info(f"Arquivos TXT criados: {len(txt_files)}")

if __name__ == "__main__":
    main()