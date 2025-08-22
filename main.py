import re
import json
import sqlite3
from datetime import datetime
from pathlib import Path
import os

class FISPQProcessor:
    def __init__(self, db_path="fispq_database.db"):
        self.db_path = db_path
        self.init_database()
        
    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Criar tabela se não existir
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS fispq_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            arquivo TEXT NOT NULL,
            data_processamento TEXT NOT NULL,
            substancia TEXT,
            numero_onu TEXT NOT NULL,
            classe_risco TEXT,
            numero_risco TEXT,
            risco_subsidiario TEXT,
            primeiros_socorros_inalacao TEXT,
            primeiros_socorros_contato_pele TEXT,
            primeiros_socorros_contato_olhos TEXT,
            primeiros_socorros_ingestao TEXT,
            primeiros_socorros_sintomas TEXT,
            combate_incendio_meios_extincao TEXT,
            combate_incendio_perigos_especificos TEXT,
            manuseio_precaucoes TEXT,
            dados_completos_json TEXT
        )
        ''')
        
        # Verificar se a coluna grupo_embalagem existe, se não, adicionar
        cursor.execute("PRAGMA table_info(fispq_data)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'grupo_embalagem' not in columns:
            print("Adicionando coluna grupo_embalagem à tabela existente...")
            cursor.execute('ALTER TABLE fispq_data ADD COLUMN grupo_embalagem TEXT')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_numero_onu ON fispq_data(numero_onu)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_substancia ON fispq_data(substancia)')
        
        conn.commit()
        conn.close()
        
    def clean_text(self, text):
        if not text:
            return ""
        text = text.replace('Ã¡', 'á').replace('Ã§', 'ç').replace('Ã£', 'ã')
        text = text.replace('Ã©', 'é').replace('Ã­', 'í').replace('Ã³', 'ó')
        text = text.replace('ÃÃ', 'Ç').replace('Â', '').replace('Â°', '°')
        text = text.replace('Ãº', 'ú').replace('Ãµ', 'õ').replace('Ã‚', 'Â')
        text = text.replace('Ã€', 'À').replace('Ã', 'É').replace('Ã"', 'Ó')
        return text.strip()

    def extract_identification(self, text):
        identification = {}
        if not text:
            return identification
        
        # Nome do produto - múltiplos padrões
        nome_patterns = [
            r'Nome do produto\s*:?\s*(.+?)(?:\n|Referência|Código)',
            r'Nome comercial\s*:?\s*(.+?)(?:\n|Referência|Código)',
            r'Identificação da substância.*?:\s*(.+?)(?:\n|Referência)',
            r'1\.1.*?Nome.*?:\s*(.+?)(?:\n|1\.2)'
        ]
        
        for pattern in nome_patterns:
            nome_match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if nome_match:
                identification['substancia'] = self.clean_text(nome_match.group(1))
                break
        
        # Padrão mais específico para UN-Number e Class juntos
        onu_class_combined = re.search(
            r'UN-Number:\s*(\d{4})\s+Class:\s*([1-9](?:\.\d+)?)', 
            text, re.IGNORECASE
        )
        if onu_class_combined:
            identification['numero_onu'] = onu_class_combined.group(1)
            identification['classe_risco'] = onu_class_combined.group(2)
            identification['risco_subsidiario'] = onu_class_combined.group(2)
        
        # Número ONU - padrões expandidos
        if 'numero_onu' not in identification:
            onu_patterns = [
                r'Número ONU\s*:?\s*(\d{4})',
                r'UN\s*Number\s*:?\s*(\d{4})',
                r'ONU\s*:?\s*(\d{4})',
                r'ADR/RID\s*:?\s*(\d{4})',
                r'IMDG\s*:?\s*(\d{4})',
                r'IATA\s*:?\s*(\d{4})',
                r'14\.1[^0-9]*(\d{4})',
                r'UN\s*(\d{4})',
                r'(?:^|\s)(\d{4})(?:\s|$)',  # Números de 4 dígitos isolados
            ]
            
            for pattern in onu_patterns:
                onu_match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
                if onu_match:
                    numero_candidato = onu_match.group(1)
                    # Validar se é um número ONU válido (1000-9999)
                    if 1000 <= int(numero_candidato) <= 9999:
                        identification['numero_onu'] = numero_candidato
                        break
        
        # Classe de risco - padrões expandidos
        if 'classe_risco' not in identification:
            classe_patterns = [
                r'Classe\s*:?\s*([1-9](?:\.\d+)?)',
                r'Classe de risco\s*:?\s*([1-9](?:\.\d+)?)',
                r'Class\s*:?\s*([1-9](?:\.\d+)?)',
                r'Hazard class\s*:?\s*([1-9](?:\.\d+)?)',
                r'14\.3[^0-9]*([1-9](?:\.\d+)?)',
                r'Risco principal\s*:?\s*([1-9](?:\.\d+)?)',
            ]
            
            for pattern in classe_patterns:
                classe_match = re.search(pattern, text, re.IGNORECASE)
                if classe_match:
                    classe_valor = classe_match.group(1)
                    identification['classe_risco'] = classe_valor
                    identification['risco_subsidiario'] = classe_valor
                    break
        
        # Número de risco (Hazard Identification Number / Kemler)
        numero_risco_patterns = [
            r'Número de risco\s*:?\s*(\d{2,3})',
            r'Hazard identification number\s*:?\s*(\d{2,3})',
            r'Kemler\s*:?\s*(\d{2,3})',
            r'14\.2[^0-9]*(\d{2,3})',
            r'(?:HIN|Kemler|Número.*risco)[:\s]*(\d{2,3})',
        ]
        
        for pattern in numero_risco_patterns:
            numero_match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if numero_match:
                identification['numero_risco'] = numero_match.group(1)
                break
        
        # Grupo de embalagem - padrões expandidos
        grupo_patterns = [
            r'Grupo de embalagem\s*:?\s*([IVX]+)',
            r'Packing group\s*:?\s*([IVX]+)',
            r'14\.4[^A-Z]*([IVX]+)',
            r'Grupo\s*:?\s*([IVX]+)',
        ]
        
        for pattern in grupo_patterns:
            grupo_match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if grupo_match:
                identification['grupo_embalagem'] = grupo_match.group(1)
                break
        
        return identification

    def extract_transport_info(self, text):
        transport_info = {}

        # Seção 14 completa - padrões mais flexíveis
        transport_patterns = [
            r'14\..*?Informações sobre transporte(.*?)(?=15\.|Informações.*regulamentação|$)',
            r'SEÇÃO 14[^\n]*\n(.*?)(?=SEÇÃO 15|15\.|$)',
            r'14\s*[-\.]\s*INFORMAÇÕES.*?TRANSPORTE(.*?)(?=15\.|$)'
        ]
        
        transport_text = ""
        for pattern in transport_patterns:
            transport_section = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if transport_section:
                transport_text = transport_section.group(1)
                break

        if not transport_text:
            return transport_info

        # Número ONU na seção de transporte
        onu_match = re.search(r'Número ONU\s*:?\s*(\d{4})', transport_text, re.IGNORECASE)
        if onu_match:
            transport_info['numero_onu'] = onu_match.group(1)

        # Nome apropriado para embarque
        nome_embarque_patterns = [
            r'Nome apropriado para embarque\s*:?\s*(.+?)(?:\n|14\.)',
            r'Proper shipping name\s*:?\s*(.+?)(?:\n|14\.)',
        ]
        
        for pattern in nome_embarque_patterns:
            nome_match = re.search(pattern, transport_text, re.IGNORECASE)
            if nome_match:
                transport_info['nome_embarque'] = nome_match.group(1).strip()
                break

        # Classe de risco na seção de transporte
        classe_patterns = [
            r'Classe.*?risco.*?:?\s*([1-9](?:\.\d+)?)',
            r'Hazard class\s*:?\s*([1-9](?:\.\d+)?)',
        ]
        
        for pattern in classe_patterns:
            classe_match = re.search(pattern, transport_text, re.IGNORECASE)
            if classe_match:
                transport_info['classe_risco'] = classe_match.group(1)
                break

        # Número de risco na seção de transporte
        numero_risco_match = re.search(r'Número de risco\s*:?\s*(\d{2,3})', transport_text, re.IGNORECASE)
        if numero_risco_match:
            transport_info['numero_risco'] = numero_risco_match.group(1)

        # Grupo de embalagem na seção de transporte
        grupo_match = re.search(r'Grupo de embalagem\s*:?\s*([IVX]+)', transport_text, re.IGNORECASE)
        if grupo_match:
            transport_info['grupo_embalagem'] = grupo_match.group(1)

        # Perigo ao meio ambiente
        perigo_patterns = [
            r'Perigo ao meio ambiente\s*:?\s*(.+?)(?:\n|14\.)',
            r'Marine pollutant\s*:?\s*(.+?)(?:\n|14\.)',
        ]
        
        for pattern in perigo_patterns:
            perigo_match = re.search(pattern, transport_text, re.IGNORECASE)
            if perigo_match:
                transport_info['perigo_ambiente'] = perigo_match.group(1).strip()
                break

        return transport_info

    def extract_first_aid(self, text):
        first_aid = {}
        if not text:
            return first_aid
        
        # Padrões mais flexíveis para primeiros socorros
        inalacao_patterns = [
            r'Se for inalado\s*:?\s*(.+?)(?=No caso.*contacto.*pele|Se for engolido|4\.2|5\.|$)',
            r'Inalação\s*:?\s*(.+?)(?=Contacto.*pele|Ingestão|4\.2|5\.|$)',
            r'Por inalação\s*:?\s*(.+?)(?=Por contacto|Por ingestão|4\.2|5\.|$)',
        ]
        
        for pattern in inalacao_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                first_aid['inalacao'] = self.clean_text(match.group(1))
                break
        
        # Contato com a pele
        pele_patterns = [
            r'No caso.*contacto.*pele\s*:?\s*(.+?)(?=No caso.*contacto.*olhos|Se for engolido|4\.2|5\.|$)',
            r'Contacto com a pele\s*:?\s*(.+?)(?=Contacto.*olhos|Ingestão|4\.2|5\.|$)',
            r'Por contacto.*pele\s*:?\s*(.+?)(?=Por contacto.*olhos|Por ingestão|4\.2|5\.|$)',
        ]
        
        for pattern in pele_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                first_aid['contato_pele'] = self.clean_text(match.group(1))
                break
        
        # Contato com os olhos
        olhos_patterns = [
            r'No caso.*contacto.*olhos\s*:?\s*(.+?)(?=Se for engolido|4\.2|5\.|MEDIDAS DE COMBATE|$)',
            r'Contacto com os olhos\s*:?\s*(.+?)(?=Ingestão|4\.2|5\.|MEDIDAS DE COMBATE|$)',
        ]
        
        for pattern in olhos_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                first_aid['contato_olhos'] = self.clean_text(match.group(1))
                break
        
        # Ingestão
        ingestao_patterns = [
            r'Se for engolido\s*:?\s*(.+?)(?=4\.2|5\.|MEDIDAS DE COMBATE|$)',
            r'Ingestão\s*:?\s*(.+?)(?=4\.2|5\.|MEDIDAS DE COMBATE|$)',
            r'Por ingestão\s*:?\s*(.+?)(?=4\.2|5\.|MEDIDAS DE COMBATE|$)',
        ]
        
        for pattern in ingestao_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                first_aid['ingestao'] = self.clean_text(match.group(1))
                break
            
        # Sintomas
        sintomas_patterns = [
            r'Sintomas e efeitos.*?agudos.*?retardados\s*:?\s*(.+?)(?=4\.3|5\.|$)',
            r'Sinais e sintomas.*exposição\s*:?\s*(.+?)(?=Informação adicional|11\.|12\.|$)',
            r'Principais sintomas\s*:?\s*(.+?)(?=4\.3|5\.|$)',
        ]
        
        for pattern in sintomas_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                first_aid['sintomas'] = self.clean_text(match.group(1))
                break
        
        return first_aid

    def extract_fire_fighting(self, text):
        fire_fighting = {}
        if not text:
            return fire_fighting
        
        # Meios de extinção
        extincao_patterns = [
            r'Meios adequados de extinção\s*:?\s*(.+?)(?=Meios.*extinção.*não|Perigos especiais|5\.2|5\.3|$)',
            r'5\.1.*?extinção\s*:?\s*(.+?)(?=5\.2|5\.3|$)',
            r'Agentes extintores\s*:?\s*(.+?)(?=5\.2|5\.3|$)',
        ]
        
        for pattern in extincao_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                fire_fighting['meios_extincao'] = self.clean_text(match.group(1))
                break
        
        # Perigos especiais
        perigos_patterns = [
            r'Perigos especiais.*?substância.*?mistura\s*:?\s*(.+?)(?=5\.3|6\.|$)',
            r'5\.2.*?Perigos especiais\s*:?\s*(.+?)(?=5\.3|6\.|$)',
            r'Perigos específicos\s*:?\s*(.+?)(?=5\.3|6\.|$)',
        ]
        
        for pattern in perigos_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                fire_fighting['perigos_especificos'] = self.clean_text(match.group(1))
                break
        
        return fire_fighting

    def extract_handling_storage(self, text):
        handling = {}
        if not text:
            return handling
        
        # Precauções de manuseio
        manuseio_patterns = [
            r'Precauções.*manuseamento seguro\s*:?\s*(.+?)(?=Condições.*armazenagem|7\.2|8\.|$)',
            r'7\.1.*?manuseamento seguro\s*:?\s*(.+?)(?=7\.2|8\.|$)',
            r'Manuseamento\s*:?\s*(.+?)(?=Armazenagem|7\.2|8\.|$)',
        ]
        
        for pattern in manuseio_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                handling['precaucoes_manuseio'] = self.clean_text(match.group(1))
                break
        
        return handling

    def parse_file(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            identification = self.extract_identification(content)
            transport_info = self.extract_transport_info(content)
            
            # Consolidar informações de transporte com identificação
            if 'numero_onu' not in identification and transport_info.get('numero_onu'):
                identification['numero_onu'] = transport_info['numero_onu']
            
            if 'classe_risco' not in identification and transport_info.get('classe_risco'):
                identification['classe_risco'] = transport_info['classe_risco']
                identification['risco_subsidiario'] = transport_info['classe_risco']
            
            if 'numero_risco' not in identification and transport_info.get('numero_risco'):
                identification['numero_risco'] = transport_info['numero_risco']
                
            if 'grupo_embalagem' not in identification and transport_info.get('grupo_embalagem'):
                identification['grupo_embalagem'] = transport_info['grupo_embalagem']
            
            # Verificar se pelo menos o número ONU foi encontrado
            if 'numero_onu' not in identification:
                print(f"  ⚠️  Arquivo {os.path.basename(file_path)}: Número ONU não encontrado")
                return None
            
            result = {
                "arquivo": os.path.basename(file_path),
                "data_processamento": datetime.now().isoformat(),
                "identificacao": identification,
                "transporte": transport_info,
                "emergencia": {
                    "primeiros_socorros": self.extract_first_aid(content),
                    "combate_incendio": self.extract_fire_fighting(content)
                },
                "manuseio_armazenamento": self.extract_handling_storage(content)
            }
            
            return result
            
        except Exception as e:
            print(f"Erro ao processar arquivo {file_path}: {str(e)}")
            return None

    def save_to_database(self, data):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        identificacao = data.get('identificacao', {})
        primeiros_socorros = data.get('emergencia', {}).get('primeiros_socorros', {})
        combate_incendio = data.get('emergencia', {}).get('combate_incendio', {})
        manuseio = data.get('manuseio_armazenamento', {})
        
        cursor.execute('''
        INSERT INTO fispq_data (
            arquivo, data_processamento, substancia, numero_onu, classe_risco,
            numero_risco, risco_subsidiario, grupo_embalagem, primeiros_socorros_inalacao,
            primeiros_socorros_contato_pele, primeiros_socorros_contato_olhos,
            primeiros_socorros_ingestao, primeiros_socorros_sintomas,
            combate_incendio_meios_extincao, combate_incendio_perigos_especificos,
            manuseio_precaucoes, dados_completos_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('arquivo', ''),
            data.get('data_processamento', ''),
            identificacao.get('substancia', ''),
            identificacao.get('numero_onu', ''),
            identificacao.get('classe_risco', ''),
            identificacao.get('numero_risco', ''),
            identificacao.get('risco_subsidiario', ''),
            identificacao.get('grupo_embalagem', ''),
            primeiros_socorros.get('inalacao', ''),
            primeiros_socorros.get('contato_pele', ''),
            primeiros_socorros.get('contato_olhos', ''),
            primeiros_socorros.get('ingestao', ''),
            primeiros_socorros.get('sintomas', ''),
            combate_incendio.get('meios_extincao', ''),
            combate_incendio.get('perigos_especificos', ''),
            manuseio.get('precaucoes_manuseio', ''),
            json.dumps(data, ensure_ascii=False)
        ))
        
        conn.commit()
        conn.close()

    def process_directory(self, directory_path, json_output="fispq_dados_extraidos.json"):
        results = []
        directory = Path(directory_path)
        
        fispq_files = list(directory.glob("*.txt"))
        
        if not fispq_files:
            print(f"Nenhum arquivo .txt encontrado em {directory_path}")
            return
        
        print(f"Encontrados {len(fispq_files)} arquivos para processar...")
        
        valid_files = 0
        discarded_files = 0
        processing_details = []
        
        for file_path in fispq_files:
            print(f"Processando: {file_path.name}")
            result = self.parse_file(file_path)
            
            if result and result.get('identificacao', {}).get('numero_onu'):
                results.append(result)
                self.save_to_database(result)
                
                identificacao = result['identificacao']
                substancia = identificacao.get('substancia', 'N/A')
                numero_onu = identificacao.get('numero_onu', 'N/A')
                classe_risco = identificacao.get('classe_risco', 'N/A')
                numero_risco = identificacao.get('numero_risco', 'N/A')
                
                detail = f"  ✓ Substância: {substancia} | ONU: {numero_onu} | Classe: {classe_risco} | Nº Risco: {numero_risco}"
                print(detail)
                processing_details.append(detail)
                valid_files += 1
            else:
                detail = f"  ✗ Descartado - Sem número ONU: {file_path.name}"
                print(detail)
                processing_details.append(detail)
                discarded_files += 1
        
        # Salvar JSON
        with open(json_output, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        # Relatório detalhado
        print(f"\n=== RELATÓRIO FINAL ===")
        print(f"Total de arquivos encontrados: {len(fispq_files)}")
        print(f"Arquivos processados com sucesso: {valid_files}")
        print(f"Arquivos descartados (sem ONU): {discarded_files}")
        print(f"Taxa de sucesso: {(valid_files/len(fispq_files)*100):.1f}%")
        print(f"JSON salvo em: {json_output}")
        print(f"Banco de dados: {self.db_path}")
        
        # Estatísticas por classe
        stats = self.get_statistics()
        if stats['distribuicao_classes']:
            print(f"\nDistribuição por classe de risco:")
            for classe, count in sorted(stats['distribuicao_classes'].items()):
                if classe:
                    print(f"  Classe {classe}: {count} produtos")
        
        return results

    def query_by_onu(self, numero_onu):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM fispq_data WHERE numero_onu = ?', (numero_onu,))
        result = cursor.fetchone()
        
        conn.close()
        return result

    def query_by_substance(self, substancia):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM fispq_data WHERE substancia LIKE ?', (f'%{substancia}%',))
        results = cursor.fetchall()
        
        conn.close()
        return results

    def get_statistics(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM fispq_data')
        total = cursor.fetchone()[0]
        
        cursor.execute('SELECT classe_risco, COUNT(*) FROM fispq_data GROUP BY classe_risco ORDER BY classe_risco')
        classes = cursor.fetchall()
        
        cursor.execute('SELECT COUNT(*) FROM fispq_data WHERE numero_risco IS NOT NULL AND numero_risco != ""')
        with_numero_risco = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_registros': total,
            'distribuicao_classes': dict(classes),
            'com_numero_risco': with_numero_risco
        }

    def debug_extraction(self, file_path):
        """Função para debug - mostra o que foi extraído de um arquivo específico"""
        try:
            if not os.path.exists(file_path):
                print(f"Arquivo não encontrado: {file_path}")
                return
                
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            print(f"=== DEBUG: {os.path.basename(file_path)} ===")
            print(f"Tamanho do arquivo: {len(content)} caracteres")
            
            identification = self.extract_identification(content)
            transport_info = self.extract_transport_info(content)
            
            print("\nIDENTIFICAÇÃO EXTRAÍDA:")
            if identification:
                for key, value in identification.items():
                    print(f"  {key}: {value}")
            else:
                print("  Nenhuma identificação extraída")
            
            print("\nINFORMAÇÕES DE TRANSPORTE:")
            if transport_info:
                for key, value in transport_info.items():
                    print(f"  {key}: {value}")
            else:
                print("  Nenhuma informação de transporte extraída")
            
            # Buscar padrões no texto bruto
            print("\nPADRÕES ENCONTRADOS NO TEXTO:")
            
            # Buscar números de 4 dígitos
            numeros_4_digitos = list(set(re.findall(r'\b\d{4}\b', content)))
            if numeros_4_digitos:
                print(f"  Números 4 dígitos encontrados: {numeros_4_digitos}")
            
            # Buscar padrões ONU específicos
            onu_contexts = []
            for pattern in [r'ONU.*?(\d{4})', r'UN.*?(\d{4})', r'ADR.*?(\d{4})']:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    start = max(0, match.start() - 20)
                    end = min(len(content), match.end() + 20)
                    context = content[start:end].replace('\n', ' ').strip()
                    onu_contexts.append(f"'{context}'")
            
            if onu_contexts:
                print(f"  Contextos com possível ONU: {onu_contexts[:5]}")
            
            # Mostrar início do arquivo para análise manual
            print(f"\nPRIMEIROS 500 CARACTERES:")
            print(repr(content[:500]))
                
        except Exception as e:
            print(f"Erro no debug: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    processor = FISPQProcessor()
    
    # Debug do arquivo problemático primeiro
    debug_file = "/home/mauricio-cunha/Documentos/reconhecimento-placas-fispq-main/arquivos_extraidos/json/debug_fispq_158_Carbonato_de_sodio_m.txt"
    print("=== FAZENDO DEBUG DO ARQUIVO PROBLEMÁTICO ===")
    processor.debug_extraction(debug_file)
    print("\n" + "="*60 + "\n")
    
    directory_path = "/home/mauricio-cunha/Documentos/reconhecimento-placas-fispq-main/arquivos_extraidos/json"
    
    results = processor.process_directory(directory_path, "fispq_completo.json")
    
    stats = processor.get_statistics()
    print(f"\n=== ESTATÍSTICAS FINAIS ===")
    print(f"Total de registros no banco: {stats['total_registros']}")
    print(f"Registros com número de risco: {stats['com_numero_risco']}")
    print("Distribuição por classe de risco:")
    for classe, count in stats['distribuicao_classes'].items():
        if classe:
            print(f"  Classe {classe}: {count} produtos")