####Data Pre-processing########


#0. Preliminaries
import requests
import time
import pandas as pd
import json
from datasets import load_dataset
import nltk
nltk.download('punkt')

tokenizer_reg = nltk.RegexpTokenizer(r"\w+")

#1. Import Data

#TODO - file not exported yet
df = pd.read_csv("data/text_samples.csv")


#2. Generate features

#A. N-grams 
def calculate_ngrams(text):
    return text
    
df = df['text'].apply(calculate_ngrams)



