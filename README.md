# daechul-recommend

내 조건에 맞는 최적의 대출 조합을 찾아주는 시뮬레이터.

> 똑같이 4억을 빌려도 상환 방식과 상품 조합에 따라 월 납입액이 크게 달라집니다.
> 정책대출 최대 활용 + 은행대출 보정으로, 사용자 조건에 맞는 최적 조합을 계산합니다.

## 핵심 기능

- **정책대출 정확 계산** — 디딤돌, 보금자리론의 소득구간별 금리, 우대조건, 한도를 룰 엔진으로 정확히 산출
- **은행대출 추정** — 공시 평균금리 + 신용점수 기반 가산/감산 모델로 예상 금리 산출
- **조합 최적화** — 정책대출 + 은행대출 조합을 생성하고 총이자 기준으로 최적 순위 정렬
- **상환 방식 비교** — 원리금균등, 원금균등, 채증식 상환의 월 납입액·총이자 비교
- **규제 반영** — LTV, DSR 한도를 지역·대출 유형별로 자동 적용
- **금리 자동 갱신** — 외부 API(data.go.kr, 금감원, 한국은행, HF)에서 주기적으로 최신 데이터 수집
- **AI 설명** — Gemini API를 활용한 시뮬레이션 결과 자연어 해설

## 아키텍처

```
┌─────────────────────────────┐
│  Frontend (React + Vite)    │  ← Apps in Toss 미니앱 / Vercel
│  입력 폼 → 결과 비교 테이블   │
└────────────┬────────────────┘
             │ POST /api/simulate
┌────────────▼────────────────┐
│  Backend (FastAPI)          │  ← Cloud Run / Docker
│                             │
│  ┌─ 룰 엔진 ─────────────┐ │
│  │ 자격 판정 → 금리 산출   │ │
│  │ → 한도 계산 → 조합 생성 │ │
│  └────────────────────────┘ │
│                             │
│  ┌─ 스케줄러 ─────────────┐ │
│  │ TTL 기반 백그라운드 갱신 │ │
│  │ 인메모리 캐시 ← 외부 API│ │
│  └────────────────────────┘ │
└─────────────────────────────┘
```

## 입력 항목

| 구분 | 항목 |
|------|------|
| 기본 | 대출 목적, 희망 금액, 주택 가격, 주택 유형, 전용면적, 지역 |
| 소득 | 연소득, 배우자 소득, 순자산 |
| 가구 | 혼인 상태, 자녀 수, 생애최초 여부, 무주택 여부 |
| 신용 | 신용점수, 기존 월상환액 |
| 상환 | 상환 방식, 대출 기간 |

## 출력 결과

- 최적 조합 순위 (총이자 기준)
- 조합별 상품 구성 (정책대출 + 은행대출)
- 상품별 적용 금리, 우대 내역, 월 납입액, 총이자
- DSR/LTV 비율
- 정책대출 탈락 사유 (해당 시)
- 주의사항 및 면책 고지

## 기술 스택

### Backend

- Python 3.12+, FastAPI, Pydantic
- 인메모리 캐시 (dataclass 기반, DB 미사용)
- 외부 데이터 수집: httpx + asyncio 스케줄러
- AI 설명: Google Gemini API
- 패키지 관리: uv

### Frontend

- React 18, TypeScript, Vite
- Apps in Toss (앱인토스) Web Framework
- Vercel 배포

## 데이터 소스

| 소스 | 수집 대상 | TTL |
|------|-----------|-----|
| data.go.kr | 디딤돌·보금자리론 자격요건 | 12~24시간 |
| 금감원 FinLife | 시중은행 주담대 금리 | 24시간 |
| 한국은행 ECOS | 은행 평균 대출금리 | 48시간 |
| HF 보도자료 | 정책 변경 감지 | 6시간 |

수집된 데이터는 인메모리에 캐싱되고, 서버 재시작 시 JSON 기본값으로 폴백합니다.

## 로컬 실행

### Backend

```bash
cd backend
cp .env.example .env
# .env에 API 키 입력

uv sync
uv run uvicorn app.main:app --reload
# http://localhost:8000/health
# http://localhost:8000/docs (Swagger UI)
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# http://localhost:5173
```

## 환경변수

