from transformers import AutoModelForSequenceClassification, AutoTokenizer

MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
# Alternative: "facebook/bart-large-mnli" for content classification

class ModelConfig:
    def __init__(self):
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
        self.model = AutoModelForSequenceClassification.from_pretrained(MODEL_ID) 