import spotipy
from spotipy.oauth2 import SpotifyOAuth
import itertools
import requests

# ==== CONFIGURATION ====
CLIENT_ID = "xxxx"
CLIENT_SECRET = "xxxx"
REDIRECT_URI = "http://127.0.0.1:8888/callback"
SCOPE = "playlist-read-private playlist-modify-private playlist-modify-public"
PLAYLIST_ID = "xxxx"  # format: "spotify:playlist:xxxx"
NEW_PLAYLIST_NAME = "New Playlist"
RECCOBEATS_API = "https://api.reccobeats.com/v1/audio-features"
# =================

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SCOPE
))

print(" --- 1. Get playlist tracks ---")
def get_tracks(playlist_id):
    results = []
    offset = 0
    while True:
        data = sp.playlist_items(playlist_id, offset=offset, fields="items.track.id,items.track.name,items.track.artists.name,total,next")
        results += [item["track"] for item in data["items"] if item["track"]]
        if not data["next"]:
            break
        offset += len(data["items"])
    return results

tracks = get_tracks(PLAYLIST_ID)
track_ids = [t["id"] for t in tracks]

print("--- 2. Get ReccoBeats audio features ---")
def get_recco_features(ids):
    results = []
    for i in range(0, len(ids), 40):
        batch_ids = ids[i:i+40]
        resp = requests.get(RECCOBEATS_API, params={"ids": ",".join(batch_ids)})
        if resp.status_code == 200:
            results += resp.json()['content']
        else:
            print("Error fetching features for batch:", batch_ids)
    return results

features = get_recco_features(track_ids)

# --- 3. Camelot mapping ---
camelot_map = {
    0: ("8B","8A"), 1:("3B","3A"), 2:("10B","10A"),
    3:("5B","5A"), 4:("12B","12A"), 5:("7B","7A"),
    6:("2B","2A"), 7:("9B","9A"), 8:("4B","4A"),
    9:("11B","11A"),10:("6B","6A"),11:("1B","1A")
}

def camelot(key, mode):
    if key is None or mode is None or key < 0: return None
    return camelot_map[key][mode]
    
print(" --- 4. Combine info --- ")
data = []
# feature['href'].split('/')[-1] is track id
track_id_lookup = {track['id']: track for track in tracks}
combined_api = [
    {**feature, **track_id_lookup[feature['href'].split('/')[-1]]} 
    for feature in features 
    if feature['href'].split('/')[-1] in track_id_lookup
]

for x in combined_api:
    print(x)
    data.append({
        "id": x["id"],
        "name": x["name"],
        "artist": x["artists"][0]["name"],
        "tempo": x["tempo"],
        "camelot": camelot(x["key"], x["mode"]),
        "energy": x["energy"],
        "valence": x["valence"],
        "danceability": x["danceability"]
    })

# --- 5. Enhanced DJ Sorting Logic ---
def is_perfect_match(a, b):
    """Same Camelot key = perfect harmonic match"""
    return a == b

def is_energy_boost(a, b):
    """Adjacent +1 on wheel (energy boost transition)"""
    if not a or not b: return False
    num_a, let_a = int(a[:-1]), a[-1]
    num_b, let_b = int(b[:-1]), b[-1]
    return let_a == let_b and num_b == (num_a % 12) + 1

def is_energy_drop(a, b):
    """Adjacent -1 on wheel (energy drop transition)"""
    if not a or not b: return False
    num_a, let_a = int(a[:-1]), a[-1]
    num_b, let_b = int(b[:-1]), b[-1]
    return let_a == let_b and num_b == (num_a - 2) % 12 + 1

def is_mode_switch(a, b):
    """Switch between major/minor (A <-> B)"""
    if not a or not b: return False
    num_a, let_a = int(a[:-1]), a[-1]
    num_b, let_b = int(b[:-1]), b[-1]
    return num_a == num_b and let_a != let_b

def harmonic_compatibility(camelot_a, camelot_b):
    """Returns penalty score for harmonic transition (lower is better)"""
    if is_perfect_match(camelot_a, camelot_b):
        return 0  # Perfect mix
    elif is_energy_boost(camelot_a, camelot_b):
        return 5  # Good upward energy transition
    elif is_energy_drop(camelot_a, camelot_b):
        return 8  # Good downward energy transition
    elif is_mode_switch(camelot_a, camelot_b):
        return 12  # Mode switch (major/minor)
    else:
        return 100  # Incompatible keys

def tempo_compatibility(tempo_a, tempo_b):
    """Returns penalty for tempo difference with smart BPM halving/doubling"""
    diff = abs(tempo_a - tempo_b)
    
    # Check if one tempo is roughly double/half of the other (allows mixing different genres)
    ratio = max(tempo_a, tempo_b) / min(tempo_a, tempo_b) if min(tempo_a, tempo_b) > 0 else 999
    if 1.95 <= ratio <= 2.05:  # Within 2.5% of 2x relationship
        diff = diff / 4  # Heavily reduce penalty for tempo doubling
    
    # Gradual tempo changes are best
    if diff <= 3:
        return diff * 1  # Imperceptible change
    elif diff <= 6:
        return diff * 2  # Smooth transition
    elif diff <= 10:
        return diff * 4  # Noticeable but acceptable
    else:
        return diff * 8  # Jarring transition

