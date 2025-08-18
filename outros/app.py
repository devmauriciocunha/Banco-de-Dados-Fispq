from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import pandas as pd
import time


tabela = pd.read_excel("/home/mauricio-cunha/Documentos/reconhecimento-placas-fispq-main/ONU.xlsx") 
coluna_numeros = tabela["Nº ONU\n(1)"].dropna().astype(int).astype(str).str.zfill(4).tolist()

todos_dados = []


for numero in coluna_numeros[:100]:
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")  
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    navegador = webdriver.Chrome(options=options)
    wait = WebDriverWait(navegador, 15) 
    print(f"Processando o número ONU: {numero}")

    try:
        navegador.get("http://200.144.30.103/siipp/public/busca_pp.aspx")  

       
        wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="txtProduto"]'))).send_keys(numero)
        wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="btPesquisar"]'))).click()

       
        time.sleep(3) 
        try:
            tabela_resultados = wait.until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="dgLista"]/tbody'))
            )
            linhas = tabela_resultados.find_elements(By.TAG_NAME, "tr")
            if len(linhas) < 2:  
                print(f"Nenhum resultado encontrado para o número ONU: {numero}")
                navegador.quit()
                continue

            
            primeiro_resultado = linhas[1].find_elements(By.TAG_NAME, "td")[1]
            time.sleep(1)  #
            primeiro_resultado.click()
        except TimeoutException:
            print(f"Nenhum resultado encontrado para o número ONU: {numero}")
            navegador.quit()
            continue

        
        janela_principal = navegador.current_window_handle
        if len(navegador.window_handles) > 1:
            for janela in navegador.window_handles:
                if janela != janela_principal:
                    navegador.switch_to.window(janela)
                    break

        
        try:
            tabela_elemento = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="tabProduto"]')))
            linhas = tabela_elemento.find_elements(By.TAG_NAME, "tr")
        except TimeoutException:
            print(f"Não foi possível carregar a tabela de dados para ONU {numero}")
            navegador.quit()
            continue

       
        dados_onu = {"Nº ONU": numero}
        for linha in linhas:
            th = linha.find_elements(By.TAG_NAME, "th")
            td = linha.find_elements(By.TAG_NAME, "td")
            if th:  # ignora cabeçalho
                continue
            if len(td) >= 2:
                chave = td[0].text.strip().replace(":", "")
                valor = td[1].text.strip()
                dados_onu[chave] = valor

        todos_dados.append(dados_onu)

        
        if len(navegador.window_handles) > 1:
            navegador.close()
            navegador.switch_to.window(janela_principal)

    except (WebDriverException, Exception) as e:
        print(f"Erro ao processar ONU {numero}: {e}")
    finally:
        navegador.quit()


df_final = pd.DataFrame(todos_dados)

csv_path = "/home/mauricio-cunha/Documentos/reconhecimento-placas-fispq-main/resultado.csv"
df_final.to_csv(csv_path, index=False)
print(f"Dados salvos em CSV: {csv_path}")

json_path = "/home/mauricio-cunha/Documentos/reconhecimento-placas-fispq-main/resultado.json"
df_final.to_json(json_path, orient="records", force_ascii=False, indent=4)
print(f"Dados salvos em JSON: {json_path}")
