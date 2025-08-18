import sqlite3

def remove_medidas_fuga_column(db_path):
    try:
        # Conectar ao banco de dados
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # 1. Criar a nova tabela sem a coluna medidas_fuga
            cursor.execute("""
            CREATE TABLE fispq_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                substancia TEXT,
                numero_onu TEXT,
                numero_risco TEXT,
                classe TEXT,
                risco_subsidiario TEXT,
                primeiros_socorros TEXT,
                medidas_incendio TEXT,
                arquivo TEXT
            );
            """)

            # 2. Copiar os dados da tabela antiga para a nova tabela
            cursor.execute("""
            INSERT INTO fispq_new (id, substancia, numero_onu, numero_risco, classe, risco_subsidiario, primeiros_socorros, medidas_incendio, arquivo)
            SELECT id, substancia, numero_onu, numero_risco, classe, risco_subsidiario, primeiros_socorros, medidas_incendio, arquivo
            FROM fispq;
            """)

            # 3. Excluir a tabela antiga
            cursor.execute("DROP TABLE fispq;")

            # 4. Renomear a nova tabela para o nome original
            cursor.execute("ALTER TABLE fispq_new RENAME TO fispq;")

            print("✅ Coluna 'medidas_fuga' removida com sucesso!")
    except sqlite3.Error as e:
        print(f"❌ Erro ao remover a coluna: {e}")

# Caminho para o banco de dados
db_path = 'dados_fispq.db'
remove_medidas_fuga_column(db_path)
