import os
import requests
import psycopg2
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

TMDB_API_KEY = os.getenv('TMDB_API_KEY')
DATABASE_URL = os.getenv('DATABASE_URL')
TMDB_BASE_URL = 'https://api.themoviedb.org/3'

print("Loading embedding model...")
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
print("Model loaded!")

GENRE_MAP = {}

def fetch_genre_list():
    global GENRE_MAP

    print("Fetching genre list from TMDB...")
    url = f"{TMDB_BASE_URL}/genre/movie/list"
    params = {'api_key': TMDB_API_KEY}

    response = requests.get(url, params=params)

    if response.status_code==200:
        genres = response.json()['genres']

        GENRE_MAP = {genre['id']: genre['name'] for genre in genres}
        print(f"Loaded {len(GENRE_MAP)} genres")
    else:
        print(f"Error fetching genres: {response.status_code}")


def get_genre_names(genre_ids):
    return [GENRE_MAP.get(gid, 'Unkown') for gid in genre_ids if gid in GENRE_MAP]



def fetch_popular_movies(num_pages=5):
    movies = []

    for page in range(1,num_pages+1):
        print('Fetching page {page}')
        url = f"{TMDB_BASE_URL}/movie/popular"
        params = {
            'api_key': TMDB_API_KEY,
            'page': page,
            'language': 'en-US'
        }

        response = requests.get(url, params=params)

        if response.status_code == 200:
            data = response.json()
            movies.extend(data['results'])
        else:
            print(f"Error fetching page {page}: {response.status_code}")
    
    print(f"Fetched {len(movies)} movies from TMDB")
    return movies



def generate_embedding(title,overview,genre_names):
    parts =[title]

    if genre_names:
        parts.append(f"Genre: {', '.join(genre_names)}")
    
    if overview:
        parts.append(overview)
    
    text = ". ".join(parts)

    embedding = model.encode(text)
    return embedding.tolist()


def insert_movies_to_db(movies):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    inserted =0
    skipped =0

    for movie in movies:
        try:
            tmdb_id=movie['id']
            title = movie['title']
            overview = movie.get('overview', '')
            release_date = movie.get('release_date', None)
            poster_path = movie.get('poster_path', '')
            vote_average = movie.get('vote_average', 0)
            genre_ids = movie.get('genre_ids', [])

            if not overview:
                skipped+=1
                continue
            
            genre_names = get_genre_names(genre_ids)

            embedding = generate_embedding(title,overview,genre_names)

            release_date_obj = None
            if release_date:
                try:
                    release_date_obj = datetime.strptime(release_date, '%Y-%m-%d').date()
                except:
                    pass
            
            cur.execute("""
                INSERT INTO movies (tmdb_id, title, overview, release_date, poster_path, vote_average, embedding)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (tmdb_id) DO NOTHING
            """, (tmdb_id, title, overview, release_date_obj, poster_path, vote_average, embedding))

            if cur.rowcount>0:
                inserted+=1
            else:
                skipped+=1
            
        except Exception as e:
            print(f"Error inserting {movie.get('title', 'Unknown')}: {e}")
            skipped += 1
            continue
        
    conn.commit()
    cur.close()
    conn.close()

    print(f'inserted: {inserted}')
    print(f'skipped: {skipped}')

    
def main():
    if not TMDB_API_KEY:
        print("❌ Error: TMDB_API_KEY not found in .env file")
        return
    
    if not DATABASE_URL:
        print("❌ Error: DATABASE_URL not found in .env file")
        return
        
    fetch_genre_list()

    movies = fetch_popular_movies(num_pages=5)

    if not movies:
        print("❌ No movies fetched")
        return

    insert_movies_to_db(movies)
    
    print("\n🎉 Done! Movies are ready in your database.")
    
if __name__ == "__main__":
    main()
            
            

    
    