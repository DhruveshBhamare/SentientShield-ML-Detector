import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ProductionSetup")

def setup():
    logger.info("Starting Production Setup for SentientShield...")
    
    # 1. Define required directories
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    data_dir = os.path.join(root_dir, "data")
    artifacts_dir = os.path.join(root_dir, "artifacts")
    models_dir = os.path.join(root_dir, "models")
    logs_dir = os.path.join(root_dir, "logs")
    
    # 2. Create directories
    for d in [data_dir, artifacts_dir, models_dir, logs_dir]:
        if not os.path.exists(d):
            logger.info(f"Creating directory: {d}")
            os.makedirs(d, exist_ok=True)
        else:
            logger.info(f"Directory exists: {d}")

    # 3. Ensure Dataset exists
    dataset_path = os.path.join(data_dir, "web_threat_dataset.csv")
    if not os.path.exists(dataset_path):
        logger.info("Dataset missing. Generating synthetic production dataset...")
        try:
            # Add current directory to path for script execution or module
            sys.path.append(root_dir)
            try:
                from scripts.generate_dataset import generate
            except ImportError:
                from generate_dataset import generate
            
            generate(n_total=50000)
            logger.info("Dataset generated successfully.")
        except Exception as e:
            logger.error(f"Failed to generate dataset: {e}")
            sys.exit(1)
    else:
        logger.info("Dataset already exists.")

    # 4. Ensure Base Model exists (Train if missing)
    model_path = os.path.join(artifacts_dir, "best_model.joblib")
    if not os.path.exists(model_path):
        logger.info("Base model missing. Training initial XGBoost model...")
        try:
            try:
                from scripts.train import main as train_main
            except ImportError:
                from train import main as train_main
                
            train_and_evaluate = train_main # alias for logging consistency if needed
            train_and_evaluate()
            logger.info("Initial model training complete.")
        except Exception as e:
            logger.warning(f"Failed to train initial model: {e}. App will attempt HF download on startup.")
    else:
        logger.info("Base model already exists.")

    logger.info("Production Setup Complete.")

if __name__ == "__main__":
    setup()
