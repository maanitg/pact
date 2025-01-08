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

def create_user_vectors():
    users_data = list(coll.find({}, {
        '_email': 1,
        '_year': 1,
        '_long_alb': 1,
        '_long_art': 1,
        '_long_gen': 1,
        '_long_tracks': 1,
        '_med_alb': 1,
        '_med_art': 1,
        '_med_gen': 1,
        '_med_tracks': 1,
        '_short_tracks': 1
    }))

    # Create sets of all unique artists, songs, and genres

    all_long_alb = set()
    all_long_art = set()
    all_long_gen = set()
    all_long_tracks = set()
    all_med_alb = set()
    all_med_art = set()
    all_med_gen = set()
    all_med_tracks = set()
    all_short_tracks = set()
    


    for user in users_data:
        all_long_alb.update(user.get('_long_alb', []))
        all_long_art.update(user.get('_long_art', []))
        all_long_gen.update(user.get('_long_gen', []))
        all_long_tracks.update(user.get('_long_tracks', []))
        all_med_alb.update(user.get('_med_alb', []))
        all_med_art.update(user.get('_med_art', []))
        all_med_gen.update(user.get('_med_gen', []))
        all_med_tracks.update(user.get('_med_tracks', []))
        all_short_tracks.update(user.get('_short_tracks', []))

    # Convert sets to sorted lists for consistent indexing
    all_long_alb = sorted(all_long_alb)
    all_long_art = sorted(all_long_art)
    all_long_gen = sorted(all_long_gen)
    all_long_tracks = sorted(all_long_tracks)
    all_med_alb = sorted(all_med_alb)
    all_med_art = sorted(all_med_art)
    all_med_gen = sorted(all_med_gen)
    all_med_tracks = sorted(all_med_tracks)
    all_short_tracks = sorted(all_short_tracks)
    

    # Create index mappings
    long_alb_index = {album: i for i, album in enumerate(all_long_alb)}
    long_art_index = {artist: i for i, artist in enumerate(all_long_art)}
    long_gen_index = {genre: i for i, genre in enumerate(all_long_gen)}
    long_tracks_index = {song: i for i, song in enumerate(all_long_tracks)}
    med_alb_index = {album: i for i, album in enumerate(all_med_alb)}
    med_art_index = {artist: i for i, artist in enumerate(all_med_art)}
    med_gen_index = {genre: i for i, genre in enumerate(all_med_gen)}
    med_tracks_index = {song: i for i, song in enumerate(all_med_tracks)}
    short_tracks_index = {song: i for i, song in enumerate(all_short_tracks)}
    
  
    

    # Create user vectors
    user_vectors = []
    user_ids = []
    for user in users_data:
        vector = np.zeros(len(all_long_alb) + len(all_long_art) + len(all_long_gen) + len(all_long_tracks) +
                          len(all_med_alb) + len(all_med_art) + len(all_med_gen) + len(all_med_tracks) + len(all_short_tracks))
        
        for album in user.get('_long_alb', []):
            vector[long_alb_index[album]] = 1
        for artist in user.get('_long_art', []):
            vector[len(all_long_alb) + long_art_index[artist]] = 1
        for genre in user.get('_long_gen', []):
            vector[len(all_long_alb) + len(all_long_art) + long_gen_index[genre]] = 1
        for track in user.get('_long_tracks', []):
            vector[len(all_long_alb) + len(all_long_art) + len(all_long_gen) + long_tracks_index[track]] = 1
        for album in user.get('_med_alb', []):
            vector[len(all_long_alb) + len(all_long_art) + len(all_long_gen) + len(all_long_tracks) + med_alb_index[album]] = 1
        for artist in user.get('_med_art', []):
            vector[len(all_long_alb) + len(all_long_art) + len(all_long_gen) + len(all_long_tracks) + len(all_med_alb) + med_art_index[artist]] = 1
        for genre in user.get('_med_gen', []):
            vector[len(all_long_alb) + len(all_long_art) + len(all_long_gen) + len(all_long_tracks) + len(all_med_alb) + len(all_med_art) + med_gen_index[genre]] = 1
        for track in user.get('_med_tracks', []):
            vector[len(all_long_alb) + len(all_long_art) + len(all_long_gen) + len(all_long_tracks) + len(all_med_alb) + len(all_med_art) + len(all_med_gen) + med_tracks_index[track]] = 1
        for track in user.get('_short_tracks', []):
            vector[len(all_long_alb) + len(all_long_art) + len(all_long_gen) + len(all_long_tracks) + len(all_med_alb) + len(all_med_art) + len(all_med_gen) + len(all_med_tracks) + short_tracks_index[track]] = 1
        
        user_vectors.append(vector)
        user_ids.append(user['_id'])

    # Normalize the vectors
    normalized_vectors = normalize(user_vectors)

    return normalized_vectors, user_ids


def get_compatible_users(user_id, k=10):
    user = coll.find_one({'_email': user_id})
    user_vector = np.array(user['_vector'])
    looking_for = user['_friendpartner']
    gender = user['_gender']
    gender_preference = user.get('_partner', [])

    match_conditions = []
    if 'Friend' in looking_for:
        match_conditions.append({'looking_for': 'Friend'})
    if 'Partner' in looking_for:
        match_conditions.append({
            'looking_for': 'Partner',
            'gender': {'$in': gender_preference},
            'gender_preference': gender
        })

    compatible_users = coll.aggregate([
        {'$match': {
            '_email': {'$ne': user_id},
            '$or': match_conditions
        }},
        {'$project': {
            '_email': 1,
            '_vector': 1,
            '_similarity': {
                '$let': {
                    'vars': {'other_vector': '$vector'},
                    'in': {'$subtract': [1, {'$cosine': [user_vector, '$$other_vector']}]}
                }
            }
        }},
        {'$sort': {'similarity': -1}},
        {'$limit': k}
    ])
    
    return [user['_email'] for user in compatible_users]

def gale_shapley(user_ids, k=10):
    free_users = set(user_ids)
    engaged = {}
    proposals = defaultdict(set)
    preferences = {}

    while free_users:
        user = free_users.pop()
        if user not in preferences:
            preferences[user] = get_compatible_users(user, k)
        
        for partner in preferences[user]:
            if partner not in proposals[user]:
                proposals[user].add(partner)
                if partner not in engaged:
                    engaged[partner] = user
                    break
                else:
                    current_partner = engaged[partner]
                    if partner not in preferences:
                        preferences[partner] = get_compatible_users(partner, k)
                    
                    if preferences[partner].index(user) < preferences[partner].index(current_partner):
                        engaged[partner] = user
                        free_users.add(current_partner)
                        break
        else:
            free_users.add(user)

    return engaged

# Fetch all user IDs from the collection
all_users = list(coll.find({}, {'_email': 1}))
user_ids = [user['_email'] for user in all_users]

# Run the algorithm
matches = gale_shapley(user_ids)

# Store results in mongodb, and print
for user1, user2 in matches.items():
    coll.update_one({ "_email": user1 },
        { "$set": { "_match": user2 }  }
    )
    coll.update_one({ "_email": user2 },
        { "$set": { "_match": user1 }  }
    )
    print(f"Matched: {user1} with {user2}")
