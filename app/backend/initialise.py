import logging
from kiteconnect import KiteConnect
import server

"""
Initialise the Kite Client And Set Access Token
"""

def get_kite_client():
    kite = KiteConnect(api_key= server.kite_api_key)
    return kite

def set_access_token(kite:KiteConnect, session):
    if "access_token" in session:
        kite.set_access_token(session["access_token"])
    else :
        session["access_token"] = kite.generate_session(server.kite_request_token, server.kite_api_secret)["access_token"]
    server.kite_access_token = session["access_token"]
    # logging.debug("Access Token : {}".format(session['access_token']))

def initialise_client():
    server.kite = get_kite_client()
    set_access_token(server.kite, server.session)
    return server.kite