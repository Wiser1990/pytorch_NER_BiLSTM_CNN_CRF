# @Author : bamtercelboo
# @Datetime : 2018/1/30 15:55
# @File : Batch_Iterator.py.py
# @Last Modify Time : 2018/1/30 15:55
# @Contact : bamtercelboo@{gmail.com, 163.com}

"""
    FILE :  Batch_Iterator.py
    FUNCTION : None
"""

import torch
from torch.autograd import Variable
import random

from DataUtils.Common import *
torch.manual_seed(seed_num)
random.seed(seed_num)


class Batch_Features:
    """
    Batch_Features
    """
    def __init__(self):

        self.batch_length = 0
        self.inst = None
        self.word_features = 0
        self.char_features = 0
        self.label_features = 0
        self.sentence_length = []
        self.desorted_indices = None
        self.context_indices = None

    @staticmethod
    def cuda(features):
        """
        :param features:
        :return:
        """
        features.word_features = features.word_features.cuda()
        features.label_features = features.label_features.cuda()
        features.char_features = features.char_features.cuda()
        # features.desorted_indices = features.desorted_indices.cuda()
        features.context_indices = features.context_indices.cuda()


class Iterators:
    """
    Iterators
    """
    def __init__(self, batch_size=None, data=None, operator=None, config=None):
        self.config = config
        self.batch_size = batch_size
        self.data = data
        self.operator = operator
        self.operator_static = None
        self.iterator = []
        self.batch = []
        self.features = []
        self.data_iter = []
        self.max_char_len = config.max_char_len

    def createIterator(self):
        """
        :param batch_size:  batch size
        :param data:  data
        :param operator:
        :param config:
        :return:
        """
        assert isinstance(self.data, list), "ERROR: data must be in list [train_data,dev_data]"
        assert isinstance(self.batch_size, list), "ERROR: batch_size must be in list [16,1,1]"
        for id_data in range(len(self.data)):
            print("*****************    create {} iterator    **************".format(id_data + 1))
            self._convert_word2id(self.data[id_data], self.operator)
            self.features = self._Create_Each_Iterator(insts=self.data[id_data], batch_size=self.batch_size[id_data],
                                                       operator=self.operator)
            self.data_iter.append(self.features)
            self.features = []
        if len(self.data_iter) == 2:
            return self.data_iter[0], self.data_iter[1]
        if len(self.data_iter) == 3:
            return self.data_iter[0], self.data_iter[1], self.data_iter[2]

    @staticmethod
    def _convert_word2id(insts, operator):
        """
        :param insts:
        :param operator:
        :return:
        """
        # print(len(insts))
        # for index_inst, inst in enumerate(insts):
        for inst in insts:
            # copy with the word and pos
            for index in range(inst.words_size):
                word = inst.words[index]
                wordId = operator.word_alphabet.loadWord2idAndId2Word(word)
                # if wordID is None:
                if wordId == -1:
                    wordId = operator.word_unkId
                inst.words_index.append(wordId)

                label = inst.labels[index]
                labelId = operator.label_alphabet.loadWord2idAndId2Word(label)
                inst.label_index.append(labelId)

                char_index = []
                for char in inst.chars[index]:
                    charId = operator.char_alphabet.loadWord2idAndId2Word(char)
                    if charId == -1:
                        charId = operator.char_unkId
                    char_index.append(charId)
                inst.chars_index.append(char_index)

    def _Create_Each_Iterator(self, insts, batch_size, operator):
        """
        :param insts:
        :param batch_size:
        :param operator:
        :return:
        """
        batch = []
        count_inst = 0
        for index, inst in enumerate(insts):
            batch.append(inst)
            count_inst += 1
            # print(batch)
            if len(batch) == batch_size or count_inst == len(insts):
                one_batch = self._Create_Each_Batch(insts=batch, batch_size=batch_size, operator=operator)
                self.features.append(one_batch)
                batch = []
        print("The all data has created iterator.")
        return self.features

    def _Create_Each_Batch(self, insts, batch_size, operator):
        """
        :param insts:
        :param batch_size:
        :param operator:
        :return:
        """
        # print("create one batch......")
        batch_length = len(insts)
        # copy with the max length for padding
        max_word_size = -1
        max_label_size = -1
        sentence_length = []
        for inst in insts:
            sentence_length.append(inst.words_size)
            word_size = inst.words_size
            if word_size > max_word_size:
                max_word_size = word_size

            if len(inst.labels) > max_label_size:
                max_label_size = len(inst.labels)
        assert max_word_size == max_label_size

        # create with the Tensor/Variable
        # word features
        batch_word_features = Variable(torch.zeros(batch_length, max_word_size).type(torch.LongTensor))
        batch_char_features = Variable(torch.zeros(batch_length, max_word_size, self.max_char_len).type(torch.LongTensor))
        batch_label_features = Variable(torch.zeros(batch_length * max_word_size).type(torch.LongTensor))

        for id_inst in range(batch_length):
            inst = insts[id_inst]
            # copy with the word features
            for id_word_index in range(max_word_size):
                if id_word_index < inst.words_size:
                    batch_word_features.data[id_inst][id_word_index] = inst.words_index[id_word_index]
                else:
                    batch_word_features.data[id_inst][id_word_index] = operator.word_paddingId

                if id_word_index < len(inst.label_index):
                    batch_label_features.data[id_inst * max_word_size + id_word_index] = inst.label_index[id_word_index]
                else:
                    batch_label_features.data[id_inst * max_word_size + id_word_index] = operator.label_paddingId
                    # batch_label_features.data[id_inst * max_word_size + id_word_index] = 0

                # char
                max_char_size = len(inst.chars_index[id_word_index]) if id_word_index < inst.words_size else 0
                for id_word_c in range(self.max_char_len):
                    if id_word_c < max_char_size:
                        batch_char_features.data[id_inst][id_word_index][id_word_c] = inst.chars_index[id_word_index][id_word_c]
                    else:
                        batch_char_features.data[id_inst][id_word_index][id_word_c] = operator.char_paddingId
        # print(batch_char_features)
        # prepare for window context feature
        B, T = batch_word_features.size()
        context_indices = self._prepare_winfeature(B, T, wsize=self.config.windows_size)

        # prepare for pack_padded_sequence
        # sorted_inputs_words, sorted_seq_lengths, desorted_indices = self._prepare_pack_padded_sequence(
        #     batch_word_features, sentence_length)
        # print(sorted_seq_lengths)

        # batch
        features = Batch_Features()
        features.batch_length = batch_length
        features.inst = insts
        # features.word_features = sorted_inputs_words
        features.word_features = batch_word_features
        features.char_features = batch_char_features
        features.label_features = batch_label_features
        # features.sentence_length = sorted_seq_lengths
        features.sentence_length = sentence_length
        # features.desorted_indices = desorted_indices
        features.desorted_indices = None
        features.context_indices = context_indices

        if self.config.use_cuda is True:
            features.cuda(features)
        return features

    @staticmethod
    def _prepare_pack_padded_sequence(inputs_words, seq_lengths, descending=True):
        """
        :param inputs_words:
        :param seq_lengths:
        :param descending:
        :return:
        """
        sorted_seq_lengths, indices = torch.sort(torch.LongTensor(seq_lengths), descending=descending)
        _, desorted_indices = torch.sort(indices, descending=False)
        sorted_inputs_words = inputs_words[indices]
        return sorted_inputs_words, sorted_seq_lengths.numpy(), desorted_indices

    @staticmethod
    def _prepare_winfeature(B, T, wsize=5):
        """
        :param B:  batch size
        :param T:  words size
        :param wsize:  windows size
        :return:
        """
        assert (wsize % 2 != 0), "win feature size must be a odd number"
        winfeat = torch.zeros(T, wsize)
        winfeat_batch = torch.zeros(B, T, wsize).type(torch.LongTensor)
        wsizehalf = wsize // 2
        for t in range(T):
            for w in range(-wsizehalf, wsizehalf + 1):
                if (w + t) < 0 or (w + t + 1) > T:
                    winfeat[t][w + wsizehalf] = T
                    continue
                winfeat[t][w + wsizehalf] = w + t
        for b in range(B):
            winfeat_batch[b] = winfeat
        winfeat_batch = Variable(winfeat_batch)
        return winfeat_batch







