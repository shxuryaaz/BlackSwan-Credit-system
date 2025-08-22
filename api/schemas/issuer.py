from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class IssuerResponse(BaseModel):
    id: int
    name: str
    ticker: Optional[str] = None
    sector: Optional[str] = None
    country: Optional[str] = None
    score: Optional[float] = None
    bucket: Optional[str] = None
    delta_24h: float = 0.0
    score_ts: Optional[datetime] = None

class IssuerDetailResponse(BaseModel):
    id: int
    name: str
    ticker: Optional[str] = None
    sector: Optional[str] = None
    country: Optional[str] = None
    score: Optional[float] = None
    bucket: Optional[str] = None
    delta_24h: float = 0.0
    components: Optional[Dict[str, float]] = None
    top_features: List[Dict[str, Any]] = []
    events: List[Dict[str, Any]] = []
    score_ts: Optional[datetime] = None

class IssuerListResponse(BaseModel):
    issuers: List[IssuerResponse]
    total: int
    limit: int
    offset: int

class IssuerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    ticker: Optional[str] = Field(None, max_length=10)
    cik: Optional[str] = Field(None, max_length=20)
    sector: Optional[str] = Field(None, max_length=100)
    country: str = Field(default="US", max_length=50)

class IssuerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    ticker: Optional[str] = Field(None, max_length=10)
    cik: Optional[str] = Field(None, max_length=20)
    sector: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=50)





