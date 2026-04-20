from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv() # .env 파일에서 API 키 불러오기
app = FastAPI()

class ChatRequest(BaseModel): # 챗봇 요청
    message: str

class ChatResponse(BaseModel): # 챗봇 응답
    answer: str

@app.get("/") # 서버가 살아있는지 확인용
def health_check():
    return {"status": "ok","service": "FestAI AI Service"}

@app.post("/ai/chat") # 임시 응답만 반환, 추후 LangChain+OpenAI 연동
def chat(request: ChatRequest):
    return{"answer": f"'{request.message}' 에 대한 축제를 찾고있어요!"}