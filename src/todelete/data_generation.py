# -*- coding: utf-8 -*-
"""FL_1_Data_Generation.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1o_uniDUDg5--eG5abpJ56fPuwe4cWhEW

# 0. Preliminaries
"""

import requests
import time
import pandas as pd
import json
from datasets import load_dataset
import nltk
nltk.download('punkt')

tokenizer_reg = nltk.RegexpTokenizer(r"\w+")

"""#1. Find top AI Authors"""

dataset = load_dataset("jamescalam/ai-arxiv")

sorted(dataset['train']['published']) #2015 to 2023

dataset_sorted = pd.DataFrame(dataset['train'])

dataset_sorted = dataset_sorted.loc[dataset_sorted['published'].astype("int") > 20200000, :]

def retrieve_first_author_list(list_in, position):
    if isinstance(list_in, list):
      index_pos = position-1 if position <= (len(list_in)-1) else (len(list_in)-1)
      first_author = list_in[index_pos]
    else:
      first_author = list_in
    return first_author

dataset_sorted['first_author'] = dataset_sorted['authors'].apply(lambda x: retrieve_first_author_list(x, 1))
dataset_sorted['second_author'] = dataset_sorted['authors'].apply(lambda x: retrieve_first_author_list(x, 2))

dataset_sorted_2023 = dataset_sorted[dataset_sorted['published'].astype("int") > 20230101]

first_authors_2023 = pd.DataFrame(dataset_sorted_2023['first_author'].value_counts().reset_index())
first_authors_2023.columns = ['name', 'first_author_count_2023']
second_authors_2023 = pd.DataFrame(dataset_sorted_2023['second_author'].value_counts().reset_index())
second_authors_2023.columns = ['name', 'second_author_count_2023']
total_authors= pd.DataFrame(dataset_sorted['first_author'].value_counts().reset_index())
total_authors.columns = ['name', 'first_author_count']

total_authors_merged = total_authors.merge(first_authors_2023, on ="name", how = "left").merge(second_authors_2023, on = "name", how = "left").fillna(0)
total_authors_merged['total_2023_count'] = total_authors_merged['first_author_count_2023']+total_authors_merged['second_author_count_2023']

top_four_authors = total_authors_merged.sort_values(by = "total_2023_count").tail(4)

top_publications = dataset_sorted.loc[dataset_sorted['first_author'].isin(top_four_authors['name'].values), :]


"""# 2. Load Author Publication Data"""

#TODO - replace with final dataset
sample_papers = pd.read_csv("/content/Authors_Dataset - Sheet4 (2).csv")

sample_papers_auth = sample_papers[['Author', 'Abstract', 'Introduction', 'Conclusion']].dropna().reset_index(drop = True)

sample_papers_auth['Author'].value_counts()

def divide_chunks(l, n):
    # looping till length l
    for i in range(0, len(l), n):
        yield l[i:i + n]

def split_tokens(Text):
  for char in '-.,\n':
      Text=Text.replace(char,' ')
  Text = Text.lower()
  # split returns a list of words delimited by sequences of whitespace (including tabs, newlines, etc, like re's \s)
  word_list = Text.split()
  return word_list


def chunkify_text(df_in):
  df_in['total_text'] = df_in['Abstract']+df_in['Introduction']+df_in['Conclusion']
  df_in['total_words'] = df_in['total_text'].apply(split_tokens)
  df_in['total_text_chunked'] = df_in['total_words'].apply(lambda x: list(divide_chunks(x, int(512*0.5))))
  #df_in['total_length_chunks'] = df_in['total_text_chunked'].apply(len)
  return df_in

sample_papers_auth_chunked = chunkify_text(sample_papers_auth).reset_index(drop = True)

len(sample_papers_auth_chunked['total_words'][0])/(512*0.7)

sample_papers_auth_chunked['total_length_chunked'] = sample_papers_auth_chunked['total_text_chunked'].apply(len)

sample_papers_auth_chunked[['Author', 'total_length_chunked']].groupby(['Author']).sum()

sample_papers['Author'].value_counts()/5

sample_papers['Author'].value_counts()

"""#3. Generate AI Captions

Ideally, we should probably use the API to do this. But since we do not have it confirmed we can use ChatGPT for now.
"""

def make_GPT_prompt(text):
  return f"{text} - can you write me an abstract, introduction and conclusion for the paper that is summarized above"

sample_papers_GPT = pd.DataFrame(columns=["Author", "Abstract"])
for author in sample_papers_auth["Author"].unique():
    random_pub = sample_papers_auth[sample_papers_auth["Author"] == author][['Author', 'Abstract']].sample(n=1, random_state = 42)
    sample_papers_GPT = pd.concat([sample_papers_GPT, random_pub], ignore_index = True)

sample_papers_GPT['GPT_prompt'] = sample_papers_GPT['Abstract'].apply(make_GPT_prompt)

sample_papers_GPT['Author'].value_counts()

#Here, generate GPT texts and insert them into the CSV

GPT_results = pd.read_csv("/content/GPT_data.csv").head()

GPT_results = chunkify_text(GPT_results).reset_index(drop = True)

GPT_results['total_length_chunked'] = GPT_results['total_text_chunked'].apply(len)

GPT_results['Author'] = "GPT-3.5"

"""#4. Join Datasets"""

joined_data = pd.concat([GPT_results[['Author', 'Abstract', 'Introduction', 'Conclusion']], sample_papers_auth_chunked[['Author', 'Abstract', 'Introduction', 'Conclusion']]])

joined_data

def expand_dataframe(df):
    rows = []
    for index, row in df.iterrows():
        name = row['Author']
        name_list = row['all_chunks']
        for item in name_list:
            rows.append([name, name_list, item])

    new_df = pd.DataFrame(rows, columns=['Author', 'Pub', 'Chunk'])
    return new_df

df_chunksplit = expand_dataframe(joined_data)

#TODO - maybe to reduce this sample so that we get more samples? On the other hand, we would get less info per sample
tok_ratio = 3/4
max_seq =512

def split_text_to_chunks(text):
  list_sequences = []
  list_sentences = nltk.tokenize.sent_tokenize(text)
  #parse through each sentence
  sequence_out = ""
  token_count = 0
  for sentence in list_sentences:
      words = tokenizer_reg.tokenize(sentence)
      if len(words)+token_count < int(max_seq*tok_ratio):
        sequence_out = sequence_out+sentence
        token_count = token_count + len(words)
      else:
        list_sequences.append(sequence_out)
        sequence_out = sentence
        token_count = len(words)

  list_sequences.append(sequence_out)
  return list_sequences

joined_data['abstract_chunked'] = joined_data['Abstract'].apply(split_text_to_chunks)

joined_data['intro_chunked'] = joined_data['Introduction'].apply(split_text_to_chunks)

joined_data['conclusion_chunked'] = joined_data['Conclusion'].apply(split_text_to_chunks)

joined_data['all_chunks'] = joined_data['abstract_chunked']+joined_data['intro_chunked']+joined_data['conclusion_chunked']

joined_data['all_chunks_length'] = joined_data['all_chunks'].apply(len)

joined_data[['Author', 'all_chunks_length']].groupby("Author").sum()

df_chunksplit = expand_dataframe(joined_data)

df_chunksplit['Author'].value_counts()

df_chunksplit.head()