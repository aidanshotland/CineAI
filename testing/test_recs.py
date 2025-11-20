import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# Pick a movie (let's use Frankenstein)
cur.execute("SELECT movie_id, title, embedding FROM movies WHERE title = 'Frankenstein'")
movie = cur.fetchone()

if movie:
    movie_id, title, embedding = movie
    print(f"Finding movies similar to: {title}\n")
    
    # Find similar movies using cosine similarity
    cur.execute("""
        SELECT title, 
               1 - (embedding <=> %s::vector) as similarity
        FROM movies
        WHERE movie_id != %s
        ORDER BY embedding <=> %s::vector
        LIMIT 10
    """, (embedding, movie_id, embedding))
    
    print("Top 10 similar movies:")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]:.3f} similarity")

cur.close()
conn.close()