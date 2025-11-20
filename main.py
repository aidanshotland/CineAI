from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, EmailStr

load_dotenv()

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def hash_password(password: str ) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password:str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data:dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({'exp': expire})
    encoded_jwt=jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


app= FastAPI(title='Movie Recommender API')

def get_db_connection():
    conn = psycopg2.connect(

        host = os.getenv('DB_HOST'),
        database = os.getenv('DB_NAME'),
        user= os.getenv('DB_USER'),
        password = os.getenv('DB_PASSWORD'),
        port = os.getenv('DB_PORT',5432),
        cursor_factory=RealDictCursor
    )
    return conn

class UserSignup(BaseModel):
    email: EmailStr
    username: str
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

@app.post('/auth/signup')
async def signUp(user: UserSignup):
    try:
        print(f"Password length: {len(user.password)}")  # Debug line
        print(f"Password: {user.password}")  # Debug line
        conn =get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT email FROM users WHERE email = %s",(user.email,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail='Email already in use')
        
        hashed_password = hash_password(user.password)
        cur.execute(
            """
            INSERT INTO users (email,username,password_hash)
            VALUES (%s, %s, %s)
            RETURNING user_id, email, username, created_at  
            """, (user.email, user.username, hashed_password))
        
        new_user = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        return {
            'message': 'user created',
            'user': new_user
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/auth/login')
async def login(user: UserLogin):
    try: 
        conn= get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT user_id,email,username,password_hash FROM users WHERE email = %s", (user.email,))
        db_user = cur.fetchone()

        cur.close()
        conn.close()

        if not db_user or not verify_password(user.password, db_user['password_hash']):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        access_token = create_access_token(data={'user_id': str(db_user['user_id'])})

        return {
            'access_token': access_token,
            'token_type':'bearer',
            'user':{
                "user_id": db_user['user_id'],
                "email": db_user['email'],
                "username": db_user['username']
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    


@app.get('/')
async def root():
    return {"message": "Movie Recommender API is running"}

@app.get('/movies')
async def get_movies(limit: int =20, offset: int =0):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute('SELECT * FROM movies LIMIT %s OFFSET %s',(limit,offset))

        movies = cur.fetchall()
        
        cur.close()
        conn.close()

        return {
            'movies':movies,
            'limit':limit,
            'offset':offset
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/movies/search')
async def search(query: str, limit:int=20, offset:int=0):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT * FROM movies
            WHERE title ILIKE %s
            ORDER BY vote_average DESC
            LIMIT %s OFFSET %s
             """,
             (f'%{query}%',limit,offset)
        )

        movies = cur.fetchall()

        cur.close()
        conn.close()

        return {
            'query':query,
            'movies':movies,
            'count':len(movies),
            'limit':limit,
            'offset':offset
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail= str(e))


@app.get('/movies/{movie_id}')
async def get_movie(movie_id:str):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute('SELECT * FROM movies WHERE movie_id=%s',(movie_id,))

        movie = cur.fetchone()

        if not movie:
            raise HTTPException(status_code=404, detail='Movie Not Found')
        
        return movie
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500,detail=str(e))



if __name__=='__main__':
    import uvicorn
    uvicorn.run(app,host='0.0.0.0',port=8000)