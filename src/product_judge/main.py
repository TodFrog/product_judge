"""
Product Judgment Service - FastAPI Server.

상품 판단 서비스 메인 진입점.

기능:
- POST /api/judge: 실제 상품 판단 (스냅샷 + 로드셀)
- POST /api/test: 테스트용 판단 (YOLO 결과 직접 입력)
- POST /api/simulate: 시뮬레이션 (product_id + count 직접 지정)
- GET /api/health: 헬스 체크
- GET /api/products: 등록된 상품 목록

사용:
    uvicorn product_judge.main:app --host 0.0.0.0 --port 8080

Node.js 연동:
    POST http://localhost:8080/api/test
    {
        "detections": [...],
        "delta_weight": -365.0
    }
"""

import logging
import os
import time
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .interfaces.api_models import (
    JudgeRequest,
    JudgeResponse,
    TestRequest,
    SimulateRequest,
    ProductOutput,
    WeightInfo,
    HealthResponse,
    ErrorResponse,
    JudgmentStatusEnum,
)
from .engine.models import EnsembleResult, JudgmentStatus
from .engine.decision_engine import ProductDecisionEngine
from .database.product_db import ProductDatabase
from .vision.yolo_wrapper import YOLOWrapper, YOLODetection
from .vision.top5_extractor import Top5Extractor

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 전역 객체
product_db: Optional[ProductDatabase] = None
decision_engine: Optional[ProductDecisionEngine] = None
top5_extractor: Optional[Top5Extractor] = None

VERSION = "1.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 시 초기화."""
    global product_db, decision_engine, top5_extractor

    # 시작
    logger.info("Initializing Product Judgment Service...")
    product_db = ProductDatabase()
    decision_engine = ProductDecisionEngine(product_db)
    top5_extractor = Top5Extractor()
    logger.info(f"Service ready. {product_db.product_count} products loaded.")

    yield

    # 종료
    logger.info("Shutting down Product Judgment Service...")


# FastAPI 앱 생성
app = FastAPI(
    title="Product Judgment Service",
    description="AI 스마트 자판기 상품 판단 서비스 - Vision + Weight Fusion",
    version=VERSION,
    lifespan=lifespan,
)

# CORS 설정 (Node.js 연동용)
# 환경변수: CORS_ORIGINS (쉼표 구분, 예: "http://localhost:3000,http://localhost:8000")
# 기본값: 개발 환경에서는 모든 origin 허용, 프로덕션에서는 환경변수로 제한
_cors_origins_env = os.getenv("CORS_ORIGINS", "")
_cors_origins = (
    [origin.strip() for origin in _cors_origins_env.split(",") if origin.strip()]
    if _cors_origins_env
    else ["*"]  # 개발 환경 기본값
)
_allow_credentials = os.getenv("CORS_CREDENTIALS", "true").lower() == "true"

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_allow_credentials if _cors_origins != ["*"] else False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== API Endpoints ==========

