import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import csv
import os
import json

def extrair_dados_da_tabela(driver):
    """
    Extrai os dados da tabela de informações do produto usando XPATHs flexíveis.
    """
    dados = {}
    mapeamento = {
        "Nº ONU": "numero_onu",
        "Descrição": "descricao",
        "Classe de risco": "classe_risco",
        "Classe": "classe",
        "Provisões especiais": "provisoes_especiais",
        "Qtde (kg) por veículo": "qtde_kg",
        "Qtde (embalagem) por veículo": "qtde_embalagem",
        "Embalagem instruções": "embalagem_instrucoes",
        "Placa": "placa",
    }
    
    for label, key in mapeamento.items():
        try:
            xpath_label = f"//td[contains(text(),'{label}')]"
            elemento_label = driver.find_element(By.XPATH, xpath_label)
            elemento_valor = elemento_label.find_element(By.XPATH, "./following-sibling::td")
            dados[key] = elemento_valor.text.strip()
        except Exception:
            dados[key] = None
    
    try:
        xpath_epi_label = "//td[contains(text(),'EPI:')]"
        elemento_epi_label = driver.find_element(By.XPATH, xpath_epi_label)
        elemento_epi_valor = elemento_epi_label.find_element(By.XPATH, "./following-sibling::td")
        epi_texto = elemento_epi_valor.text.strip()
        dados["epi"] = [item.strip() for item in epi_texto.split('\n') if item.strip()]
    except Exception:
        dados["epi"] = None
        
    return dados

def automacao_com_excel(excel_path, csv_saida):
    """
    Lê uma planilha, itera pelos números da coluna "Nº ONU", pesquisa
    no site, extrai os dados, baixa o JSON e salva tudo em um arquivo CSV.
    """
    print("Iniciando a automação...")
    
    try:
        df = pd.read_excel(excel_path)
        numeros_onu = df["Nº ONU\n(1)"].dropna().astype(int).astype(str).str.zfill(4).tolist()
    except Exception as e:
        print(f"❌ Erro ao ler a planilha Excel: {e}")
        return

    dados_totais = []
    
    pasta_json = "jsons_onu"
    os.makedirs(pasta_json, exist_ok=True)

    service = Service()
    options = webdriver.ChromeOptions()
    driver = None
    
    try:
        driver = webdriver.Chrome(service=service, options=options)
        wait = WebDriverWait(driver, 10)
        
        for numero in numeros_onu:
            print(f"\n🚀 Processando número ONU: {numero}")
            
            url = "http://200.144.30.103/siipp/public/busca_pp.aspx"
            driver.get(url)
            original_window = driver.current_window_handle
            
            try:
                campo_produto = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="txtProduto"]')))
                campo_produto.clear()
                campo_produto.send_keys(numero)
                
                botao_pesquisar = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="btPesquisar"]')))
                botao_pesquisar.click()
                
                # CORREÇÃO: Usa um XPATH dinâmico para encontrar o link de resultado na tabela
                xpath_link_resultado = f"//table[@id='dgLista']//td[text()='{numero}']/following-sibling::td/a"
                link_resultado = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_link_resultado)))
                link_resultado.click()
                
                wait.until(EC.number_of_windows_to_be(2))
                for window_handle in driver.window_handles:
                    if window_handle != original_window:
                        driver.switch_to.window(window_handle)
                        break
                
                dados_extraidos = extrair_dados_da_tabela(driver)
                
                if dados_extraidos:
                    dados_totais.append(dados_extraidos)
                    print(f"✅ Dados para {numero} extraídos com sucesso.")
                    
                    # Extração e salvamento do JSON
                    json_content = driver.page_source
                    try:
                        start = json_content.find('{')
                        end = json_content.rfind('}') + 1
                        if start != -1 and end != -1:
                            json_text = json_content[start:end]
                            json_data = json.loads(json_text)
                            
                            nome_arquivo_json = os.path.join(pasta_json, f"dados_onu_{numero}.json")
                            with open(nome_arquivo_json, 'w', encoding='utf-8') as f:
                                json.dump(json_data, f, indent=4, ensure_ascii=False)
                            print(f"✅ JSON para {numero} baixado com sucesso em '{nome_arquivo_json}'.")
                    except Exception as e:
                        print(f"❌ Erro ao extrair/salvar JSON para {numero}: {e}")
                else:
                    print(f"⚠️ Não foi possível extrair dados para {numero}. Dados vazios ou incompletos.")
            
                driver.close()
                driver.switch_to.window(original_window)

            except TimeoutException:
                print(f"❌ Tempo limite excedido. Nenhum resultado encontrado para o número {numero}. Pulando...")
            except NoSuchElementException:
                print(f"❌ Elemento não encontrado. Nenhum resultado para o número {numero} ou a página mudou. Pulando...")
            except Exception as e:
                print(f"❌ Ocorreu um erro ao processar o número {numero}: {e}")

    except Exception as e:
        print(f"❌ Ocorreu um erro geral durante a automação: {e}")

    finally:
        if 'driver' in locals() and driver:
            print("\nFinalizando e fechando o navegador.")
            driver.quit()

    if dados_totais:
        print(f"\n✅ Salvando {len(dados_totais)} registros no arquivo CSV '{csv_saida}'...")
        fieldnames = list(dados_totais[0].keys())
        with open(csv_saida, 'w', newline='', encoding='utf-8') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames, delimiter=';')
            writer.writeheader()
            writer.writerows(dados_totais)
        print("✅ Processo concluído. CSV gerado com sucesso!")
    else:
        print("\n⚠️ Nenhum dado foi coletado para salvar no CSV.")

if __name__ == "__main__":
    caminho_excel = "/home/mauricio-cunha/Documentos/reconhecimento-placas-fispq-main/ONU.xlsx"
    caminho_csv_saida = "relatorio_onu_final.csv"
    
    automacao_com_excel(caminho_excel, caminho_csv_saida)