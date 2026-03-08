"""
NeuralFort API Endpoints
========================

FastAPI endpoints for the NeuralFort AI-Based Intelligent Infrastructure Resilience Framework.
Provides website-based activation, real-time monitoring, anomaly detection, self-healing automation,
and LLM-powered insights.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import asyncio
import json
import logging

from .neuralfort import (
    NeuralFortFramework, get_neuralfort_framework,
    WebsiteActivationManager, SystemComponent, ThreatLevel, ActionType,
    WebsiteRegistration, SystemMetrics, AnomalyEvent, HealingAction
)

# Configure logging
logger = logging.getLogger(__name__)

# Create API router
router = APIRouter(tags=["NeuralFort"])

# Pydantic models for API requests/responses
class WebsiteActivationRequest(BaseModel):
    website_url: str = Field(..., description="Website URL to register for NeuralFort activation")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata for registration")

class WebsiteActivationResponse(BaseModel):
    activation_key: str
    website_url: str
    domain: str
    status: str
    message: str

class FrameworkActivationRequest(BaseModel):
    activation_key: str = Field(..., description="Activation key for NeuralFort framework")

class FrameworkStatusResponse(BaseModel):
    status: str
    framework_state: Dict[str, Any]
    system_health: Dict[str, Any]
    anomaly_detection: Dict[str, Any]
    self_healing: Dict[str, Any]
    llm_insights: Optional[Dict[str, Any]]
    activation_info: Dict[str, Any]

class ComponentMetricsRequest(BaseModel):
    component: Optional[str] = Field(default=None, description="Specific component to query")
    minutes: int = Field(default=60, ge=1, le=1440, description="Time range in minutes (1-1440)")

class ComponentMetricsResponse(BaseModel):
    component: str
    metrics: List[Dict[str, Any]]
    health_score: float
    anomaly_count: int

class AnomalyHistoryResponse(BaseModel):
    total_anomalies: int
    recent_anomalies: List[Dict[str, Any]]
    component_breakdown: Dict[str, int]
    severity_breakdown: Dict[str, int]

class HealingActionsResponse(BaseModel):
    total_actions: int
    successful_actions: int
    success_rate: float
    recent_actions: List[Dict[str, Any]]
    component_success_rates: Dict[str, float]

class RiskPredictionResponse(BaseModel):
    component: str
    risk_level: str
    failure_probability: float
    predicted_failure_time: Optional[str]
    contributing_factors: List[str]
    recommended_actions: List[str]
    confidence: float

class LLMInsightRequest(BaseModel):
    query: Optional[str] = Field(default=None, description="Specific query for LLM analysis")
    include_recommendations: bool = Field(default=True, description="Include recommendations in response")

class LLMInsightResponse(BaseModel):
    timestamp: str
    query: Optional[str]
    insights: Dict[str, Any]
    recommendations: Optional[List[Dict[str, Any]]]

class CopilotChatRequest(BaseModel):
    message: str = Field(..., description="User message or question for the Security Copilot")
    top_k: int = Field(default=3, ge=1, le=10, description="Number of KB results to use")

class CopilotSource(BaseModel):
    id: Optional[str]
    title: Optional[str]
    score: float
    tags: List[str] = []

class CopilotChatResponse(BaseModel):
    answer: str
    sources: List[CopilotSource]
    suggested_precautions: List[str] = []
    suggested_steps: List[str] = []
    context: Optional[Dict[str, Any]]

# Global instances
activation_manager = WebsiteActivationManager()
framework_instance = None

# Dependency to get framework instance
async def get_framework() -> NeuralFortFramework:
    """Get or create NeuralFort framework instance"""
    global framework_instance
    if framework_instance is None:
        framework_instance = get_neuralfort_framework()
    return framework_instance

def require_activation(framework: NeuralFortFramework = Depends(get_framework)):
    """Dependency to ensure framework is activated"""
    if not framework.is_activated:
        raise HTTPException(
            status_code=403,
            detail="NeuralFort framework not activated. Please activate with valid activation key."
        )
    return framework

# Website Registration and Activation Endpoints
@router.post("/register-website", response_model=WebsiteActivationResponse)
async def register_website(request: WebsiteActivationRequest):
    """
    Register a website for NeuralFort activation.
    
    This endpoint allows users to register their website and receive an activation key
    that enables the NeuralFort framework functionality.
    """
    try:
        # Validate URL format
        if not request.website_url:
            raise HTTPException(status_code=400, detail="Website URL is required")
        
        # Generate activation key
        activation_key = activation_manager.register_website(
            request.website_url,
            request.metadata or {}
        )
        
        # Get registration info
        registration = activation_manager.get_registration_info(activation_key)
        
        return WebsiteActivationResponse(
            activation_key=activation_key,
            website_url=registration.website_url,
            domain=registration.domain,
            status="active",
            message="Website successfully registered for NeuralFort activation"
        )
        
    except Exception as e:
        logger.error(f"Website registration failed: {e}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@router.post("/activate-framework", response_model=Dict[str, Any])
async def activate_framework(request: FrameworkActivationRequest):
    """
    Activate NeuralFort framework with website-based activation key.
    
    The framework will not function until activated with a valid activation key
    obtained through website registration.
    """
    try:
        framework = await get_framework()
        
        # Attempt activation
        success = await framework.activate_framework(request.activation_key)
        
        if success:
            registration = activation_manager.get_registration_info(request.activation_key)
            return {
                "status": "activated",
                "message": "NeuralFort framework successfully activated",
                "website_url": registration.website_url,
                "domain": registration.domain,
                "activated_at": datetime.now().isoformat()
            }
        else:
            raise HTTPException(
                status_code=401,
                detail="Invalid activation key or activation failed"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Framework activation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Activation failed: {str(e)}")

@router.get("/activation-status", response_model=Dict[str, Any])
async def get_activation_status(framework: NeuralFortFramework = Depends(get_framework)):
    """
    Get current activation status of NeuralFort framework.
    """
    try:
        if not framework.is_activated:
            return {
                "status": "inactive",
                "message": "Framework not activated",
                "requires_activation": True
            }
        
        activation_info = framework._get_activation_info()
        return {
            "status": "active",
            "activation_info": activation_info,
            "requires_activation": False
        }
        
    except Exception as e:
        logger.error(f"Failed to get activation status: {e}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")

# Framework Status and Monitoring Endpoints
@router.get("/status", response_model=FrameworkStatusResponse)
async def get_framework_status(framework: NeuralFortFramework = Depends(require_activation)):
    """
    Get comprehensive status of NeuralFort framework including system health,
    anomaly detection stats, self-healing metrics, and LLM insights.
    """
    try:
        status = framework.get_framework_status()
        return FrameworkStatusResponse(**status)
        
    except Exception as e:
        logger.error(f"Failed to get framework status: {e}")
        raise HTTPException(status_code=500, detail=f"Status retrieval failed: {str(e)}")

@router.get("/system-health", response_model=Dict[str, Any])
async def get_system_health(framework: NeuralFortFramework = Depends(require_activation)):
    """
    Get current system health metrics and scores.
    """
    try:
        health_score = framework.infrastructure_monitor.get_system_health_score()
        recent_metrics = framework.infrastructure_monitor.get_recent_metrics(minutes=5)
        
        # Calculate component health scores
        component_health = {}
        for component in SystemComponent:
            component_metrics = [m for m in recent_metrics if m.component == component]
            if component_metrics:
                violations = sum(1 for m in component_metrics 
                             if m.threshold_max and m.value > m.threshold_max)
                health = max(0, 100 - (violations * 10))
                component_health[component.value] = health
        
        return {
            "overall_health_score": health_score,
            "health_status": framework._get_health_status(health_score),
            "component_health": component_health,
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get system health: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

# Metrics and Analytics Endpoints
@router.post("/metrics", response_model=ComponentMetricsResponse)
async def get_component_metrics(
    request: ComponentMetricsRequest,
    framework: NeuralFortFramework = Depends(require_activation)
):
    """
    Get detailed metrics for specific system components.
    """
    try:
        # Get recent metrics
        if request.component:
            component = SystemComponent(request.component)
            metrics = framework.infrastructure_monitor.get_recent_metrics(
                component=component, minutes=request.minutes
            )
        else:
            metrics = framework.infrastructure_monitor.get_recent_metrics(
                minutes=request.minutes
            )
        
        # Convert metrics to serializable format
        metrics_data = []
        for metric in metrics:
            metrics_data.append({
                "timestamp": metric.timestamp.isoformat(),
                "component": metric.component.value,
                "metric_name": metric.metric_name,
                "value": metric.value,
                "threshold_min": metric.threshold_min,
                "threshold_max": metric.threshold_max,
                "unit": metric.unit
            })
        
        # Calculate health score and anomaly count
        if request.component:
            component = SystemComponent(request.component)
            health_score = framework.infrastructure_monitor.get_system_health_score()
            anomaly_count = len([
                a for a in framework.anomaly_detector.anomaly_history
                if a.component == component
                and datetime.now() - a.timestamp < timedelta(minutes=request.minutes)
            ])
        else:
            health_score = framework.infrastructure_monitor.get_system_health_score()
            anomaly_count = len([
                a for a in framework.anomaly_detector.anomaly_history
                if datetime.now() - a.timestamp < timedelta(minutes=request.minutes)
            ])
        
        return ComponentMetricsResponse(
            component=request.component or "all",
            metrics=metrics_data,
            health_score=health_score,
            anomaly_count=anomaly_count
        )
        
    except Exception as e:
        logger.error(f"Failed to get component metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Metrics retrieval failed: {str(e)}")

@router.get("/anomalies", response_model=AnomalyHistoryResponse)
async def get_anomaly_history(
    hours: int = 24,
    framework: NeuralFortFramework = Depends(require_activation)
):
    """
    Get anomaly detection history and statistics.
    """
    try:
        # Get recent anomalies
        recent_anomalies = [
            anomaly for anomaly in framework.anomaly_detector.anomaly_history
            if datetime.now() - anomaly.timestamp < timedelta(hours=hours)
        ]
        
        # Convert to serializable format
        anomalies_data = []
        for anomaly in recent_anomalies:
            anomalies_data.append({
                "id": anomaly.id,
                "timestamp": anomaly.timestamp.isoformat(),
                "component": anomaly.component.value,
                "severity": anomaly.severity.value,
                "anomaly_score": anomaly.anomaly_score,
                "description": anomaly.description,
                "confidence": anomaly.confidence,
                "predicted_failure_time": anomaly.predicted_failure_time.isoformat() if anomaly.predicted_failure_time else None
            })
        
        # Calculate breakdowns
        component_breakdown = {}
        severity_breakdown = {}
        
        for anomaly in recent_anomalies:
            component_breakdown[anomaly.component.value] = component_breakdown.get(anomaly.component.value, 0) + 1
            severity_breakdown[anomaly.severity.value] = severity_breakdown.get(anomaly.severity.value, 0) + 1
        
        return AnomalyHistoryResponse(
            total_anomalies=len(framework.anomaly_detector.anomaly_history),
            recent_anomalies=anomalies_data,
            component_breakdown=component_breakdown,
            severity_breakdown=severity_breakdown
        )
        
    except Exception as e:
        logger.error(f"Failed to get anomaly history: {e}")
        raise HTTPException(status_code=500, detail=f"Anomaly history retrieval failed: {str(e)}")

@router.get("/healing-actions", response_model=HealingActionsResponse)
async def get_healing_actions(
    hours: int = 24,
    framework: NeuralFortFramework = Depends(require_activation)
):
    """
    Get self-healing actions history and statistics.
    """
    try:
        # Get recent healing actions
        recent_actions = [
            action for action in framework.healing_engine.actions_history
            if datetime.now() - action.timestamp < timedelta(hours=hours)
        ]
        
        # Convert to serializable format
        actions_data = []
        for action in recent_actions:
            actions_data.append({
                "id": action.id,
                "timestamp": action.timestamp.isoformat(),
                "action_type": action.action_type.value,
                "target_component": action.target_component.value,
                "description": action.description,
                "success": action.success,
                "execution_time": action.execution_time,
                "error_message": action.error_message
            })
        
        # Calculate component success rates
        component_success_rates = {}
        for component in SystemComponent:
            component_actions = [
                a for a in recent_actions if a.target_component == component
            ]
            if component_actions:
                success_rate = sum(1 for a in component_actions if a.success) / len(component_actions)
                component_success_rates[component.value] = success_rate
        
        return HealingActionsResponse(
            total_actions=len(framework.healing_engine.actions_history),
            successful_actions=framework.framework_state["successful_healing_actions"],
            success_rate=framework.healing_engine.get_success_rate(),
            recent_actions=actions_data,
            component_success_rates=component_success_rates
        )
        
    except Exception as e:
        logger.error(f"Failed to get healing actions: {e}")
        raise HTTPException(status_code=500, detail=f"Healing actions retrieval failed: {str(e)}")

# Risk Prediction and Analytics Endpoints
@router.get("/risk-prediction/{component}", response_model=RiskPredictionResponse)
async def get_risk_prediction(
    component: str,
    framework: NeuralFortFramework = Depends(require_activation)
):
    """
    Get risk prediction for a specific system component.
    """
    try:
        system_component = SystemComponent(component)
        
        # Get recent metrics for prediction
        recent_metrics = framework.infrastructure_monitor.get_recent_metrics(
            component=system_component, minutes=30
        )
        
        # Generate risk prediction
        failure_probability = framework.anomaly_detector.predict_threat_likelihood(
            system_component, recent_metrics
        )
        
        # Determine risk level
        if failure_probability > 0.8:
            risk_level = ThreatLevel.CRITICAL
        elif failure_probability > 0.6:
            risk_level = ThreatLevel.HIGH
        elif failure_probability > 0.3:
            risk_level = ThreatLevel.MEDIUM
        else:
            risk_level = ThreatLevel.LOW
        
        # Estimate failure time
        if failure_probability > 0.7:
            time_to_failure = datetime.now() + timedelta(hours=1)
        elif failure_probability > 0.5:
            time_to_failure = datetime.now() + timedelta(hours=4)
        else:
            time_to_failure = datetime.now() + timedelta(hours=24)
        
        # Get contributing factors
        contributing_factors = []
        if recent_metrics:
            threshold_violations = sum(1 for m in recent_metrics 
                                     if m.threshold_max and m.value > m.threshold_max)
            if threshold_violations > 0:
                contributing_factors.append(f"{threshold_violations} threshold violations detected")
        
        recent_anomalies = [
            a for a in framework.anomaly_detector.anomaly_history
            if a.component == system_component
            and datetime.now() - a.timestamp < timedelta(hours=2)
        ]
        
        if recent_anomalies:
            contributing_factors.append(f"{len(recent_anomalies)} recent anomalies detected")
        
        # Recommended actions
        recommended_actions = []
        if risk_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
            recommended_actions.extend([
                "Monitor component closely",
                "Prepare contingency plans",
                "Consider proactive maintenance"
            ])
        
        return RiskPredictionResponse(
            component=component,
            risk_level=risk_level.value,
            failure_probability=failure_probability,
            predicted_failure_time=time_to_failure.isoformat(),
            contributing_factors=contributing_factors,
            recommended_actions=recommended_actions,
            confidence=min(failure_probability + 0.2, 1.0)
        )
        
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid component: {component}")
    except Exception as e:
        logger.error(f"Failed to get risk prediction: {e}")
        raise HTTPException(status_code=500, detail=f"Risk prediction failed: {str(e)}")

@router.post("/shap-explanations", response_model=Dict[str, Any])
async def get_shap_explanations(
    metrics: SystemMetrics,
    framework: NeuralFortFramework = Depends(require_activation)
):
    """
    Get SHAP explanations for a given set of system metrics.
    """
    try:
        shap_values, feature_names = framework.get_shap_explanations(metrics)
        return {
            "shap_values": shap_values.tolist(),
            "feature_names": feature_names
        }
    except Exception as e:
        logger.error(f"Failed to get SHAP explanations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# LLM Insights and Recommendations Endpoints
@router.get("/llm-insights", response_model=LLMInsightResponse)
async def generate_llm_insights(
    query: Optional[str] = None,
    include_recommendations: bool = True,
    framework: NeuralFortFramework = Depends(require_activation)
):
    """
    Generate LLM-powered insights and recommendations based on recent system data.
    """
    try:
        # Get recent data for analysis
        recent_anomalies = list(framework.anomaly_detector.anomaly_history)[-20:]
        recent_metrics = framework.infrastructure_monitor.get_recent_metrics(minutes=15)
        recent_actions = list(framework.healing_engine.actions_history)[-10:]
        
        # Generate LLM insights
        insights = framework.llm_copilot.generate_insights(
            recent_anomalies, recent_metrics, recent_actions
        )
        
        return LLMInsightResponse(
            timestamp=datetime.now().isoformat(),
            query=query,
            insights=insights,
            recommendations=insights.get("recommendations") if include_recommendations else None
        )
        
    except Exception as e:
        logger.error(f"Failed to generate LLM insights: {e}")
        raise HTTPException(status_code=500, detail=f"LLM insight generation failed: {str(e)}")

# Security Copilot Chat Endpoint
@router.post("/copilot/chat", response_model=CopilotChatResponse)
async def copilot_chat(
    request: CopilotChatRequest,
    framework: NeuralFortFramework = Depends(require_activation)
):
    """Chat with the self-made Security Copilot backed by the hacking precaution KB."""
    try:
        result = framework.chat_with_copilot(request.message)
        # Map sources to response model
        sources = [
            CopilotSource(
                id=s.get("id"),
                title=s.get("title"),
                score=float(s.get("score", 0.0)),
                tags=s.get("tags", [])
            ) for s in result.get("sources", [])
        ]
        return CopilotChatResponse(
            answer=result.get("answer", ""),
            sources=sources,
            suggested_precautions=result.get("suggested_precautions", []),
            suggested_steps=result.get("suggested_steps", []),
            context=result.get("context")
        )
    except Exception as e:
        logger.error(f"Copilot chat failed: {e}")
        raise HTTPException(status_code=500, detail=f"Copilot chat failed: {str(e)}")

# WebSocket endpoint for real-time updates
@router.websocket("/ws/realtime")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time NeuralFort updates.
    """
    await websocket.accept()
    
    try:
        framework = await get_framework()
        
        # Check if framework is activated
        if not framework.is_activated:
            await websocket.send_json({
                "type": "error",
                "message": "Framework not activated. Please activate first.",
                "timestamp": datetime.now().isoformat()
            })
            await websocket.close()
            return
        
        # Send initial status
        status = framework.get_framework_status()
        await websocket.send_json({
            "type": "initial_status",
            "data": status,
            "timestamp": datetime.now().isoformat()
        })
        
        # Send periodic updates
        while True:
            try:
                # Wait for next update cycle
                await asyncio.sleep(10)
                
                # Get current status
                status = framework.get_framework_status()
                
                # Send update
                await websocket.send_json({
                    "type": "status_update",
                    "data": {
                        "system_health": status["system_health"],
                        "anomaly_detection": status["anomaly_detection"],
                        "self_healing": status["self_healing"]
                    },
                    "timestamp": datetime.now().isoformat()
                })
                
            except WebSocketDisconnect:
                logger.info("WebSocket client disconnected")
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": f"Update error: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                })
                
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket endpoint error: {e}")
        try:
            await websocket.close()
        except:
            pass

