# !/usr/bin/env python3
# -*- coding: utf-8 -*-


import codecs
import csv
import os
import re
import time
import pickle

import numpy as np
import pandas as pd
from gensim.models import KeyedVectors
from keras.callbacks import EarlyStopping, ModelCheckpoint
from keras.layers import Dense, Input, LSTM, Embedding, Dropout, \
	Conv2D, MaxPool2D, Reshape
from keras.layers.merge import concatenate, add, multiply
from keras.layers.normalization import BatchNormalization
from keras.models import Model
from keras.preprocessing.sequence import pad_sequences
from keras.preprocessing.text import Tokenizer
from nltk.corpus import stopwords
from nltk.stem import SnowballStemmer

from data_helpers import get_idf_dict, get_extra_features, \
	get_question_freq, get_inter_dict

import helpers
import preprocessing

np.random.seed(888)

########################################
## set directories and parameters
########################################
BASE_DIR = os.path.join('~/', 'input')
DATA_PATH = './data/'
RESULT_PATH = './result/'
TRAIN_DATA_FILE = 'train_simple.csv'
TEST_DATA_FILE = 'test_simple.csv'
H5_PATH = './h5/'
EMBEDDING_FILE = ''

EMBEDDING_DIM = ''
MAX_SEQUENCE_LENGTH = 32
MAX_NB_WORDS = 200000
VALIDATION_SPLIT = 0.1

class0_weight = 1.756
class1_weight = 0.329

act = 'relu'
re_weight = True  # whether to re-weight classes to fit the 17.5% share in test set




def text_to_word_list(text, remove_stopwords=False, stem_words=False):
	# Clean the text, with the option to remove stopwords and to stem words.

	# Convert words to lower case and split them
	text = text.lower().split()

	# Optionally, remove stop words
	if remove_stopwords:
		stops = set(stopwords.words("english"))
		text = [w for w in text if w not in stops]

	text = " ".join(text)

	# Clean the text
	text = re.sub(r"[^A-Za-z0-9^,!./'+-=]", " ", text)
	text = re.sub(r"what's", "what is ", text)
	text = re.sub(r"\'s", " ", text)
	text = re.sub(r"\'ve", " have ", text)
	text = re.sub(r"can't", "cannot ", text)
	text = re.sub(r"n't", " not ", text)
	text = re.sub(r"i'm", "i am ", text)
	text = re.sub(r"\'re", " are ", text)
	text = re.sub(r"\'d", " would ", text)
	text = re.sub(r"\'ll", " will ", text)
	text = re.sub(r",", " ", text)
	text = re.sub(r"\.", " ", text)
	text = re.sub(r"!", " ! ", text)
	text = re.sub(r"\/", " ", text)
	text = re.sub(r"\^", " ^ ", text)
	text = re.sub(r"\+", " + ", text)
	text = re.sub(r"\-", " - ", text)
	text = re.sub(r"\=", " = ", text)
	text = re.sub(r"'", " ", text)
	text = re.sub(r"60k", " 60000 ", text)
	text = re.sub(r":", " : ", text)
	text = re.sub(r" e g ", " eg ", text)
	text = re.sub(r" b g ", " bg ", text)
	text = re.sub(r" u s ", " american ", text)
	text = re.sub(r"\0s", "0", text)
	text = re.sub(r" 9 11 ", "911", text)
	text = re.sub(r"e - mail", "email", text)
	text = re.sub(r"j k", "jk", text)
	text = re.sub(r"\s{2,}", " ", text)

	# Optionally, shorten words to their stems
	if stem_words:
		text = text.split()
		stemmer = SnowballStemmer('english')
		stemmed_words = [stemmer.stem(word) for word in text]
		text = " ".join(stemmed_words)

	# Return a list of words
	return text

def load_texts():

	train_texts_1 = []
	train_texts_2 = []
	train_labels = []

	with open (DATA_PATH+'train_texts_1', 'rb') as fp:
		train_texts_1 = pickle.load(fp)
	with open (DATA_PATH+'train_texts_2', 'rb') as fp:
		train_texts_2 = pickle.load(fp)
	with open (DATA_PATH+'train_labels', 'rb') as fp:
		train_labels = pickle.load(fp)

	print('Found %s texts in train.csv' % len(train_texts_1))

	test_ids = []
	test_texts_1 = []
	test_texts_2 = []

	with open (DATA_PATH+'test_ids', 'rb') as fp:
		test_ids = pickle.load(fp)
	with open (DATA_PATH+'test_texts_1', 'rb') as fp:
		test_texts_1 = pickle.load(fp)
	with open (DATA_PATH+'test_texts_2', 'rb') as fp:
		test_texts_2 = pickle.load(fp)

	print('Found %s texts in test.csv' % len(test_texts_1))

	return train_texts_1, train_texts_2, train_labels, test_ids, test_texts_1, test_texts_2


