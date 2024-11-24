from bs4 import BeautifulSoup
import requests
from fake_useragent import UserAgent
import logging
import time
from datetime import datetime
import sys
from typing import Optional
import csv
import os


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("currency_scraper.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


class CurrencyScraper:
    def __init__(self, interval: int = 60):
        self.interval = interval
        self.session = requests.Session()
        self.csv_file = "usd_rub_rates.csv"
        self.initialize_csv()

    def initialize_csv(self):
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Timestamp", "USD/RUB Rate", "Source"])

    def get_headers(self) -> dict:
        ua = UserAgent()
        return {
            "User-Agent": ua.random,
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "en-US,en;q=0.5",
            "X-Requested-With": "XMLHttpRequest",
            "Connection": "keep-alive",
            "Referer": "https://www.investing.com/currencies/usd-rub",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }

    def get_rate_from_webpage(self) -> Optional[float]:
        try:
            url = "https://www.investing.com/currencies/usd-rub"
            response = self.session.get(url, headers=self.get_headers(), timeout=10)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                selectors = [
                    ".last-price-value",
                    ".text-5xl",
                    "#last_last",
                    'div[data-test="instrument-price-last"]',
                    ".instrument-price_last",
                ]

                for selector in selectors:
                    element = soup.select_one(selector)
                    if element:
                        text = element.text.strip()
                        try:
                            return float(
                                "".join(c for c in text if c.isdigit() or c == ".")
                            )
                        except ValueError:
                            continue
            return None
        except Exception as e:
            logger.error(f"Webpage error: {str(e)}")
            return None

    def save_rate(self, rate: float, source: str):
        try:
            with open(self.csv_file, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([datetime.now().isoformat(), rate, source])
        except Exception as e:
            logger.error(f"Failed to save to CSV: {str(e)}")

    def get_current_rate(self) -> Optional[float]:
        rate = self.get_rate_from_webpage()
        if rate:
            self.save_rate(rate, "Webpage")
            return rate

        return None

    def run(self):
        failures = 0
        max_failures = 5

        logger.info(f"Starting USD/RUB rate scraping every {self.interval} seconds")
        logger.info(f"Saving results to {self.csv_file}")

        while True:
            try:
                rate = self.get_current_rate()

                if rate:
                    print(
                        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - USD/RUB: {rate}"
                    )
                    failures = 0
                else:
                    failures += 1
                    logger.warning(
                        f"Failed to get rate. Consecutive failures: {failures}"
                    )

                wait_time = self.interval * (2 if failures >= max_failures else 1)

                time.sleep(wait_time)

            except KeyboardInterrupt:
                logger.info("Scraping stopped by user")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                time.sleep(self.interval)


def main():
    scraper = CurrencyScraper()
    scraper.run()


if __name__ == "__main__":
    main()
