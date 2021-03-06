

#
# Import packages
# ----------------------------------------------------------------------------
import os
import re
import csv
import codecs
import numpy as np
import pandas as pd
import math
from operator import add

from string import punctuation

from gensim.models import KeyedVectors
from keras.preprocessing.text import Tokenizer
from keras.preprocessing.sequence import pad_sequences
from keras.layers import Dense, Input, LSTM, Embedding, Dropout, Activation, Flatten, Reshape, Merge, Bidirectional
from keras.layers import merge
#from keras.layers.merge import concatenate
from keras.models import Model,Sequential
from keras.layers.normalization import BatchNormalization
from keras.callbacks import EarlyStopping, ModelCheckpoint
from sklearn.utils import class_weight
from keras import losses

import sys
from importlib import reload
import helpers
import pickle

reload(sys)
# Since the default on Python 3 is UTF-8 already, there is no point in leaving those statements in.
# sys.setdefaultencoding('utf-8')


#
# Set directories and parameters
# ----------------------------------------------------------------------------
test_CVID = 0

#BASE_DIR = '../input/'
TRAIN_DATA_FILE = 'sk_train_v2'
MAX_SEQUENCE_LENGTH = 35
MAX_NB_WORDS = 200000
#EMBEDDING_DIM = 300
EMBEDDING_DIM = 300
VALIDATION_SPLIT = 0.1

num_lstm = np.random.randint(75, 100)
num_dense = np.random.randint(50, 75)
rate_drop_lstm = 0.15 + np.random.rand() * 0.25
rate_drop_dense = 0.15 + np.random.rand() * 0.25

act = 'sigmoid'
#act = 'relu'
re_weight = True  # whether to re-weight classes to fit the 17.5% share in test set

STAMP = 'lstm_%d_%d_%.2f_%.2f' % (num_lstm, num_dense, rate_drop_lstm, rate_drop_dense)
STAMP1 = 'attention_%d_%d_%.2f_%.2f' % (num_lstm, num_dense, rate_drop_lstm, rate_drop_dense)
STAMP_merged = 'merged_%d_%d_%.2f_%.2f' % (num_lstm, num_dense, rate_drop_lstm, rate_drop_dense)


#
# Read Training data
# ----------------------------------------------------------------------------
print ("Loading data..")
train_texts = []
train_tags = []
train_labels = []
word_index_pickle = open(TRAIN_DATA_FILE, 'rb')
pickling = pickle.load(word_index_pickle)
x = pickling['word_indices']
y = pickling['y']
tags= pickling['meta_tag']
word_index = 60000 


embedding_matrix = helpers.build_initial_embedding_matrix(word_index, EMBEDDING_DIM)


#
# Prepare embeddings
# ----------------------------------------------------------------------------
print('Preparing embedding matrix')

#nb_words = min(MAX_NB_WORDS, len(word_index)) + 1
nb_words = min(MAX_NB_WORDS, len(word_index))


#
# Sample train/validation data
# ----------------------------------------------------------------------------
np.random.seed(1234)


x_shuffled=[]
y_shuffled=[]
tag_shuffled=[]
result = [0]*len(y[0])
for i in range(len(perm)):
    result = list(map(add, result, y[i]))
