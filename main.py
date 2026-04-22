from fastapi import FastAPI # API 서버 프레임워크
from pydantic import BaseModel # 요청/응답 데이터 형태 정의
from dotenv import load_dotenv # .env 파일에서 API키, DB 정보 읽기
from langchain_openai import ChatOpenAI # LangChain을 통해 OpenAI GPT 사용
from langchain_core.prompts import ChatPromptTemplate # AI에게 보낼 프롬프트 템플릿 구성 # 변경됨
import psycopg2 # python에서 PostgreSQL 연결하는 라이브러리
import os # 환경 변수

load_dotenv() # .env 파일에서 API 키 불러오기
app = FastAPI()

# DB 연결
def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", 'festivaldb'),
        user=os.getenv("DB_USER", "admin"),
        password=os.getenv("DB_PASSWORD", "password")
    )

# LLM 설정
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.7, # AI 답변의 창의성 조절(0~1)
    api_key=os.getenv("OPENAI_API_KEY")
)

# 프롬프트 템플릿
prompt = ChatPromptTemplate.from_messages([
    ("system", """
당신은 한국 축제 전문 AI 안내원이에요.
아래 축제 데이터를 바탕으로 사용자 질문에 친절하게 답변해주세요.
축제 데이터에 없는 내용은 모른다고 말해주세요.

축제 데이터:
{festival_data}
"""),
    ("human", "{message}") #사용자가 보낸 실제 질문
])

class ChatRequest(BaseModel): # 챗봇 요청
    message: str

class ChatResponse(BaseModel): # 챗봇 응답
    answer: str

@app.get("/") # 서버가 살아있는지 확인용
def health_check():
    return {"status": "ok","service": "FestAI AI Service"}

@app.post("/ai/chat", response_model=ChatResponse) # 챗봇 엔드포인트
def chat(request: ChatRequest):

    # DB에서 축제 데이터 조회
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT name, address, start_date, end_date, theme 
        FROM festival
        LIMIT 20
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    # 축제 데이터 텍스트로 변환
    festival_data = "\n".join([
        f"- {row[0]} | {row[1]} | {row[2]}~{row[3]} | 테마: {row[4]}"
        for row in rows
    ])

    # mock 응답 (OpenAI 없이 DB 데이터 그대로 반환)
    answer = f"'{request.message}'에 관련된 축제를 찾았어요!\n\n{festival_data}"

    return {"answer": answer}

    # LangChain으로 답변 생성
    chain = prompt | llm
    response = chain.invoke({
        "festival_data": festival_data,
        "message": request.message
    })

    return {"answer": response.content}