from pymongo import MongoClient
from pymongo.server_api import ServerApi
from scipy.spatial.distance import cosine
import numpy as np
from collections import defaultdict
from sklearn.preprocessing import normalize




# Connect to MongoDB

# database set up
uri = "mongodb+srv://maanit:We'reall50%25banana@tangle.h9qzr.mongodb.net/?retryWrites=true&w=majority&appName=tangle"
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
        '_email': 1,
        '_year': 1,
        '_match': 1
    }))
    for user in users:
        
