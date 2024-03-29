import asyncpg
import asyncio
import os
# from cs50 import SQL
import asyncio
import psycopg2
from psycopg2 import sql
from psycopg2 import OperationalError
from urllib.parse import urlparse
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

postgres_url = "postgres://default:KHS7RdOxCEp1@ep-lively-poetry-a4k7k20v.us-east-1.aws.neon.tech:5432/verceldb?sslmode=require"
parsed_url = urlparse(postgres_url)

# Establishing connection=
connection = psycopg2.connect(
    dbname=parsed_url.path[1:],
    user=parsed_url.username,
    password=parsed_url.password,
    host=parsed_url.hostname,
    port=parsed_url.port
)


db = connection.cursor()

# q=db.execute("select * from users")

# result=db.fetchall()

# for i in result:
#     print(i)


async def fetch_data(query):
    # Replace 'your_connection_string' with your actual connection string
    conn = await asyncpg.connect(postgres_url)
    rows = await conn.fetch(query)
    await conn.close()
    return rows


# Ensure responses aren't cached


@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# username ="u"
# query = "select * from users where username = '{}' ".format(username)
# db.execute(query)
# result=db.fetchone()
# print(result)

# Configure CS50 Library to use SQLite database
# db = SQL("sqlite:///finance.db")

# Make sure API key is set
# if not os.environ.get("API_KEY"):
#     raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    prices = {}       # dictionay to store current prices
    total = 0
    user_id = session["user_id"]

    """Show portfolio of stocks"""

    # information of stocks owned
    query = sql.SQL("SELECT * FROM portfolio WHERE user_id = '{}'")
    params = (user_id,)
    db.execute(query, params)
    stocks = db.fetchall()
    print("printing stocks")
    print(stocks)

    # querying cash remainig
    query = sql.SQL("SELECT cash FROM users WHERE id=%s")
    params = (user_id,)
    db.execute(query, params)
    balance_amt = db.fetchone()
    print("printing balance amt")
    print(balance_amt)

    for stock in stocks:
        # stroring price of each stock price
        print(stock)
        info = lookup(stock[4])

        total += (info["price"] * int(stock["quantity"]))
        # stroring prices in a dictionary
        prices[info["symbol"]] = info["price"]

    return render_template("index.html", user=balance_amt, stocks=stocks, prices=prices, total=total)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    user_id = session["user_id"]
    query = sql.SQL("SELECT username from users where id = %s")
    params = (user_id,)
    db.execute(query, params)
    user = db.fetchone()
    username = user[0]["username"]
    """Buy shares of stocks"""
    if request.method == "POST":
        stocks = lookup(request.form.get("symbol"))
        if not request.form.get("symbol") or stocks["symbol"] == "Invalid":
            return apology("Enter a valid Stock Symbol", 400)

        elif not request.form.get("number"):
            return apology("Please provide number of stocks to buy", 400)

        number = int(request.form.get("number"))
        price = stocks["price"]
        cost = price * number
        symbol = stocks["symbol"]
        name = stocks["name"]
        # querying data for cash
        query = sql.SQL("SELECT cash FROM users WHERE id=%s")
        params = (user_id,)
        db.execute(query, params)
        user = db.fetchall()

        cash = float(user[0]["cash"])
        if cash < cost:
            return apology("Not enough money")
        else:
            # deductinh money from balance
            cash -= cost
            query1 = sql.SQL("UPDATE users SET cash = %s WHERE id = %s")
            params1 = (cash, user_id)
            db.execute(query1, params1)
            connection.commit()

            # updating history
            query2 = sql.SQL(
                "INSERT INTO history (user_id, name, symbol, quantity, price) VALUES (%s,%s,%s,%s,%s)")
            params2 = (user_id, name, symbol, number, price)
            db.execute(query2, params2)
            connection.commit()

            # updating personal portfolio
            query3 = sql.SQL(
                "SELECT quantity from portfolio where user_id = %s and  symbol = %s")
            params3 = (user_id, symbol)
            db.execute(query3, params3)
            stocks = db.fetchall()

            # if user has purchased the stocks before, update the quantity otherwise create new entry
            if len(stocks) == 1:
                amount = int(stocks[0]["quantity"]) + number
                query = sql.SQL(
                    "UPDATE portfolio SET quantity = %s WHERE symbol = %s AND user_id = %s")
                params = (amount, symbol, user_id)
                db.execute(query, params)
                connection.commit()

            else:
                query = sql.SQL(
                    "INSERT INTO portfolio (user_id, username, stock_name, symbol, quantity) VALUES (%s,%s,%s,%s,%s)")
                params = (user_id, username, name, symbol, number)
                db.execute(query, params)
                connection.commit()
    # if requested by GET, render purchase form
    else:
        return render_template("buy.html")

    return redirect("/")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    user_id = session["user_id"]

    # querying databse
    query = sql.SQL("SELECT * FROM history WHERE user_id = %s")
    params = (user_id,)
    db.execute(query, params)
    stocks = db.fetchall()
    print(stocks)
    return render_template("history.html", stocks=stocks)


