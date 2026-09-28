import ccxt
import polars as pl
import matplotlib.pyplot as plt
import numpy as np
import os

def parser(symbol):
    limit = 1000
    timeframe = "1d"

    exchange = ccxt.binance()
    ohlcv = exchange.fetch_ohlcv(f"{symbol}/USDT", timeframe=timeframe, limit=limit)
    dataFrame = pl.DataFrame(ohlcv, schema=["timestamp", "open", "high", "low", "close", "volume"])
    
    plt.plot(dataFrame['close'])
    output_file = f'plot.png'
    plt.savefig(output_file, dpi=100)
    print(f"savefig {output_file}")

def main():
    symbols = ["BTC", "ETH", "BNB", "SOL"]
    
    for symbol in symbols:
        parser(symbol)

if __name__ == "__main__":
    main()