# Framework Management Endpoints
@router.post("/shutdown")
async def shutdown_framework(framework: NeuralFortFramework = Depends(require_activation)):
    """
    Shutdown NeuralFort framework gracefully.
    """
    try:
        await framework.shutdown_framework()
        return {
            "status": "shutdown",
            "message": "NeuralFort framework shutdown successfully",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Framework shutdown failed: {e}")
        raise HTTPException(status_code=500, detail=f"Shutdown failed: {str(e)}")

@router.post("/restart")
async def restart_framework(
    background_tasks: BackgroundTasks,
    framework: NeuralFortFramework = Depends(require_activation)
):
    """
    Restart NeuralFort framework.
    """
    try:
        # Shutdown current instance
        await framework.shutdown_framework()
        
        # Restart in background
        async def restart_task():
            global framework_instance
            await asyncio.sleep(2)  # Brief pause
            framework_instance = NeuralFortFramework()
            await framework_instance.activate_framework(framework.activation_key)
            logger.info("NeuralFort framework restarted")
        
        background_tasks.add_task(restart_task)
        
        return {
            "status": "restarting",
            "message": "NeuralFort framework is restarting",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Framework restart failed: {e}")
        raise HTTPException(status_code=500, detail=f"Restart failed: {str(e)}")

# Health check endpoint
@router.get("/health")
async def health_check():
    """
    Basic health check endpoint.
    """
    return {
        "status": "healthy",
        "service": "neuralfort",
        "timestamp": datetime.now().isoformat()
    }

# Additional endpoints for test script compatibility

@router.post("/website/register")
async def register_website_compat(request: WebsiteActivationRequest):
    """
    Compatible endpoint for website registration (alias for /register-website).
    """
    return await register_website(request)

@router.post("/activate")
async def activate_framework_compat(request: FrameworkActivationRequest):
    """
    Compatible endpoint for framework activation (alias for /activate-framework).
    """
    return await activate_framework(request)

@router.get("/llm/insights")
async def get_llm_insights_compat(framework: NeuralFortFramework = Depends(require_activation)):
    """
    Compatible endpoint for LLM insights (simplified version of /llm-insights).
    """
    try:
        # Use existing LLM insights endpoint with default parameters
        request = LLMInsightRequest(query=None, include_recommendations=True)
        result = await get_llm_insights(request, framework)
        
        # Format response to match test script expectations
        return {
            "key_findings": f"System analysis completed. {len(result.insights)} insights generated.",
            "recommendations": result.recommendations or [],
            "timestamp": result.timestamp
        }
        
    except Exception as e:
        logger.error(f"Failed to generate LLM insights: {e}")
        raise HTTPException(status_code=500, detail=f"LLM insight generation failed: {str(e)}")

# Simple metrics endpoint for test script compatibility
@router.get("/metrics")
async def get_simple_metrics(framework: NeuralFortFramework = Depends(require_activation)):
    """
    Simple metrics endpoint compatible with test script expectations.
    """
    try:
        # Get basic system metrics
        import psutil
        
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "disk_percent": (disk.used / disk.total) * 100,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get simple metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Metrics retrieval failed: {str(e)}")

# Exception handlers should be registered on the FastAPI app instance, not the router
@router.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    """
    Get the dashboard HTML file.
    """
    try:
        framework = get_neuralfort_framework()
        if not framework.is_activated:
            return JSONResponse(status_code=403, content={"error": "Framework not activated"})
        
        history = framework.get_metrics_history(60)
        return JSONResponse(content=history)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@router.get("/metrics/history", summary="Get Historical Metrics", tags=["Metrics"])
async def get_metrics_history(minutes: int = 60):
    """
    Retrieve historical metrics for all system components.
    """
    try:
        framework = get_neuralfort_framework()
        if not framework.is_activated:
            return JSONResponse(status_code=403, content={"error": "Framework not activated"})
        
        history = framework.get_metrics_history(minutes)
        return JSONResponse(content=history)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@router.get("/alerts", summary="Get Active Alerts", tags=["Alerts"])
async def get_active_alerts():
    """
    Get the list of currently active alerts.
    """
    try:
        framework = get_neuralfort_framework()
        if not framework.is_activated:
            return JSONResponse(status_code=403, content={"error": "Framework not activated"})
        
        alerts = framework.get_active_alerts()
        return JSONResponse(content=alerts)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@router.post("/alerts/config", summary="Update Alerts Configuration", tags=["Alerts"])
async def update_alerts_config(request: Request):
    """
    Update the configuration for metric thresholds and alerts.
    """
    try:
        framework = get_neuralfort_framework()
        if not framework.is_activated:
            return JSONResponse(status_code=403, content={"error": "Framework not activated"})
        
        new_config = await request.json()
        framework.update_alerts_config(new_config)
        return JSONResponse(content={"message": "Alerts configuration updated successfully"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# Serve the dashboard HTML file
@router.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    """
    Get the dashboard HTML file.
    """
    try:
        framework = get_neuralfort_framework()
        if not framework.is_activated:
            return JSONResponse(status_code=403, content={"error": "Framework not activated"})
        
        history = framework.get_metrics_history(minutes)
        return JSONResponse(content=history)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@router.get("/uptime", tags=["NeuralFort"]) 
async def get_uptime(framework: NeuralFortFramework = Depends(get_framework)):
    status = framework.get_framework_status()
    uptime_str = status.get('uptime', 'N/A')
    return {"uptime_str": uptime_str}

@router.get("/alerts", tags=["NeuralFort"]) 
async def get_alerts(framework: NeuralFortFramework = Depends(get_framework)):
    status = framework.get_framework_status()
    active_alerts = status.get('active_alerts', 0)
    return {"active_alerts": active_alerts}

@router.post("/restart", tags=["NeuralFort"]) 
async def restart_framework_endpoint(
    background_tasks: BackgroundTasks,
    framework: NeuralFortFramework = Depends(require_activation)
):
    try:
        # Shutdown current instance
        await framework.shutdown_framework()
        
        # Restart in background
        async def restart_task():
            global framework_instance
            await asyncio.sleep(2)  # Brief pause
            framework_instance = NeuralFortFramework()
            await framework_instance.activate_framework(framework.activation_key)
            logger.info("NeuralFort framework restarted")
        
        background_tasks.add_task(restart_task)
        
        return {
            "status": "restarting",
            "message": "NeuralFort framework is restarting",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Framework restart failed: {e}")
        raise HTTPException(status_code=500, detail=f"Restart failed: {str(e)}")

# Health check endpoint
@router.get("/health")
async def health_check():
    """
    Basic health check endpoint.
    """
    return {
        "status": "healthy",
        "service": "neuralfort",
        "timestamp": datetime.now().isoformat()
    }

# Additional endpoints for test script compatibility

@router.post("/website/register")
async def register_website_compat(request: WebsiteActivationRequest):
    """
    Compatible endpoint for website registration (alias for /register-website).
    """
    return await register_website(request)

@router.post("/activate")
async def activate_framework_compat(request: FrameworkActivationRequest):
    """
    Compatible endpoint for framework activation (alias for /activate-framework).
    """
    return await activate_framework(request)

@router.get("/llm/insights")
async def get_llm_insights_compat(framework: NeuralFortFramework = Depends(require_activation)):
    """
    Compatible endpoint for LLM insights (simplified version of /llm-insights).
    """
    try:
        # Use existing LLM insights endpoint with default parameters
        request = LLMInsightRequest(query=None, include_recommendations=True)
        result = await get_llm_insights(request, framework)
        
        # Format response to match test script expectations
        return {
            "key_findings": f"System analysis completed. {len(result.insights)} insights generated.",
            "recommendations": result.recommendations or [],
            "timestamp": result.timestamp
        }
        
    except Exception as e:
        logger.error(f"Failed to generate LLM insights: {e}")
        raise HTTPException(status_code=500, detail=f"LLM insight generation failed: {str(e)}")

# Simple metrics endpoint for test script compatibility
@router.get("/metrics")
async def get_simple_metrics(framework: NeuralFortFramework = Depends(require_activation)):
    """
    Simple metrics endpoint compatible with test script expectations.
    """
    try:
        # Get basic system metrics
        import psutil
        
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "disk_percent": (disk.used / disk.total) * 100,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get simple metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Metrics retrieval failed: {str(e)}")

# Exception handlers should be registered on the FastAPI app instance, not the router
@router.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    """
    Get the dashboard HTML file.
    """
    try:
        framework = get_neuralfort_framework()
        if not framework.is_activated:
            return JSONResponse(status_code=403, content={"error": "Framework not activated"})
        
        history = framework.get_metrics_history(minutes)
        return JSONResponse(content=history)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@router.get("/metrics/history", summary="Get Historical Metrics", tags=["Metrics"])
async def get_metrics_history(minutes: int = 60):
    """
    Retrieve historical metrics for all system components.
    """
    try:
        framework = get_neuralfort_framework()
        if not framework.is_activated:
            return JSONResponse(status_code=403, content={"error": "Framework not activated"})
        
        history = framework.get_metrics_history(minutes)
        return JSONResponse(content=history)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@router.get("/alerts", summary="Get Active Alerts", tags=["Alerts"])
async def get_active_alerts():
    """
    Get the list of currently active alerts.
    """
    try:
        framework = get_neuralfort_framework()
        if not framework.is_activated:
            return JSONResponse(status_code=403, content={"error": "Framework not activated"})
        
        alerts = framework.get_active_alerts()
        return JSONResponse(content=alerts)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@router.post("/alerts/config", summary="Update Alerts Configuration", tags=["Alerts"])
async def update_alerts_config(request: Request):
    """
    Update the configuration for metric thresholds and alerts.
    """
    try:
        framework = get_neuralfort_framework()
        if not framework.is_activated:
            return JSONResponse(status_code=403, content={"error": "Framework not activated"})
        
        new_config = await request.json()
        framework.update_alerts_config(new_config)
        return JSONResponse(content={"message": "Alerts configuration updated successfully"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# Serve the dashboard HTML file
@router.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    """
    Get the dashboard HTML file.
    """
    try:
        framework = get_neuralfort_framework()
        if not framework.is_activated:
            return JSONResponse(status_code=403, content={"error": "Framework not activated"})
        
        history = framework.get_metrics_history(minutes)
        return JSONResponse(content=history)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})