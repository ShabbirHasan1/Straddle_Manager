from os import name
import threading
from kiteconnect import KiteConnect
import logging, coloredlogs
import server, data, db, user
import json

logger = logging.getLogger(__name__)
coloredlogs.install(level= 'DEBUG')

log_orders = True

def handle_postback(payload):
    logger.debug(payload)
    if payload["status"] == "COMPLETE":
        logger.debug("Removing order_id: {} from wait set".format(payload['order_id']))
        server.order_ids_wait_set.remove(payload['order_id'])
        if payload['tradingsymbol'] == server.call_symbol_data['tradingsymbol']:
            server.call_average_price = payload['average_price']
        if payload['tradingsymbol'] == server.put_symbol_data['tradingsymbol']:
            server.put_average_price = payload['average_price']
    else:
        logger.debug("Order Execution Error")
        raise(Exception)

def get_orders():
    try:
        orders = server.kite.orders()
        server.orders_list = orders
        if log_orders:
            logger.debug("Orders are :" + str(orders))
    except Exception as e:
        logger.error("Error Occured in get_orders() : {}".format(e))

"""
Fetches latest order entries and then checks if order_id of type is executed successfully
"""
def check_order(order_id, type, entry_type):
    logging.debug("Check Order Thread Started With Order Id : {} type : {}".format(order_id, type))
    try:
        logging.debug("Starting Check Order Infinite Loop")
        while True:
            global log_orders
            log_orders = False
            get_orders()
            log_orders = True
            for order in server.orders_list:
                if order["order_id"] == order_id:
                    if order["status"] == "COMPLETE":
                        if type == "CE":
                            if entry_type == "entry":
                                server.call_average_price = order["average_price"]
                                server.in_call_position = True
                                logger.debug("Spawn a new DB thread and save order executed")
                                db_order_writer_thread = threading.Thread(target= db.write_order, args=(order, "CE"))
                                db_order_writer_thread.start()
                            elif entry_type == "exit":
                                server.call_exit_average_price = order["average_price"]
                                server.in_call_exit_position = True
                                server.in_call_position = False
                                server.call_order_id = None
                                server.call_average_price = None
                                server.call_exit_order_id = None
                                server.call_tick_data = None
                                server.call_exit_tick_data = None
                                logger.debug("Spawn a new DB thread and remove previous call from executed order DB")
                                db_order_remove_thread = threading.Thread(target= db.remove_order, args=("CE"), name= "db_order_remove_thread_call")
                                db_order_remove_thread.start()
                            return True
                        elif type == "PE":
                            if entry_type == "entry":
                                server.put_average_price = order["average_price"]
                                server.in_put_position = True
                                logger.debug("Spawn a new DB thread and save order executed")
                                db_order_writer_thread = threading.Thread(target= db.write_order, args=(order, "PE"))
                                db_order_writer_thread.start()
                            elif entry_type == "exit":
                                server.put_average_price = order["average_price"]
                                server.in_put_exit_position = True
                                server.in_put_position = False
                                server.put_order_id = None
                                server.put_average_price = None
                                server.put_exit_order_id = None
                                server.put_tick_data = None
                                server.put_exit_tick_data = None
                                logger.debug("Spawn a new DB thread and remove previous put from executed order DB")
                                db_order_remove_thread_put = threading.Thread(target= db.remove_order, args=("PE"), name= "db_order_remove_thread_put")
                                db_order_remove_thread_put.start()
                            return True

                    elif order["status"] == "CANCELLED" or order["status"] == "REJECTED":
                        logger.error("Order Not Placed With status : {}".format(order["status"]))
                        raise

    except Exception as e:
        logger.error("Error Occured in check_order() : {}".format(e))


def place_limit_order(trading_symbol, exchange, transaction_type, quantity, variety, order_type, product, price):
    try:
        order_id = server.kite.place_order(
            tradingsymbol = trading_symbol,
            exchange= exchange,
            transaction_type= transaction_type,
            quantity= quantity,
            product= product,
            order_type= order_type,
            variety= variety,
            price= price
        )

        logger.debug("Order Placed With Order ID : {}".format(order_id))
        return order_id
    except Exception as e:
        logger.error("Some Error Occured in placing limit_order() : {}".format(e))
        raise 

