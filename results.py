from pymongo import MongoClient
from pymongo.server_api import ServerApi
from scipy.spatial.distance import cosine
import numpy as np
from collections import defaultdict
import os
from sklearn.preprocessing import normalize




# Connect to MongoDB

# database set up
uri = os.environ.get("MONGO_URI")
if not uri:
    raise RuntimeError("Set MONGO_URI before running the legacy results script.")
# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))
# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)
db = client.tangle
coll = db.users

def send_results():
    users = list(coll.find({}, {
        'email': 1,
        '_year': 1,
        '_match': 1
    }))
    for user in users:
        # Result notification delivery is intentionally left for a later phase.
        # Keeping this script syntactically valid prevents deployment tooling
        # from failing while the new participant journey is piloted.
        print(user.get('email'), user.get('_match'))
