from flask import Flask, render_template, request, redirect, url_for, flash, Response
import sqlite3
import csv
import io
from pathlib import Path
from datetime import datetime

app = Flask(__name__)
app.secret_key = "portfolio-pilot-local-demo-key"

BASE_DIR = Path(__file__).resolve().parent
DB_DIR = BASE_DIR / "instance"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "portfolio.db"

# Fixed sample prices. These are NOT live market prices.
STOCKS = {
    "AAPL": {"name": "Apple", "price": 180.00},
    "TSLA": {"name": "Tesla", "price": 250.00},
    "GOOGL": {"name": "Alphabet", "price": 150.00},
    "AMZN": {"name": "Amazon", "price": 180.00},
    "MSFT": {"name": "Microsoft", "price": 420.00}
}


def get_db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with get_db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS holdings (
                symbol TEXT PRIMARY KEY,
                quantity REAL NOT NULL,
                avg_buy_price REAL NOT NULL
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                action TEXT NOT NULL,
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                total REAL NOT NULL,
                created_at TEXT NOT NULL
            )
        """)


def get_portfolio():
    with get_db() as con:
        holdings = con.execute(
            "SELECT * FROM holdings ORDER BY symbol"
        ).fetchall()

        transactions = con.execute(
            "SELECT * FROM transactions ORDER BY id DESC LIMIT 10"
        ).fetchall()

    portfolio = []
    total_invested = 0
    total_value = 0

    for item in holdings:
        symbol = item["symbol"]
        quantity = item["quantity"]
        avg_price = item["avg_buy_price"]

        market_price = STOCKS[symbol]["price"]
        invested = quantity * avg_price
        value = quantity * market_price
        profit_loss = value - invested

        total_invested += invested
        total_value += value

        portfolio.append({
            "symbol": symbol,
            "name": STOCKS[symbol]["name"],
            "quantity": quantity,
            "avg_price": avg_price,
            "market_price": market_price,
            "invested": invested,
            "value": value,
            "pnl": profit_loss
        })

    return portfolio, transactions, total_invested, total_value


@app.route("/")
def dashboard():
    holdings, transactions, invested, value = get_portfolio()

    return render_template(
        "dashboard.html",
        holdings=holdings,
        transactions=transactions,
        total_invested=invested,
        total_value=value,
        total_pnl=value - invested,
        stocks=STOCKS
    )


@app.post("/buy")
def buy_stock():
    symbol = request.form.get("symbol", "").upper()

    try:
        quantity = float(request.form.get("quantity", "0"))
    except ValueError:
        quantity = 0

    if symbol not in STOCKS or quantity <= 0:
        flash("Please select a valid stock and quantity.", "error")
        return redirect(url_for("dashboard"))

    price = STOCKS[symbol]["price"]

    with get_db() as con:
        existing = con.execute(
            "SELECT * FROM holdings WHERE symbol = ?",
            (symbol,)
        ).fetchone()

        if existing:
            old_quantity = existing["quantity"]
            old_average = existing["avg_buy_price"]

            new_quantity = old_quantity + quantity

            new_average = (
                (old_quantity * old_average) + (quantity * price)
            ) / new_quantity

            con.execute("""
                UPDATE holdings
                SET quantity = ?, avg_buy_price = ?
                WHERE symbol = ?
            """, (new_quantity, new_average, symbol))

        else:
            con.execute("""
                INSERT INTO holdings(symbol, quantity, avg_buy_price)
                VALUES (?, ?, ?)
            """, (symbol, quantity, price))

        con.execute("""
            INSERT INTO transactions
            (symbol, action, quantity, price, total, created_at)
            VALUES (?, 'BUY', ?, ?, ?, ?)
        """, (
            symbol,
            quantity,
            price,
            quantity * price,
            datetime.now().strftime("%d %b %Y, %I:%M %p")
        ))

    flash(f"Successfully added {quantity:g} shares of {symbol}.", "success")
    return redirect(url_for("dashboard"))


@app.post("/sell")
def sell_stock():
    symbol = request.form.get("symbol", "").upper()

    try:
        quantity = float(request.form.get("quantity", "0"))
    except ValueError:
        quantity = 0

    if quantity <= 0:
        flash("Enter a valid quantity.", "error")
        return redirect(url_for("dashboard"))

    with get_db() as con:
        holding = con.execute(
            "SELECT * FROM holdings WHERE symbol = ?",
            (symbol,)
        ).fetchone()

        if not holding or quantity > holding["quantity"]:
            flash("Not enough shares available to sell.", "error")
            return redirect(url_for("dashboard"))

        remaining = holding["quantity"] - quantity
        price = STOCKS[symbol]["price"]

        if remaining <= 0.0000001:
            con.execute(
                "DELETE FROM holdings WHERE symbol = ?",
                (symbol,)
            )
        else:
            con.execute("""
                UPDATE holdings SET quantity = ?
                WHERE symbol = ?
            """, (remaining, symbol))

        con.execute("""
            INSERT INTO transactions
            (symbol, action, quantity, price, total, created_at)
            VALUES (?, 'SELL', ?, ?, ?, ?)
        """, (
            symbol,
            quantity,
            price,
            quantity * price,
            datetime.now().strftime("%d %b %Y, %I:%M %p")
        ))

    flash(f"Successfully sold {quantity:g} shares of {symbol}.", "success")
    return redirect(url_for("dashboard"))


@app.post("/delete/<symbol>")
def delete_holding(symbol):
    symbol = symbol.upper()

    with get_db() as con:
        con.execute(
            "DELETE FROM holdings WHERE symbol = ?",
            (symbol,)
        )

    flash(
        f"{symbol} removed from holdings. Transaction history is retained.",
        "success"
    )
    return redirect(url_for("dashboard"))


@app.get("/export")
def export_csv():
    holdings, _, _, _ = get_portfolio()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Symbol", "Company", "Quantity",
        "Average Buy Price", "Demo Market Price",
        "Invested Value", "Portfolio Value", "Profit/Loss"
    ])

    for item in holdings:
        writer.writerow([
            item["symbol"],
            item["name"],
            item["quantity"],
            item["avg_price"],
            item["market_price"],
            item["invested"],
            item["value"],
            item["pnl"]
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition":
            "attachment; filename=portfolio_report.csv"
        }
    )


@app.get("/health")
def health():
    return {"status": "ok"}


init_db()

if __name__ == "__main__":
    app.run(debug=True)