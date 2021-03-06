

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
TEST_DOC = 20

DATA_PATH = "../real_data/"
#CLIENT_DATA_PATH = DATA_PATH + 'client/'
#RESPONSE_DATA_PATH = DATA_PATH + 'response/'
CLIENT_DATA_PATH = DATA_PATH + 'new_cli/'
RESPONSE_DATA_PATH = DATA_PATH + 'new_res/'


before_bayes = {}

word_dict = {}
document_dict = {}
# with open('Topic_List', 'rb') as handle:
#     word_dict = pickle.load(handle)
with open('word_dic', 'rb') as handle:
    word_dict = pickle.load(handle)
with open('reduced_document_dict','rb') as handle:
    document_dict = pickle.load(handle)


with open('before_bayes', 'rb') as handle:
   before_bayes= pickle.load(handle)
word_score = {}
with open('bayes', 'rb') as handle:
   word_score= pickle.load(handle)
print ("generating meta_tag")
count = 0
after_bayes = {}
for doc_idx in before_bayes:
    candidates = before_bayes[doc_idx]
    if (TEST_DOC<count):
        continue
    group = (list((itertools.combinations(candidates,2))))
    temp_dic = {}
    for _,comb in enumerate(group):
        comb1 = comb[0]
        comb2 = comb[1]
        try:
            if not comb1 in temp_dic:
                temp_dic[comb1] = word_score[comb1][comb2]
            else:
                temp_dic[comb1] += word_score[comb1][comb2]
            if not comb2 in temp_dic:
                temp_dic[comb2] = word_score[comb1][comb2]
            else:
                temp_dic[comb2] += word_score[comb1][comb2]
        except:
            pass 
#            print("no dic")
#            print(comb1)
#            print(comb2)
#    print (temp_dic)
    if len(temp_dic)> 15:
        after_bayes[doc_idx] = (sorted(temp_dic.items(), key = operator.itemgetter(1), reverse=True)[:15])
#        print(sorted(temp_dic.items(), key = operator.itemgetter(1),reverse=True)[:6])
    else:
        after_bayes[doc_idx] = (temp_dic)
    print ("count: %d"%count)
    count +=1

client_list = os.listdir( CLIENT_DATA_PATH )
count = 0
word_relation = []
for doc_idx in after_bayes:
#for page_title in client_list:
    if TEST_DOC < count:
        continue
    
    #with open(CLIENT_DATA_PATH+page_title, 'r', encoding="utf-8") as cli:

    # for grouping
    temp_dic= {}
    word_relation = []
    group = (list(itertools.combinations(after_bayes[doc_idx],2)))
    for _,comb in enumerate(group):
        comb_word = comb[0][0] + '_'+ comb[1][0]
        temp_dic[comb_word] = word_score[comb[0][0]][comb[1][0]]

    
    word_relation = (sorted(temp_dic.items(), key = operator.itemgetter(1), reverse = True)[:3])
    token_relation = []
    reduce_relation = []
    for i in range(len(word_relation)):
        tokens = (word_relation[i][0].split('_'))
        token_relation.append(tokens)
        reduce_relation.append(tokens[0])
        reduce_relation.append(tokens[1])

    reduce_relation = list(set(reduce_relation))
    temp_dic = {}
    for _, comb in enumerate(group):
        first = comb[0][0] 
        second =  comb[1][0]
        comb_word = first + '_'+ second
        if (first in reduce_relation):
            continue
        if (second in reduce_relation):
            continue
        temp_dic[comb_word] = word_score[first][second]
    word_relation_second = (sorted(temp_dic.items(), key = operator.itemgetter(1), reverse = True)[:3])
    token_relation_second = []
    for i in range(len(word_relation_second)):
        tokens = (word_relation_second[i][0].split('_'))
        token_relation_second.append(tokens)

    flag = True
    while (flag == True):
        flag = False
        temp_token = []
        for i in range(len(token_relation)):
            if flag == True:
                break
            temp_token = []
            for j in range(len(token_relation)):
                if i == j :
                    continue
                for a in range(len(token_relation[i])):
                    temp_token.append(token_relation[i][a])
                for b in range(len(token_relation[j])):
                    temp_token.append(token_relation[j][b])
                if ( len(set(temp_token))< len(list(temp_token))):
                    token_relation.append(list(set(temp_token)))
                    if (i > j):
                        del token_relation[i]
                        del token_relation[j]
                    else :
                        del token_relation[j]
                        del token_relation[i]
                    flag = True
                    break

    print (token_relation)
    flag = True
    while (flag == True):
        flag = False
        temp_token = []
        for i in range(len(token_relation_second)):
            if flag == True:
                break
            temp_token = []
            for j in range(len(token_relation_second)):
                if i == j :
                    continue
                for a in range(len(token_relation_second[i])):
                    temp_token.append(token_relation_second[i][a])
                for b in range(len(token_relation_second[j])):
                    temp_token.append(token_relation_second[j][b])
                if ( len(set(temp_token))< len(list(temp_token))):
                    token_relation_second.append(list(set(temp_token)))
                    if (i > j):
                        del token_relation_second[i]
                        del token_relation_second[j]
                    else :
                        del token_relation_second[j]
                        del token_relation_second[i]
                    flag = True
                    break
    print (token_relation_second)
#            print (comb)
#        for candidates in after_bayes[i]:
#            group = (list(itertools.combinations(candidates,2)))
#            temp_dic = {}    
    whole_sentence = document_dict[doc_idx]

    print (whole_sentence)
    print (after_bayes[doc_idx])
    count += 1
