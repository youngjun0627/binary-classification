# -*- coding: utf-8 -*-
"""dataloader.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1CAhHrMA3Pg403szXpku4vABuSNnooMyA
"""

import torch
import numpy as np
import pandas as pd
from PIL import Image
import glob, os, re
from torch.utils.data.dataset import Dataset
from torch.utils.data import DataLoader
from torchvision import transforms
from albumentations.pytorch.functional import img_to_tensor
import albumentations
from .TRANSFORMS.transform import create_train_transform, create_val_transform
from .TRANSFORMS.masking import horizontal_mask, vertical_mask
import cv2
import random

class ImageDataset(Dataset):
    def __init__(self, root='.', transform = None, mode='binary', use_masking=False):
        super(ImageDataset, self).__init__()
        self.root = root
        self.transform = transform
        self.filenames = glob.glob(os.path.join(self.root, '*.jpg'))
        self.mode = mode
        self.use_masking = use_masking
        self.max_mask_num=3
    def __getitem__(self, index):
        img , label = read_data(self.filenames[index],self.mode)
        if self.transform:
            img = self.transform(image = img)['image']

        if self.use_masking:
            mask_num = random.randrange(1,self.max_mask_num+1)
            mask_prob = 0.25
            rand_val = random.random()
            if rand_val < mask_prob:
                img = horizontal_mask(img, num_masks = mask_num)

            rand_val = random.random()
            if rand_val < mask_prob:
                img = vertical_mask(img, num_masks = mask_num)

        img = img_to_tensor(img)
        return img,label

    def __len__(self):
        return len(self.filenames)

def read_data(fn, mode):
    img = cv2.imread(fn, cv2.IMREAD_COLOR)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    splitUnderbar = lambda x : re.sub(r'^.+/','',x).replace('.jpg','').split()
    label = splitUnderbar(fn)[-1]
    label = convert_label(mode,label[-1])
    return img, label

def convert_label(mode,label):
    if mode=='binary':
        #dic = {'C':1, 'N':0, 'B':0}
        dic = {'d':0,'c':1}
        result = dic[label]
    elif mode=='onehot':
        dic = {'C':[0,1,0], 'N':[1,0,0], 'B':[0,0,1]}
        result = dic[label]
    elif mode=='sparse':
        dic = {'C':1,'N':0,'B':2}
        result = dic[label]
    elif mode=='BCE':
        dic = {'C':[0,1], 'N':[1,0], 'B':[1,0]}
        result = dic[label]
    elif mode == 'test':
        result = -1
    return torch.tensor(result)

def write_result_table(preds, filename, savename):
    pd.DataFrame({'filename':filename, 'pred':preds}).to_csv(savename, index=False)

def Custom_transformer(mode, flip=True, noise=True, clahe=True, cutout=True, normalize = False, resize=True, size=224):
    transformer = None
    if mode == 'train':
        transformer = create_train_transform(flip=flip, noise=noise, clahe=clahe, cutout=cutout, normalize=normalize, resize=resize, size=size)
    elif mode == 'valid':
        transformer = create_val_transform(normalize = normalize, resize = resize, size=size)
    elif mode == 'test':
        transformer = create_val_transform(normalize = normalize, resize = resize, size=size)
    else:
        raise('{} is not supported'.format(mode))
    return transformer

def test_example(mode):
    ### train ###
    if mode=='train':
        mode = 'train'
        flip = True
        noise = True
        clahe = True
        cutout = True
        normalize = True
        resize = True
        use_masking = True
        custom_transformer = Custom_transformer(mode, flip, noise, clahe, cutout, resize)
        train_dataset = ImageDataset(root='../../../../DATA/sample_cancer', transform = custom_transformer,mode='binary', use_masking = use_masking)
        trainloader = DataLoader(train_dataset, batch_size = 1)

    ### validation or test ###
    if mode=='test':
        mode = 'test'
        resize = True
        custom_transformer = Custom_transformer(mode,resize = resize)
        val_dataset = ImageDataset(root='../../../../DATA/sample_cancer', transform = custom_transformer)


        ### write submit_csv ###
        remove_path = lambda x : re.sub(r'^.+/','',x)
        fn = [remove_path(i) for i in val_dataset.filenames]
        write_result_table(preds = np.random.rand(len(val_dataset)),filename=fn, savename = 'testresult.csv')