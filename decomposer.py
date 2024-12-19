# decomposer.py
import pandas as pd
import json
import os
import time
import argparse
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
        TimeoutException, NoSuchElementException, WebDriverException
)

# add logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
)


def load_etf_positions(file_path):
    """Load ETF positions from a JSON file."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"ETF positions file '{file_path}' not found.")
        return {}
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON: {e}")
        return {}


def scrape_vanguard_etf(driver, etf_ticker):
    """Scrape ETF holdings data from Vanguard website."""
    base_url = ('https://investor.vanguard.com/investment-products/etfs/'
                'profile/{}#portfolio-composition')
    url = base_url.format(etf_ticker.lower())
    logging.info(f"Accessing URL: {url}")

    try:
        driver.get(url)
    except WebDriverException as e:
        logging.error(f"Error accessing URL for {etf_ticker}: {e}")
        return []

    all_data = []
    table_xpath = ('/html/body/vmf-root/vg-vgn-nav/profile/div/div[2]/'
                   'portfolio/section/div/div[5]/div/holding-details-'
                   'container/div/div[1]/div/c11n-tabs/c11n-tab-panel[1]'
                   '//table')
    pagination_select_xpath = ('/html/body/vmf-root/vg-vgn-nav/profile/div/'
                               'div[2]/portfolio/section/div/div[5]/div/'
                               'holding-details-container/div/div[2]/div[2]/'
                               'holding-details-pagination/div/div/'
                               'vmf-pagination/div/div/div/c11n-select/div/'
                               'select')

    def extract_table_data():
        try:
            table = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, table_xpath))
            )
            rows = table.find_elements(By.XPATH, './/tbody/tr')
            return [[cell.text for cell in row.find_elements(
                By.XPATH, './/th|.//td')] for row in rows]
        except (TimeoutException, NoSuchElementException) as e:
            logging.error(f"Error extracting table data for {etf_ticker}: {e}")
            return []

    try:
        select = Select(WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, pagination_select_xpath)
            )
        ))
        total_pages = len(select.options)

        for index in range(total_pages):
            logging.info(f"Processing page {index + 1}/{total_pages} "
                         f"for {etf_ticker}")
            select.select_by_index(index)
            time.sleep(2)
            all_data.extend(extract_table_data())
    except (TimeoutException, NoSuchElementException) as e:
        logging.error(f"Error processing pagination for {etf_ticker}: {e}")
    except Exception as e:
        logging.error(f"Unexpected error scraping {etf_ticker}: {e}")

    return all_data


def save_to_csv(data, filename):
    """Save scraped data to a CSV file."""
    if data:
        df = pd.DataFrame(data, columns=[
            'Ticker', 'Holdings', 'CUSIP', 'SEDOL', '% of fund',
            'Shares', 'Market value'
        ])
        df.to_csv(filename, index=False)
        logging.info(f"Data saved to {filename}")
    else:
        logging.warning(f"No data to save for {filename}")


def aggregate_holdings(etf_positions):
    """Aggregate holdings across all ETFs."""
    all_holdings = pd.DataFrame()
    etf_summary = []
    for etf, position_data in etf_positions.items():
        etf_summary.append({
            'ETF': etf,
            'Shares': position_data['shares'],
            'Price': position_data['price']
        })
        csv_file = f"{etf}_decomposed.csv"
        if os.path.exists(csv_file):
            df = pd.read_csv(csv_file)
            df['Market value'] = df['Market value'].str.replace(
                r'[\$,]', '', regex=True
            ).astype(float)
            df['% of fund'] = df['% of fund'].str.replace(
                r'[%]', '', regex=True
            ).astype(float).fillna(0)
            total_market_value = df['Market value'].sum()

            df['Weight'] = df['% of fund'] / 100

            zero_weight_rows = df['Weight'] == 0
            df.loc[zero_weight_rows, 'Weight'] = (
                df.loc[zero_weight_rows, 'Market value'] / total_market_value
            )

            etf_value = position_data['shares'] * position_data['price']
            df['Value'] = etf_value * df['Weight']
            df['Ticker'] = df['Ticker'].str.upper()
            df = df[['Ticker', 'Value']]

            df = df.groupby('Ticker', as_index=False).sum()
            df.rename(columns={'Value': f"Value of Ticker in {etf.upper()}"},
                      inplace=True)
            if all_holdings.empty:
                all_holdings = df
            else:
                all_holdings = pd.merge(
                    all_holdings, df, on='Ticker', how='outer'
                )
        else:
            logging.warning(
                f"Holdings file '{csv_file}' not found for ETF '{etf}'. "
                "Skipping."
            )

    if not all_holdings.empty:
        all_holdings.fillna(0, inplace=True)
        numeric_cols = [col for col in all_holdings.columns if col != 'Ticker']
        all_holdings['Total'] = all_holdings[numeric_cols].sum(axis=1)
        return pd.DataFrame(etf_summary), all_holdings.sort_values(
            'Total', ascending=False
        )
    else:
        logging.error("No holdings data available to aggregate.")
        return pd.DataFrame(), pd.DataFrame()


def main():
    parser = argparse.ArgumentParser(description="Vanguard ETF Decomposer")
    parser.add_argument(
        '--positions', default='positions.json',
        help='Path to ETF positions JSON file'
    )
    args = parser.parse_args()

    etf_positions = load_etf_positions(args.positions)
    if not etf_positions:
        logging.error("No ETF positions to process. Exiting.")
        return

    try:
        driver = webdriver.Chrome()  # Ensure chromedriver in PATH
    except WebDriverException as e:
        logging.error(f"Error initializing WebDriver: {e}")
        return

    try:
        for etf in etf_positions:
            csv_file = f"{etf}_decomposed.csv"
            if not os.path.exists(csv_file):
                logging.info(f"Scraping data for {etf}...")
                holdings_data = scrape_vanguard_etf(driver, etf)
                save_to_csv(holdings_data, csv_file)
            else:
                logging.info(f"Using existing data for {etf}")
    finally:
        driver.quit()
    logging.info("Aggregating holdings...")
    etf_summary, aggregated_holdings = aggregate_holdings(etf_positions)

    if not aggregated_holdings.empty:
        logging.info("Saving aggregated holdings...")

        with open("aggregated_holdings.csv", "w") as f:
            etf_summary.to_csv(f, index=False)
            f.write("\n")  # Add an empty row
            aggregated_holdings.to_csv(f, index=False)
        logging.info("Analysis complete. Results saved in "
                     "aggregated_holdings.csv")

        # print summary statistics
        total_portfolio_value = aggregated_holdings['Total'].sum()
        logging.info(f"\nTotal portfolio value: ${total_portfolio_value:,.2f}")
        logging.info("\nTop 10 ETF component holdings by value:")
        top_10 = aggregated_holdings.head(10)
        for _, row in top_10.iterrows():
            ticker = row['Ticker']
            total_value = row['Total']
            percentage = (total_value / total_portfolio_value) * 100
            logging.info(f"{ticker}: ${total_value:,.2f} ({percentage:.2f}%)")
    else:
        logging.error("Aggregated holdings data is empty. "
                      "No results to display.")


if __name__ == "__main__":
    main()