###
### TEXT & MATRIX
###

########################################
## process texts in datasets
########################################
print('Processing text dataset')

texts_1 = []
texts_2 = []
labels = []

test_texts_1 = []
test_texts_2 = []
test_ids = []

texts_1, texts_2, labels, test_ids, test_texts_1, test_texts_2 = load_texts()

tokenizer = Tokenizer(num_words=MAX_NB_WORDS)
tokenizer.fit_on_texts(texts_1 + texts_2 + test_texts_1 + test_texts_2)

sequences_1 = tokenizer.texts_to_sequences(texts_1)
sequences_2 = tokenizer.texts_to_sequences(texts_2)
test_sequences_1 = tokenizer.texts_to_sequences(test_texts_1)
test_sequences_2 = tokenizer.texts_to_sequences(test_texts_2)

word_index = tokenizer.word_index
print('Found %s unique tokens' % len(word_index))

data_1 = pad_sequences(sequences_1, maxlen=MAX_SEQUENCE_LENGTH, truncating='post')
data_2 = pad_sequences(sequences_2, maxlen=MAX_SEQUENCE_LENGTH, truncating='post')
labels = np.array(labels)
print('Shape of data tensor:', data_1.shape)
print('Shape of label tensor:', labels.shape)

test_data_1 = pad_sequences(test_sequences_1, maxlen=MAX_SEQUENCE_LENGTH, truncating='post')
test_data_2 = pad_sequences(test_sequences_2, maxlen=MAX_SEQUENCE_LENGTH, truncating='post')
test_ids = np.array(test_ids)



########################################
## prepare embeddings
########################################
print('Preparing embedding matrix')

# if(embedding == "glove"):
# 	EMBEDDING_FILE = 'glove.840B.300d.txt'
# 	EMBEDDING_DIM = 300
# elif(embedding == "google"):
# 	EMBEDDING_FILE = 'GoogleNews-vectors-negative300.bin'
# 	EMBEDDING_DIM = 300
# elif(embedding == "twitter"):
# 	EMBEDDING_FILE = 'glove.twitter.27B.200d.txt'
# 	EMBEDDING_DIM = 200
EMBEDDING_FILE = 'glove.twitter.27B.200d.txt'
EMBEDDING_DIM = 200
EMBEDDING_FILE = DATA_PATH+EMBEDDING_FILE

embedding_matrix = ''

nb_words = min(MAX_NB_WORDS, len(word_index)) + 1

glove_vectors, glove_dict = helpers.load_glove_vectors(EMBEDDING_FILE, vocab=set(word_index))
embedding_matrix = helpers.build_initial_embedding_matrix(word_index, glove_dict, glove_vectors, EMBEDDING_DIM)

# if(embedding == 'google'):
# 	word2vec = KeyedVectors.load_word2vec_format(EMBEDDING_FILE,
# 											 binary=True)
# 	embedding_matrix = np.zeros((nb_words, EMBEDDING_DIM))
# 	for word, i in word_index.items():
# 		if word in word2vec.vocab:
# 			embedding_matrix[i] = word2vec.word_vec(word)
# else:
# 	glove_vectors, glove_dict = helpers.load_glove_vectors(EMBEDDING_FILE, vocab=set(word_index))
# 	embedding_matrix = helpers.build_initial_embedding_matrix(word_index, glove_dict, glove_vectors, EMBEDDING_DIM)



########################################
## sample train/validation data
########################################
# np.random.seed(1234)
perm = np.random.permutation(len(data_1))
idx_train = perm[:int(len(data_1) * (1 - VALIDATION_SPLIT))]
idx_val = perm[int(len(data_1) * (1 - VALIDATION_SPLIT)):]

data_1_train = np.vstack((data_1[idx_train], data_2[idx_train]))
data_2_train = np.vstack((data_2[idx_train], data_1[idx_train]))
labels_train = np.concatenate((labels[idx_train], labels[idx_train]))

data_1_val = np.vstack((data_1[idx_val], data_2[idx_val]))
data_2_val = np.vstack((data_2[idx_val], data_1[idx_val]))
labels_val = np.concatenate((labels[idx_val], labels[idx_val]))

weight_val = np.ones(len(labels_val))
if re_weight:
	weight_val *= class1_weight
	weight_val[labels_val == 0] = class0_weight