def place_market_order(trading_symbol, exchange, transaction_type, quantity, variety, order_type, product):
    try:
        order_id = server.kite.place_order(
            tradingsymbol = trading_symbol,
            exchange= exchange,
            transaction_type= transaction_type,
            quantity= quantity,
            product= product,
            order_type= order_type,
            variety= variety
        )

        logger.debug("Market Order Sent With Order ID : {}".format(order_id))
        return order_id
    except Exception as e:
        logger.error("Some Error Occured in placing market_order() : {}".format(e))
        raise 

def place_gtt(tradingsymbol, exchange, trigger_values, last_price, orders):
    try:
        gtt = server.kite.place_gtt(
            trigger_type= server.kite.GTT_TYPE_SINGLE,
            tradingsymbol= tradingsymbol,
            exchange= exchange,
            trigger_values= trigger_values,
            last_price= last_price,
            orders= orders,
        )
        logger.debug("Gtt Response is {}".format(gtt['trigger_id']))
        return gtt['trigger_id']
    except Exception as e:
        logger.error("Some Error Occured : {}".format(e))

def place_sell_banknifty_option_market_order(type, quantity):
    trading_symbol= server.call_symbol_data['tradingsymbol']
    if type == "PE":
        trading_symbol= server.put_symbol_data['tradingsymbol']
    order_id = place_market_order(
        trading_symbol= trading_symbol,
        exchange= server.call_symbol_data['exchange'],
        transaction_type= server.kite.TRANSACTION_TYPE_SELL,
        quantity= server.call_symbol_data['lot_size']*(int)(quantity),
        variety= server.kite.VARIETY_REGULAR,
        order_type= server.kite.ORDER_TYPE_MARKET,
        product= server.kite.PRODUCT_NRML,
    )
    return order_id

def place_buy_banknifty_option_market_order(type, quantity):
    trading_symbol= server.call_exit_symbol_data['tradingsymbol']
    if type == "PE":
        trading_symbol= server.put_exit_symbol_data['tradingsymbol']
    order_id = place_market_order(
        trading_symbol= trading_symbol,
        exchange= server.call_exit_symbol_data['exchange'],
        transaction_type= server.kite.TRANSACTION_TYPE_BUY,
        quantity= server.call_exit_symbol_data['lot_size']*(int)(quantity),
        variety= server.kite.VARIETY_REGULAR,
        order_type= server.kite.ORDER_TYPE_MARKET,
        product= server.kite.PRODUCT_NRML,
    )
    logger.debug("Order Sent with order_id : {}".format(order_id))
    return order_id

def place_sell_banknifty_option_gtt_order(expiry, strike_price, type, quantity):
    symbol_data = data.get_option_straddle_symbol_data("BANKNIFTY", expiry, strike_price, type)
    orders = [
        {
        "transaction_type" : "SELL",
        "quantity" : symbol_data['lot_size']*(int)(quantity),
        "price" : 150,
        "order_type" : server.kite.ORDER_TYPE_LIMIT,
        "product" : server.kite.PRODUCT_CNC
        }
    ]

    return place_gtt(
        tradingsymbol= symbol_data['tradingsymbol'],
        exchange= symbol_data['exchange'],
        trigger_values= [1000],
        last_price = 120,
        orders = orders
    )

def cancel_order(type):
    order_id_to_cancel = server.call_order_id
    if type == "PE":
        order_id_to_cancel = server.put_order_id
    order_id = server.kite.cancel_order(
        variety= server.kite.VARIETY_REGULAR,
        order_id = order_id_to_cancel
    )
    return order_id

# def exit_all():
#     if server.position_list == None:
#         server.position_list = user.positions()

#     for position in server.position_list:
#         place_market_order(
#             position["trading_symbol"],
#             position["exchange"],
#             ,
#             position["quantity"],

#         )
