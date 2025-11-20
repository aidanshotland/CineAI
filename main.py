from fastapi import FastAPI
from dotenv import load_dotenv

load_dotenv()

app= FastAPI(title='Movie Recommender API')

@app.get('/')
async def root():
    return {"message": "Movie Recommender API is running"}

if __name__=='__main__':
    import uvicorn
    uvicorn.run(app,host='0.0.0.0',port=8000)