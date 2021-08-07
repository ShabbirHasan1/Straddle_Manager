import logging, coloredlogs
import threading
import db
from kiteconnect import KiteConnect
import pandas as pd
import server, stream

logger = logging.getLogger(__name__)
coloredlogs.install(level= 'DEBUG')

"""
Fetch Any Symbol Related Historical And MetaData For Tickers
"""

def fetch_instruments():
    logger.debug("Calling The Instruments Api")
    instruments = server.kite.instruments()
    db.write_instruments(instruments)
    server.instument_data = pd.read_csv("instruments.csv", dtype= {
        "instrument_token" : int,
        "exchange_token" : int,
        "tradingsymbol" : str,
        "last_price" : int,
        "expiry" : str,
        "strike" : float,
        "tick_size" : float })
    logger.debug("Instrument Data : {}".format(server.instument_data))



"""
Returns Dataframe Contaning Straddle Symbol Data
Volatile in Ram (Not Storing in DB)
"""
def get_option_straddle_symbol_data(expiry):
    try:
        data_required = server.instument_data[(server.instument_data['expiry'] == expiry)]
        data_required = data_required[data_required['tradingsymbol'].str.contains(str(server.straddle_strike_price))]
        logger.debug("Straddle Option symbol data Returned is : \n {}".format(data_required))
        return data_required
    except Exception as e:
        logger.error("Error Occured in get_option_data() : {}".format(e))

def get_option_chain_data(expiry):
    try:
        data_required = server.instument_data[(server.instument_data['expiry'] == expiry)]
        data_required = data_required[data_required['tradingsymbol'].str.contains("BANKNIFTY")]
        data_required = data_required[~data_required['tradingsymbol'].str.contains("FUT")]
        logger.debug("Option Chain data Returned is : \n {}".format(data_required))
        logger.debug("Saving Data to DB using new thread")
        option_list_token = []
        for idx,row in data_required.iterrows():
            if idx != 0:
                option_list_token.append(int(row.to_dict()["instrument_token"]))
        stream.start_stream()
        logger.debug(option_list_token)
        if server.kws != None:
            server.kws.subscribe(option_list_token)
        return data_required
    except Exception as e:
        logger.error("Error Occured in get_option_data() : {}".format(e))
        raise

def get_exit_option_symbol_data():
    try:
        if server.call_symbol_data != None:
            data_required = server.instument_data[server.instument_data['tradingsymbol'].str.contains(server.call_symbol_data['tradingsymbol'][:-2])]
        elif server.put_symbol_data != None:
            data_required = server.instument_data[server.instument_data['tradingsymbol'].str.contains(server.put_symbol_data['tradingsymbol'][:-2])]
        else:
            logger.error("Symbol Data Not Loaded into memory")
        logger.debug("Straddle Exit Option Symbol Data Returned is : \n {}".format(data_required))
        return data_required
    except Exception as e:
        logger.error("Error occured in get_exit_opton_symbol_data() : {}".format(e)),

"""
Returns DataFrame Containing Spot Symbol Data
Volatile in Ram (Not Storing in DB)
"""
def get_banknifty_spot_data():
    data_required = server.instument_data[(server.instument_data['name'] == "NIFTY BANK") & (server.instument_data["segment"] == "INDICES")].iloc[0]
    server.spot_symbol_data = data_required.to_dict()
    logger.debug("Spot Data is : \n {}".format(server.spot_symbol_data))

def get_strike(instrument_token):
    data_required = server.instument_data[(server.instument_data["instrument_token"]) == instrument_token]
    strike = str(data_required.iloc[0]["tradingsymbol"])
    logger.debug(strike)
    type = strike[-2:]
    strike = int(strike[-7:-2])
    # logger.debug(strike)
    # logger.debug(type)
    return [strike, type]
