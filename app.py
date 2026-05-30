import os
import sqlite3
from flask import Flask, jsonify, render_template, request
import requests
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

app = Flask(__name__)

# Fetch the token safely from the environment
ANILIST_TOKEN = os.getenv("ANILIST_TOKEN")
ANILIST_URL = "https://graphql.anilist.co"

HEADERS = {
    "Authorization": f"Bearer {ANILIST_TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}
DB_PATH = "anilist_manager.db"

def init_db():
    """
    Initializes the local SQLite database used for persistence 
    of nested child rows mapped to parent rows.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS media_groupings (
            parent_id TEXT,
            child_id TEXT,
            PRIMARY KEY (parent_id, child_id)
        )
    """)
    conn.commit()
    conn.close()

def get_my_private_watchlist():
    """
    Queries the AniList GraphQL engine for authentic user data logs.
    Includes explicit queries for formatting, metadata tracking metrics, 
    genres arrays, and raw text layout descriptions.
    """
    query = """
    query {
      Viewer { name }
      animeList: MediaListCollection(userId: 7320378, type: ANIME) {
        lists {
          status
          entries {
            id
            status
            notes
            score(format: POINT_10_DECIMAL)
            media {
              id
              title { english romaji }
              type
              format
              episodes
              genres
              description
              coverImage { large }
            }
          }
        }
      }
      mangaList: MediaListCollection(userId: 7320378, type: MANGA) {
        lists {
          status
          entries {
            id
            status
            notes
            score(format: POINT_10_DECIMAL)
            media {
              id
              title { english romaji }
              type
              format
              chapters
              genres
              description
              coverImage { large }
            }
          }
        }
      }
    }
    """
    try:
        response = requests.post(ANILIST_URL, json={'query': query}, headers=HEADERS)
        if response.status_code == 200:
            return response.json().get('data')
        else:
            print(f"API Error Response: {response.text}")
    except Exception as e:
        print(f"Network error: {e}")
    return None

def parse_tier_from_notes(notes_str):
    """
    Utility parser sorting custom tracking text data from internal watch notes streams.
    """
    if not notes_str:
        return "None"
    cleaned = notes_str.strip().lower()
    if cleaned.startswith("tier 1"): return "Tier 1"
    if cleaned.startswith("tier 2"): return "Tier 2"
    if cleaned.startswith("tier 3"): return "Tier 3"
    return "None"

@app.route('/')
def home():
    """
    Main tracking controller. Parses both lists, assigns localized structural references,
    maps nested layout parameters, and computes metadata lists.
    """
    all_media = []
    username = "Profile"
    api_data = get_my_private_watchlist()
    
    # Track baseline authentic entries directly from AniList payload
    anilist_total = 0

    if api_data:
        if api_data.get('Viewer') and api_data['Viewer']:
            username = api_data['Viewer']['name']
            
        # Parse Anime Lists
        if api_data.get('animeList'):
            for current_list in api_data['animeList']['lists']:
                for entry in current_list['entries']:
                    anilist_total += 1  
                    media = entry['media']
                    score_val = entry.get('score') or 0.0
                    display_title = media['title']['english'] or media['title']['romaji']
                    raw_status = entry.get('status') or current_list.get('status') or "CURRENT"

                    # Clean description data text fields
                    desc_text = media.get('description') or "No description available."

                    all_media.append({
                        "entry_id": str(entry['id']),
                        "title": display_title,
                        "display_type": (media['format'] or 'ANIME').upper(),
                        "length": f"{media['episodes'] or '?'} Eps",
                        "genres": media.get('genres') or [],
                        "description": desc_text,
                        "user_status": raw_status.upper(),  
                        "tier": parse_tier_from_notes(entry.get('notes')),
                        "raw_notes": entry.get('notes') or "",
                        "raw_score": float(score_val),
                        "user_rating": f"{score_val}/10" if score_val > 0 else "Unrated",
                        "cover_image": media.get('coverImage', {}).get('large', ''),
                        "children_entries": []
                    })

        # Parse Manga Lists
        if api_data.get('mangaList'):
            for current_list in api_data['mangaList']['lists']:
                for entry in current_list['entries']:
                    anilist_total += 1  
                    media = entry['media']
                    score_val = entry.get('score') or 0.0
                    display_title = media['title']['english'] or media['title']['romaji']
                    raw_status = entry.get('status') or current_list.get('status') or "CURRENT"

                    # Clean description data text fields
                    desc_text = media.get('description') or "No description available."

                    all_media.append({
                        "entry_id": str(entry['id']),
                        "title": display_title,
                        "display_type": (media['format'] or 'MANGA').upper(),
                        "length": f"{media['chapters'] or '?'} Chaps",
                        "genres": media.get('genres') or [],
                        "description": desc_text,
                        "user_status": raw_status.upper(),  
                        "tier": parse_tier_from_notes(entry.get('notes')),
                        "raw_notes": entry.get('notes') or "",
                        "raw_score": float(score_val),
                        "user_rating": f"{score_val}/10" if score_val > 0 else "Unrated",
                        "cover_image": media.get('coverImage', {}).get('large', ''),
                        "children_entries": []
                    })

        # Query local SQLite relationships to parse parent/child row linkages
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT parent_id, child_id FROM media_groupings")
        links = cursor.fetchall()
        conn.close()

        child_to_parent = {link[1]: link[0] for link in links}
        items_by_id = {item['entry_id']: item for item in all_media}

        master_list = []
        for item in all_media:
            eid = item['entry_id']
            if eid not in child_to_parent:
                master_list.append(item)

        for child_id, parent_id in child_to_parent.items():
            if parent_id in items_by_id and child_id in items_by_id:
                items_by_id[parent_id]['children_entries'].append(items_by_id[child_id])

        # Strict weight sorting function matching Tier levels and visual criteria
        def sort_weights(x):
            tier_map = {"Tier 1": 1, "Tier 2": 2, "Tier 3": 3, "None": 4}
            return (tier_map[x['tier']], x['user_status'] != 'COMPLETED', -x['raw_score'], x['title'].lower())

        master_list.sort(key=sort_weights)

    return render_template('index.html', all_media=master_list, full_raw_list=all_media, username=username, anilist_total=anilist_total)

