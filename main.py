"""
main.py

Main entry point for David's Trading Platform.

Responsibilities:
1. Create required folders.
2. Download the S&P 500 ticker list.
3. Scan the stocks.
4. Display and save the results.
5. Open a chart for the strongest stock.
"""
import time
from charts import plot_chart
from config import SP500_URL, TICKER_FILE, CSV_FILE
from scanner import scan_stocks
from utils import create_folders, download_sp500_tickers
from backtester import backtest



def main():
    """Run the trading platform."""

    start_time = time.perf_counter()
    # Create required project folders
    create_folders()

    # Download the current S&P 500 list
    # The local CSV is used as a backup if this fails
    stocks = download_sp500_tickers(
        SP500_URL,
        TICKER_FILE
    )

    # Stop if no ticker symbols could be loaded
    if not stocks:
        print("No ticker symbols were loaded. Program stopped.")
        return

    print(f"\nStarting scan of {len(stocks)} stocks...\n")

    # Analyse every stock
    df, chart_data = scan_stocks(stocks)

    # Stop if no stocks were successfully analysed
    if df.empty:
        print("No stock results were generated. Program stopped.")
        return

    # Display only the top 20 stocks in the terminal
    print("\nTop 20 Stock Opportunities")
    print(df.head(20).to_string(index=False))

    # Save all results to CSV
    df.to_csv(CSV_FILE, index=False)

    print(f"\nFull results saved to {CSV_FILE}")

    # Select the strongest stock
    best_ticker = df.iloc[0]["Ticker"]

    print(f"\nOpening chart for strongest stock: {best_ticker}")

    # Display its chart
    plot_chart(
        best_ticker,
        chart_data[best_ticker]["close"],
        chart_data[best_ticker]["ma_short"],
        chart_data[best_ticker]["ma_long"]
        
        
        
    )
    
    end_time = time.perf_counter()
    backtest(best_ticker)

    print(f"\nExecution Time: {end_time - start_time:.2f} seconds")


if __name__ == "__main__":
    main()