all_sequences = sequences_1 + sequences_2 + test_sequences_1 + test_sequences_2
idf_dict = get_idf_dict(all_sequences)
question_freq = get_question_freq(all_sequences)
inter_dict = get_inter_dict(sequences_1 + test_sequences_1, sequences_2 + test_sequences_2)

train_features = get_extra_features(data_1_train.tolist(), data_2_train.tolist(), idf_dict,
									embedding_matrix, question_freq, inter_dict)
val_features = get_extra_features(data_1_val.tolist(), data_2_val.tolist(), idf_dict,
								  embedding_matrix, question_freq, inter_dict)
test_features = get_extra_features(test_data_1.tolist(), test_data_2.tolist(), idf_dict,
								   embedding_matrix, question_freq, inter_dict)
extra_feature_num = len(train_features[0])

########################################





def train_model(embedding, mode):

	num_lstm = np.random.randint(175, 275)
	num_dense = np.random.randint(150, 250)
	hidden_size = 150
	rate_drop_lstm = 0.25 + np.random.rand() * 0.25
	rate_drop_dense = 0.25 + np.random.rand() * 0.25

	now = time.localtime()
	current_timestamp = "%04d-%02d-%02d_%02d:%02d:%02d" % (now.tm_year, now.tm_mon, now.tm_mday, now.tm_hour, now.tm_min, now.tm_sec)

	STAMP = '{:s}_{:d}_{:d}_{:.2f}_{:.2f}'.format(embedding, num_lstm, num_dense,
												  rate_drop_lstm, rate_drop_dense)


	########################################
	## define the model structure
	########################################
	embedding_layer = Embedding(nb_words,
								EMBEDDING_DIM,
								weights=[embedding_matrix],
								input_length=MAX_SEQUENCE_LENGTH,
								trainable=False)
	lstm_layer = LSTM(num_lstm, dropout=rate_drop_lstm, recurrent_dropout=rate_drop_lstm)


	#cnn	
	window_size = [1, 2, 3, 4]
	num_filters = 20
	conv_layers = []
	pool_layers = []
	for w in window_size:
		conv_layer = Conv2D(filters=num_filters, kernel_size=(w, EMBEDDING_DIM),
							strides=(1, 1), padding='valid',
							activation='relu')
		pool_layer = MaxPool2D(pool_size=(MAX_SEQUENCE_LENGTH - w + 1, 1), strides=(1, 1),
							   padding='valid')
		conv_layers.append(conv_layer)
		pool_layers.append(pool_layer)

	sequence_1_input = Input(shape=(MAX_SEQUENCE_LENGTH,), dtype='int32')
	embedded_sequences_1 = embedding_layer(sequence_1_input)
	x1 = lstm_layer(embedded_sequences_1)


	#cnn
	embedded_sequences_1 = Reshape((MAX_SEQUENCE_LENGTH, EMBEDDING_DIM, 1))(embedded_sequences_1)
	xs = []
	for i in range(len(conv_layers)):
		x = conv_layers[i](embedded_sequences_1)
		x = pool_layers[i](x)
		x = Reshape((num_filters,))(x)
		xs.append(x)

	sequence_2_input = Input(shape=(MAX_SEQUENCE_LENGTH,), dtype='int32')
	embedded_sequences_2 = embedding_layer(sequence_2_input)
	y1 = lstm_layer(embedded_sequences_2)

	#cnn
	embedded_sequences_2 = Reshape((MAX_SEQUENCE_LENGTH, EMBEDDING_DIM, 1))(embedded_sequences_2)
	ys = []
	for i in range(len(conv_layers)):
		y = conv_layers[i](embedded_sequences_2)
		y = pool_layers[i](y)
		y = Reshape((num_filters,))(y)
		ys.append(y)
	#
	x2 = concatenate(xs)
	y2 = concatenate(ys)

	extra_features = Input(shape=(extra_feature_num,), dtype='float32')

	# merged = concatenate([x1, y1])
	add_distance1 = add([x1, y1])
	mul_distance1 = multiply([x1, y1])
	input0 = concatenate([add_distance1, mul_distance1])
	input1 = Dropout(rate_drop_dense)(input0)
	input1 = BatchNormalization()(input1)
	output1 = Dense(hidden_size, activation='relu')(input1)
	add_distance2 = add([x2, y2])
	mul_distance2 = multiply([x2, y2])
	input2 = concatenate([add_distance2, mul_distance2])
	input3 = Dropout(rate_drop_dense)(input2)
	input3 = BatchNormalization()(input3)
	output3 = Dense(hidden_size, activation='relu')(input3)
	# merged = concatenate([add_distance1, mul_distance1, add_distance2, mul_distance2])

	merged = Dropout(rate_drop_dense)(input0)
	merged = BatchNormalization()(merged)
	merged = concatenate([merged, extra_features])

	merged = Dense(num_dense, activation=act)(merged)
	merged = Dropout(rate_drop_dense)(merged)
	merged = BatchNormalization()(merged)

	merged1 = Dropout(rate_drop_dense)(input2)
	merged1 = BatchNormalization()(merged1)
	merged1 = concatenate([merged1, extra_features])

	merged1 = Dense(num_dense, activation=act)(merged1)
	merged1 = Dropout(rate_drop_dense)(merged1)
	merged1 = BatchNormalization()(merged1)

	output2 = Dense(hidden_size, activation='relu')(merged)
	output4 = Dense(hidden_size, activation='relu')(merged1)
	merged = add([output1, output2])
	merged = BatchNormalization()(merged)
	merged1 = add([output3, output4])
	merged1 = BatchNormalization()(merged1)
	final_merged = concatenate([merged,merged1])
	final_merged = Dropout(rate_drop_dense)(final_merged)
	preds = Dense(1, activation='sigmoid')(final_merged)

	########################################
	## add class weight
	########################################
	if re_weight:
		class_weight = {0: class0_weight, 1: class1_weight}
	else:
		class_weight = None

	########################################
	## train the model
	########################################
	model = Model(inputs=[sequence_1_input, sequence_2_input, extra_features],
				  outputs=preds)
	model.compile(loss='binary_crossentropy',
				  optimizer='nadam',
				  metrics=['acc'])
	# model.summary()
	print(STAMP)

	if(mode == 'train'):
		#
		#	TRAIN SCRIPT
		#
		early_stopping = EarlyStopping(monitor='val_loss', patience=10)
		bst_model_path = H5_PATH+ STAMP + '.h5'
		model_checkpoint = ModelCheckpoint(bst_model_path, save_best_only=True, save_weights_only=True)

		hist = model.fit([data_1_train, data_2_train, train_features], labels_train,
						 validation_data=([data_1_val, data_2_val, val_features], labels_val, weight_val),
						 epochs=10, batch_size=2048, shuffle=True,
						 class_weight=class_weight, callbacks=[early_stopping, model_checkpoint])

		model.load_weights(bst_model_path)
		bst_val_score = min(hist.history['val_loss'])

		print('best val score: {}'.format(bst_val_score))

		########################################
		## make the submission
		########################################
		print('Start making the submission before fine-tuning')

		preds = model.predict([test_data_1, test_data_2, test_features], batch_size=1024, verbose=1)
		preds += model.predict([test_data_2, test_data_1, test_features], batch_size=1024, verbose=1)
		preds /= 2

		submission = pd.DataFrame({'test_id': test_ids, 'is_duplicate': preds.ravel()})
		file_name = '%.4f_' % bst_val_score + STAMP + '_'+ current_timestamp+ '.csv'

		submission.to_csv(RESULT_PATH+file_name, index=False)

	elif(mode == 'test'):

		model.load_weights(H5_PATH+'glove_191_207_0.48_0.27.h5')
		#
		#	TEST SCRIPT
		#
		while(1):

			print('')
			print('##')
			print('## TEST START')
			print('##')
			tsentence1 = input("Enter Sentence 1: ")
			tsentence2 = input("Enter Sentence 2: ")

			tlist1 = []
			tlist2 = []

			tlist1.append(text_to_word_list(tsentence1))
			tlist2.append(text_to_word_list(tsentence2))

			tsequences_1 = tokenizer.texts_to_sequences(tlist1)
			tsequences_2 = tokenizer.texts_to_sequences(tlist2)

			tdata_1 = pad_sequences(tsequences_1, maxlen=MAX_SEQUENCE_LENGTH)
			tdata_2 = pad_sequences(tsequences_2, maxlen=MAX_SEQUENCE_LENGTH)

			tfeatures = get_extra_features(tdata_1.tolist(), tdata_2.tolist(), idf_dict,
								   embedding_matrix, question_freq, inter_dict)

			print('Calculating...')
			preds = model.predict([tdata_1, tdata_2, tfeatures], batch_size=1, verbose=1)
			preds += model.predict([tdata_2, tdata_1, tfeatures], batch_size=1, verbose=1)
			preds /= 2

			result = pd.DataFrame({'similarity': preds.ravel()})
			print(result)
			print('')






# if __name__ == "__main__":

for i in range(10):
	print("%d/10 iteration" % (i+1) )
	train_model('twitter','train')

