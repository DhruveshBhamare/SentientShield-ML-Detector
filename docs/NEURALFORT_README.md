# NeuralFort - AI-Based Intelligent Infrastructure Resilience Framework

## 🧠 Overview

NeuralFort is an advanced AI-driven framework designed to enhance the reliability, stability, and self-healing capabilities of digital infrastructure. It continuously monitors system behavior, detects irregular patterns, predicts potential failures, and autonomously performs recovery actions — ensuring uninterrupted system performance and reduced downtime.

## 🚀 Key Features

### 🤖 AI-Powered Intelligence
- **Machine Learning Models**: XGBoost, LSTM, GRU for anomaly detection and prediction
- **Large Language Model Integration**: LLM-powered Copilot for intelligent insights
- **Adaptive Learning**: Continuously improves performance through historical data feedback
- **Explainable AI**: Provides transparency on why certain actions were taken

### 🔧 Self-Healing Automation
- **Automated Recovery**: Executes corrective actions like restarting services, reallocating resources
- **Predictive Analytics**: Uses AI forecasting to prevent failures before they occur
- **Real-Time Monitoring**: Continuously gathers metrics (CPU, memory, disk, network, processes)
- **Risk Assessment**: Multi-factor risk calculation with ML confidence scoring

### 🌐 Website-Based Activation
- **Secure Registration**: Website-based activation system with unique keys
- **Access Control**: Framework only operates after valid website registration
- **License Management**: Activation key verification and validation

### 📊 Unified Dashboard
- **Real-Time Visualization**: Interactive charts for metrics and anomalies
- **Threat Intelligence**: Comprehensive threat detection and analysis
- **Healing Actions**: Track automated recovery actions and success rates
- **LLM Insights**: AI-generated recommendations and predictions

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    NeuralFort Framework                     │
├─────────────────────────────────────────────────────────────┤
│  Website Activation Manager  │  Infrastructure Monitor    │
│  • Registration System       │  • CPU/Memory Monitoring   │
│  • Key Generation           │  • Disk/Network Tracking   │
│  • License Validation       │  • Process Monitoring       │
├─────────────────────────────┼─────────────────────────────┤
│  Anomaly Detector           │  Self-Healing Engine       │
│  • Isolation Forest ML      │  • Automated Recovery       │
│  • Real-Time Detection      │  • Predictive Actions       │
│  • Severity Assessment      │  • Success Rate Tracking    │
├─────────────────────────────┼─────────────────────────────┤
│  NeuralFort LLM Copilot     │  Framework Orchestrator     │
│  • Intelligent Insights     │  • Lifecycle Management     │
│  • Recommendations          │  • Service Coordination     │
│  • Predictive Analysis      │  • Status Monitoring        │
└─────────────────────────────────────────────────────────────┘
```

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.8+
- FastAPI
- scikit-learn
- psutil
- requests

### Quick Start

1. **Start the API Server**
   ```bash
   cd api
   python main.py
   ```

2. **Test the Framework**
   ```bash
   python test_neuralfort.py
   ```

3. **Access Dashboards**
   - Main Dashboard: http://localhost:8000/static/dashboard.html
   - NeuralFort Dashboard: http://localhost:8000/static/neuralfort_dashboard.html

## 📋 API Endpoints

### Website Registration & Activation
- `POST /neuralfort/website/register` - Register infrastructure website
- `POST /neuralfort/activate` - Activate framework with key
- `GET /neuralfort/status` - Get framework status

### Monitoring & Analytics
- `GET /neuralfort/metrics` - Get system metrics
- `GET /neuralfort/anomalies` - Get anomaly detection results
- `GET /neuralfort/healing-actions` - Get healing action history

### AI & Insights
- `GET /neuralfort/llm/insights` - Get LLM-generated insights
- `GET /neuralfort/risk-prediction` - Get risk predictions
- `GET /neuralfort/health` - Health check endpoint

### Framework Management
- `POST /neuralfort/start` - Start framework services
- `POST /neuralfort/stop` - Stop framework services
- `POST /neuralfort/restart` - Restart framework

## 🎯 Usage Guide

### Step 1: Website Registration
```python
import requests

# Register your infrastructure website
response = requests.post("http://localhost:8000/neuralfort/website/register", json={
    "website_name": "my-infrastructure.com",
    "website_url": "https://my-infrastructure.com",
    "owner_email": "admin@my-infrastructure.com"
})

activation_key = response.json()["activation_key"]
```

### Step 2: Framework Activation
```python
# Activate the framework
response = requests.post("http://localhost:8000/neuralfort/activate", json={
    "website_name": "my-infrastructure.com",
    "activation_key": activation_key
})
```

### Step 3: Monitor Your Infrastructure
```python
# Get real-time metrics
metrics = requests.get("http://localhost:8000/neuralfort/metrics").json()

# Get AI insights
insights = requests.get("http://localhost:8000/neuralfort/llm/insights").json()

