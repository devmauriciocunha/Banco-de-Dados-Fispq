import sqlite3
import logging
import os
from datetime import datetime

# Configuração do log
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

class DatabaseManager:
    def __init__(self, db_name="fispq.db"):
        self.db_name = db_name
        self.conn = None
        self.cursor = None
        self.conectar()

    def conectar(self):
        """Conecta ao banco de dados SQLite."""
        try:
            self.conn = sqlite3.connect(self.db_name)
            self.cursor = self.conn.cursor()
            logging.info("✅ Banco de dados inicializado com sucesso")
        except Exception as e:
            logging.error(f"❌ Erro ao conectar no banco: {e}")

    def criar_tabelas(self):
        """Cria as tabelas principais."""
        try:
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS substancias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                fornecedor TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS fispq (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                substancia_id INTEGER,
                lote TEXT,
                valor REAL,
                competencia TEXT,
                FOREIGN KEY(substancia_id) REFERENCES substancias(id)
            )
            """)

            self.conn.commit()
            logging.info("✅ Tabelas criadas com sucesso")
        except Exception as e:
            logging.error(f"❌ Erro ao criar tabelas: {e}")

    def criar_view(self):
        """Cria uma view unificada juntando as tabelas."""
        try:
            self.cursor.execute("DROP VIEW IF EXISTS view_fispq_unificada")
            self.cursor.execute("""
            CREATE VIEW view_fispq_unificada AS
            SELECT s.id AS substancia_id, s.nome, s.fornecedor,
                   f.lote, f.valor, f.competencia
            FROM substancias s
            LEFT JOIN fispq f ON s.id = f.substancia_id
            """)
            self.conn.commit()
            logging.info("✅ View unificada criada com sucesso")
        except Exception as e:
            logging.error(f"❌ Erro ao criar view: {e}")

    def inserir_dados_teste(self):
        """Insere dados fictícios para teste."""
        try:
            self.cursor.execute("INSERT INTO substancias (nome, fornecedor) VALUES (?, ?)", 
                                ("Ácido Sulfúrico", "Fornecedor A"))
            self.cursor.execute("INSERT INTO substancias (nome, fornecedor) VALUES (?, ?)", 
                                ("Soda Cáustica", "Fornecedor B"))

            self.cursor.execute("INSERT INTO fispq (substancia_id, lote, valor, competencia) VALUES (?, ?, ?, ?)", 
                                (1, "L001", 1500.75, "2025-08"))
            self.cursor.execute("INSERT INTO fispq (substancia_id, lote, valor, competencia) VALUES (?, ?, ?, ?)", 
                                (2, "L002", 3200.40, "2025-08"))

            self.conn.commit()
            logging.info("✅ Dados de teste inseridos com sucesso")
        except Exception as e:
            logging.error(f"❌ Erro ao inserir dados de teste: {e}")

    def obter_estatisticas(self):
        """Retorna estatísticas do banco."""
        try:
            self.cursor.execute("SELECT COUNT(*) FROM substancias")
            total_substancias = self.cursor.fetchone()[0]

            self.cursor.execute("SELECT COUNT(*) FROM fispq")
            total_registros = self.cursor.fetchone()[0]

            self.cursor.execute("SELECT IFNULL(SUM(valor),0) FROM fispq")
            total_valor = self.cursor.fetchone()[0]

            return {
                "total_substancias": total_substancias,
                "total_registros": total_registros,
                "valor_total": total_valor
            }
        except Exception as e:
            logging.error(f"❌ Erro ao obter estatísticas: {e}")
            return {}

    def executar_consulta(self, query, params=()):
        """Executa consultas personalizadas."""
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except Exception as e:
            logging.error(f"❌ Erro na consulta: {e}")
            return []

if __name__ == "__main__":
    db = DatabaseManager()
    db.criar_tabelas()
    db.criar_view()

    # Inserir dados de teste só na primeira vez
    if not os.path.exists(".dados_inseridos.flag"):
        db.inserir_dados_teste()
        with open(".dados_inseridos.flag", "w") as f:
            f.write("ok")

    # Estatísticas
    stats = db.obter_estatisticas()
    print("📊 Estatísticas do banco:")
    print(stats)

    # Consulta exemplo
    print("\n📋 Dados na view unificada:")
    resultados = db.executar_consulta("SELECT * FROM view_fispq_unificada")
    for linha in resultados:
        print(linha)
