"""
API Models for Node.js Interface.

Pydantic 모델 정의 - FastAPI 자동 문서화 지원.

Request/Response 형식:
- JudgeRequest: 상품 판단 요청
- JudgeResponse: 상품 판단 응답 (Node.js 전달용)
- TestRequest: 테스트용 요청 (로드셀 없이)
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class JudgmentStatusEnum(str, Enum):
    """상품 판단 상태."""
    COMPLETE = "complete"
    PARTIAL = "partial"
    UNCERTAIN = "uncertain"
    NO_DETECTION = "no_detection"


# ========== Detection 관련 ==========

class DetectionInput(BaseModel):
    """YOLO 감지 입력."""
    xyxy: List[float] = Field(..., description="Bounding box [x1, y1, x2, y2]")
    conf: float = Field(..., ge=0, le=1, description="Confidence")
    cls: int = Field(..., ge=0, description="Class ID")
    name: str = Field(..., description="Class name")

    class Config:
        json_schema_extra = {
            "example": {
                "xyxy": [258.72, 47.65, 315.12, 113.97],
                "conf": 0.788,
                "cls": 0,
                "name": "hand"
            }
        }


# ========== Request 모델 ==========

class JudgeRequest(BaseModel):
    """
    상품 판단 요청.

    실제 시스템에서 사용:
    - snapshot_folder: 스냅샷 이미지 경로
    - loadcell_weights: 현재 로드셀 무게
    - baseline_weights: 기준 무게
    """
    snapshot_folder: str = Field(..., description="스냅샷 이미지 폴더 경로")
    loadcell_weights: List[float] = Field(
        ...,
        min_items=10,
        max_items=10,
        description="10채널 로드셀 현재 무게 (g)"
    )
    baseline_weights: List[float] = Field(
        ...,
        min_items=10,
        max_items=10,
        description="10채널 로드셀 기준 무게 (g)"
    )
    zone_id: Optional[int] = Field(None, ge=0, le=4, description="Zone ID (0-4)")

    class Config:
        json_schema_extra = {
            "example": {
                "snapshot_folder": "/data/260116_1200/",
                "loadcell_weights": [500, 500, 0, 0, 0, 0, 0, 0, 0, 0],
                "baseline_weights": [865, 500, 0, 0, 0, 0, 0, 0, 0, 0],
                "zone_id": 0
            }
        }


class TestRequest(BaseModel):
    """
    테스트용 요청 (로드셀 연결 없이 테스트).

    Node.js 전체 결제 프로세스 점검용.
    직접 YOLO 감지 결과와 무게 변화량 입력.
    """
    detections: List[DetectionInput] = Field(
        ...,
        description="YOLO 감지 결과 리스트"
    )
    delta_weight: float = Field(
        ...,
        description="무게 변화량 (g, 음수=제거)"
    )
    zone_id: Optional[int] = Field(None, ge=0, le=4, description="Zone ID")
    use_hand_filter: bool = Field(True, description="손 근접 필터링 사용 여부")

    class Config:
        json_schema_extra = {
            "example": {
                "detections": [
                    {"xyxy": [258.72, 47.65, 315.12, 113.97], "conf": 0.788, "cls": 0, "name": "hand"},
                    {"xyxy": [257.67, 75.54, 284.33, 110.22], "conf": 0.492, "cls": 26, "name": "chickenmayo_rice"},
                ],
                "delta_weight": -365.0,
                "zone_id": 0,
                "use_hand_filter": True
            }
        }


class SimulateRequest(BaseModel):
    """
    시뮬레이션 요청 (완전 테스트용).

    직접 class_id와 개수를 지정하여 결과 생성.
    """
    product_id: int = Field(..., ge=1, description="상품 ID")
    count: int = Field(..., ge=1, le=10, description="개수")
    confidence: float = Field(0.8, ge=0, le=1, description="Vision 신뢰도")

    class Config:
        json_schema_extra = {
            "example": {
                "product_id": 26,
                "count": 1,
                "confidence": 0.85
            }
        }


# ========== Response 모델 ==========

class ProductOutput(BaseModel):
    """개별 상품 응답."""
    productId: int = Field(..., description="상품 ID")
    name: str = Field(..., description="상품 이름")
    count: int = Field(..., description="개수")
    unitPrice: int = Field(..., description="단가 (원)")
    totalPrice: int = Field(..., description="총 가격 (원)")
    confidence: float = Field(..., description="신뢰도 (0.0-1.0)")

    class Config:
        json_schema_extra = {
            "example": {
                "productId": 26,
                "name": "chickenmayo_rice",
                "count": 1,
                "unitPrice": 3500,
                "totalPrice": 3500,
                "confidence": 0.85
            }
        }


class WeightInfo(BaseModel):
    """무게 정보."""
    delta: float = Field(..., description="무게 변화량 (g)")
    explained: float = Field(..., description="설명된 무게 (g)")
    residual: float = Field(..., description="잔여 무게 (g)")


class JudgeResponse(BaseModel):
    """
    상품 판단 응답 (Node.js 전달용).

    success=True면 결제 진행 가능.
    """
    success: bool = Field(..., description="판단 성공 여부")
    products: List[ProductOutput] = Field(..., description="판단된 상품 리스트")
    totalPrice: int = Field(..., description="총 결제 금액 (원)")
    status: JudgmentStatusEnum = Field(..., description="판단 상태")
    confidence: float = Field(..., description="전체 신뢰도 (0.0-1.0)")
    weightInfo: WeightInfo = Field(..., description="무게 정보")
    productCount: int = Field(..., description="총 상품 개수")
    isRemoval: bool = Field(..., description="상품 제거 여부")
    timestamp: float = Field(..., description="판단 시각 (Unix timestamp)")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
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
                "isRemoval": True,
                "timestamp": 1737046800.123
            }
        }


class HealthResponse(BaseModel):
    """헬스 체크 응답."""
    status: str = Field("ok", description="서비스 상태")
    version: str = Field(..., description="서비스 버전")
    product_count: int = Field(..., description="등록된 상품 수")


class ErrorResponse(BaseModel):
    """에러 응답."""
    success: bool = Field(False)
    error: str = Field(..., description="에러 메시지")
    detail: Optional[str] = Field(None, description="상세 정보")