@app.route("/login", methods=["GET", "POST"])
async def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        username = request.form.get("username")

        # query = sql.SQL("select * from users where Username = %s")
        # params=(username ,)
        connection.autocommit = True
        db.execute(f"select * from users where username = '{username}'")
        d = db.fetchone()

        print(d)
        stocks = d[2]

        print("Hash")
        print(d[1])

        # Ensure username exists and password is correct
        if not check_password_hash(stocks, request.form.get("password")):
            return apology("invalid username and/or password", 403)
        print("user found")
        # Remember which user has logged in
        session["user_id"] = d[0]
        # connection.autocommit=True
        # Redirect user to home page
        connection.autocommit = False
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stocks quote."""
    # if visited via post
    if request.method == "POST":

        # get data from servers
        stocks = lookup(request.form.get("symbol"))

        # if valid output is recieved, turn the price into cost. otherwise pass it without altering
        try:
            return render_template("quoted.html", symbol=stocks["symbol"], name=stocks["name"], price=usd(stocks["price"]))
        except:
            return render_template("quoted.html", symbol=stocks["symbol"], name=stocks["name"], price=stocks["price"])

    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == "POST":
        # getting and validating inputs
        print(request.form.get("username"))
        print(request.form.get("password"))
        print(request.form.get("confirmation"))
        if not request.form.get("username"):
            return apology("NO username provided!", 403)

        elif not request.form.get("password") or not request.form.get("confirmation"):
            return apology("password must be provided and confirmed", 403)

        elif not request.form.get("password") == request.form.get("confirmation"):
            return apology("Passwords don't match")

        password = request.form.get("password")
        username = request.form.get("username")
        passhash = generate_password_hash(password)

        # confirming unique username
        query = sql.SQL("select * from users where username = %s")
        params = (username, )

        stocks = db.execute(query, params)
        print("search query exec successful")
        result = db.fetchall()
        print("result:", result)
        if stocks is not None and len(stocks) > 0:
            return apology("Username Already Taken", 400)

        # adding user
        query = sql.SQL("insert into users (username, hash)  VALUES (%s,%s)")
        params = (username, passhash)
        db.execute(query, params)

        # Commit changes
        connection.commit()

        # loggin in user automatically
        if db.rowcount > 0:
            # loggin in user automatically
            query = sql.SQL("SELECT id FROM users WHERE username = %s")
            params = (username,)
            db.execute(query, params)
            id = db.fetchone()
            print(id)

        session["user_id"] = id[0]
        return redirect("/")

        # except Exception as e:
        #     # Handle exception
        #     print("Error:", e)
        #     return apology("An error occurred while registering the user", 500)

    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    user_id = session["user_id"]
    # querying portfolio
    query1 = sql.SQL("SELECT * FROM portfolio WHERE user_id = %s")
    params1 = (user_id,)
    db.execute(query1, params1)
    stocks = db.fetchall()

    """Sell shares of stocks"""
    # keeps rack of sold status
    stock_sold = False

    if request.method == "POST":
        # validating inputs
        if not request.form.get("symbol") or not request.form.get("shares"):
            return apology("No Stock Selected", 400)

        # variables
        symbol = request.form.get("symbol")
        info = lookup(symbol)  # fetches data through API
        symbol = symbol.upper()

        # shares owned
        query2 = sql.SQL(
            "SELECT * FROM portfolio WHERE user_id = %s and symbol = %s")
        params2 = (user_id, symbol)
        db.execute(query2, params2)
        stocks = db.fetchall()
        shares = int(stocks[0]["quantity"])

        shares_to_sell = int(request.form.get("shares"))

        if shares == 0:
            return apology("You Don't Own That Stock")

        elif (shares) < (shares_to_sell):
            return apology("You Don't Own Enough Shares")

        # removes the entry of share from portfolio if no shares are left after selling
        elif shares == shares_to_sell:
            query3 = sql.SQL(
                "DELETE FROM portfolio WHERE user_id = %s AND symbol = %s")
            params3 = (user_id, symbol)
            db.execute(query3, params3)
            connection.commit()
            stock_sold = True

        # decreases the number of shares owned
        elif shares > shares_to_sell:
            shares_left = shares - shares_to_sell
            query4 = sql.SQL(
                "UPDATE portfolio SET quantity =%s WHERE symbol = %s AND user_id = %s")
            params4 = (shares_left, symbol, user_id)
            db.execute(query4, params4)
            stock_sold = True

        # if successfully sold, then add money to balance
        if (stock_sold):
            # add entry in history
            query5 = sql.SQL(
                "INSERT INTO history (user_id, name, symbol, quantity, price, action) VALUES (%s, %s, %s, %s, %s, %s)")
            params5 = (user_id, info["name"], symbol,
                       shares_to_sell, info["price"], "SOLD")
            db.execute(query5, params5)
            connection.commit()

            query6 = sql.SQL("SELECT * FROM users WHERE id = %s")
            params6 = (user_id,)
            db.execute(query6, params6)
            user = db.fetchone()
            cash = float(user[0]["cash"])
            cash += (int(shares_to_sell) * info["price"])

            query7 = sql.SQL("UPDATE users SET cash = %s WHERE id = %s")
            params7 = (cash, user_id)
            db.execute(query7, params7)
            connection.commit()

    else:
        return render_template("sell.html", stocks=stocks)
    return redirect("/")


@app.route("/recharge", methods=["GET", "POST"])
@login_required
def recharge():
    user_id = session["user_id"]
    query1 = sql.SQL("SELECT * FROM users WHERE id = %s")
    params1 = (user_id,)
    db.execute(query1, params1)
    user = db.fetchall()
    cash = float(user[0]["cash"])
    if request.method == "POST":
        amount = int(request.form.get("amount"))
        cash += amount
        quantity = 1
        dash = "-"

        # updating database
        query2 = sql.SQL("UPDATE users SET cash = %s WHERE id = %s")
        params2 = (cash, user_id)
        db.execute(query2, params2)
        connection.commit()
        query3 = sql.SQL(
            "INSERT INTO history (user_id, name, symbol, price, quantity, action) VALUES (%s, %s, %s, %s, %s, %s)")
        params3 = (user_id, dash, dash, amount, quantity, "Recharge")
        db.execute(query3, params3)
        connection.commit()

    else:
        return render_template("recharge.html", cash=cash)

    return redirect("/recharge")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
