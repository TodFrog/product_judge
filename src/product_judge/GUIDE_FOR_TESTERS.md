# Product Judgment Service - 테스터 가이드

## 개요

이 문서는 `product_judge` 서비스를 테스트하려는 작업자를 위한 가이드입니다.

### 서비스 기능
- YOLO 상품 인식 결과 + 로드셀 무게 변화를 결합하여 **최종 상품과 개수를 판단**
- Node.js Orchestrator에 JSON 응답 반환
- 테스트용 API 제공 (실제 하드웨어 없이 테스트 가능)

---

## 1. 환경 설정

### 1.1 Python 환경 (3.10+)

```bash
cd CRK/src/product_judge

# 가상환경 생성 및 활성화
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 패키지 설치
pip install -e ".[dev]"
```

### 1.2 의존성 확인

```bash
pip list | grep -E "fastapi|uvicorn|pydantic|pytest"
```

---

## 2. 서버 실행

### 2.1 개발 서버 (자동 리로드)

```bash
uvicorn product_judge.main:app --host 0.0.0.0 --port 8080 --reload
```

### 2.2 프로덕션 서버

```bash
# CORS 설정 (특정 origin만 허용)
set CORS_ORIGINS=http://localhost:3000,http://your-frontend.com
uvicorn product_judge.main:app --host 0.0.0.0 --port 8080
```

### 2.3 서버 확인

브라우저에서 접속:
- Swagger UI: http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc
- Health Check: http://localhost:8080/api/health

---

## 3. API 테스트 방법

### 3.1 Health Check

```bash
curl http://localhost:8080/api/health
```

**응답 예시:**
```json
{
  "status": "ok",
  "version": "1.0.0",
  "product_count": 50
}
```

### 3.2 테스트 판단 (/api/test) - 핵심 API

**실제 로직을 전부 타면서 응답을 반환합니다.**

```bash
curl -X POST http://localhost:8080/api/test \
  -H "Content-Type: application/json" \
  -d '{
    "detections": [
      {"xyxy": [258.72, 47.65, 315.12, 113.97], "conf": 0.788, "cls": 0, "name": "hand"},
      {"xyxy": [257.67, 75.54, 284.33, 110.22], "conf": 0.492, "cls": 26, "name": "chickenmayo_rice"}
    ],
    "delta_weight": -365.0,
    "use_hand_filter": true
  }'
```

**파라미터 설명:**
- `detections`: YOLO 감지 결과 배열
  - `xyxy`: Bounding box [x1, y1, x2, y2]
  - `conf`: 신뢰도 (0.0 ~ 1.0)
  - `cls`: 클래스 ID (0=hand, 1+=products)
  - `name`: 클래스 이름
- `delta_weight`: 무게 변화량 (음수 = 상품 제거)
- `use_hand_filter`: 손 근접 필터링 사용 여부 (기본값 true)

**응답 예시:**
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

### 3.3 시뮬레이션 (/api/simulate)

상품 ID와 개수를 직접 지정하여 응답 형식 확인:

```bash
curl -X POST http://localhost:8080/api/simulate \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 26,
    "count": 1,
    "confidence": 0.85
  }'
```

### 3.4 상품 목록 조회

```bash
# 전체 상품
curl http://localhost:8080/api/products

# 특정 상품
curl http://localhost:8080/api/products/26
```

---

## 4. 테스트 시나리오

### 4.1 단일 상품 정확 매칭

```bash
# chickenmayo_rice: weight=365g, price=3500원
curl -X POST http://localhost:8080/api/test \
  -H "Content-Type: application/json" \
  -d '{
    "detections": [
      {"xyxy": [100, 100, 200, 200], "conf": 0.9, "cls": 26, "name": "chickenmayo_rice"}
    ],
    "delta_weight": -365.0
  }'
```
**예상 결과:** `status: "complete"`, `count: 1`

### 4.2 다중 개수 (같은 상품 2개)

```bash
# vita500: weight=130g, 2개 = 260g
curl -X POST http://localhost:8080/api/test \
  -H "Content-Type: application/json" \
  -d '{
    "detections": [
      {"xyxy": [100, 100, 200, 200], "conf": 0.85, "cls": 9, "name": "vita500"}
    ],
    "delta_weight": -260.0
  }'
```
**예상 결과:** `status: "complete"`, `count: 2`, `totalPrice: 2400`

### 4.3 허용 오차 내 매칭

```bash
# chickenmayo_rice: 365g, food 카테고리 8% 허용 오차
# 380g은 오차 15g < 29.2g (8% of 365) 이므로 매칭됨
curl -X POST http://localhost:8080/api/test \
  -H "Content-Type: application/json" \
  -d '{
    "detections": [
      {"xyxy": [100, 100, 200, 200], "conf": 0.9, "cls": 26, "name": "chickenmayo_rice"}
    ],
    "delta_weight": -380.0
  }'
```
**예상 결과:** `status: "complete"`

