"""
NeuralFort - AI-Based Intelligent Infrastructure Resilience Framework
=====================================================================

An advanced AI-driven framework designed to enhance the reliability, stability, 
and self-healing capabilities of digital infrastructure through:

- Real-Time Monitoring & Anomaly Detection
- Predictive Analytics & Risk Assessment  
- Self-Healing Automation
- Explainable AI Insights
- Website-Based Activation System
"""

import os
import json
import asyncio
import logging
import hashlib
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np
import pandas as pd
from collections import defaultdict, deque
import psutil
import platform
import socket
import time
# Optional SHAP import for explainability; gracefully degrade if unavailable
try:
    import shap  # type: ignore
    _HAS_SHAP = True
except Exception:
    shap = None  # type: ignore
    _HAS_SHAP = False

# ML Libraries
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
try:
    from sentence_transformers import SentenceTransformer
    _HAS_ST = True
except Exception:
    SentenceTransformer = None
    _HAS_ST = False
import joblib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SystemComponent(Enum):
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    PROCESS = "process"
    SERVICE = "service"

class ThreatLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ActionType(Enum):
    RESTART_SERVICE = "restart_service"
    REALLOCATE_RESOURCES = "reallocate_resources"
    APPLY_PATCH = "apply_patch"
    ISOLATE_COMPONENT = "isolate_component"
    ALERT_ADMIN = "alert_admin"
    LOG_INCIDENT = "log_incident"

@dataclass
class WebsiteRegistration:
    """Website registration for NeuralFort activation"""
    website_url: str
    domain: str
    registration_date: datetime
    activation_key: str
    status: str  # "pending", "active", "expired"
    metadata: Dict[str, Any]
    
@dataclass
class SystemMetrics:
    """System performance metrics"""
    timestamp: datetime
    component: SystemComponent
    metric_name: str
    value: float
    threshold_min: Optional[float] = None
    threshold_max: Optional[float] = None
    unit: str = ""

@dataclass
class AnomalyEvent:
    """Detected anomaly event"""
    id: str
    timestamp: datetime
    component: SystemComponent
    severity: ThreatLevel
    anomaly_score: float
    description: str
    metrics: List[SystemMetrics]
    predicted_failure_time: Optional[datetime] = None
    confidence: float = 0.0

@dataclass
class HealingAction:
    """Self-healing action taken"""
    id: str
    timestamp: datetime
    action_type: ActionType
    target_component: SystemComponent
    description: str
    success: bool
    execution_time: float
    error_message: Optional[str] = None
    rollback_possible: bool = True

@dataclass
class RiskPrediction:
    """Risk prediction for system components"""
    component: SystemComponent
    risk_level: ThreatLevel
    probability: float
    time_to_failure: Optional[timedelta]
    contributing_factors: List[str]
    recommended_actions: List[ActionType]
    confidence: float = 0.0

