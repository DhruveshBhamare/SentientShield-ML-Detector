from typing import Optional
from pydantic import BaseModel, Field


class RequestFeatures(BaseModel):
    request_type: str = Field(..., description="HTTP method, e.g., GET, POST")
    headers: Optional[str] = Field(None, description="Raw headers string or serialized map")
    payload_size: float = Field(..., description="Payload size in bytes")
    response_time: float = Field(..., description="Response time in ms")
    ip_reputation: float = Field(..., description="Reputation score 0-100")
    url: Optional[str] = Field(None, description="Request URL")
    user_agent: Optional[str] = Field(None, description="User-Agent string")
    anomaly_score: float = Field(..., description="Anomaly score 0.0-1.0")
    raw_log: Optional[str] = Field(None, description="Raw log content for deep intelligence analysis")


class WebsiteAnalysisRequest(BaseModel):
    website_url: str = Field(..., description="Website URL to analyze for attacks")
    analysis_depth: str = Field("standard", description="Analysis depth: basic, standard, or deep")