@app.get("/api/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """헬스 체크."""
    return HealthResponse(
        status="ok",
        version=VERSION,
        product_count=product_db.product_count if product_db else 0,
    )


@app.get("/api/products", tags=["Products"])
async def get_products():
    """등록된 상품 목록 조회."""
    if not product_db:
        raise HTTPException(status_code=500, detail="Database not initialized")

    products = product_db.get_all_products()
    return {
        "count": len(products),
        "products": [p.to_dict() for p in products],
    }


@app.get("/api/products/{product_id}", tags=["Products"])
async def get_product(product_id: int):
    """특정 상품 정보 조회."""
    if not product_db:
        raise HTTPException(status_code=500, detail="Database not initialized")

    product = product_db.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")

    return product.to_dict()


@app.post("/api/test", response_model=JudgeResponse, tags=["Test"])
async def test_judge(request: TestRequest):
    """
    테스트용 상품 판단 (로드셀 연결 없이).

    YOLO 감지 결과와 무게 변화량을 직접 입력하여 테스트.
    Node.js 전체 결제 프로세스 점검용.

    Example:
        POST /api/test
        {
            "detections": [
                {"xyxy": [258.72, 47.65, 315.12, 113.97], "conf": 0.788, "cls": 0, "name": "hand"},
                {"xyxy": [257.67, 75.54, 284.33, 110.22], "conf": 0.492, "cls": 26, "name": "chickenmayo_rice"}
            ],
            "delta_weight": -365.0
        }
    """
    if not decision_engine or not top5_extractor:
        raise HTTPException(status_code=500, detail="Service not initialized")

    try:
        # 1. YOLO Detection 파싱
        detections = [
            YOLODetection(
                xyxy=tuple(d.xyxy),
                conf=d.conf,
                cls=d.cls,
                name=d.name,
            )
            for d in request.detections
        ]

        logger.info(f"Test request: {len(detections)} detections, delta={request.delta_weight}g")

        # 2. Top-5 추출 (손 근접 필터 선택적)
        if request.use_hand_filter:
            candidates = top5_extractor.process_single_camera(detections)
        else:
            # 필터 없이 모든 상품
            candidates = [
                EnsembleResult(
                    class_id=d.cls,
                    class_name=d.name,
                    top_confidence=d.conf,
                    side_confidence=0.0,
                    combined_confidence=d.conf,
                    vote_count=1,
                )
                for d in detections if d.cls != 0
            ]
            candidates.sort(key=lambda c: c.combined_confidence, reverse=True)
            candidates = candidates[:5]

        # 3. 상품 판단
        result = decision_engine.judge(candidates, request.delta_weight)

        # 4. 응답 변환
        return _convert_to_response(result)

    except Exception as e:
        logger.error(f"Test judge error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/simulate", response_model=JudgeResponse, tags=["Test"])
async def simulate_judge(request: SimulateRequest):
    """
    시뮬레이션 상품 판단 (product_id + count 직접 지정).

    상품 ID와 개수를 직접 지정하여 결과 생성.
    테스트/데모용.

    Example:
        POST /api/simulate
        {
            "product_id": 26,
            "count": 1,
            "confidence": 0.85
        }
    """
    if not decision_engine or not product_db:
        raise HTTPException(status_code=500, detail="Service not initialized")

    try:
        product = product_db.get_product(request.product_id)
        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"Product {request.product_id} not found"
            )

        # 가상의 delta_weight 계산
        delta_weight = -(product.weight * request.count)

        # 가상의 EnsembleResult 생성
        candidates = [
            EnsembleResult(
                class_id=request.product_id,
                class_name=product.name,
                top_confidence=request.confidence,
                side_confidence=request.confidence,
                combined_confidence=request.confidence,
                vote_count=2,
            )
        ]

        # 판단
        result = decision_engine.judge(candidates, delta_weight)

        return _convert_to_response(result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Simulate error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/judge", response_model=JudgeResponse, tags=["Production"])
async def judge_product(request: JudgeRequest):
    """
    실제 상품 판단 (스냅샷 + 로드셀).

    프로덕션 환경에서 사용:
    1. snapshot_folder에서 이미지 로드
    2. YOLO 추론
    3. 손 근접 필터링 + Top-5 추출
    4. 무게 기반 검증
    5. 최종 결과 반환

    Example:
        POST /api/judge
        {
            "snapshot_folder": "/data/260116_1200/",
            "loadcell_weights": [500, 500, 0, 0, 0, 0, 0, 0, 0, 0],
            "baseline_weights": [865, 500, 0, 0, 0, 0, 0, 0, 0, 0],
            "zone_id": 0
        }
    """
    if not decision_engine:
        raise HTTPException(status_code=500, detail="Service not initialized")

    try:
        # 무게 변화량 계산
        deltas = [
            curr - base
            for curr, base in zip(request.loadcell_weights, request.baseline_weights)
        ]

        if request.zone_id is not None:
            start_idx = request.zone_id * 2
            delta_weight = sum(deltas[start_idx:start_idx + 2])
        else:
            delta_weight = sum(deltas)

        logger.info(
            f"Judge request: folder={request.snapshot_folder}, "
            f"delta={delta_weight:.1f}g, zone={request.zone_id}"
        )

        # TODO: 실제 구현에서는 이미지 로드 + YOLO 추론 추가
        # 현재는 이미지 없이 빈 결과 반환 (테스트용)

        # 임시: 빈 후보군으로 판단
        candidates: List[EnsembleResult] = []
        result = decision_engine.judge(candidates, delta_weight)

        return _convert_to_response(result)

    except Exception as e:
        logger.error(f"Judge error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ========== Helper Functions ==========

def _convert_to_response(result) -> JudgeResponse:
    """JudgmentResult를 JudgeResponse로 변환."""
    products = [
        ProductOutput(
            productId=p.product_id,
            name=p.name,
            count=p.count,
            unitPrice=p.unit_price,
            totalPrice=p.total_price,
            confidence=round(p.confidence, 2),
        )
        for p in result.products
    ]

    # JudgmentStatus enum 변환
    status_map = {
        JudgmentStatus.COMPLETE: JudgmentStatusEnum.COMPLETE,
        JudgmentStatus.PARTIAL: JudgmentStatusEnum.PARTIAL,
        JudgmentStatus.UNCERTAIN: JudgmentStatusEnum.UNCERTAIN,
        JudgmentStatus.NO_DETECTION: JudgmentStatusEnum.NO_DETECTION,
    }

    return JudgeResponse(
        success=result.is_success,
        products=products,
        totalPrice=result.total_price,
        status=status_map[result.status],
        confidence=round(result.confidence, 2),
        weightInfo=WeightInfo(
            delta=round(result.weight_delta, 1),
            explained=round(result.weight_explained, 1),
            residual=round(result.weight_residual, 1),
        ),
        productCount=result.product_count,
        isRemoval=result.is_removal,
        timestamp=result.timestamp,
    )


# ========== CLI Entry Point ==========

def main():
    """CLI 진입점."""
    import uvicorn
    uvicorn.run(
        "product_judge.main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
    )


if __name__ == "__main__":
    main()
