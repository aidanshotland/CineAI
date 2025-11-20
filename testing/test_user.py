import psycopg2
from dotenv import load_dotenv
import os
import numpy as np

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')

def create_test_user(email, username):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("SELECT user_id, email, username FROM users WHERE email = %s", (email,))
    user = cur.fetchone()
    
    if user:
        print(f"✓ Found existing user: {user[2]} ({user[1]})")
        cur.close()
        conn.close()
        return user[0]  # Return user_id

    cur.execute("""
        INSERT INTO users (email,username)
        VALUES(%s,%s)
        RETURNING user_id ,email,username   
        """, (email,username))
    
    user = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    return user[0]

def like_movie(user_id,movie_title):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("SELECT movie_id, title FROM movies WHERE title = %s", (movie_title,))
    movie = cur.fetchone()

    if not movie:
        print(f"✗ Movie '{movie_title}' not found")
        cur.close()
        conn.close()
        return False
    
    movie_id, title = movie

    try:
        cur.execute("""
            INSERT INTO user_likes (user_id, movie_id) 
            VALUES (%s, %s)
            """, (user_id, movie_id))
        conn.commit()
        print(f"♥ Liked: {title}")

    except psycopg2.IntegrityError:
        print(f"  Already liked: {title}")
        conn.rollback()
    
    cur.close()
    conn.close()
    return True

def get_user_likes(user_id):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""
        SELECT m.title, m.vote_average
        FROM user_likes ul
        JOIN movies m ON ul.movie_id = m.movie_id
        WHERE ul.user_id = %s
        ORDER BY ul.liked_at DESC
    """, (user_id,))
    
    likes = cur.fetchall()
    cur.close()
    conn.close()
    
    return likes

def get_recommendations(user_id, limit=10, recency_weight=True):
    conn = psycopg2.connect(DATABASE_URL)
    cur=conn.cursor()

    cur.execute("""
        SELECT m.embedding, ul.liked_at
        FROM user_likes ul
        JOIN movies m ON ul.movie_id = m.movie_id
        WHERE ul.user_id = %s
        ORDER BY ul.liked_at DESC
    """, (user_id,))
    
    liked_data = cur.fetchall()
    
    if not liked_data:
        print("User hasn't liked any movies yet!")
        cur.close()
        conn.close()
        return []
    
    embeddings_list = []
    for item in liked_data:
        embedding = item[0]
        # If it's a string, parse it
        if isinstance(embedding, str):
            # Remove brackets and split by comma
            embedding = embedding.strip('[]').split(',')
            embedding = [float(x) for x in embedding]
        embeddings_list.append(embedding)
    
    embeddings_array = np.array(embeddings_list, dtype=np.float64)

    if recency_weight:
        num_likes = len(liked_data)
        weights = np.array([.9 ** i for i in range(num_likes)], dtype=np.float64)
        weights = weights / weights.sum()

        user_preference_vector = np.average(embeddings_array, axis=0,weights=weights).tolist()
    else:
        user_preference_vector = np.mean(embeddings_array, axis=0).tolist()
    
    cur.execute("""
        SELECT m.title, 
               m.vote_average,
               1 - (m.embedding <=> %s::vector) as similarity
        FROM movies m
        WHERE m.movie_id NOT IN (
            SELECT movie_id FROM user_likes WHERE user_id = %s
        )
        ORDER BY m.embedding <=> %s::vector
        LIMIT %s
    """, (user_preference_vector, user_id, user_preference_vector, limit))
    
    recommendations = cur.fetchall()
    cur.close()
    conn.close()
    
    return recommendations


def main():
    user_id = create_test_user("scifi_fan@example.com", "SciFiFan")
    like_movie(user_id, "Interstellar")
    like_movie(user_id, "The Matrix")  # If you have it
    like_movie(user_id, "Inception")   # If you have it

    recommendations = get_recommendations(user_id, limit=10)

    print("\n--- User's liked movies ---")
    likes = get_user_likes(user_id)
    for title, rating in likes:
        print(f"  ♥ {title} (⭐ {rating})")

    
    print("\n--- Personalized Recommendations ---")
    recommendations = get_recommendations(user_id, limit=15)

    if recommendations:
        print(f"\nTop {len(recommendations)} recommendations:")
        for i, (title, rating, similarity) in enumerate(recommendations, 1):
            print(f"  {i}. {title} (⭐ {rating}) - {similarity:.3f} similarity")
    else:
        print("No recommendations available")

if __name__ == "__main__":
    main()



    



    




