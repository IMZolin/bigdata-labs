import re
import string
import numpy as np

def clean_text(text: str) -> str:
    text = re.sub(r"http\S+|www\S+", "", text)  
    text = re.sub(r"@\w+", "", text)  
    text = re.sub(r"#\w+", "", text)  
    text = text.translate(str.maketrans("", "", string.punctuation))  
    return text.lower().strip()

def prepare_text(text_series, vectorizer):
    return vectorizer.fit_transform(text_series).toarray()
