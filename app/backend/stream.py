import logging
from os import name
import threading
import coloredlogs
from kiteconnect import KiteTicker
import data, server, db

logger = logging.getLogger(__name__)
coloredlogs.install(level= 'DEBUG')

"""
Receives all the tick related data
"""

def on_ticks(ws, ticks):
    try:
        logger.debug("Tick Data Received Length Of Tick Data : {}".format(len(ticks)))
        logger.debug("Tick Data : {}".format(ticks))
        
        if server.data_fetching == False:
            for tick in ticks:
                if server.spot_symbol_data != None and (tick["instrument_token"] == server.spot_symbol_data["instrument_token"]):
                        server.spot_tick_data = tick
                        logger.debug("spot_tick_data is : {}".format(server.\
                        spot_tick_data))
                elif server.call_symbol_data != None and (tick["instrument_token"] == server.call_symbol_data["instrument_token"]):
                        server.call_tick_data = tick
                        logger.debug("call_tick_data is : {}".format(server.\
                        call_tick_data))
                elif server.put_symbol_data != None and (tick["instrument_token"] == server.put_symbol_data["instrument_token"]):
                        server.put_tick_data = tick
                        logger.debug("put_tick_data is : {}".format(server.\
                        put_tick_data))
                elif server.call_exit_symbol_data != None and (tick["instrument_token"] == server.call_exit_symbol_data["instrument_token"]):
                        server.call_exit_tick_data = tick
                        logger.debug("call_exit_tick_data is : {}".format(server.\
                        call_exit_tick_data))
                elif server.put_exit_symbol_data != None and (tick["instrument_token"] == server.put_exit_symbol_data["instrument_token"]):
                        server.put_exit_tick_data = tick
                        logger.debug("put_exit_tick_data is : {}".format(server.\
                        put_exit_tick_data))
            
            if server.start_algo_on_tick == True:
                logger.debug("Sending flow to a new thread which checks algo conditions")
                if server.algo_thread != None and server.algo_thread.is_alive():
                    logger.debug("Algo Already Running")
                else:
                    server.algo_thread = threading.Thread(target= strategy.sell_straddle, daemon= True)
                    server.algo_thread.start()
        else:
            option_chain_writer = threading.Thread(target= db.write_option_chain, args=(ticks, ))
            option_chain_writer.start()
    except Exception as e:
        logger.error("Exception in on_tick() : {} ".format(e))
        raise

"""
Subscribe to Spot Data As soon as websocket is Opened
"""
def on_connect(ws:KiteTicker, response):
    try:
        if server.data_fetching == False:
            data.get_banknifty_spot_data()
            instrument_tokens = []
            instrument_tokens.append((int)(server.spot_symbol_data['instrument_token']))

            ws.subscribe(instrument_tokens)
            ws.set_mode(ws.MODE_FULL, instrument_tokens)
        logger.debug("Subscribed to instrument tokens : {}".format(ws.subscribed_tokens))
    except Exception as e:
        logger.error("Some Exception Occured on_connect() : {}".format(e))
        raise

def on_close(ws:KiteTicker, code, reason):
    logger.debug("Connection Closed with Code : {} with Reason : {}".format(code, reason))

def on_error(ws, code, reason):
    logger.debug("Connection Closed With Error: {code} - \
    Reason: {reason}".format(code = code, reason = reason))

def on_noreconnect(ws):
    logger.debug("Reconnect Failed")

def init_stream():
    try:
        server.kws = KiteTicker(server.kite_api_key, server.kite_access_token)
        server.kws.on_ticks = on_ticks
        server.kws.on_connect = on_connect
        server.kws.on_close = on_close
        server.kws.on_error = on_error
        server.kws.on_noreconnect = on_noreconnect
    except Exception as e:
        logger.error("Exception Occured in init_stream(): {}".format(e))

def start_stream():
    try:
        if server.kws != None and server.kws.is_connected():
            logger.debug("Websocket Already Connected")
            return
        init_stream()
        server.kws.connect(threaded= True)
    except Exception as e:
        logger.error("Error Occured in start_stream() : {}".format(e))
        raise