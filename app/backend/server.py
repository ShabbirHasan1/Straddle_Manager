from datetime import datetime
from kiteconnect.ticker import KiteTicker
from pandas.core.series import Series
from order import place_sell_banknifty_option_gtt_order, place_sell_banknifty_option_market_order
from os import access, name, read,urandom 
from flask import Flask, render_template, request, abort, session
from flask.helpers import url_for
from werkzeug.utils import redirect
from werkzeug.exceptions import *
from kiteconnect import KiteConnect
from flask_pymongo import PyMongo
import initialise, order, stream, data, user
import coloredlogs,logging
import threading
import pandas as pd

logger = logging.getLogger(__name__)
coloredlogs.install(level= 'DEBUG')

# App Data
app = Flask(__name__)
app.secret_key = urandom(24)
app.config['MONGO_URI'] = "mongodb://localhost:27017/straddle_algo"
mongo = PyMongo(app)
mongo_option_chain = PyMongo(app, uri="mongodb://localhost:27017/option_chain")

# Kite Client Data
kite:KiteConnect = None
kws:KiteTicker = None
kite_api_key = "hbfo44ol4yj68c0w"
kite_api_secret = "r91kmo1p3vh56fqnc0v9s8rsljk9wfr3"
kite_request_token = None
kite_access_token = None

# Symbol Data
instument_data = None
spot_symbol_data = None
call_symbol_data = None
put_symbol_data = None
call_exit_symbol_data = None
put_exit_symbol_data = None

# Tick Data
spot_tick_data = None
call_tick_data = None
put_tick_data = None
call_exit_tick_data = None
put_exit_tick_data = None

# Price Data
straddle_strike_price = None
call_average_price = None
put_average_price = None
call_exit_average_price = None
put_exit_average_price = None

# Order Data
orders_list = None
position_list = None


# Flag Data
in_call_position = False
in_put_position = False
in_call_exit_position = False
in_put_exit_position = False
algo_thread = None
strategy_stop_event = threading.Event()
strategy_thread = None
data_fetching = True

def kite_client_not_connected():
    return render_template('error.html', error= "Kite Client is None")

@app.route("/")
def root():
    return render_template('display.html', screen= "Root")

@app.route("/login")
def login():
    try:
        global kite_request_token
        kite_request_token = request.args['request_token']
        # print("Request Token" , kite_request_token)
        global kite
        initialise.initialise_client()
        data.fetch_instruments()

        #Just for debugging
        # global instument_data
        # instument_data = pd.read_csv("instruments.csv")
        # pd.read_csv("instruments.csv", dtype= {
        # "instrument_token" : int,
        # "exchange_token" : int,
        # "tradingsymbol" : str,
        # "last_price" : int,
        # "expiry" : str,
        # "strike" : float,
        # "tick_size" : float })
    except BadRequestKeyError:
        abort(401)

    return render_template('display.html', screen= "Login")

@app.route("/holdings")
def holdings():
    if kite is not None:
        user.holdings()
        return render_template('display.html', screen= "Holdings")
    else :
        return kite_client_not_connected()

@app.route("/positions")
def positions():
    if kite is not None:
        position_list = user.positions()
        return render_template('display.html', screen= "Positions")
    else :
        return kite_client_not_connected()

@app.route("/info")
def info():
    # print(kite)
    # if kite is not None:
    #     # logger.debug(kite['access_token'])
    return render_template('display.html', screen= "Info")

@app.route("/session/clear")
def clear_session():
    session.clear()
    return render_template('display.html', screen= "Session Cleared")

@app.route("/check_connection")
def check_connection():
    if kite == None:
        return kite_client_not_connected()
    else :
        return render_template('display.html', screen= "Connection OK")

@app.route("/get_orders")
def orders():
    if kite == None:
        return kite_client_not_connected()
    else :
        order.get_orders()
        return render_template('display.html', screen= 'Orders')

@app.route("/instruments")
def instruments():
    if kite == None:
        return kite_client_not_connected()
    else :
        data.fetch_instruments(kite)
        return render_template('display.html', screen= 'Instruments')

@app.route("/place_order/sell")
def place_sell_order():
    try:
        order_id = order.place_sell_banknifty_option_market_order(
            request.args['expiry'],
            request.args['strike_price'],
            request.args['type'],
            request.args['quantity'],
            request.args['price']
        )
        return render_template('display.html', screen= "Order Placed with order_id : {}".format(order_id))
    except BadRequestKeyError:
        abort(401)

@app.route("/place_order/buy")
def place_buy_order():
    try:
        order_id = order.place_buy_banknifty_option_market_order(
            request.args['expiry'],
            request.args['strike_price'],
            request.args['type'],
            request.args['quantity'],
            request.args['price']
        )
        return render_template('display.html', screen= "Order Placed with order_id : {}".format(order_id))
    except BadRequestKeyError:
        abort(401)

@app.route("/place_order/gtt")
def place_gtt_order():
    try:
        order_id = place_sell_banknifty_option_gtt_order(
            request.args['expiry'],
            request.args['strike_price'],
            request.args['type'],
            request.args['quantity']
        )
        return render_template('display.html', screen= "Gtt Order Placed with trigger_id : {}".format(order_id))
    except BadRequestKeyError:
        abort(401)

@app.route("/start_stream")
def start_stream():
    try:
        stream.start_stream()
        return render_template('display.html', screen= "Started LTP Qoute Stream")
    except Exception as e:
        logger.debug("Exception Occured in start_stream() : {}".format(e))
        abort(401)

@app.route("/stop_stream")
def stop_stream():
    try:
        if kws == None:
            logger.debug("Kite is None")
        elif kws.is_connected() == False:
            logger.debug("KiteTicker is Already Not Connected")
        else:
            logger.debug("Closing The Ticker Thread")
            kws.close(code= 1000, reason= "Normal closure; the connection successfully \
            completed whatever purpose for which it was created")
        return render_template('display.html', screen= "Stopped The Stream Thread")
    except Exception as e:
        logger.debug("Exception Occured in stop_stream(): {}".format(e))
        abort(401)

@app.route("/check_threads")
def check_threads():
    try:
        logger.debug("Check the threads in Code : {}".format(threading.active_count()))
        logger.debug("Check the Current Thread in Code : {}".format(threading.current_thread()))
        logger.debug("Check the all Thread in Code : {}".format(threading.enumerate()))
        return render_template('display.html', screen= "Threads Checking")
    except Exception as e:
        logger.debug("Exception Occured in check_threads(): {} ".format(e))
        abort(401)

@app.route("/postback", methods= ['POST'])
def postback():
    print("hello")

@app.route("/get_option_chain")
def get_option_chain():
    try:
        logger.debug(request.args["expiry"])
        data.get_option_chain_data(str(request.args["expiry"]))
        return render_template('display.html', screen= "Option Chain Fetch")
    except Exception as e:
        logger.error("Exception Occured in Option Chain Getter : {}".format(e))
        abort(401)

@app.errorhandler(BadRequestKeyError)
def displayError(e):
    app.logger.error(e)
    return render_template('error.html', error = e), 401