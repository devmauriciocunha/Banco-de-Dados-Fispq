import sqlite3
import logging
import json
import os
from datetime import datetime
from typing import Dict, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path="fispq_database.db"):
        self.db_path = db_path
        self.conn = None
        self.conectar()
        self.criar_tabelas()

    def conectar(self):
        """Conecta ao banco de dados SQLite."""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row  # Para retornar dicts
            logger.info("✅ Conectado ao banco de dados")
        except Exception as e:
            logger.error(f"❌ Erro ao conectar no banco: {e}")

    def criar_tabelas(self):
        """Cria as tabelas para dados de FISPQ."""
        try:
            cursor = self.conn.cursor()
            
            # Tabela principal de produtos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS produtos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    arquivo TEXT NOT NULL,
                    substancia TEXT,
                    numero_onu TEXT,
                    classe_risco TEXT,
                    numero_risco TEXT,
                    risco_subsidiario TEXT,
                    data_processamento TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(numero_onu, substancia)
                )
            """)
            
            # Tabela de primeiros socorros
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS primeiros_socorros (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    produto_id INTEGER,
                    inalacao TEXT,
                    contato_pele TEXT,
                    contato_olhos TEXT,
                    ingestao TEXT,
                    sintomas TEXT,
                    notas_medico TEXT,
                    FOREIGN KEY(produto_id) REFERENCES produtos(id)
                )
            """)
            
            # Tabela de combate a incêndio
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS combate_incendio (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    produto_id INTEGER,
                    meios_extincao TEXT,
                    perigos_especificos TEXT,
                    protecao_equipe TEXT,
                    FOREIGN KEY(produto_id) REFERENCES produtos(id)
                )
            """)
            
            # Tabela de propriedades
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS propriedades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    produto_id INTEGER,
                    aspecto TEXT,
                    odor TEXT,
                    ph TEXT,
                    ponto_fusao TEXT,
                    ponto_ebulicao TEXT,
                    ponto_fulgor TEXT,
                    densidade TEXT,
                    solubilidade TEXT,
                    FOREIGN KEY(produto_id) REFERENCES produtos(id)
                )
            """)
            
            # Tabela de manuseio e armazenamento
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS manuseio_armazenamento (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    produto_id INTEGER,
                    precaucoes_manuseio TEXT,
                    condicoes_armazenamento TEXT,
                    FOREIGN KEY(produto_id) REFERENCES produtos(id)
                )
            """)
            
            self.conn.commit()
            logger.info("✅ Tabelas criadas com sucesso")
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar tabelas: {e}")

    def inserir_produto(self, dados: Dict) -> Optional[int]:
        """Insere um produto completo no banco de dados."""
        try:
            cursor = self.conn.cursor()
            
            # Extrair dados de identificação
            identificacao = dados.get("identificacao", {})
            
            # Inserir produto principal
            cursor.execute("""
                INSERT OR IGNORE INTO produtos 
                (arquivo, substancia, numero_onu, classe_risco, numero_risco, 
                 risco_subsidiario, data_processamento)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                dados.get("arquivo"),
                identificacao.get("substancia"),
                identificacao.get("numero_onu"),
                identificacao.get("classe_risco"),
                identificacao.get("numero_risco"),
                identificacao.get("risco_subsidiario"),
                dados.get("data_processamento")
            ))
            
            produto_id = cursor.lastrowid
            
            # Se produto já existe, pegar ID
            if produto_id == 0:
                cursor.execute("""
                    SELECT id FROM produtos 
                    WHERE numero_onu = ? AND substancia = ?
                """, (identificacao.get("numero_onu"), identificacao.get("substancia")))
                result = cursor.fetchone()
                if result:
                    produto_id = result[0]
            
            if produto_id:
                # Inserir primeiros socorros
                primeiros_socorros = dados.get("emergencia", {}).get("primeiros_socorros", {})
                if primeiros_socorros:
                    cursor.execute("""
                        INSERT OR REPLACE INTO primeiros_socorros
                        (produto_id, inalacao, contato_pele, contato_olhos, 
                         ingestao, sintomas, notas_medico)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        produto_id,
                        primeiros_socorros.get("inalacao"),
                        primeiros_socorros.get("contato_pele"),
                        primeiros_socorros.get("contato_olhos"),
                        primeiros_socorros.get("ingestao"),
                        primeiros_socorros.get("sintomas"),
                        primeiros_socorros.get("notas_medico")
                    ))
                
                # Inserir combate a incêndio
                combate_incendio = dados.get("emergencia", {}).get("combate_incendio", {})
                if combate_incendio:
                    cursor.execute("""
                        INSERT OR REPLACE INTO combate_incendio
                        (produto_id, meios_extincao, perigos_especificos, protecao_equipe)
                        VALUES (?, ?, ?, ?)
                    """, (
                        produto_id,
                        combate_incendio.get("meios_extincao"),
                        combate_incendio.get("perigos_especificos"),
                        combate_incendio.get("protecao_equipe")
                    ))
                
                # Inserir propriedades
                propriedades = dados.get("propriedades", {})
                if propriedades:
                    cursor.execute("""
                        INSERT OR REPLACE INTO propriedades
                        (produto_id, aspecto, odor, ph, ponto_fusao, ponto_ebulicao, 
                         ponto_fulgor, densidade, solubilidade)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        produto_id,
                        propriedades.get("aspecto"),
                        propriedades.get("odor"),
                        propriedades.get("ph"),
                        propriedades.get("ponto_fusao"),
                        propriedades.get("ponto_ebulicao"),
                        propriedades.get("ponto_fulgor"),
                        propriedades.get("densidade"),
                        propriedades.get("solubilidade")
                    ))
                
                # Inserir manuseio e armazenamento
                manuseio = dados.get("manuseio_armazenamento", {})
                if manuseio:
                    cursor.execute("""
                        INSERT OR REPLACE INTO manuseio_armazenamento
                        (produto_id, precaucoes_manuseio, condicoes_armazenamento)
                        VALUES (?, ?, ?)
                    """, (
                        produto_id,
                        manuseio.get("precaucoes_manuseio"),
                        manuseio.get("condicoes_armazenamento")
                    ))
                
                self.conn.commit()
                logger.info(f"✅ Produto inserido no BD - ID: {produto_id}")
                return produto_id
            
        except Exception as e:
            logger.error(f"❌ Erro ao inserir produto: {e}")
            self.conn.rollback()
            return None

    def buscar_por_onu(self, numero_onu: str) -> Optional[Dict]:
        """Busca produto por número ONU."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT * FROM produtos WHERE numero_onu = ?
            """, (numero_onu,))
            
            produto = cursor.fetchone()
            if produto:
                return dict(produto)
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar por ONU: {e}")
            return None

    def buscar_por_substancia(self, nome_substancia: str) -> List[Dict]:
        """Busca produtos por nome da substância."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT * FROM produtos 
                WHERE substancia LIKE ?
            """, (f"%{nome_substancia}%",))
            
            produtos = cursor.fetchall()
            return [dict(produto) for produto in produtos]
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar por substância: {e}")
            return []

    def buscar_por_classe_risco(self, classe_risco: str) -> List[Dict]:
        """Busca produtos por classe de risco."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT * FROM produtos WHERE classe_risco = ?
            """, (classe_risco,))
            
            produtos = cursor.fetchall()
            return [dict(produto) for produto in produtos]
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar por classe de risco: {e}")
            return []

    def obter_estatisticas(self) -> Dict:
        """Retorna estatísticas do banco de dados."""
        try:
            cursor = self.conn.cursor()
            
            # Total de produtos
            cursor.execute("SELECT COUNT(*) FROM produtos")
            total_produtos = cursor.fetchone()[0]
            
            # Produtos por classe de risco
            cursor.execute("""
                SELECT classe_risco, COUNT(*) as qtd 
                FROM produtos 
                WHERE classe_risco IS NOT NULL 
                GROUP BY classe_risco 
                ORDER BY qtd DESC
            """)
            por_classe = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Produtos mais recentes
            cursor.execute("""
                SELECT substancia, numero_onu, data_processamento 
                FROM produtos 
                ORDER BY created_at DESC 
                LIMIT 5
            """)
            mais_recentes = []
            for row in cursor.fetchall():
                mais_recentes.append({
                    'substancia': row[0],
                    'onu': row[1],
                    'data': row[2]
                })
            
            return {
                'total_produtos': total_produtos,
                'por_classe_risco': por_classe,
                'mais_recentes': mais_recentes
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter estatísticas: {e}")
            return {}

    def carregar_json_consolidado(self, caminho_json: str) -> Dict:
        """Carrega dados de um JSON consolidado para o banco."""
        sucessos = 0
        erros = 0
        
        try:
            with open(caminho_json, 'r', encoding='utf-8') as f:
                dados = json.load(f)
            
            for item in dados:
                if self.inserir_produto(item):
                    sucessos += 1
                else:
                    erros += 1
                    
            logger.info(f"🔄 Carga concluída: {sucessos} sucessos, {erros} erros")
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar JSON: {e}")
            erros += 1
        
        return {'sucessos': sucessos, 'erros': erros}

    def exportar_para_json(self, caminho_saida: str) -> bool:
        """Exporta dados do banco para JSON."""
        try:
            cursor = self.conn.cursor()
            
            # Buscar todos os produtos com dados relacionados
            cursor.execute("""
                SELECT 
                    p.*,
                    ps.inalacao, ps.contato_pele, ps.contato_olhos, ps.ingestao, 
                    ps.sintomas, ps.notas_medico,
                    ci.meios_extincao, ci.perigos_especificos, ci.protecao_equipe,
                    pr.aspecto, pr.odor, pr.ph, pr.ponto_fusao, pr.ponto_ebulicao,
                    pr.ponto_fulgor, pr.densidade, pr.solubilidade,
                    ma.precaucoes_manuseio, ma.condicoes_armazenamento
                FROM produtos p
                LEFT JOIN primeiros_socorros ps ON p.id = ps.produto_id
                LEFT JOIN combate_incendio ci ON p.id = ci.produto_id  
                LEFT JOIN propriedades pr ON p.id = pr.produto_id
                LEFT JOIN manuseio_armazenamento ma ON p.id = ma.produto_id
            """)
            
            produtos_exportados = []
            
            for row in cursor.fetchall():
                produto = {
                    "arquivo": row[1],
                    "data_processamento": row[7],
                    "identificacao": {
                        "substancia": row[2],
                        "numero_onu": row[3],
                        "classe_risco": row[4],
                        "numero_risco": row[5],
                        "risco_subsidiario": row[6]
                    },
                    "emergencia": {
                        "primeiros_socorros": {
                            "inalacao": row[9],
                            "contato_pele": row[10],
                            "contato_olhos": row[11],
                            "ingestao": row[12],
                            "sintomas": row[13],
                            "notas_medico": row[14]
                        },
                        "combate_incendio": {
                            "meios_extincao": row[15],
                            "perigos_especificos": row[16],
                            "protecao_equipe": row[17]
                        }
                    },
                    "propriedades": {
                        "aspecto": row[18],
                        "odor": row[19],
                        "ph": row[20],
                        "ponto_fusao": row[21],
                        "ponto_ebulicao": row[22],
                        "ponto_fulgor": row[23],
                        "densidade": row[24],
                        "solubilidade": row[25]
                    },
                    "manuseio_armazenamento": {
                        "precaucoes_manuseio": row[26],
                        "condicoes_armazenamento": row[27]
                    }
                }
                
                # Remove campos vazios
                produto = self._remover_campos_vazios(produto)
                produtos_exportados.append(produto)
            
            # Salvar JSON
            with open(caminho_saida, 'w', encoding='utf-8') as f:
                json.dump(produtos_exportados, f, ensure_ascii=False, indent=2)
            
            logger.info(f"📤 {len(produtos_exportados)} produtos exportados para {caminho_saida}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao exportar: {e}")
            return False

    def _remover_campos_vazios(self, dados):
        """Remove campos vazios recursivamente."""
        if isinstance(dados, dict):
            return {k: self._remover_campos_vazios(v) for k, v in dados.items() 
                   if v is not None and v != "" and v != {}}
        elif isinstance(dados, list):
            return [self._remover_campos_vazios(item) for item in dados if item]
        else:
            return dados

    def fechar_conexao(self):
        """Fecha conexão com o banco."""
        if self.conn:
            self.conn.close()
            logger.info("🔌 Conexão com banco fechada")

    def __del__(self):
        """Destrutor para garantir fechamento da conexão."""
        self.fechar_conexao()