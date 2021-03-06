

# -*- coding: utf-8 -*-

import konlpy
import nltk
import pickle
import numpy as np
import os, re,copy
import operator
from gensim import corpora, models
import gensim
import math
from collections import Counter
import itertools
import json


WORD_MAX = 15000
WORD_MIN = 500

DATA_PATH = "../real_data/"
#CLIENT_DATA_PATH = DATA_PATH + 'client/'
#RESPONSE_DATA_PATH = DATA_PATH + 'response/'
CLIENT_DATA_PATH = DATA_PATH + 'new_cli/'
RESPONSE_DATA_PATH = DATA_PATH + 'new_res/'


client_list = os.listdir( CLIENT_DATA_PATH )
# file = open(DATA_PATH+'nng_jkb.txt', 'w', encoding='utf-8')

word_dict = {}
document_dict = {}
# with open('Topic_List', 'rb') as handle:
#     word_dict = pickle.load(handle)
with open('word_dic', 'rb') as handle:
    word_dict = pickle.load(handle)
with open('reduced_document_dict','rb') as handle:
    document_dict = pickle.load(handle)

# print( word_dict )


before_bayes = []
idf_dic = {}


count = 0

WORD_MIN = 0.25
WORD_FREQ_MIN = 0.15
WORD_FREQ_MAX = 0.04
dic_len = len(word_dict)
print((sorted(word_dict.items(),key= operator.itemgetter(1), reverse=True))[int(dic_len*WORD_MIN)][1])
calculator_min = (sorted(word_dict.items(),key= operator.itemgetter(1), reverse=True))[int(dic_len*WORD_MIN)][1]
calculator_freq_min = (sorted(word_dict.items(),key= operator.itemgetter(1), reverse=True))[int(dic_len*WORD_FREQ_MIN)][1]
calculator_freq_max = (sorted(word_dict.items(),key= operator.itemgetter(1), reverse=True))[int(dic_len*WORD_FREQ_MAX)][1]
for document in document_dict:
    whole_sentence = document_dict[document]
    tokens = []
    pre_tokens = whole_sentence.split(" ")
    for token in pre_tokens:
        token = token.replace("\n", "")
        token = token.strip()
        try:
            if(word_dict[token] > calculator_min):
                tokens.append(token)
        except:
            continue
    before_bayes.append(tokens)

with open('idf_dic', 'rb') as handle:
   idf_dic= pickle.load(handle)
#print (before_bayes[0][1])
# word weight = word_dict[word]/WORD_MAX
#SIMILAR_TWEETS = before_bayes[]...
new_word_dict = copy.deepcopy(word_dict)
for words in word_dict:
    if word_dict[words] >calculator_freq_min:
        new_word_dict[words] = calculator_freq_min
    if word_dict[words] > calculator_freq_max:
        new_word_dict[words] = calculator_freq_min/4

after_bayes = []
word_score = {}

def idf (word):
    try:
        result = math.log(len(before_bayes)/(1+ idf_dic[word]))
    except:
        result = 1
    return result
count = 0
for candidates in before_bayes:

#    if len(candidates)>5:
#        candidates = candidates[:5]
    group = (list((itertools.combinations(candidates,2))))
    for _,comb in enumerate(group):
        comb1 = comb[0]
        comb2 = comb[1]
        if not comb1 in word_score:
            word_score[comb1] = {}
        if not comb2 in word_score:
            word_score[comb2] = {}
        if not comb2 in word_score[comb1]:
            word_score[comb1][comb2] = (new_word_dict[comb1] + new_word_dict[comb2])*idf(comb1)*idf(comb2)
#            word_score[comb1][comb2] = (1)/(WORD_MAX*2)
        else :
            try:
                word_score[comb1][comb2] += (new_word_dict[comb1] + new_word_dict[comb2])*idf(comb1)*idf(comb2)
#                word_score[comb1][comb2] += (1)/(WORD_MAX*2)
            except:
                print(comb1)
                print(comb2)
                print (word_score[comb1])
                print (word_score[comb1][comb2])
        
        if not comb1 in word_score[comb2] :
            word_score[comb2][comb1] = (new_word_dict[comb1] + new_word_dict[comb2])*idf(comb1)*idf(comb2)
#            word_score[comb2][comb1] = (1)/(WORD_MAX*2)
        else :
            word_score[comb2][comb1] += (new_word_dict[comb1] + new_word_dict[comb2])*idf(comb1)*idf(comb2)
    print ("count: %d"%count)
    count +=1
    if count %1000 == 0:
        pickling = word_score
        with open('bayes', 'wb') as handle:
            pickle.dump(pickling, handle, protocol=pickle.HIGHEST_PROTOCOL)
        
#            word_score[comb2][comb1] += (1)/(WORD_MAX*2)
#    for word in candidates:
#        if word not in word_score:
#            word_score[word] = 0
#    print(list((itertools.combinations(candidates,2))))
#        word_scores[word] =
#print (word_score)
word_score = {}
with open('bayes', 'rb') as handle:
   word_score= pickle.load(handle)
print ("generating meta_tag")
count = 0
for candidates in before_bayes:
    group = (list((itertools.combinations(candidates,2))))
    temp_dic = {}
    for _,comb in enumerate(group):
        comb1 = comb[0]
        comb2 = comb[1]
        if not comb1 in temp_dic:
            temp_dic[comb1] = word_score[comb1][comb2]
        else:
            temp_dic[comb1] += word_score[comb1][comb2]
        if not comb2 in temp_dic:
            temp_dic[comb2] = word_score[comb1][comb2]
        else:
            temp_dic[comb2] += word_score[comb1][comb2]
    print (temp_dic)
    if len(temp_dic)> 6:
        after_bayes.append(sorted(temp_dic.items(), key = operator.itemgetter(1), reverse=True)[:6])
        print(sorted(temp_dic.items(), key = operator.itemgetter(1),reverse=True)[:6])
    else:
        after_bayes.append(temp_dic)
    print ("count: %d"%count)
    count +=1

count = 0
for page_title in client_list:
    with open(CLIENT_DATA_PATH+page_title, 'r', encoding="utf-8") as cli:
        whole_sentence = ''
        for sentence in cli:
            whole_sentence += sentence
    print (whole_sentence)
    print (after_bayes[count])
    count += 1