#result = list(map (sum, y))
labels_dict = {i:b for i,b in enumerate(result)}
print (result)
print (labels_dict)
#labels_dict = {b:sum(b) for b in y}
#print (labels_dict)
for i in range(len(perm)):
    x_shuffled.append(x[perm[i]])
    y_shuffled.append(y[perm[i]])
    tag_shuffled.append(tags[perm[i])
    
#    if perm[i] > temp:
#        temp = perm[i]
#print (temp)
#print (len(y))
for i in range(len(perm)):
    x_shuffled[i] = x[perm[i]]
    y_shuffled[i] = y[perm[i]]
    tag_shuffled[i] = tags[perm[i]]
print (y_shuffled[0])
data_1_train, data_1_val = x_shuffled[:-2000], x_shuffled[-2000:-1000]
data_2_train, data_2_val = tag_shuffled[:-2000], tag_shuffled[-2000:-1000]
labels_train, labels_val = y_shuffled[:-2000], y_shuffled[-2000:-1000]
data_1_train = np.vstack(data_1_train)
data_1_val = np.vstack(data_1_val)
data_2_train = np.vstack(data_2_train)
data_2_val = np.vstack(data_2_val)
labels_train = np.vstack(labels_train)
labels_val = np.vstack(labels_val)

#
# Define the model structure
# ----------------------------------------------------------------------------
"""embedding_layer = Embedding(nb_words,
                            EMBEDDING_DIM,
                            weights=[embedding_matrix],
                            input_length=MAX_SEQUENCE_LENGTH,
                            trainable=False)
lstm_layer = LSTM(num_lstm, dropout=rate_drop_lstm, recurrent_dropout=rate_drop_lstm)
#lstm_layer = LSTM(num_lstm, dropout=rate_drop_lstm)

sequence_1_input = Input(shape=(MAX_SEQUENCE_LENGTH,), dtype='int32')
embedded_sequences_1 = embedding_layer(sequence_1_input)
x1 = lstm_layer(embedded_sequences_1)

sequence_2_input = Input(shape=(MAX_SEQUENCE_LENGTH,), dtype='int32')
embedded_sequences_2 = embedding_layer(sequence_2_input)
y1 = lstm_layer(embedded_sequences_2)

merged = concatenate([x1, y1])
merged = Dropout(rate_drop_dense)(merged)
merged = BatchNormalization()(merged)

merged = Dense(num_dense, activation=act)(merged)
merged = Dropout(rate_drop_dense)(merged)
merged = BatchNormalization()(merged)

preds = Dense(1, activation='sigmoid')(merged)
#
#"""
#attention
print("build attention")
ques1_enc = Sequential()
ques1_enc.add(Embedding(nb_words,
                            EMBEDDING_DIM,
                            weights=[embedding_matrix],
                            input_length=MAX_SEQUENCE_LENGTH,
                            trainable=True))
ques1_enc.add(Bidirectional(LSTM(num_lstm, return_sequences =True,dropout=rate_drop_lstm, recurrent_dropout=rate_drop_lstm)))
#ques1_enc.add(Dropout(0.3))

ques2_enc = Sequential()
ques2_enc.add(Embedding(nb_words,
                            EMBEDDING_DIM,
                            weights=[embedding_matrix],
                            input_length=MAX_SEQUENCE_LENGTH,
                            trainable=True))
#ques2_enc.add(LSTM(num_lstm, return_sequence=True))
ques2_enc.add(Bidirectional(LSTM(num_lstm,return_sequences=True, dropout=rate_drop_lstm, recurrent_dropout=rate_drop_lstm)))
#ques2_enc.add(Dropout(0.3))

#attention model
attn = Sequential()
attn.add(Merge([ques1_enc,ques2_enc], mode="dot", dot_axes=[1,1]))

attn.add(Flatten())
attn.add(Dense(MAX_SEQUENCE_LENGTH * num_lstm))
attn.add(Reshape((MAX_SEQUENCE_LENGTH, num_lstm)))

#model1 = concatenate([ques1_enc, attn])
#model1 = Dropout(rate_drop_dense)(model1)
#model1 = BatchNormalization()(model1)

#model1 = Dense(num_dense, activation=act)(model1)
#model1 = Dropout(rate_drop_dense)(model1)
#model1 = BatchNormalization()(model1)

#att_preds = Dense(1, activation='sigmoid')(model1)

model1 = Sequential()
"""model2 = Sequential()
model3 = Sequential()
model2.add(Merge([ques1_enc, attn], mode="concat"))
model2.add(BatchNormalization())
model2.add(Dense(MAX_SEQUENCE_LENGTH * num_lstm))
model2.add(Reshape((MAX_SEQUENCE_LENGTH, num_lstm)))
model3.add(Merge([ques2_enc, attn], mode="concat"))
model3.add(Dense(MAX_SEQUENCE_LENGTH * num_lstm))
model3.add(Reshape((MAX_SEQUENCE_LENGTH, num_lstm)))"""
model1.add(Merge([ques1_enc, attn], mode="sum",))
model1.add(Flatten())
#model1.add(Dropout(rate_drop_dense))
#model1.add(BatchNormalization())

#model1.add(Dense(num_dense, activation=act))
#model1.add(Dropout(rate_drop_dense))
#model1.add(BatchNormalization())
model1.add(Dense(1, activation="sigmoid"))
#att_preds = Dense(1, activation='sigmoid')(model1)
#att_preds=model1.add(Dense(1, activation="sigmoid"))
#model1.add(BatchNormalization())

#model1.add(Dense(1))
#model1.add(Activation('sigmoid'))
#att_preds = Dense(1, activation='sigmoid')(model1)
#model1.add(Flatten())
#att_preds=model1.add(Dense(1, activation="sigmoid"))
#att_preds = Dense(1, activation='sigmoid')(merged)
#att_preds = Dense(1, activation='sigmoid')(model1)
#model1.add(Dense(1, activation="softmax"))

#merged_model = Sequential()
#attn.add(Merge([ques1_enc,ques2_enc], mode="dot", dot_axes=[1,1]))
#merged_model = concatenate([preds, att_preds])
#merged_model.add(Merge([preds,att_preds],mode = 'concat'))


#merged_model = Dropout(rate_drop_dense)(merged_model)
#merged_model = BatchNormalization()(merged_model)

#merged_model = Dense(num_dense, activation=act)(merged_model)
#merged_model = Dropout(rate_drop_dense)(merged_model)
#merged_model = BatchNormalization()(merged_model)

#preds = Dense(1, activation='sigmoid')(merged_model)
#merged_model.add(Dense(1))
#merged_model.add(Activation('sigmoid'))

#merged_preds = Dense(1, activation='sigmoid')(merged_model)
#
# Add class weight
# ----------------------------------------------------------------------------
def create_class_weight(labels_dict, mu = 0.15):
    total = sum(labels_dict)
#    total = np.sum(labels_dict.values())
#    keys = list(labels_dict.keys())
    class_weight = dict()
    for key in range(len(labels_dict)):
        score = math.log(mu*total/float(labels_dict[key]))
        class_weight[key] = score if score > 1.0 else 1.0
    return class_weight

if re_weight:
#    class_weight = {0: 1.309028344, 1: 0.472001959, 2: 1, 3:1, 4:1}
#    class_weight = create_class_weight(result)
#    class_weight = class_weight.compute_class_weight('balanced',np.unique(y), y)
    print (class_weight)
#    class_weight = {0: 1, 1: 1, 2: 1, 3:1, 4:1}
else:
    class_weight = None
#
# Train the model
# ----------------------------------------------------------------------------
#model = Model(inputs=[sequence_1_input, sequence_2_input], \
#              outputs=preds)
#model1 = Model(inputs=[sequence_1_input, sequence_2_input], \
#              outputs=att_preds)

#merged_model = Model(inputs=[sequence_1_input, sequence_2_input,sequence_1_input, sequence_2_input], \
 #             outputs=merged_preds)
#merged_model.compile(loss='binary_crossentropy',
#              optimizer='nadam',
#              metrics=['acc'])
#model1.compile(loss='binary_crossentropy',
model1.compile(loss=losses.kullback_leibler_divergence,
              optimizer='nadam',
              metrics=['acc'])
#model.compile(loss='binary_crossentropy',
#              optimizer='nadam',
#              metrics=['acc'])
# model.summary()

early_stopping = EarlyStopping(monitor='val_loss', patience=3)
#bst_model_path = STAMP + '.h5'
bst_model_path1 = STAMP1 + '.h5'
#bst_model_path_merged = STAMP_merged + '.h5'
#model_checkpoint_merged = ModelCheckpoint(bst_model_path_merged, save_best_only=True, save_weights_only=True)
#model_checkpoint = ModelCheckpoint(bst_model_path, save_best_only=True, save_weights_only=True)
model_checkpoint1 = ModelCheckpoint(bst_model_path1, save_best_only=True, save_weights_only=True)


#hist_merged = merged_model.fit([data_1_train, data_2_train,data_1_train, data_2_train], labels_train, \
#                 validation_data=([data_1_val, data_2_val,data_1_train, data_2_train], labels_val, weight_val), \
#                 epochs=20, batch_size=2048, shuffle=True, \
#                 class_weight=class_weight, callbacks=[early_stopping, model_checkpoint_merged])
#merged_model.load_weights(bst_model_path_merged)
#bst_val_score_merged = min(hist_merged.history['val_loss'])

hist1 = model1.fit([data_1_train, data_2_train], labels_train, \
                 validation_data=([data_1_val, data_2_val], labels_val), \
#                 epochs=12, batch_size=1024, shuffle=True, \
                 epochs=12, batch_size=8, shuffle=True, \
                 class_weight='auto', callbacks=[early_stopping, model_checkpoint1])
#model1.load_weights(bst_model_path1)
#bst_val_score1 = min(hist1.history['val_loss'])

#hist = model.fit([data_1_train, data_2_train], labels_train, \
#                 validation_data=([data_1_val, data_2_val], labels_val, weight_val), \
#                 epochs=20, batch_size=2048, shuffle=True, \
#                 class_weight=class_weight, callbacks=[early_stopping, model_checkpoint])

#model.load_weights(bst_model_path)
#bst_val_score = min(hist.history['val_loss'])


#
# Make the submission
# ----------------------------------------------------------------------------
'''print('Start making the submission before fine-tuning')

att_preds = model1.predict([test_data_1, test_data_2], batch_size=8192, verbose=1)
att_preds += model1.predict([test_data_2, test_data_1], batch_size=8192, verbose=1)
att_preds /= 2

submission = pd.DataFrame({'test_id': test_ids, 'is_duplicate': att_preds.ravel()})
submission.to_csv('%.4f_' % (bst_val_score1) + STAMP1 + '.csv', index=False)'''

#submission = pd.DataFrame({'test_id': test_ids, 'is_duplicate': preds.ravel()})
#tm_200_124_0.23_0.36.csv ubmission.to_csv('%.4f_' % (bst_val_score) + STAMP + '.csv', index=False)