def energy_flow_score(track_a, track_b, position, total_tracks):
    """Reward building/maintaining energy appropriately throughout set"""
    energy_diff = track_b["energy"] - track_a["energy"]
    
    # Early set: prefer building energy gradually
    if position < total_tracks * 0.3:
        return -abs(energy_diff) * 5 if energy_diff >= -0.1 else abs(energy_diff) * 10
    
    # Mid set: maintain high energy or create dynamic waves
    elif position < total_tracks * 0.7:
        return -abs(energy_diff) * 3 if abs(energy_diff) < 0.15 else abs(energy_diff) * 5
    
    # Late set: allow gradual wind-down but avoid sudden drops
    else:
        return -abs(energy_diff) * 5 if energy_diff <= 0.1 else abs(energy_diff) * 8

def transition_score(track_a, track_b, position=0, total_tracks=100):
    """Comprehensive DJ transition scoring"""
    harmonic_penalty = harmonic_compatibility(track_a["camelot"], track_b["camelot"])
    tempo_penalty = tempo_compatibility(track_a["tempo"], track_b["tempo"])
    energy_score = energy_flow_score(track_a, track_b, position, total_tracks)
    
    # Weight the components (adjust these to preference)
    total_score = (
        harmonic_penalty * 1.5 +  # Harmony is very important
        tempo_penalty * 1.0 +      # Tempo transitions matter
        energy_score * 0.8          # Energy flow shapes the set
    )
    
    return total_score

# Greedy nearest-neighbor sort with position awareness
ordered = [data[0]]
remaining = data[1:]
total_tracks = len(data)

while remaining:
    last = ordered[-1]
    current_position = len(ordered)
    
    # Find best next track considering position in set
    next_track = min(
        remaining, 
        key=lambda x: transition_score(last, x, current_position, total_tracks)
    )
    ordered.append(next_track)
    remaining.remove(next_track)

# Print transition analysis
print("\n=== DJ SET FLOW ===")
for i in range(len(ordered) - 1):
    curr, nxt = ordered[i], ordered[i + 1]
    score = transition_score(curr, nxt, i, len(ordered))
    print(f"{i+1}. {curr['name'][:30]:30} ({curr['camelot']}, {curr['tempo']:.0f} BPM) "
          f"→ {nxt['name'][:30]:30} ({nxt['camelot']}, {nxt['tempo']:.0f} BPM) "
          f"[Score: {score:.1f}]")

print(" --- 6. Create new playlist --- ")
user_id = sp.me()["id"]
new_playlist = sp.user_playlist_create(user_id, NEW_PLAYLIST_NAME, public=False)
for i in range(0, len(ordered), 100):
    sp.playlist_add_items(new_playlist["id"], [t["id"] for t in ordered[i:i+100]])
print(f"\nCreated '{NEW_PLAYLIST_NAME}' with {len(ordered)} tracks sorted with DJ transitions.")

# print(" --- 4. Combine info --- ")
# data = []

# # feature['href'].split('/')[-1] is track id
# track_id_lookup = {track['id']: track for track in tracks}
# combined_api = [
    # {**feature, **track_id_lookup[feature['href'].split('/')[-1]]} 
    # for feature in features 
    # if feature['href'].split('/')[-1] in track_id_lookup
# ]

# print(combined_api)

# for x in combined_api:
    # print(x)
    # data.append({
        # "id": x["id"],
        # "name": x["name"],
        # "artist": x["artists"][0]["name"],
        # "tempo": x["tempo"],
        # "camelot": camelot(x["key"], x["mode"])
    # })

# # --- 5. Sorting logic ---
# def is_adjacent(a, b):
    # if not a or not b: return False
    # num_a, let_a = int(a[:-1]), a[-1]
    # num_b, let_b = int(b[:-1]), b[-1]
    # same_mode = let_a == let_b
    # next_num = (num_a % 12) + 1
    # prev_num = (num_a - 2) % 12 + 1
    # return (num_b == next_num or num_b == prev_num) and same_mode

# def score(a, b):
    # bpm_diff = abs(a["tempo"] - b["tempo"])
    # if a["camelot"] == b["camelot"]:
        # harmonic_penalty = 0
    # elif is_adjacent(a["camelot"], b["camelot"]):
        # harmonic_penalty = 10
    # else:
        # harmonic_penalty = 100
    # return bpm_diff + harmonic_penalty

# # Greedy nearest-neighbor sort
# ordered = [data[0]]
# remaining = data[1:]
# while remaining:
    # last = ordered[-1]
    # next_track = min(remaining, key=lambda x: score(last, x))
    # ordered.append(next_track)
    # remaining.remove(next_track)

# print(ordered)

# print(" --- 6. Create new playlist --- ")
# user_id = sp.me()["id"]
# new_playlist = sp.user_playlist_create(user_id, NEW_PLAYLIST_NAME, public=False)
# for i in range(0, len(ordered), 100):
    # sp.playlist_add_items(new_playlist["id"], [t["id"] for t in ordered[i:i+100]])


# print(f"Created '{NEW_PLAYLIST_NAME}' with {len(ordered)} tracks sorted by BPM and Camelot key.")