### 4.4 무게 변화 없음 (5g 미만)

```bash
curl -X POST http://localhost:8080/api/test \
  -H "Content-Type: application/json" \
  -d '{
    "detections": [
      {"xyxy": [100, 100, 200, 200], "conf": 0.9, "cls": 26, "name": "chickenmayo_rice"}
    ],
    "delta_weight": -3.0
  }'
```
**예상 결과:** `status: "no_detection"`

### 4.5 무게 불일치 (부분 결과)

```bash
# chickenmayo_rice: 365g이지만 무게는 500g
curl -X POST http://localhost:8080/api/test \
  -H "Content-Type: application/json" \
  -d '{
    "detections": [
      {"xyxy": [100, 100, 200, 200], "conf": 0.9, "cls": 26, "name": "chickenmayo_rice"}
    ],
    "delta_weight": -500.0
  }'
```
**예상 결과:** `status: "partial"` 또는 `"uncertain"`

---

## 5. 단위 테스트 실행

```bash
cd CRK/src/product_judge

# 전체 테스트
pytest tests/test_engine.py -v

# 특정 테스트 클래스
pytest tests/test_engine.py::TestProductDecisionEngine -v

# 특정 테스트
pytest tests/test_engine.py::TestProductDecisionEngine::test_single_product_exact_match -v

# 커버리지 포함
pytest tests/test_engine.py -v --cov=product_judge --cov-report=term-missing
```

### 5.1 테스트 케이스 목록

| 클래스 | 테스트 | 설명 |
|--------|--------|------|
| TestProductDecisionEngine | test_single_product_exact_match | 단일 상품 정확 매칭 |
| | test_single_product_with_tolerance | 허용 오차 내 매칭 |
| | test_multiple_count | 다중 개수 감지 |
| | test_no_detection | 감지 없음 |
| | test_weight_too_small | 무게 변화 너무 작음 |
| | test_weight_mismatch_partial | 무게 불일치 |
| | test_beverage_product | 음료 상품 |
| TestVisionModules | test_hand_filter_no_hands | 손 없으면 모든 상품 반환 |
| | test_hand_filter_nearest_product | 손 근처 상품만 필터링 |
| | test_top5_extractor_basic | Top-5 추출 기본 |
| | test_ensemble_common_class_bonus | 앙상블 공통 클래스 보너스 |
| TestCombinationMatching | test_combination_two_products | 2개 상품 조합 매칭 |
| | test_combination_with_multiple_counts | 다중 개수 조합 매칭 |
| TestCategoryTolerance | test_beverage_tolerance | 음료 5% |
| | test_snack_tolerance | 스낵 10% |
| | test_food_tolerance | 식품 8% |
| | test_dairy_tolerance | 유제품 7% |
| TestEdgeCases | test_zero_weight_product | 무게 0인 상품 |
| | test_exact_boundary_tolerance | 경계값 테스트 |
| | test_nonexistent_product | 없는 상품 조회 |

---

## 6. 상품 데이터

### 6.1 기본 상품 (50개)

| ID | 이름 | 카테고리 | 무게(g) | 가격(원) |
|----|------|----------|---------|---------|
| 0 | hand | - | 0 | 0 |
| 1-10 | 음료 (생수, 이온음료 등) | beverage | 130~640 | 1000~2500 |
| 11-20 | 스낵 (빼빼로, 감자칩 등) | snack | 53~90 | 1400~2500 |
| 21-25 | 초콜릿/캔디 | candy | 37~52 | 1200~2500 |
| 26-35 | 편의점 식품 (삼각김밥 등) | food | 65~380 | 1200~3800 |
| 36-42 | 유제품 | dairy | 85~250 | 1000~3500 |
| 43-47 | 건강식품 | health | 30~50 | 1500~2500 |
| 48-50 | 기타 | etc | 15~50 | 800~1000 |

### 6.2 카테고리별 허용 오차

| 카테고리 | 허용 오차 |
|----------|----------|
| beverage | 5% |
| snack | 10% |
| candy | 10% |
| food | 8% |
| dairy | 7% |
| health | 10% |
| frozen | 15% |
| etc | 15% |

---

## 7. 트러블슈팅

### Q: 서버가 시작되지 않아요
```bash
# 포트 충돌 확인
netstat -ano | findstr :8080

# 다른 포트 사용
uvicorn product_judge.main:app --port 8081
```

### Q: 테스트가 실패해요
```bash
# 패키지 재설치
pip install -e ".[dev]" --force-reinstall

# 캐시 삭제
pytest --cache-clear
```

### Q: CORS 에러가 발생해요
```bash
# 환경변수로 origin 설정
set CORS_ORIGINS=http://localhost:3000
```

---

## 8. 연락처

문의사항이 있으면 이슈를 등록해주세요.
