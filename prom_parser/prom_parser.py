import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class PromParser:
    def __init__(self, query, max_price=None, max_pages=None):
        self.query = query
        self.max_price = max_price
        self.max_pages = max_pages
        self.data = []
        self.driver = None

    def start_driver(self):
        """Запуск браузера и поиск на Prom.ua"""
        self.driver = webdriver.Chrome()
        self.driver.get("https://prom.ua/")

        search_box = self.driver.find_element(By.NAME, "search_term")
        search_box.send_keys(self.query)
        search_box.send_keys(Keys.RETURN)

        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-qaid='product_block']"))
            )
        except TimeoutException:
            print("❌ Товары не найдены на странице поиска.")
            self.driver.quit()
            return

    def scroll_to_load_all(self):
        """Скроллим страницу, пока новые товары продолжают появляться"""
        last_count = 0
        while True:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            products = self.driver.find_elements(By.CSS_SELECTOR, "div[data-qaid='product_block']")
            if len(products) == last_count:
                break
            last_count = len(products)

    def expand_keywords(self):
        """Автоматическое расширение ключевых слов через базу синонимов"""
        base = self.query.lower()
        keywords = [base]

        synonyms_dict = {
            "футбол": ["футболка", "футболки", "футбольный"],
            "шлеп": ["шлёпки", "шлепанцы"],
            "комп": ["компьютер", "компьютеры", "комплектующие"],
            "телефон": ["смартфон", "мобильный", "айфон", "андроид"],
            "обувь": ["ботинки", "кроссовки", "туфли", "сандалии"],
            # Можно расширять словарь под нужные категории
        }

        for key, syn_list in synonyms_dict.items():
            if key in base:
                keywords.extend(syn_list)

        keywords = list(set(keywords))  # убираем дубликаты
        return keywords

    def fetch_products_from_page(self):
        """Сбор данных с текущей страницы с учётом ключевых слов"""
        keywords = self.expand_keywords()

        products = self.driver.find_elements(By.CSS_SELECTOR, "div[data-qaid='product_block']")
        for prod in products:
            try:
                name_tag = prod.find_element(By.CSS_SELECTOR, "span[data-qaid='product_name']")
                name = name_tag.text.strip()

                link_tag = prod.find_element(By.CSS_SELECTOR, "a[data-qaid='product_link']")
                link = link_tag.get_attribute("href")

                price_tag = prod.find_element(By.CSS_SELECTOR, "div[data-qaid='product_price'] span")
                price_text = price_tag.text.replace(" ", "").strip()
                price = int(price_text)

                if any(kw in name.lower() for kw in keywords):
                    if self.max_price is None or price <= self.max_price:
                        self.data.append({"Название": name, "Цена": price, "Ссылка": link})
            except Exception:
                continue

    def go_to_next_page(self):
        """Переход на следующую страницу поиска"""
        try:
            next_button = self.driver.find_element(By.CSS_SELECTOR, "a[data-qaid='next_page']")
            self.driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
            time.sleep(1)
            self.driver.execute_script("arguments[0].click();", next_button)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-qaid='product_block']"))
            )
            return True
        except (NoSuchElementException, TimeoutException):
            return False

    def fetch_all_products(self):
        """Собираем товары с заданного количества страниц"""
        current_page = 1
        while True:
            self.scroll_to_load_all()
            self.fetch_products_from_page()

            if self.max_pages and current_page >= self.max_pages:
                break

            if not self.go_to_next_page():
                break

            current_page += 1

        self.driver.quit()

    def show_results(self):
        """Вывод результатов в консоль"""
        if not self.data:
            print("❌ Товары не найдены по условиям.")
            return

        df = pd.DataFrame(self.data)
        df = df.sort_values(by="Цена", ascending=False).reset_index(drop=True)
        df.index += 1
        df.index.name = "№"
        print("\n✅ Результаты поиска:")
        print(df.to_string(index=True))
        return df

    def save_to_excel(self, filename="prom_products.xlsx"):
        if not self.data:
            return

        print("\n⏳ Ждём 10 секунд перед сохранением файла...")
        time.sleep(10)

        df = pd.DataFrame(self.data)
        df = df.sort_values(by="Цена", ascending=False).reset_index(drop=True)
        df.index += 1
        df.index.name = "№"
        df.to_excel(filename, index=True)
        print(f"✅ Результат сохранён в {filename}")

    def run(self):
        """Запуск полного парсинга"""
        self.start_driver()
        self.fetch_all_products()
        df = self.show_results()
        self.save_to_excel()
        return df


# -------------------------------
# Пример запуска
# -------------------------------
if __name__ == "__main__":
    query = input("Введите ключевое слово для поиска: ")
    max_price_input = input("Введите максимальную цену (или оставьте пустым): ")
    max_pages_input = input("Введите максимальное количество страниц (или оставьте пустым): ")

    try:
        max_price = int(max_price_input) if max_price_input else None
    except ValueError:
        print("⚠ Ошибка: цена должна быть числом.")
        max_price = None

    try:
        max_pages = int(max_pages_input) if max_pages_input else None
    except ValueError:
        print("⚠ Ошибка: количество страниц должно быть числом.")
        max_pages = None

    parser = PromParser(query, max_price, max_pages)
    parser.run()
