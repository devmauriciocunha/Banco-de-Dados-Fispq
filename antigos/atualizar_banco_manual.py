from antigos.extractor import FISPQExtractor

def main():
    # Criação de uma instância do extrator
    extractor = FISPQExtractor()

    # Atualiza o banco de dados a partir dos arquivos JSON alterados manualmente
    extractor.importar_json_manual_para_db()

if __name__ == '__main__':
    main()