# Check framework status
status = requests.get("http://localhost:8000/neuralfort/status").json()
```

## 🔍 Key Metrics

### System Health Indicators
- **CPU Usage**: Real-time CPU utilization
- **Memory Usage**: RAM consumption tracking
- **Disk Usage**: Storage space monitoring
- **Network Activity**: Network I/O statistics

### AI/ML Metrics
- **Anomaly Detection Rate**: ML model detection accuracy
- **False Positive Rate**: Incorrect anomaly classifications
- **Healing Success Rate**: Automated recovery effectiveness
- **LLM Confidence**: AI insight reliability scoring

### Risk Assessment
- **Security Score**: Overall security posture (0-100)
- **Risk Level**: Categorized risk (low/medium/high/critical)
- **Threat Likelihood**: ML-predicted threat probability
- **Impact Assessment**: Potential damage evaluation

## 🚀 Advanced Features

### Federated Learning (Future)
- Distributed model training across multiple infrastructure nodes
- Privacy-preserving learning without centralizing sensitive data
- Collaborative threat intelligence sharing

### Blockchain Audit Trail (Future)
- Immutable logging of all AI actions and decisions
- Transparent audit trail for compliance
- Decentralized verification of framework operations

### Edge Computing Integration (Future)
- Low-latency autonomous recovery at the edge
- Distributed anomaly detection
- Local decision-making capabilities

## 🔧 Configuration

### Environment Variables
```bash
# NeuralFort Configuration
NEURALFOT_LOG_LEVEL=INFO
NEURALFORT_MONITORING_INTERVAL=30
NEURALFORT_ANOMALY_THRESHOLD=0.7
NEURALFORT_HEALING_ENABLED=true

# ML Model Settings
NEURALFORT_MODEL_RETRAIN_INTERVAL=86400
NEURALFORT_MODEL_CONFIDENCE_THRESHOLD=0.8

# Website Activation
NEURALFORT_ACTIVATION_REQUIRED=true
NEURALFORT_LICENSE_VALIDATION=true
```

### Custom Thresholds
```python
# Configure monitoring thresholds
thresholds = {
    "cpu_percent": 80.0,
    "memory_percent": 85.0,
    "disk_percent": 90.0,
    "network_errors": 10,
    "process_count": 200
}
```

## 📈 Performance Optimization

### ML Model Optimization
- **Model Selection**: Auto-selection of best performing models
- **Feature Engineering**: Automated feature selection and transformation
- **Hyperparameter Tuning**: Continuous model optimization
- **Ensemble Methods**: Multiple model voting for improved accuracy

### System Performance
- **Asynchronous Processing**: Non-blocking operations
- **Memory Management**: Efficient resource utilization
- **Caching Strategy**: Intelligent data caching
- **Load Balancing**: Distributed processing capabilities

## 🔒 Security Features

### Authentication & Authorization
- **JWT Token-Based Authentication**: Secure API access
- **Role-Based Access Control**: Granular permissions
- **Website-Based Activation**: License validation system
- **Audit Logging**: Comprehensive action logging

### Data Protection
- **Encryption**: Data encryption in transit and at rest
- **Privacy-Preserving**: No sensitive data exposure
- **Secure Communication**: HTTPS/TLS encryption
- **Access Logging**: Detailed access tracking

## 📚 Expand Security Copilot Knowledge Base

The Security Copilot uses a local knowledge base for fast, explainable guidance. You can grow it without code changes:

- Drop JSON files under `data/copilot_kb/` (each file is a list of entries)
- Each entry supports: `id`, `title`, `description`, `precautions[]`, `steps[]`, `tags[]`
- The Copilot automatically merges `data/security_precautions.json` with all files in `data/copilot_kb/` at server start

Example entry:
```json
{
  "id": "kb-201",
  "title": "Zero Trust Network Segmentation",
  "description": "Minimize lateral movement with microsegmentation and strict identity checks.",
  "precautions": [
    "Segment networks by sensitivity",
    "Enforce identity-aware access",
    "Log east-west traffic anomalies"
  ],
  "steps": [
    "Define segmentation policy",
    "Deploy identity proxy",
    "Instrument anomaly alerts"
  ],
  "tags": ["network", "zero-trust", "segmentation"]
}
```

After adding files, restart the server to re-index the KB.

## 📞 Support & Troubleshooting

### Common Issues
1. **Framework Not Starting**: Check activation status and logs
2. **High False Positive Rate**: Adjust anomaly threshold settings
3. **Healing Actions Failing**: Verify system permissions and resources
4. **Dashboard Not Loading**: Check static file serving configuration

### Debug Mode
```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check framework logs
response = requests.get("http://localhost:8000/neuralfort/logs")
```

### Performance Monitoring
```python
# Get performance metrics
perf_metrics = requests.get("http://localhost:8000/neuralfort/performance").json()

# Check resource usage
resources = requests.get("http://localhost:8000/neuralfort/resources").json()
```

## 🌟 Future Roadmap

### Version 2.0 (Coming Soon)
- Multi-cloud infrastructure support
- Advanced predictive analytics
- Enhanced LLM integration
- Mobile dashboard application

### Version 3.0 (In Development)
- Federated learning implementation
- Blockchain audit trail
- Edge computing support
- Advanced automation workflows

## 🤝 Contributing

We welcome contributions to the NeuralFort framework! Please see our contributing guidelines and submit pull requests to our repository.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **SentientShield Team**: For the foundational threat detection framework
- **Open Source Community**: For the amazing libraries and tools
- **AI/ML Research**: For the cutting-edge algorithms and models

---

**NeuralFort** - *Intelligent Infrastructure Resilience Through AI*

Built with ❤️ by the SentientShield Team
---