@app.route('/update_tier', methods=['POST'])
def update_tier():
    """
    Updates localized note parameters across public AniList database records.
    """
    data = request.get_json()
    entry_id = data.get('entry_id')
    new_tier = data.get('tier')
    old_notes = data.get('old_notes', "")

    cleaned_notes = old_notes
    for token in ["tier 1", "tier 2", "tier 3", "Tier 1", "Tier 2", "Tier 3"]:
        cleaned_notes = cleaned_notes.replace(token, "")
    cleaned_notes = cleaned_notes.strip()

    final_notes = cleaned_notes
    if new_tier != "None":
        final_notes = f"{new_tier} | {cleaned_notes}" if cleaned_notes else new_tier

    mutation = """
    mutation ($id: Int, $notes: String) {
        SaveMediaListEntry (id: $id, notes: $notes) {
            id
            notes
        }
    }
    """
    variables = {'id': int(entry_id), 'notes': final_notes}
    response = requests.post(ANILIST_URL, json={'query': mutation, 'variables': variables}, headers=HEADERS)
    
    if response.status_code == 200:
        return jsonify({"success": True, "updated_notes": final_notes})
    return jsonify({"success": False, "error": response.text}), 400

@app.route('/sync_anilist', methods=['POST'])
def sync_anilist():
    """
    Asynchronous manual synchronization polling endpoint.
    """
    try:
        api_data = get_my_private_watchlist()
        total_items = 0
        if api_data:
            if api_data.get('animeList'):
                total_items += sum(len(l['entries']) for l in api_data['animeList']['lists'])
            if api_data.get('mangaList'):
                total_items += sum(len(l['entries']) for l in api_data['mangaList']['lists'])
        return jsonify({"success": True, "message": f"Successfully synchronized {total_items} items!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/link_entries', methods=['POST'])
def link_entries():
    """
    Binds nested media sub-items to assigned group container entries inside sqlite tables.
    """
    try:
        data = request.get_json()
        parent_id = str(data.get('parent_id'))
        child_ids = data.get('child_ids', [])
        
        if not parent_id or not child_ids:
            return jsonify({"success": False, "error": "Missing parameters"}), 400
            
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        for child_id in child_ids:
            if str(child_id) != parent_id:
                cursor.execute(
                    "INSERT OR IGNORE INTO media_groupings (parent_id, child_id) VALUES (?, ?)",
                    (parent_id, str(child_id))
                )
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/unlink_entry', methods=['POST'])
def unlink_entry():
    """
    Removes group binding parameters to transform mapped children into standalone items.
    """
    try:
        data = request.get_json()
        child_id = str(data.get('child_id'))
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM media_groupings WHERE child_id = ?", (child_id,))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5001)