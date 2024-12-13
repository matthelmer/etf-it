# ETF Decomposer

ETF Decomposer is an (alpha) tool designed to provide investors with a deeper understanding of the companies that comprise their ETF investments. This information is sometimes not easily accessible.

This tool aims to offer transparency into the exact companies included in ETF holdings.

The primary goals of the project are:

1. To help retail investors make more informed decisions about where their investment capital is allocated.
2. To help identify holdings in companies that do not align with an investor's ethical standards.
3. Assist retail investors in managing portfolio diversification.

## Current Features

- Scrapes ETF holdings data from Vanguard's website
- Aggregates holdings across multiple ETFs
- Provides a breakdown of the top holdings by value
- Calculates the total portfolio value of each holding

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/matthelmer/etf-decomposer.git
   cd etf-decomposer
   ```

2. Install the required Python packages:
   ```
   pip install -r requirements.txt
   ```

3. Ensure you have Chrome browser installed and the appropriate ChromeDriver for your Chrome version in your system PATH.

## Usage

1. Update the `positions.json` file with your ETF holdings and market prices:
   ```json
   {
       "VOO": {"shares": 10, "price": 550},
       "VTI": {"shares": 22.22, "price": 299.30}
   }
   ```

2. Run the script:
   ```
   python decomposer.py
   ```

3. View the results in the generated `aggregated_holdings.csv` file.


## Disclaimer

This tool is provided for informational purposes only. It is not intended to be used as financial or investment advice. The data provided by this tool may not be complete, accurate, or up-to-date. Use this tool at your own risk. The creators and contributors of this tool are not responsible for any financial losses or other damages that may result from its use.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
