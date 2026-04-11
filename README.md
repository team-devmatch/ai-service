# ai-service

FastAPI 기반 AI 여행코스 추천 서비스

## 기술 스택
- Python
- FastAPI
- LangChain / LlamaIndex
- OpenAI API / Hugging Face
- Vector DB (Milvus)
- Pandas & NumPy
- ONNX / TensorRT (모델 경량화)

## 주요 기능
- 지역 / 날짜 / 테마 기반 여행코스 자동 추천
- LLM 기반 코스 요약 생성
- 감성 분석 (Sentiment Analysis)
- AI 모델 서빙 (Kubernetes 환경)

## API
- POST /ai/course → 여행코스 추천 요청

## 브랜치 규칙
- feature/기능명 → 기능 개발
- fix/버그명 → 버그 수정
- main → 최종 배포 브랜치
