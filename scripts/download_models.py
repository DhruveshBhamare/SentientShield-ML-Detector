import os
import shutil
import os
from transformers import AutoTokenizer, AutoModel, pipeline
from sentence_transformers import SentenceTransformer
from huggingface_hub import snapshot_download

def download_models():
    print("Starting model download process...")
    
    models_dir = os.path.join(os.getcwd(), "models")
    os.makedirs(models_dir, exist_ok=True)

    # 1. DistilBERT
    print("\n[1/4] Downloading DistilBERT...")
    try:
        model_id = "distilbert-base-uncased"
        local_model_path = os.path.join(models_dir, model_id)
        print(f"Downloading {model_id} to {local_model_path}...")
        snapshot_download(repo_id=model_id, local_dir=local_model_path)
        
        tokenizer = AutoTokenizer.from_pretrained(local_model_path)
        model = AutoModel.from_pretrained(local_model_path)
        print("DistilBERT ready.")
    except Exception as e:
        print(f"Error: {e}")

    # 2. BART (Zero-shot)
    print("\n[2/4] Downloading BART (Zero-shot)...")
    try:
        model_id = "facebook/bart-large-mnli"
        local_model_path = os.path.join(models_dir, "facebook", "bart-large-mnli") # Keep structure
        print(f"Downloading {model_id} to {local_model_path}...")
        snapshot_download(repo_id=model_id, local_dir=local_model_path)
        
        clf = pipeline("zero-shot-classification", model=local_model_path)
        print("BART ready.")
    except Exception as e:
        print(f"Error: {e}")

    # 3. MiniLM
    print("\n[3/4] Downloading MiniLM...")
    try:
        model_id = "sentence-transformers/all-MiniLM-L6-v2"
        local_model_path = os.path.join(models_dir, "sentence-transformers", "all-MiniLM-L6-v2")
        print(f"Downloading {model_id} to {local_model_path}...")
        snapshot_download(repo_id=model_id, local_dir=local_model_path)

        SentenceTransformer(local_model_path)
        print("MiniLM ready.")
    except Exception as e:
        print(f"Error: {e}")
    
    # 4. Phishing BERT
    print("\n[4/4] Downloading Phishing BERT...")
    try:
        model_id = "ealvaradob/bert-finetuned-phishing"
        local_model_path = os.path.join(models_dir, "ealvaradob", "bert-finetuned-phishing")
        print(f"Downloading {model_id} to {local_model_path}...")
        snapshot_download(repo_id=model_id, local_dir=local_model_path)
        
        # Verify load
        model = pipeline("text-classification", model=local_model_path)
        print("Phishing BERT ready.")
    except Exception as e:
        print(f"Error downloading Phishing BERT: {e}")

    print("\n--- Model Download Process Complete ---")

if __name__ == "__main__":
    download_models()