| 변수 | 설명 |
|------|------|
| `GEMINI_API_KEY` | Google Gemini API 키 |
| `ADMIN_API_KEY` | 관리자 API 인증 키 |
| `CORS_ORIGINS` | 허용 오리진 (쉼표 구분) |
| `INTOSS_APP_NAME` | 앱인토스 앱 이름 (CORS 자동 추가) |
| `DATA_GO_KR_SERVICE_KEY` | 공공데이터포털 서비스키 (Decoding 값) |
| `FINLIFE_AUTH_KEY` | 금감원 금융상품한눈에 인증키 |
| `ECOS_API_KEY` | 한국은행 ECOS API 키 |

## API 엔드포인트

| Method | Path | 설명 |
|--------|------|------|
| GET | `/health` | 헬스체크 |
| GET | `/api/products` | 대출 상품 목록 |
| POST | `/api/simulate` | 시뮬레이션 실행 |
| POST | `/api/explain` | AI 결과 설명 |
| POST | `/api/admin/refresh-all` | 전체 데이터 갱신 (관리자) |
| GET | `/api/admin/status` | 시스템 상태 조회 (관리자) |
| GET | `/api/admin/product/{id}` | 상품 데이터 조회 (관리자) |
| PUT | `/api/admin/product/{id}` | 상품 데이터 수정 (관리자) |

관리자 엔드포인트는 `X-Admin-Key` 헤더 인증이 필요합니다.

## 프로젝트 구조

```
backend/
├── app/
│   ├── api/routes.py          # API 라우터
│   ├── cache.py               # 인메모리 캐시 저장소
│   ├── config.py              # 환경변수 설정
│   ├── main.py                # FastAPI 앱 + 스케줄러
│   ├── calculator/
│   │   ├── optimizer.py       # 조합 최적화 엔진
│   │   ├── repayment.py       # 상환 계산 (원리금/원금/채증식)
│   │   └── bank_estimator.py  # 은행 금리 추정
│   ├── fetchers/
│   │   ├── scheduler.py       # TTL 기반 갱신 스케줄러
│   │   ├── data_go_kr.py      # 공공데이터포털 수집
│   │   ├── ecos.py            # 한국은행 ECOS 수집
│   │   ├── finlife.py         # 금감원 FinLife 수집
│   │   └── hf_scraper.py      # HF 보도자료 크롤링
│   ├── llm/
│   │   ├── client.py          # Gemini 클라이언트
│   │   └── explainer.py       # 결과 설명 생성
│   ├── rules/
│   │   ├── engine.py          # 정책대출 룰 엔진
│   │   ├── eligibility.py     # 자격요건 판정
│   │   ├── rate_calculator.py # 금리 산출
│   │   ├── regulation.py      # LTV/DSR 규제
│   │   ├── product_loader.py  # 상품 데이터 로딩
│   │   └── data/              # JSON 룰 데이터
│   └── schemas/               # Pydantic 스키마
├── tests/                     # pytest 테스트
├── Dockerfile
└── pyproject.toml

frontend/
├── src/
│   ├── App.tsx
│   ├── api.ts                 # 백엔드 API 호출
│   ├── calculator.ts          # 프론트 계산 유틸
│   ├── types.ts               # 타입 정의
│   ├── components/            # UI 컴포넌트
│   └── pages/                 # 페이지 (입력/결과)
├── package.json
└── vite.config.ts
```

## 설계 원칙

- **추천 로직은 deterministic 룰 엔진** — LLM은 설명 생성에만 사용하고, 금리·한도 계산은 룰 기반으로 수행
- **정보 제공형 시뮬레이터** — 금융상품 판매·중개가 아닌 참고용 계산 도구
- **인메모리 캐싱** — PostgreSQL 없이 운영 가능. 서버 재시작 시 JSON 폴백 + 외부 API 재수집
- **2단계 데이터 로딩** — 인메모리 캐시(최신) → JSON 파일(기본값) 폴백 구조

## 면책 고지

> 본 서비스는 금융상품 판매 또는 중개를 하지 않습니다.
> 제공되는 금리 및 한도는 공개 자료 기반의 예상치이며, 실제 적용 조건은 금융기관 심사 결과에 따라 달라질 수 있습니다.
> 대출 실행 여부는 이용자 본인의 판단과 책임 하에 결정해 주세요.
