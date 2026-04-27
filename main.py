from fastapi import FastAPI # API 서버 프레임워크
from fastapi.middleware.cors import CORSMiddleware #FastAPI에서 CORS를 처리하는 미들웨어
from pydantic import BaseModel # 요청/응답 데이터 형태 정의
from dotenv import load_dotenv # .env 파일에서 API키, DB 정보 읽기
from langchain_openai import ChatOpenAI # LangChain을 통해 OpenAI GPT 사용
from langchain_core.prompts import ChatPromptTemplate # AI에게 보낼 프롬프트 템플릿 구성 # 변경됨
from datetime import date #현재 날짜 기준
import requests as req #현재 날씨 기준
import psycopg2 # python에서 PostgreSQL 연결하는 라이브러리
import os # 환경 변수

load_dotenv() # .env 파일에서 API 키 불러오기
app = FastAPI()

# CORS 설정 추가(프론트 연결)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True, #JWT 토큰이나 쿠키를 함께 보낼 때 필요
    allow_methods=["*"],
    allow_headers=["*"], #JSON 데이터 전송할 때 필요한 헤더
)

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
아래 축제 데이터를 바탕으로 사용자 질문에 친절하고 자세하게 답변해주세요.
데이터에 없는 축제는 절대 언급하지 마세요.     
축제 데이터가 비어있을 때만 "관련 축제 정보가 없습니다."라고 답변하세요.

오늘 날짜: {today} 
현재 날씨: {weather}

날짜 규칙:
- 오늘 날짜 이후에 시작하는 축제만 추천하세요.
- 이미 끝난 축제는 절대 추천하지 마세요.
- 날짜가 가까운 축제를 우선 추천하세요.

지역 규칙:
- 사용자가 특정 지역을 언급하면 반드시 그 지역 축제만 추천하세요.
- 다른 지역 축제는 절대 포함하지 마세요.

답변 형식:
- 자연스러운 한국어 문장으로 작성
- JSON 형식 절대 사용 금지     
- 마크다운 기호(**,- 등) 절대 사용 금지
- 축제마다 이름, 위치, 기간을 자연스럽게 포함
- 각 축제는 반드시 아래 태그 형식으로만 작성:
[FESTIVAL]이름,
위치,
시작일~종료일.   
- 태그 외 다른 형식 절대 사용 금지
- 줄바꿈으로 구분하면서 번호도 추가
- 2~3개 추천 후 마무리 멘트 추가          

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

def get_weather(): # 날씨
    try:
        api_key = os.getenv("WEATHER_API_KEY")
        url = f"http://api.openweathermap.org/data/2.5/weather?q=Seoul&appid={api_key}&lang=kr&units=metric"
        response = req.get(url, timeout=5)
        data = response.json()
        temp = round(data["main"]["temp"])
        desc = data["weather"][0]["description"]
        return f"{desc}, 기온 {temp}°C"
    except:
        return "날씨 정보를 가져올 수 없습니다."

@app.post("/ai/chat", response_model=ChatResponse) # 챗봇 엔드포인트
def chat(request: ChatRequest):

    # DB에서 축제 데이터 조회
    conn = get_db_connection()
    cursor = conn.cursor()

    # 의미없는 단어 제거
    stopwords = ["추천해줘", "추천해", "알려줘", "알려", "찾아줘",
    "뭐야", "있어", "현재", "기준으로", "기준",
    "축제", "행사", "이번", "요즘", "지금",
    "좋은", "괜찮은", "어떤", "뭐가", "어디",
    "해줘", "줘", "으로", "에서", "에", "의",
    "좀", "한번", "추천", "부탁해"]
    keywords = [kw for kw in request.message.split() if kw not in stopwords]

    # 지역명 매핑
    region_map = {
        "강원도": "강원특별자치도",
        "제주도": "제주특별자치도",
        "세종시": "세종특별자치도",
        "전라도": "전라",
        "경상도": "경상",
        "충청도": "충청",
    }
    keywords = [region_map.get(kw, kw) for kw in keywords]

    # 키워드 없으면 전체 조회
    if not keywords:
        cursor.execute("""
            SELECT name, address, start_date, end_date, theme
            FROM festival
            WHERE end_date >= %s
            ORDER BY start_date ASC
            LIMIT 20
        """, (date.today().strftime("%Y%m%d"),))
    else:
        conditions = " OR ".join([
            f"(name ILIKE %s OR address ILIKE %s OR theme ILIKE %s)"
            for _ in keywords
        ])
        params = []
        for kw in keywords:
            params.extend([f"%{kw}%", f"%{kw}%", f"%{kw}%"])
        params.append(date.today().strftime("%Y%m%d"))

        cursor.execute(f"""
            SELECT name, address, start_date, end_date, theme
            FROM festival
            WHERE ({conditions})
            AND end_date >= %s
            ORDER BY start_date ASC
            LIMIT 20
        """, params)

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    # 축제 데이터 텍스트로 변환
    festival_data = "\n".join([
        f"- {row[0]} | {row[1]} | {row[2]}~{row[3]} | 테마: {row[4]}"
        for row in rows
    ]) if rows else "관련 축제 데이터가 없습니다."

    # LangChain으로 답변 생성
    chain = prompt | llm
    response = chain.invoke({
        "festival_data": festival_data,
        "message": request.message,
        "today": date.today().strftime("%Y년 %m월 %d일"),
        "weather": get_weather()
    })

    return {"answer": response.content}