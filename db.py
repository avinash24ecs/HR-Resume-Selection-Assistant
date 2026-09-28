"""Returns a MongoDB database.
 - MONGO_URI set  -> real MongoDB (Atlas / local).
 - not set        -> local MongoDB if running, else in-memory mongomock (always the case on Vercel)."""
import os
from config import MONGO_URI, MONGO_DB

SOURCE = "unknown"
_db = None

def get_db(verbose=True):
    global SOURCE, _db
    if _db is not None:
        return _db
    explicit = "MONGO_URI" in os.environ
    if explicit or not os.getenv("VERCEL"):
        try:
            from pymongo import MongoClient
            client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000 if explicit else 1500)
            client.admin.command("ping")
            SOURCE = "mongodb"
            if verbose: print("[MongoDB] Connected to real MongoDB server")
            _db = client[MONGO_DB]
            return _db
        except Exception as e:
            if verbose: print(f"[MongoDB] Could not connect ({type(e).__name__}) -> using in-memory mongomock")
    import mongomock
    SOURCE = "mongomock (in-memory)"
    _db = mongomock.MongoClient()[MONGO_DB]
    return _db
