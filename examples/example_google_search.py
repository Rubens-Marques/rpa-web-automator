"""
Exemplo: busca automatizada no Google e extração dos títulos dos resultados.
"""
import csv
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from src.rpa.base import WebAutomator


def search_and_extract(query: str, output_csv: str = "/tmp/resultados.csv"):
    results = []
    with WebAutomator(headless=True) as bot:
        bot.go("https://www.google.com.br")
        time.sleep(1)
        search_box = bot.wait_for("textarea[name='q']")
        search_box.send_keys(query)
        search_box.send_keys(Keys.RETURN)
        time.sleep(2)
        elements = bot.driver.find_elements(By.CSS_SELECTOR, "h3")
        for el in elements[:10]:
            title = el.text.strip()
            if title:
                results.append({"titulo": title})
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["titulo"])
        writer.writeheader()
        writer.writerows(results)
    print(f"✓ {len(results)} resultados salvos em {output_csv}")
    return results


if __name__ == "__main__":
    search_and_extract("automação de processos Python")
