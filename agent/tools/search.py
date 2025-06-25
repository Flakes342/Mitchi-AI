import os
import time
import subprocess
import urllib.parse
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By


def scrape_gemini_answer(query):
    chrome_path = "/usr/bin/google-chrome"

    options = uc.ChromeOptions()
    options.binary_location = chrome_path
    options.add_argument("--disable-blink-features=AutomationControlled")

    browser = uc.Chrome(options=options)


    try:
        search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        browser.get(search_url)
        time.sleep(5)

        elems = browser.find_elements(By.CSS_SELECTOR, "div.LT6XE div.Ii22Cf div.oD6fhb span")

        for elem in elems:
            text = elem.text.strip()
            if text and len(text.split()) > 8:
                return text

        return "No Gemini answer found."

    finally:
        browser.quit()


def search_web(query):
    summary = scrape_gemini_answer(query)
    if summary and summary!='No Gemini answer found.':
        return summary
    else:
        print(f"Error scraping Gemini answer: {e}")
        try:
            encoded_query = urllib.parse.quote_plus(query)
            url = f"https://www.google.com/search?q={encoded_query}"
            cmd = f"firefox {url}"
            subprocess.Popen(cmd, shell=True)
            return f"Searching for: {query}"
        except Exception as e:
            return f"Failed to open browser for search: {str(e)}"
