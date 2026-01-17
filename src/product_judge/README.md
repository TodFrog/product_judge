# Product Judgment Service

AI 스마트 자판기 상품 판단 서비스 - Vision + Weight Fusion

## 개요

YOLO 기반 상품 인식과 다중 로드셀 무게 검증을 결합하여 정확한 상품 판단을 수행합니다.

### 핵심 기능

- **YOLO nano Top-5 추출**: 낮은 confidence에서도 상위 5개 후보군 추출
- **손 근접 필터링**: 손과 가까운 상품만 선별하여 노이즈 제거
- **무게 기반 개수 계산**: `count = round(delta_weight / unit_weight)`
- **완전/불완전 상태 판별**: 무게 검증 성공 여부로 status 반환
- **Node.js 연동 API**: FastAPI 기반 REST API

## 설치

```bash
# 기본 설치
pip install product-judge

# YOLO 포함 설치
pip install product-judge[yolo]

# 개발 환경
pip install product-judge[dev]
```

## 빠른 시작

### 1. 서버 실행

```bash
# CLI
product-judge

# 또는 uvicorn
uvicorn product_judge.main:app --host 0.0.0.0 --port 8080
```

### 2. API 테스트

```bash
# 헬스 체크
curl http://localhost:8080/api/health

# 테스트 판단 (로드셀 없이)
curl -X POST http://localhost:8080/api/test \
  -H "Content-Type: application/json" \
  -d '{
    "detections": [
      {"xyxy": [258.72, 47.65, 315.12, 113.97], "conf": 0.788, "cls": 0, "name": "hand"},
      {"xyxy": [257.67, 75.54, 284.33, 110.22], "conf": 0.492, "cls": 26, "name": "chickenmayo_rice"}
    ],
    "delta_weight": -365.0
  }'

# 시뮬레이션 (product_id + count 직접 지정)
curl -X POST http://localhost:8080/api/simulate \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 26,
    "count": 1,
    "confidence": 0.85
  }'
```

### 3. Python 직접 사용

```python
from product_judge import (
    ProductDatabase,
    ProductDecisionEngine,
    Top5Extractor,
    YOLODetection,
    EnsembleResult,
)

# 초기화
db = ProductDatabase()
engine = ProductDecisionEngine(db)
extractor = Top5Extractor()

# YOLO 결과 파싱
detections = [
    YOLODetection(
        xyxy=(258.72, 47.65, 315.12, 113.97),
        conf=0.788,
        cls=0,
        name="hand"
    ),
    YOLODetection(
        xyxy=(257.67, 75.54, 284.33, 110.22),
        conf=0.492,
        cls=26,
        name="chickenmayo_rice"
    ),
]

# Top-5 추출 (손 근접 필터링)
candidates = extractor.process_single_camera(detections)

# 상품 판단
result = engine.judge(candidates, delta_weight=-365.0)

# Node.js 응답 형식
print(result.to_node_response())
# {
#     "success": True,
#     "products": [{"productId": 26, "name": "chickenmayo_rice", "count": 1, ...}],
#     "totalPrice": 3500,
#     "status": "complete",
#     ...
# }
```

## API 엔드포인트

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/health` | 헬스 체크 |
| GET | `/api/products` | 등록된 상품 목록 |
| GET | `/api/products/{id}` | 상품 상세 정보 |
| POST | `/api/test` | 테스트 판단 (YOLO 결과 직접 입력) |
| POST | `/api/simulate` | 시뮬레이션 (product_id + count) |
| POST | `/api/judge` | 프로덕션 판단 (스냅샷 + 로드셀) |

## 응답 형식

```json
{
  "success": true,
  "products": [
    {
      "productId": 26,
      "name": "chickenmayo_rice",
      "count": 1,
      "unitPrice": 3500,
      "totalPrice": 3500,
      "confidence": 0.85
    }
  ],
  "totalPrice": 3500,
  "status": "complete",
  "confidence": 0.85,
  "weightInfo": {
    "delta": -365.0,
    "explained": 365.0,
    "residual": 0.0
  },
  "productCount": 1,
  "isRemoval": true,
  "timestamp": 1737046800.123
}
```

### status 값

| Status | 설명 |
|--------|------|
| `complete` | 무게가 완전히 설명됨 - 결제 진행 가능 |
| `partial` | 일부만 설명됨 - 확인 필요 |
| `uncertain` | 확신할 수 없음 - 수동 확인 필요 |
| `no_detection` | 감지된 상품 없음 |

## 프로젝트 구조

```
product_judge/
├── __init__.py           # 패키지 진입점
├── main.py               # FastAPI 서버
├── pyproject.toml        # 패키지 설정
├── engine/
│   ├── models.py         # 데이터 모델
│   └── decision_engine.py  # 판단 엔진
├── database/
│   └── product_db.py     # 상품 DB (50개 기본 포함)
├── weight/
│   └── count_calculator.py  # 개수 계산기
├── vision/
│   ├── yolo_wrapper.py   # YOLO 래퍼
│   ├── hand_filter.py    # 손 근접 필터
│   └── top5_extractor.py # Top-5 추출기
├── interfaces/
│   └── api_models.py     # Pydantic 모델
└── tests/
    └── ...
```

## 상품 데이터베이스

기본 50개 상품이 내장되어 있습니다. 커스텀 상품은 YAML로 추가:

```python
db = ProductDatabase.from_yaml("my_products.yaml")
```

## Node.js 연동

```javascript
// Node.js에서 호출
const response = await fetch('http://localhost:8080/api/test', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    detections: yoloResults,
    delta_weight: -365.0
  })
});

const result = await response.json();
if (result.success) {
  // 결제 진행
  processPayment(result.totalPrice, result.products);
}
```

## 라이선스

MIT License
