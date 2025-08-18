import json
from tabulate import tabulate

# Caminho do JSON
CAMINHO_JSON = "/home/mauricio-cunha/Documentos/reconhecimento-placas-fispq-main/teste/json/consolidado.json"

# Carrega os dados do arquivo JSON
with open(CAMINHO_JSON, "r", encoding="utf-8") as f:
    registros = json.load(f)


def consultar_por_onu():
    """Consulta um registro pelo número ONU"""
    numero_onu = input("\nDigite o número ONU que deseja consultar: ").strip()
    encontrados = [r for r in registros if r.get("identificacao", {}).get("numero_onu") == numero_onu]

    if not encontrados:
        print(f"\n⚠️ Nenhum registro encontrado para ONU {numero_onu}\n")
    else:
        for registro in encontrados:
            print("\n=== Resultado Encontrado ===")

            # Informações principais
            tabela_principal = [
                ["Arquivo", registro.get("arquivo")],
                ["Data Processamento", registro.get("data_processamento")],
                ["Substância", registro["identificacao"].get("substancia")],
                ["Número ONU", registro["identificacao"].get("numero_onu")],
                ["Classe de Risco", registro["identificacao"].get("classe_risco")],
                ["Número de Risco", registro["identificacao"].get("numero_risco")],
                ["Risco Subsidiário", registro["identificacao"].get("risco_subsidiario")]
            ]
            print(tabulate(tabela_principal, headers=["Campo", "Valor"], tablefmt="grid"))

            # Primeiros socorros
            primeiros_socorros = registro["emergencia"].get("primeiros_socorros", {})
            if primeiros_socorros:
                tabela_socorros = [[k.replace("_", " ").title(), v] for k, v in primeiros_socorros.items()]
                print("\n--- Primeiros Socorros ---")
                print(tabulate(tabela_socorros, headers=["Situação", "Procedimento"], tablefmt="fancy_grid"))

            # Combate ao incêndio
            combate = registro["emergencia"].get("combate_incendio", {})
            if combate:
                tabela_incendio = [[k.replace("_", " ").title(), v] for k, v in combate.items()]
                print("\n--- Combate ao Incêndio ---")
                print(tabulate(tabela_incendio, headers=["Aspecto", "Descrição"], tablefmt="fancy_grid"))

            # Manuseio / Armazenamento
            manuseio = registro.get("manuseio_armazenamento", {})
            if manuseio:
                tabela_manuseio = [[k.replace("_", " ").title(), v] for k, v in manuseio.items()]
                print("\n--- Manuseio e Armazenamento ---")
                print(tabulate(tabela_manuseio, headers=["Recomendação", "Descrição"], tablefmt="fancy_grid"))


def listar_substancias():
    """Lista todas as substâncias cadastradas"""
    tabela = []
    for r in registros:
        identificacao = r.get("identificacao", {})
        tabela.append([
            identificacao.get("numero_onu"),
            identificacao.get("substancia"),
            identificacao.get("classe_risco"),
            identificacao.get("numero_risco")
        ])

    print("\n=== Lista de Substâncias Cadastradas ===")
    print(tabulate(tabela, headers=["ONU", "Substância", "Classe Risco", "Número Risco"], tablefmt="grid"))


def menu():
    """Menu interativo"""
    while True:
        print("\n=== MENU PRINCIPAL ===")
        print("1 - Consultar substância por número ONU")
        print("2 - Listar todas as substâncias")
        print("3 - Sair")

        opcao = input("\nEscolha uma opção: ").strip()

        if opcao == "1":
            consultar_por_onu()
        elif opcao == "2":
            listar_substancias()
        elif opcao == "3":
            print("\n👋 Saindo do sistema...\n")
            break
        else:
            print("\n⚠️ Opção inválida, tente novamente!\n")


if __name__ == "__main__":
    menu()
