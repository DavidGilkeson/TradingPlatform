"""
main.py

Main entry point for David's Trading Platform.

Responsibilities:
1. Create required folders.
2. Load stock tickers from a CSV file.
3. Scan the stocks.
4. Display the analysis.
5. Save results to a CSV file.
6. Open a chart for the strongest stock.
"""

from config import TICKER_FILE, CSV_FILE
from scanner import scan_stocks
from charts import plot_chart
from utils import create_folders, load_tickers_from_csv


def main():
    """Run the trading platform."""

    # Create the data and charts folders if they do not exist
    create_folders()

    # Load ticker symbols from the CSV file
    stocks = load_tickers_from_csv(TICKER_FILE)

    # Stop the program if no tickers were loaded
    if not stocks:
        print("No ticker symbols were loaded. Program stopped.")
        return

    print(f"\nLoaded {len(stocks)} ticker symbols.")

    # Scan all loaded stocks
    df, chart_data = scan_stocks(stocks)

    # Stop if the scanner returned no results
    if df.empty:
        print("No stock results were generated. Program stopped.")
        return

    # Display the results in the terminal
    print("\nStock Analysis")
    print(df.to_string(index=False))

    # Save the results to a CSV file
    df.to_csv(CSV_FILE, index=False)

    print(f"\nResults saved to {CSV_FILE}")

    # The scanner sorts the strongest trend to the top
    best_ticker = df.iloc[0]["Ticker"]

    print(f"\nOpening chart for strongest stock: {best_ticker}")

    # Plot the strongest stock using data stored during the scan
    plot_chart(
        best_ticker,
        chart_data[best_ticker]["close"],
        chart_data[best_ticker]["ma_short"],
        chart_data[best_ticker]["ma_long"]
    )


# Run main() only when this file is executed directly
if __name__ == "__main__":
    main()