class WebsiteActivationManager:
    """Manages website-based activation system for NeuralFort"""
    
    def __init__(self, activation_file: str = "neuralfort_activations.json"):
        self.activation_file = activation_file
        self.activations: Dict[str, WebsiteRegistration] = {}
        self.load_activations()
    
    def load_activations(self):
        """Load existing activations from file"""
        if os.path.exists(self.activation_file):
            try:
                with open(self.activation_file, 'r') as f:
                    data = json.load(f)
                    for key, reg_data in data.items():
                        self.activations[key] = WebsiteRegistration(
                            website_url=reg_data['website_url'],
                            domain=reg_data['domain'],
                            registration_date=datetime.fromisoformat(reg_data['registration_date']),
                            activation_key=reg_data['activation_key'],
                            status=reg_data['status'],
                            metadata=reg_data.get('metadata', {})
                        )
            except Exception as e:
                logger.error(f"Failed to load activations: {e}")
    
    def save_activations(self):
        """Save activations to file"""
        try:
            data = {}
            for key, registration in self.activations.items():
                data[key] = {
                    'website_url': registration.website_url,
                    'domain': registration.domain,
                    'registration_date': registration.registration_date.isoformat(),
                    'activation_key': registration.activation_key,
                    'status': registration.status,
                    'metadata': registration.metadata
                }
            
            with open(self.activation_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save activations: {e}")
    
    def generate_activation_key(self, website_url: str) -> str:
        """Generate unique activation key based on website URL"""
        timestamp = datetime.now().isoformat()
        combined = f"{website_url}{timestamp}{os.urandom(16).hex()}"
        return hashlib.sha256(combined.encode()).hexdigest()[:32]
    
    def register_website(self, website_url: str, metadata: Dict[str, Any] = None) -> str:
        """Register a website for NeuralFort activation"""
        domain = self.extract_domain(website_url)
        
        # Check if already registered
        for registration in self.activations.values():
            if registration.domain == domain:
                if registration.status == "active":
                    return registration.activation_key
                else:
                    # Reactivate expired registration
                    registration.status = "active"
                    registration.registration_date = datetime.now()
                    self.save_activations()
                    return registration.activation_key
        
        # Create new registration
        activation_key = self.generate_activation_key(website_url)
        registration = WebsiteRegistration(
            website_url=website_url,
            domain=domain,
            registration_date=datetime.now(),
            activation_key=activation_key,
            status="active",
            metadata=metadata or {}
        )
        
        self.activations[activation_key] = registration
        self.save_activations()
        
        logger.info(f"Website registered for NeuralFort: {website_url} (Key: {activation_key[:8]}...)")
        return activation_key
    
    def verify_activation(self, activation_key: str) -> bool:
        """Verify if activation key is valid"""
        if activation_key not in self.activations:
            return False
        
        registration = self.activations[activation_key]
        
        # Check if expired (1 year validity)
        if datetime.now() - registration.registration_date > timedelta(days=365):
            registration.status = "expired"
            self.save_activations()
            return False
        
        return registration.status == "active"
    
    def get_registration_info(self, activation_key: str) -> Optional[WebsiteRegistration]:
        """Get registration information for an activation key"""
        return self.activations.get(activation_key)
    
    def extract_domain(self, website_url: str) -> str:
        """Extract domain from website URL"""
        from urllib.parse import urlparse
        
        # Add protocol if missing
        if not website_url.startswith(('http://', 'https://')):
            website_url = f'https://{website_url}'
        
        parsed = urlparse(website_url)
        return parsed.netloc

class InfrastructureMonitor:
    """Real-time infrastructure monitoring and metrics collection"""
    
    def __init__(self, metrics_history_size: int = 1000):
        self.metrics_history = deque(maxlen=metrics_history_size)
        self.monitoring_active = False
        self.monitor_thread = None
        self.metrics_lock = threading.Lock()
        
        # System thresholds
        self.thresholds = {
            SystemComponent.CPU: {"min": 0, "max": 85, "unit": "%"},
            SystemComponent.MEMORY: {"min": 0, "max": 80, "unit": "%"},
            SystemComponent.DISK: {"min": 0, "max": 90, "unit": "%"},
            SystemComponent.NETWORK: {"min": 0, "max": 1000, "unit": "MB/s"},
        }
    
    def start_monitoring(self):
        """Start real-time monitoring"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Infrastructure monitoring started")
    
    def stop_monitoring(self):
        """Stop real-time monitoring"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Infrastructure monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                metrics = self.collect_system_metrics()
                with self.metrics_lock:
                    self.metrics_history.extend(metrics)
                
                time.sleep(5)  # Collect metrics every 5 seconds
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(10)  # Wait longer on error
    
    def collect_system_metrics(self) -> List[SystemMetrics]:
        """Collect current system metrics"""
        metrics = []
        timestamp = datetime.now()
        
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        
        metrics.append(SystemMetrics(
            timestamp=timestamp,
            component=SystemComponent.CPU,
            metric_name="usage_percent",
            value=cpu_percent,
            threshold_min=self.thresholds[SystemComponent.CPU]["min"],
            threshold_max=self.thresholds[SystemComponent.CPU]["max"],
            unit="%"
        ))
        
        # Memory metrics
        memory = psutil.virtual_memory()
        metrics.append(SystemMetrics(
            timestamp=timestamp,
            component=SystemComponent.MEMORY,
            metric_name="usage_percent",
            value=memory.percent,
            threshold_min=self.thresholds[SystemComponent.MEMORY]["min"],
            threshold_max=self.thresholds[SystemComponent.MEMORY]["max"],
            unit="%"
        ))
        
        # Disk metrics
        disk_usage = psutil.disk_usage('/')
        disk_percent = (disk_usage.used / disk_usage.total) * 100
        metrics.append(SystemMetrics(
            timestamp=timestamp,
            component=SystemComponent.DISK,
            metric_name="usage_percent",
            value=disk_percent,
            threshold_min=self.thresholds[SystemComponent.DISK]["min"],
            threshold_max=self.thresholds[SystemComponent.DISK]["max"],
            unit="%"
        ))
        
        # Network metrics
        net_io = psutil.net_io_counters()
        metrics.append(SystemMetrics(
            timestamp=timestamp,
            component=SystemComponent.NETWORK,
            metric_name="bytes_sent",
            value=net_io.bytes_sent,
            unit="bytes"
        ))
        
        metrics.append(SystemMetrics(
            timestamp=timestamp,
            component=SystemComponent.NETWORK,
            metric_name="bytes_recv",
            value=net_io.bytes_recv,
            unit="bytes"
        ))
        
        # Process metrics
        process_count = len(psutil.pids())
        metrics.append(SystemMetrics(
            timestamp=timestamp,
            component=SystemComponent.PROCESS,
            metric_name="count",
            value=process_count,
            unit="processes"
        ))
        
        return metrics
    
    def get_recent_metrics(self, component: SystemComponent = None, 
                          minutes: int = 5) -> List[SystemMetrics]:
        """Get recent metrics, optionally filtered by component"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        with self.metrics_lock:
            recent_metrics = [
                metric for metric in self.metrics_history
                if metric.timestamp >= cutoff_time
            ]
        
        if component:
            recent_metrics = [
                metric for metric in recent_metrics
                if metric.component == component
            ]
        
        return recent_metrics
    
    def get_system_health_score(self) -> float:
        """Calculate overall system health score (0-100)"""
        recent_metrics = self.get_recent_metrics(minutes=1)
        if not recent_metrics:
            return 0.0
        
        health_scores = []
        
        for component in SystemComponent:
            component_metrics = [m for m in recent_metrics if m.component == component]
            if not component_metrics:
                continue
            
            # Calculate health based on threshold violations
            violations = 0
            total_checks = 0
            
            for metric in component_metrics:
                if metric.threshold_max is not None:
                    total_checks += 1
                    if metric.value > metric.threshold_max:
                        violations += 1
                
                if metric.threshold_min is not None:
                    total_checks += 1
                    if metric.value < metric.threshold_min:
                        violations += 1
            
            if total_checks > 0:
                component_health = (1 - (violations / total_checks)) * 100
                health_scores.append(component_health)
        
        return sum(health_scores) / len(health_scores) if health_scores else 0.0

class AnomalyDetector:
    """ML-powered anomaly detection for infrastructure monitoring"""
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.is_fitted = False
        self.anomaly_history = deque(maxlen=1000)
        
        # Initialize models for each component
        for component in SystemComponent:
            self.models[component] = IsolationForest(
                contamination=0.1,  # Expect 10% anomalies
                random_state=42,
                n_estimators=100
            )
            self.scalers[component] = StandardScaler()
    
    def fit_models(self, historical_data: Dict[SystemComponent, List[SystemMetrics]]):
        """Fit anomaly detection models with historical data"""
        logger.info("Fitting anomaly detection models...")
        
        for component, metrics in historical_data.items():
            if not metrics:
                continue
            
            # Prepare feature matrix
            features = self._extract_features(metrics)
            if len(features) < 10:  # Need minimum data
                continue
            
            # Scale features
            scaled_features = self.scalers[component].fit_transform(features)
            
            # Fit model
            self.models[component].fit(scaled_features)
            logger.info(f"Fitted anomaly model for {component.value}")
        
        self.is_fitted = True
        logger.info("Anomaly detection models fitted successfully")
    
    def _extract_features(self, metrics: List[SystemMetrics]) -> np.ndarray:
        """Extract features from metrics for anomaly detection"""
        if not metrics:
            return np.array([])
        
        # Group by metric name
        metric_groups = defaultdict(list)
        for metric in metrics:
            metric_groups[metric.metric_name].append(metric.value)
        
        # Calculate statistical features
        features = []
        for metric_name, values in metric_groups.items():
            if len(values) > 1:
                features.extend([
                    np.mean(values),
                    np.std(values),
                    np.min(values),
                    np.max(values),
                    np.percentile(values, 25),
                    np.percentile(values, 75)
                ])
            else:
                features.extend([values[0]] * 6)  # Single value features
        
        return np.array(features).reshape(1, -1)
    
    def detect_anomalies(self, current_metrics: List[SystemMetrics]) -> List[AnomalyEvent]:
        """Detect anomalies in current system metrics"""
        if not self.is_fitted:
            logger.warning("Anomaly detection models not fitted yet")
            return []
        
        anomalies = []
        
        # Group metrics by component
        component_metrics = defaultdict(list)
        for metric in current_metrics:
            component_metrics[metric.component].append(metric)
        
        for component, metrics in component_metrics.items():
            if component not in self.models:
                continue
            
            features = self._extract_features(metrics)
            if features.size == 0:
                continue
            
            try:
                # Scale features
                scaled_features = self.scalers[component].transform(features)
                
                # Predict anomaly
                anomaly_score = self.models[component].decision_function(scaled_features)[0]
                is_anomaly = self.models[component].predict(scaled_features)[0] == -1
                
                if is_anomaly:
                    # Determine severity based on anomaly score
                    severity = self._determine_severity(anomaly_score)
                    
                    anomaly = AnomalyEvent(
                        id=f"anomaly_{datetime.now().timestamp()}_{component.value}",
                        timestamp=datetime.now(),
                        component=component,
                        severity=severity,
                        anomaly_score=float(anomaly_score),
                        description=f"Anomalous behavior detected in {component.value}",
                        metrics=metrics,
                        confidence=float(abs(anomaly_score))
                    )
                    
                    anomalies.append(anomaly)
                    self.anomaly_history.append(anomaly)
                    
                    logger.warning(f"Anomaly detected in {component.value}: score={anomaly_score:.3f}")
            
            except Exception as e:
                logger.error(f"Error detecting anomaly for {component.value}: {e}")
        
        return anomalies
    
    def _determine_severity(self, anomaly_score: float) -> ThreatLevel:
        """Determine threat severity based on anomaly score"""
        # IsolationForest: more negative = more anomalous
        if anomaly_score < -0.8:
            return ThreatLevel.CRITICAL
        elif anomaly_score < -0.5:
            return ThreatLevel.HIGH
        elif anomaly_score < -0.2:
            return ThreatLevel.MEDIUM
        else:
            return ThreatLevel.LOW
    
    def predict_failure_probability(self, component: SystemComponent, 
                                  recent_metrics: List[SystemMetrics]) -> float:
        """Predict probability of component failure"""
        if not self.is_fitted or not recent_metrics:
            return 0.0
        
        # Simple failure prediction based on anomaly history and current state
        recent_anomalies = [
            anomaly for anomaly in self.anomaly_history
            if anomaly.component == component
            and datetime.now() - anomaly.timestamp < timedelta(hours=1)
        ]
        
        # Higher probability if more recent anomalies
        base_probability = min(len(recent_anomalies) * 0.2, 0.8)
        
        # Adjust based on current metrics
        threshold_violations = 0
        for metric in recent_metrics:
            if metric.threshold_max and metric.value > metric.threshold_max:
                threshold_violations += 1
        
        violation_factor = min(threshold_violations * 0.1, 0.3)
        
        return min(base_probability + violation_factor, 1.0)

class SelfHealingEngine:
    """Self-healing automation engine"""
    
    def __init__(self):
        self.actions_history = deque(maxlen=500)
        self.healing_strategies = self._initialize_healing_strategies()
        self.success_rates = defaultdict(lambda: {"success": 0, "total": 0})
    
    def _initialize_healing_strategies(self) -> Dict[SystemComponent, List[Dict]]:
        """Initialize healing strategies for each component"""
        return {
            SystemComponent.CPU: [
                {
                    "trigger_severity": ThreatLevel.HIGH,
                    "condition": lambda metrics: any(
                        m.value > 90 for m in metrics if m.metric_name == "usage_percent"
                    ),
                    "action": ActionType.REALLOCATE_RESOURCES,
                    "description": "High CPU usage detected, reallocating resources"
                },
                {
                    "trigger_severity": ThreatLevel.MEDIUM,
                    "condition": lambda metrics: any(
                        m.value > 80 for m in metrics if m.metric_name == "usage_percent"
                    ),
                    "action": ActionType.ALERT_ADMIN,
                    "description": "Elevated CPU usage, alerting administrator"
                }
            ],
            SystemComponent.MEMORY: [
                {
                    "trigger_severity": ThreatLevel.HIGH,
                    "condition": lambda metrics: any(
                        m.value > 85 for m in metrics if m.metric_name == "usage_percent"
                    ),
                    "action": ActionType.REALLOCATE_RESOURCES,
                    "description": "High memory usage, reallocating resources"
                }
            ],
            SystemComponent.DISK: [
                {
                    "trigger_severity": ThreatLevel.CRITICAL,
                    "condition": lambda metrics: any(
                        m.value > 95 for m in metrics if m.metric_name == "usage_percent"
                    ),
                    "action": ActionType.ALERT_ADMIN,
                    "description": "Critical disk space, immediate action required"
                }
            ]
        }
    
    def evaluate_healing_actions(self, anomaly: AnomalyEvent) -> List[HealingAction]:
        """Evaluate and recommend healing actions for detected anomaly"""
        recommended_actions = []
        
        # Get healing strategies for the component
        strategies = self.healing_strategies.get(anomaly.component, [])
        
        for strategy in strategies:
            # Check if severity matches
            if self._severity_meets_threshold(anomaly.severity, strategy["trigger_severity"]):
                # Check if condition is met
                if strategy["condition"](anomaly.metrics):
                    action = HealingAction(
                        id=f"action_{datetime.now().timestamp()}_{strategy['action'].value}",
                        timestamp=datetime.now(),
                        action_type=strategy["action"],
                        target_component=anomaly.component,
                        description=strategy["description"],
                        success=False,  # Will be updated after execution
                        execution_time=0.0
                    )
                    recommended_actions.append(action)
        
        return recommended_actions
    
    def _severity_meets_threshold(self, anomaly_severity: ThreatLevel, 
                                 trigger_severity: ThreatLevel) -> bool:
        """Check if anomaly severity meets action trigger threshold"""
        severity_order = {
            ThreatLevel.LOW: 1,
            ThreatLevel.MEDIUM: 2,
            ThreatLevel.HIGH: 3,
            ThreatLevel.CRITICAL: 4
        }
        
        return severity_order[anomaly_severity] >= severity_order[trigger_severity]
    
    def execute_healing_action(self, action: HealingAction) -> bool:
        """Execute a healing action"""
        start_time = time.time()
        
        try:
            logger.info(f"Executing healing action: {action.description}")
            
            if action.action_type == ActionType.REALLOCATE_RESOURCES:
                success = self._reallocate_resources(action.target_component)
            elif action.action_type == ActionType.RESTART_SERVICE:
                success = self._restart_service(action.target_component)
            elif action.action_type == ActionType.ALERT_ADMIN:
                success = self._alert_administrator(action)
            elif action.action_type == ActionType.LOG_INCIDENT:
                success = self._log_incident(action)
            else:
                success = False
                logger.warning(f"Unknown action type: {action.action_type}")
            
            action.success = success
            action.execution_time = time.time() - start_time
            
            # Update success rates
            self.success_rates[action.action_type]["total"] += 1
            if success:
                self.success_rates[action.action_type]["success"] += 1
            
            self.actions_history.append(action)
            
            logger.info(f"Healing action completed: {action.description} (Success: {success})")
            return success
            
        except Exception as e:
            action.success = False
            action.execution_time = time.time() - start_time
            action.error_message = str(e)
            
            self.actions_history.append(action)
            logger.error(f"Healing action failed: {action.description} - {e}")
            return False
    
    def _reallocate_resources(self, component: SystemComponent) -> bool:
        """Simulate resource reallocation"""
        try:
            # In a real implementation, this would:
            # 1. Analyze current resource usage
            # 2. Identify resource bottlenecks
            # 3. Reallocate CPU/memory/disk resources
            # 4. Verify the reallocation was successful
            
            logger.info(f"Simulating resource reallocation for {component.value}")
            time.sleep(2)  # Simulate operation time
            return True
        except Exception as e:
            logger.error(f"Resource reallocation failed: {e}")
            return False
    
    def _restart_service(self, component: SystemComponent) -> bool:
        """Simulate service restart"""
        try:
            logger.info(f"Simulating service restart for {component.value}")
            time.sleep(3)  # Simulate restart time
            return True
        except Exception as e:
            logger.error(f"Service restart failed: {e}")
            return False
    
    def _alert_administrator(self, action: HealingAction) -> bool:
        """Send alert to system administrator"""
        try:
            # In a real implementation, this would:
            # 1. Send email/SMS notification
            # 2. Create incident ticket
            # 3. Log to monitoring system
            
            logger.warning(f"ADMIN ALERT: {action.description}")
            return True
        except Exception as e:
            logger.error(f"Administrator alert failed: {e}")
            return False
    
    def _log_incident(self, action: HealingAction) -> bool:
        """Log incident for tracking"""
        try:
            incident_data = {
                "timestamp": action.timestamp.isoformat(),
                "action_type": action.action_type.value,
                "component": action.target_component.value,
                "description": action.description,
                "success": action.success,
                "execution_time": action.execution_time
            }
            
            logger.info(f"Incident logged: {json.dumps(incident_data)}")
            return True
        except Exception as e:
            logger.error(f"Incident logging failed: {e}")
            return False
    
    def get_success_rate(self, action_type: ActionType = None) -> float:
        """Get success rate for healing actions"""
        if action_type:
            stats = self.success_rates[action_type]
            return stats["success"] / max(stats["total"], 1)
        else:
            total_success = sum(stats["success"] for stats in self.success_rates.values())
            total_actions = sum(stats["total"] for stats in self.success_rates.values())
            return total_success / max(total_actions, 1)

class NeuralFortLLMCopilot:
    """LLM-powered Copilot for intelligent insights and recommendations"""
    
    def __init__(self):
        self.insights_history = deque(maxlen=100)
        self.recommendation_templates = self._load_recommendation_templates()
    
    def _load_recommendation_templates(self) -> Dict[str, List[str]]:
        """Load recommendation templates for different scenarios"""
        return {
            "high_cpu_usage": [
                "Consider optimizing CPU-intensive processes",
                "Scale horizontally to distribute load",
                "Implement caching to reduce computation",
                "Review and optimize database queries"
            ],
            "high_memory_usage": [
                "Investigate memory leaks in applications",
                "Implement memory pooling strategies",
                "Consider increasing available memory",
                "Optimize data structures and algorithms"
            ],
            "high_disk_usage": [
                "Implement log rotation policies",
                "Clean up temporary files regularly",
                "Consider data archival strategies",
                "Monitor for disk space hogs"
            ],
            "network_anomaly": [
                "Check for unusual network traffic patterns",
                "Investigate potential security threats",
                "Review firewall configurations",
                "Monitor for DDoS attacks"
            ],
            "general_performance": [
                "Implement comprehensive monitoring",
                "Set up automated alerting",
                "Regular performance testing",
                "Capacity planning reviews"
            ]
        }
    
    def generate_insights(self, anomalies: List[AnomalyEvent], 
                         metrics: List[SystemMetrics],
                         healing_actions: List[HealingAction]) -> Dict[str, Any]:
        """Generate intelligent insights using simulated LLM analysis"""
        
        insights = {
            "timestamp": datetime.now().isoformat(),
            "summary": self._generate_summary(anomalies, healing_actions),
            "key_findings": self._generate_key_findings(anomalies, metrics),
            "recommendations": self._generate_recommendations(anomalies, metrics),
            "predictions": self._generate_predictions(anomalies),
            "explainable_analysis": self._generate_explainable_analysis(anomalies, metrics)
        }
        
        self.insights_history.append(insights)
        return insights
    
    def _generate_summary(self, anomalies: List[AnomalyEvent], 
                         healing_actions: List[HealingAction]) -> str:
        """Generate system status summary"""
        
        if not anomalies:
            return "System is operating normally with no detected anomalies."
        
        critical_count = sum(1 for a in anomalies if a.severity == ThreatLevel.CRITICAL)
        high_count = sum(1 for a in anomalies if a.severity == ThreatLevel.HIGH)
        
        summary = f"Detected {len(anomalies)} anomalies in the last period. "
        
        if critical_count > 0:
            summary += f"{critical_count} critical issues require immediate attention. "
        if high_count > 0:
            summary += f"{high_count} high-priority anomalies detected. "
        
        if healing_actions:
            successful_actions = sum(1 for a in healing_actions if a.success)
            summary += f"Self-healing system executed {len(healing_actions)} actions with {successful_actions} successes."
        
        return summary
    
    def _generate_key_findings(self, anomalies: List[AnomalyEvent], 
                              metrics: List[SystemMetrics]) -> List[str]:
        """Generate key findings from analysis"""
        findings = []
        
        # Component-specific findings
        component_issues = defaultdict(list)
        for anomaly in anomalies:
            component_issues[anomaly.component].append(anomaly)
        
        for component, component_anomalies in component_issues.items():
            if len(component_anomalies) > 3:
                findings.append(f"{component.value.upper()} shows persistent anomalous behavior ({len(component_anomalies)} incidents)")
            elif len(component_anomalies) > 1:
                findings.append(f"{component.value.upper()} has recurring anomalies that may indicate developing issues")
        
        # Performance trend findings
        if metrics:
            recent_metrics = [m for m in metrics if datetime.now() - m.timestamp < timedelta(minutes=15)]
            
            # Check for threshold violations
            violations = defaultdict(int)
            for metric in recent_metrics:
                if metric.threshold_max and metric.value > metric.threshold_max:
                    violations[metric.component] += 1
            
            for component, count in violations.items():
                if count > 5:
                    findings.append(f"{component.value.upper()} consistently exceeding operational thresholds")
        
        if not findings:
            findings.append("No significant patterns detected in current anomalies")
        
        return findings[:5]  # Limit to top 5 findings
    
    def _generate_recommendations(self, anomalies: List[AnomalyEvent], 
                                 metrics: List[SystemMetrics]) -> List[Dict[str, Any]]:
        """Generate specific recommendations"""
        recommendations = []
        
        # Analyze component issues
        component_issues = defaultdict(list)
        for anomaly in anomalies:
            component_issues[anomaly.component].append(anomaly)
        
        for component, component_anomalies in component_issues.items():
            # Get template recommendations
            template_key = self._get_recommendation_template_key(component, component_anomalies)
            templates = self.recommendation_templates.get(template_key, [])
            
            for template in templates[:3]:  # Limit recommendations
                priority = "high" if len(component_anomalies) > 2 else "medium"
                recommendations.append({
                    "category": template_key,
                    "priority": priority,
                    "description": template,
                    "estimated_impact": self._estimate_impact(template),
                    "implementation_complexity": self._estimate_complexity(template)
                })
        
        # Add general recommendations if few specific ones
        if len(recommendations) < 3:
            general_templates = self.recommendation_templates["general_performance"]
            for template in general_templates[:2]:
                recommendations.append({
                    "category": "general_performance",
                    "priority": "medium",
                    "description": template,
                    "estimated_impact": "medium",
                    "implementation_complexity": "low"
                })
        
        return recommendations[:8]  # Limit total recommendations
    
    def _get_recommendation_template_key(self, component: SystemComponent, 
                                       anomalies: List[AnomalyEvent]) -> str:
        """Determine recommendation template key based on component and anomalies"""
        if component == SystemComponent.CPU:
            return "high_cpu_usage"
        elif component == SystemComponent.MEMORY:
            return "high_memory_usage"
        elif component == SystemComponent.DISK:
            return "high_disk_usage"
        elif component == SystemComponent.NETWORK:
            return "network_anomaly"
        else:
            return "general_performance"
    
    def _estimate_impact(self, recommendation: str) -> str:
        """Estimate impact of recommendation"""
        high_impact_keywords = ["scale", "optimize", "implement caching", "memory pooling"]
        medium_impact_keywords = ["monitor", "review", "clean up", "testing"]
        
        recommendation_lower = recommendation.lower()
        
        if any(keyword in recommendation_lower for keyword in high_impact_keywords):
            return "high"
        elif any(keyword in recommendation_lower for keyword in medium_impact_keywords):
            return "medium"
        else:
            return "low"
    
    def _estimate_complexity(self, recommendation: str) -> str:
        """Estimate implementation complexity"""
        high_complexity_keywords = ["scale", "federated learning", "blockchain", "distributed"]
        medium_complexity_keywords = ["implement", "optimize", "pooling", "archival"]
        
        recommendation_lower = recommendation.lower()
        
        if any(keyword in recommendation_lower for keyword in high_complexity_keywords):
            return "high"
        elif any(keyword in recommendation_lower for keyword in medium_complexity_keywords):
            return "medium"
        else:
            return "low"
    
    def _generate_predictions(self, anomalies: List[AnomalyEvent]) -> Dict[str, Any]:
        """Generate predictions based on current anomalies"""
        predictions = {
            "failure_probability": 0.0,
            "time_to_failure": None,
            "affected_components": [],
            "confidence": 0.0
        }
        
        if not anomalies:
            return predictions
        
        # Calculate failure probability based on recent anomalies
        recent_anomalies = [
            a for a in anomalies 
            if datetime.now() - a.timestamp < timedelta(hours=2)
        ]
        
        if recent_anomalies:
            # Simple failure prediction model
            critical_count = sum(1 for a in recent_anomalies if a.severity == ThreatLevel.CRITICAL)
            high_count = sum(1 for a in recent_anomalies if a.severity == ThreatLevel.HIGH)
            
            failure_probability = min(
                (critical_count * 0.4 + high_count * 0.2 + len(recent_anomalies) * 0.05),
                0.95
            )
            
            predictions["failure_probability"] = failure_probability
            predictions["confidence"] = min(failure_probability + 0.1, 1.0)
            
            # Estimate time to failure (simplified)
            if critical_count > 0:
                predictions["time_to_failure"] = "30-60 minutes"
            elif high_count > 2:
                predictions["time_to_failure"] = "2-4 hours"
            else:
                predictions["time_to_failure"] = "4-8 hours"
            
            # Identify affected components
            affected_components = list(set(a.component.value for a in recent_anomalies))
            predictions["affected_components"] = affected_components
        
        return predictions
    
    def _generate_explainable_analysis(self, anomalies: List[AnomalyEvent], 
                                     metrics: List[SystemMetrics]) -> Dict[str, Any]:
        """Generate explainable AI analysis"""
        analysis = {
            "methodology": "Isolation Forest anomaly detection with threshold-based validation",
            "data_sources": ["System metrics", "Performance counters", "Threshold violations"],
            "confidence_factors": [],
            "limitations": []
        }
        
        # Confidence factors
        if len(anomalies) > 5:
            analysis["confidence_factors"].append("Large sample size improves detection accuracy")
        
        if metrics:
            recent_data_points = len([m for m in metrics if 
                                    datetime.now() - m.timestamp < timedelta(minutes=10)])
            if recent_data_points > 20:
                analysis["confidence_factors"].append("High-frequency data collection ensures timely detection")
        
        # Limitations
        analysis["limitations"] = [
            "Anomaly detection requires sufficient historical data for accurate modeling",
            "Seasonal patterns and business cycles may affect detection accuracy",
            "Hardware-specific anomalies may require custom thresholds",
            "Network anomalies can be influenced by external factors beyond system control"
        ]
        
        return analysis

class SecurityKnowledgeBase:
    """Self-made security knowledge base with simple retrieval for chatbot."""

    def __init__(self, kb_path: Optional[str] = None):
        base_dir = os.path.dirname(os.path.dirname(__file__))
        self.kb_path = kb_path or os.path.join(base_dir, "data", "security_precautions.json")
        self.kb_dir = os.path.join(base_dir, "data", "copilot_kb")
        self.entries: List[Dict[str, Any]] = []
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.matrix = None
        self.st_model = None
        self.embeddings = None
        self._load_and_index()

    def _load_and_index(self):
        try:
            loaded_entries: List[Dict[str, Any]] = []
            # Load base KB file
            if os.path.exists(self.kb_path):
                try:
                    with open(self.kb_path, "r", encoding="utf-8") as f:
                        base_entries = json.load(f)
                        if isinstance(base_entries, list):
                            loaded_entries.extend(base_entries)
                        else:
                            logger.warning("Base KB file is not a list; skipping")
                except Exception as e:
                    logger.error(f"Failed to load base KB file: {e}")
            else:
                logger.warning(f"Security KB not found at {self.kb_path}")

            # Load any additional KB files from directory
            if os.path.isdir(self.kb_dir):
                for name in os.listdir(self.kb_dir):
                    if not name.lower().endswith(".json"):
                        continue
                    path = os.path.join(self.kb_dir, name)
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            extra_entries = json.load(f)
                            if isinstance(extra_entries, list):
                                loaded_entries.extend(extra_entries)
                            else:
                                logger.warning(f"KB file {name} is not a list; skipping")
                    except Exception as e:
                        logger.error(f"Failed to load KB file {name}: {e}")
            else:
                # Directory not present is fine; creation is optional
                logger.info(f"KB directory not found at {self.kb_dir}; using base KB only")

            self.entries = loaded_entries
            corpus = [self._entry_text(e) for e in self.entries]
            if corpus:
                if _HAS_ST:
                    try:
                        self.st_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
                        import numpy as np
                        self.embeddings = self.st_model.encode(corpus, normalize_embeddings=True)
                    except Exception:
                        self.st_model = None
                        self.embeddings = None
                if self.embeddings is None:
                    self.vectorizer = TfidfVectorizer(stop_words="english")
                    self.matrix = self.vectorizer.fit_transform(corpus)
            else:
                self.vectorizer = None
                self.matrix = None
        except Exception as e:
            logger.error(f"Failed to load/index security KB: {e}")
            self.entries = []
            self.vectorizer = None
            self.matrix = None

    def _entry_text(self, e: Dict[str, Any]) -> str:
        parts = [e.get("title", ""), e.get("description", "")]
        parts += e.get("precautions", [])
        parts += e.get("steps", [])
        parts += e.get("tags", [])
        return " \n ".join([str(p) for p in parts if p])

    def query(self, message: str, top_k: int = 3) -> List[Tuple[Dict[str, Any], float]]:
        if not message:
            return []
        try:
            if self.st_model is not None and self.embeddings is not None:
                q = self.st_model.encode([message], normalize_embeddings=True)
                import numpy as np
                sims = (q @ self.embeddings.T).ravel()
                idx = np.argsort(-sims)[:top_k]
                return [(self.entries[int(i)], float(sims[int(i)])) for i in idx]
            if self.vectorizer and self.matrix is not None:
                q_vec = self.vectorizer.transform([message])
                sims = cosine_similarity(q_vec, self.matrix).ravel()
                idx_scores = sorted(list(enumerate(sims)), key=lambda x: x[1], reverse=True)[:top_k]
                results = [(self.entries[i], float(score)) for i, score in idx_scores]
                return results
            return []
        except Exception as e:
            logger.error(f"KB query failed: {e}")
            return []

    def answer_query(self, message: str, top_k: int = 3) -> Dict[str, Any]:
        matches = self.query(message, top_k=top_k)
        if not matches:
            return {
                "answer": "I couldn't find relevant guidance. Try rephrasing or be more specific.",
                "sources": [],
                "suggested_precautions": []
            }

        combined_precautions: List[str] = []
        combined_steps: List[str] = []
        sources: List[Dict[str, Any]] = []
        for entry, score in matches:
            combined_precautions += entry.get("precautions", [])
            combined_steps += entry.get("steps", [])
            sources.append({
                "id": entry.get("id"),
                "title": entry.get("title"),
                "score": round(score, 4),
                "tags": entry.get("tags", []),
            })

        def dedupe(seq: List[str]) -> List[str]:
            seen = set()
            out = []
            for item in seq:
                if item not in seen:
                    seen.add(item)
                    out.append(item)
            return out

        combined_precautions = dedupe(combined_precautions)[:8]
        combined_steps = dedupe(combined_steps)[:8]

        answer = (
            "Here are security precautions and steps based on your query:\n\n"
            + "Precautions:\n- " + "\n- ".join(combined_precautions) + "\n\n"
            + "Action Steps:\n- " + "\n- ".join(combined_steps)
        )

        return {
            "answer": answer,
            "sources": sources,
            "suggested_precautions": combined_precautions,
            "suggested_steps": combined_steps
        }

from .services.log_service import NVIDIAQwenChatbot

class NeuralFortFramework:
    """Main NeuralFort framework orchestrator"""
    
    def __init__(self, activation_key: str = None):
        self.activation_key = activation_key
        # Auto-activate for local development/deployment ease
        self.is_activated = True
        
        # Core components
        self.activation_manager = WebsiteActivationManager()
        self.infrastructure_monitor = InfrastructureMonitor()
        self.anomaly_detector = AnomalyDetector()
        self.healing_engine = SelfHealingEngine()
        self.llm_copilot = NeuralFortLLMCopilot()
        self.security_kb = SecurityKnowledgeBase()
        self.nvidia_bot = NVIDIAQwenChatbot()
        
        # Uptime and alerts
        self.start_time = datetime.now()
        self.alerts_config = self.infrastructure_monitor.thresholds.copy()
        self.active_alerts = deque(maxlen=50)
        self.framework_state = {
            "status": "active",
            "system_health_score": 100.0,
            "total_anomalies_detected": 0,
            "total_healing_actions": 0,
            "successful_healing_actions": 0,
            "last_update": datetime.now().isoformat()
        }

        # SHAP Explainer
        self.shap_explainer = None
        self._load_shap_explainer()

    def chat_with_copilot(self, message: str) -> Dict[str, Any]:
        """Respond to a chat query using the NVIDIA Qwen API, security KB, and system context."""
        try:
            # 1. Get relevant context from local Knowledge Base
            kb_response = self.security_kb.answer_query(message, top_k=3)
            
            # 2. Get system status context
            health = self.infrastructure_monitor.get_system_health_score()
            anomalies_recent = list(self.anomaly_detector.anomaly_history)[-5:]
            
            # 3. Construct a rich prompt for the NVIDIA LLM
            context_prompt = (
                f"You are SentientBot, an advanced AI security co-pilot. "
                f"Answer the user query based on the provided security knowledge base and system context.\n\n"
                f"User Query: {message}\n\n"
                f"Security KB Context:\n{kb_response['answer']}\n\n"
                f"Current System Status:\n"
                f"- Health Score: {health}/100\n"
            )
            
            if anomalies_recent:
                sev_counts = defaultdict(int)
                for a in anomalies_recent:
                    sev_counts[a.severity.value] += 1
                context_prompt += f"- Recent Anomalies: {dict(sev_counts)}\n"
            
            context_prompt += "\nProvide a professional, technical, and actionable response."

            # 4. Generate response using NVIDIA Qwen
            try:
                ai_answer = self.nvidia_bot.generate_response(context_prompt, stream=False)
                kb_response["answer"] = ai_answer
                kb_response["model"] = self.nvidia_bot.model
            except Exception as e:
                logger.error(f"NVIDIA Chat failed, using KB fallback: {e}")
                kb_response["fallback"] = True

            # 5. Add context metadata
            context_notes = []
            if health < 70:
                context_notes.append("System health is below optimal; prioritize stability hardening.")
            if anomalies_recent:
                context_notes.append("Recent anomalies detected; review logs for lateral movement.")

            if context_notes:
                kb_response["context"] = {
                    "health_score": health,
                    "notes": context_notes
                }
            return kb_response
        except Exception as e:
            logger.error(f"Copilot chat failed: {e}")
            return {
                "answer": "An internal error occurred while processing your query.",
                "sources": [],
                "suggested_precautions": []
            }

    def _load_shap_explainer(self):
        """Load the SHAP explainer."""
        # Skip if SHAP is not installed
        if not _HAS_SHAP:
            logger.warning("SHAP not installed; explainability is disabled.")
            return
        try:
            if self.anomaly_detector.is_fitted:
                # We need to decide which model to use for the explainer.
                # For now, let's use the CPU model as an example.
                model = self.anomaly_detector.models.get(SystemComponent.CPU)
                if model:
                    self.shap_explainer = shap.TreeExplainer(model)
                    logger.info("SHAP explainer loaded successfully for CPU component.")
        except Exception as e:
            logger.error(f"Failed to load SHAP explainer: {e}")

    def get_shap_explanations(self, metrics: List[SystemMetrics]) -> Optional[Dict]:
        """Generate SHAP explanations for the given metrics."""
        if not self.shap_explainer:
            logger.warning("SHAP explainer is not available.")
            return None

        try:
            features = self.anomaly_detector._extract_features(metrics)
            if features.size == 0:
                return None

            scaled_features = self.anomaly_detector.scalers[SystemComponent.CPU].transform(features)
            shap_values = self.shap_explainer.shap_values(scaled_features)

            # For a single prediction, shap_values will be a numpy array.
            # We can convert it to a list for JSON serialization.
            return {
                "shap_values": shap_values.tolist(),
                "base_value": self.shap_explainer.expected_value,
                "feature_names": self._get_feature_names(metrics)
            }
        except Exception as e:
            logger.error(f"Error generating SHAP explanations: {e}")
            return None

    def _get_feature_names(self, metrics: List[SystemMetrics]) -> List[str]:
        """Extract feature names from metrics."""
        metric_groups = defaultdict(list)
        for metric in metrics:
            metric_groups[metric.metric_name].append(metric.value)

        feature_names = []
        for metric_name in metric_groups.keys():
            feature_names.extend([
                f"{metric_name}_mean",
                f"{metric_name}_std",
                f"{metric_name}_min",
                f"{metric_name}_max",
                f"{metric_name}_p25",
                f"{metric_name}_p75"
            ])
        return feature_names

    def _format_uptime(self):
        if not self.start_time:
            return "N/A"
        uptime_delta = datetime.now() - self.start_time
        days = uptime_delta.days
        hours, rem = divmod(uptime_delta.seconds, 3600)
        minutes, seconds = divmod(rem, 60)
        return f"{days}d {hours}h {minutes}m {seconds}s"

    async def activate_framework(self, activation_key: str) -> bool:
        """Activate NeuralFort framework with website-based activation key"""
        try:
            # Reload activations to avoid stale cache when registration occurs post-init
            self.activation_manager.load_activations()
            # Verify activation key
            if not self.activation_manager.verify_activation(activation_key):
                logger.error(f"Invalid activation key: {activation_key[:8]}...")
                return False
            
            self.activation_key = activation_key
            self.is_activated = True
            self.framework_state["status"] = "active"
            self.framework_state["activation_timestamp"] = datetime.now().isoformat()
            self.start_time = datetime.now()
            await self.start_framework_services()
            logger.info(f"NeuralFort Framework activated successfully for domain: {self.activation_info['domain']}")
            return True
        except Exception as e:
            logger.error(f"Error activating framework: {e}")
            return False

    async def start_framework_services(self):
        """Start all framework services"""
        if not self.is_activated:
            logger.error("Framework not activated. Cannot start services.")
            return
        
        try:
            # Start infrastructure monitoring
            self.infrastructure_monitor.start_monitoring()
            
            # Start background tasks
            self.framework_active = True
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
            self.healing_task = asyncio.create_task(self._healing_loop())
            
            logger.info("NeuralFort framework services started")
            
        except Exception as e:
            logger.error(f"Failed to start framework services: {e}")
            self.framework_active = False
    
    async def stop_framework_services(self):
        """Stop all framework services"""
        self.framework_active = False
        
        # Stop infrastructure monitoring
        self.infrastructure_monitor.stop_monitoring()
        
        # Cancel background tasks
        if self.monitoring_task:
            self.monitoring_task.cancel()
        if self.healing_task:
            self.healing_task.cancel()
        
        self.infrastructure_monitor.stop_monitoring()
        self.anomaly_detector.stop_anomaly_detection()
        self.healing_engine.stop_healing_engine()
        self.start_time = None

    async def shutdown_framework(self):
        """Shutdown NeuralFort framework gracefully"""
        logger.info("Shutting down NeuralFort framework...")
        
        await self.stop_framework_services()
        self.is_activated = False
        self.activation_key = None
        self.activation_info = {}
        self.framework_state = {}
        logger.info("NeuralFort framework has been shut down.")

    def get_framework_status(self) -> Dict[str, Any]:
        """Get current framework status and insights"""
        if not self.is_activated:
            return {
                "status": "inactive",
                "message": "Framework not activated. Please provide valid activation key."
            }
        
        uptime_str = self._format_uptime()
        active_alerts_count = len(self.active_alerts)

        # Get recent data for analysis
        recent_anomalies = list(self.anomaly_detector.anomaly_history)[-20:]
        recent_metrics = self.infrastructure_monitor.get_recent_metrics(minutes=5)
        recent_actions = list(self.healing_engine.actions_history)[-10:]
        
        # Generate LLM insights
        insights = self.llm_copilot.generate_insights(
            recent_anomalies, recent_metrics, recent_actions
        )
        
        # Update framework state with current monitoring data
        health_score = self.infrastructure_monitor.get_system_health_score()
        self.framework_state.update({
            "activation_status": "active" if self.is_activated else "inactive",
            "healing_success_rate": self.healing_engine.get_success_rate(),
            "total_anomalies": len(self.anomaly_detector.anomaly_history),
            "recent_anomalies": len(recent_anomalies),
            "recent_healing_actions": len(recent_actions),
            "system_health_score": health_score,
            "total_anomalies_detected": len(self.anomaly_detector.anomaly_history),
            "total_healing_actions": len(self.healing_engine.actions_history),
            "successful_healing_actions": sum(1 for a in self.healing_engine.actions_history if a.success),
            "last_update": datetime.now().isoformat()
        })
        
        return {
            "status": "active",
            "framework_state": self.framework_state,
            "system_health": {
                "score": self.framework_state["system_health_score"],
                "status": self._get_health_status(self.framework_state["system_health_score"]),
                "last_updated": self.framework_state["last_update"]
            },
            "anomaly_detection": {
                "total_detected": self.framework_state["total_anomalies_detected"],
                "recent_count": len(recent_anomalies),
                "models_fitted": self.anomaly_detector.is_fitted
            },
            "self_healing": {
                "total_actions": self.framework_state["total_healing_actions"],
                "successful_actions": self.framework_state["successful_healing_actions"],
                "success_rate": self.framework_state.get("healing_success_rate", 0.0)
            },
            "llm_insights": insights,
            "activation_info": self._get_activation_info()
        }
    
    def _get_health_status(self, health_score: float) -> str:
        """Get health status description"""
        if health_score >= 90:
            return "Excellent"
        elif health_score >= 80:
            return "Good"
        elif health_score >= 70:
            return "Fair"
        elif health_score >= 60:
            return "Poor"
        else:
            return "Critical"
    
    def _get_activation_info(self) -> Dict[str, Any]:
        """Get activation information"""
        if not self.is_activated:
            return {"status": "inactive"}
        
        registration = self.activation_manager.get_registration_info(self.activation_key)
        if registration:
            return {
                "status": "active" if self.is_activated else "inactive",
                "website_url": registration.website_url,
                "domain": registration.domain,
                "registered_since": registration.registration_date,
                "days_remaining": (registration.registration_date + timedelta(days=365) - datetime.now()).days
            }
        
        return {"status": "unknown"}
    
    async def shutdown_framework(self):
        """Shutdown NeuralFort framework gracefully"""
        logger.info("Shutting down NeuralFort framework...")
        
        await self.stop_framework_services()
        self.is_activated = False
        
        logger.info("NeuralFort framework shutdown complete")

# Global NeuralFort instance
neuralfort_framework = None

def get_neuralfort_framework() -> NeuralFortFramework:
    """Get or create global NeuralFort framework instance"""
    global neuralfort_framework
    if neuralfort_framework is None:
        neuralfort_framework = NeuralFortFramework()
    return neuralfort_framework

# Example usage and testing
if __name__ == "__main__":
    # Test website activation
    async def test_neuralfort():
        # Create framework instance
        framework = get_neuralfort_framework()
        
        # Test website registration
        activation_manager = WebsiteActivationManager()
        activation_key = activation_manager.register_website("https://example.com")
        print(f"Generated activation key: {activation_key}")
        
        # Activate framework
        success = await framework.activate_framework(activation_key)
        print(f"Framework activation: {'Success' if success else 'Failed'}")
        
        if success:
            # Run for a short time to collect some data
            await asyncio.sleep(30)
            
            # Get framework status
            status = framework.get_framework_status()
            print(f"Framework status: {json.dumps(status, indent=2, default=str)}")
            
            # Shutdown
            await framework.shutdown_framework()
    
    # Run test
    asyncio.run(test_neuralfort())
