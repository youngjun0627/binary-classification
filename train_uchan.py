# -*- coding: utf-8 -*-
"""train_uchan.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1CAhHrMA3Pg403szXpku4vABuSNnooMyA
"""

'''
train_uchan.py
'''
import os
import torch
import torch.nn as nn
import torch.nn.functional as F
from DATALOADER.dataloader import ImageDataset, Custom_transformer, write_result_table
#from UTILS.utils_uchan import LabelSmoothingLoss, GradualWarmupSchedulerV2
from MODELS.model_uchan import build_model, build_newmodel, build_jaydenmodel, build_uchanmodel
from torch.utils.data import DataLoader
from torch.optim import AdamW,SGD, Adam
from torch.optim.lr_scheduler import CosineAnnealingLR, StepLR, ReduceLROnPlateau
#from warmup_scheduler import GradualWarmupScheduler
from tqdm import tqdm
import sklearn
from pytorch_lightning.metrics.functional.classification import auroc
import argparse
import re
import numpy as np
from sklearn.metrics import roc_auc_score

parser = argparse.ArgumentParser(description='learning_cancer')
parser.add_argument('--mode', type=str, default = None, help ='')
parser.add_argument('--name', type = str, default = None, help='')
'''
def weighted_binary_cross_entropy(output,target,weights=None):
    if weights is not None:
        assert len(weights)==2

        loss = weights[1] * (target*torch.log(output)) + weights[0] * ((1-target) * torch.log(1-output))
    else:
        loss = target * torch.log(output) + ((1-target) * torch.log(1-output))
    return torch.neg(torch.mean(loss))
'''
class WeightedBCELoss(nn.BCELoss):
    def __init__(self):
        super(WeightedBCELoss,self).__init__()
        self.weight = torch.tensor([0.695,1.875]).float().cuda()

    def forward(self, output, label):
        batch_weight = self.weight[label.data.view(-1).long()].view_as(label).cuda()
        bce = nn.BCELoss(weight=batch_weight, reduction='mean').cuda()
        loss = bce(output, label)
        return loss

def save_model(model,model_name,epoch):#:, optimizer, scheduler,epoch):
    model_cpu = model.to('cpu')
    state = {
        'model': model_cpu.state_dict()
        #'optimizer' : optimizer.state_dict(),
        #'scheduler': scheduler.state_dict()
    }
    if not (os.path.isdir('./WEIGHTS/uchan_saved_model')):
        os.mkdir('./WEIGHTS/uchan_saved_model')
    torch.save(state, './WEIGHTS/uchan_saved_model/{}_model_{}.pth'.format(model_name,epoch))

def train(args):
    mode = 'train'
    flip = args['flip']
    noise = args['noise']
    clahe = args['clahe']
    cutout = args['cutout']
    normalize = args['normalize']
    resize = args['resize']
    size = args['size']
    normalize = args['normalize']
    use_masking = args['use_masking']
    num_classes = args['num_classes']
    batch_size = args['batch_size']
    epochs = args['epochs']
    pretrained = args['pretrained']
    label_smoothing = args['label_smoothing']
    device = torch.device('cuda')
    model_name = args['model_name']

    custom_transformer = Custom_transformer(mode = mode, flip = flip, noise = noise, clahe = clahe, cutout = cutout, normalize = normalize, resize = resize, size=size) # size default = 224

    train_dataset = ImageDataset('../training_set/train', transform = custom_transformer, mode='binary', use_masking=use_masking)
    train_loader = DataLoader(train_dataset, batch_size)
    model=None
    if model_name=='uchan':
        model = build_uchanmodel(num_classes)
        if pretrained:
            print('load pretrained')
            state = torch.load('./WEIGHTS/uchan_saved_model/uchan_model_5.pth')
            model.load_state_dict(state['model'])
        model.to(device)
    elif model_name=='jayden':
        model = build_jaydenmodel(num_classes)
        if pretrained:
            state = torch.load('./WEIGHTS/uchan_saved_model/jayden_model_60.pth')
            model.load_state_dict(state['model'])
        model.to(device)
    '''
    optimizer = AdamW(model.parameters(), lr=0.001)
    scheduler_cosine = CosineAnnealingLR(optimizer,5)
    scheduler_warmup = GradualWarmupSchedulerV2(optimizer, multiplier=1, total_epoch=1, after_scheduler = scheduler_cosine)
    '''
    #scheduler = ReduceOnPlateauLearningRateScheduler(optimizer, factor=0.5,patience=2, mode='min', verbose=True)
    '''
    optimizer = Adam(model.parameters(), lr = 0.001)
    scheduler_steplr = StepLR(optimizer, step_size = 10, gamma = 0.1)
    scheduler_warmup = GradualWarmupScheduler(optimizer, multiplier=1, total_epoch=5, after_scheduler = scheduler_steplr)
    '''
    '''
    optimizer = SGD(model.parameters(),lr = 0.001)
    scheduler_steplr = StepLR(optimizer, step_size = 10, gamma = 0.1)
    scheduler_warmup = GradualWarmupScheduler(optimizer, multiplier=1, total_epoch=5, after_scheduler = scheduler_steplr)
    '''
    optimizer = AdamW(model.parameters())
    scheduler=ReduceLROnPlateau(optimizer,'min',patience=5, factor=0.9, verbose=True)
    if label_smoothing:
        criterion = LabelSmoothingLoss(num_classes).to(device)
    else:
        #criterion = nn.BCELoss().to(device)
        criterion = WeightedBCELoss().to(device)

    running_loss=0
    step_loss = 0
    print('train size : {}'.format(len(train_loader)))
    for epoch in range(1,epochs+1):
        #bar = tqdm(train_loader)
        for idx, data in enumerate(train_loader):
            img, label = data
            #print(img.shape, label)
            #print(img.shape, label)
            img = img.to(device)
            output = model(img)
            #print(output)
            label  = label.to(device).unsqueeze(1).type_as(output)

            loss = criterion(output,label)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            running_loss += loss.item()
            step_loss += loss.item()
            #bar.set_description('loss : % 5f' %(loss.item()))
            if idx%100==0:
                print('step : {} \t loss -> {}'.format(idx, step_loss/100))
                step_loss=0
        if epoch%1==0:
            epoch_loss = running_loss/(1*(len(train_loader)))
            scheduler.step(epoch_loss)
            print('model save! \t epoch {}: loss -> {}'.format(epoch, epoch_loss))
            running_loss=0
            #save_model(model, optimizer,scheduler,epoch)

            save_model(model,model_name, epoch)
            model.to(device)

def val(args):
    mode = 'val'
    flip = args['flip']
    noise = args['noise']
    clahe = args['clahe']
    cutout = args['cutout']
    normalize = args['normalize']
    resize = args['resize']
    size = args['size']
    normalize = args['normalize']
    use_masking = args['use_masking']
    num_classes = args['num_classes']
    batch_size = args['batch_size']
    epochs = args['epochs']
    pretrained = args['pretrained']
    label_smoothing = args['label_smoothing']
    device = torch.device('cuda')

    custom_transformer = Custom_transformer(mode = 'train', flip = flip, noise = noise, clahe = clahe, cutout = cutout, normalize = normalize, resize = resize) # size default = 224

    train_dataset = ImageDataset('../../../DATA/data_cancer/train', transform = custom_transformer, mode='binary', use_masking=use_masking)
    train_loader = DataLoader(train_dataset, batch_size)
    '''
    optimizer = Adam(model.parameters(), lr = 0.001)
    scheduler_steplr = StepLR(optimizer, step_size = 10, gamma = 0.1)
    scheduler_warmup = GradualWarmupScheduler(optimizer, multiplier=1, total_epoch=5, after_scheduler = scheduler_steplr)
    '''
    '''
    optimizer = SGD(model.parameters(),lr = 0.001)
    scheduler_steplr = StepLR(optimizer, step_size = 10, gamma = 0.1)
    scheduler_warmup = GradualWarmupScheduler(optimizer, multiplier=1, total_epoch=5, after_scheduler = scheduler_steplr)
    '''

    model = build_jaydenmodel(num_classes)
    if pretrained:
        state = torch.load('./WEIGHTS/uchan_saved_model/saved_b0_model_30.pth')
        model.load_state_dict(state['model'])
    model.to(device)
    outputs = []
    labels = []
    for epoch in range(1,epochs+1):
        bar = tqdm(train_loader)
        #scheduler_warmup.step(epoch)
        for img, label in bar:
            #print(img.shape, label)

            img = img.to(device)
            output = model(img)
            for i in range(output.shape[0]):
                outputs.append(output[i].item())
                labels.append(label[i].item())
        print(roc_auc_score(np.array(labels),np.array(outputs)))


def test(args):
    mode = args['mode']
    num_classes = args['num_classes']
    batch_size = args['batch_size']
    normalize = args['normalize']
    resize = args['resize']
    size = args['size']
    device = torch.device('cuda')
    model = build_uchanmodel(num_classes)
    model.to(device)
    state = torch.load('./WEIGHTS/uchan_saved_model/uchan_model_30.pth')

    model.load_state_dict(state['model'])
    model.to(device)

    custom_transformer = Custom_transformer(mode, normalize = normalize, resize = resize,size=size)

    test_dataset = ImageDataset('../../../DATA/data_cancer/test', transform = custom_transformer, mode='test')
    test_loader = DataLoader(test_dataset, batch_size)

    remove_path = lambda x : re.sub(r'^.+/','',x)
    fn = [remove_path(i) for i in test_dataset.filenames]
    result = []
    bar = tqdm(test_loader)
    for image, _ in bar:
        image = image.to(device)
        outputs = model(image)
        #_outputs = F.sigmoid(outputs)
        #print('output : {}, \t sigmoid : {}'.format(outputs, _outputs))
        for output in outputs:
            #print(output)
            result.append(output.item())

    write_result_table(preds = np.array(result), filename=fn, savename='test_uchan.csv')
if __name__=='__main__':
    args = parser.parse_args()
    mode = args.mode
    print(mode)
    if mode=='train':
        train_args = {'mode' : 'train', 'flip': True,'noise' : True,'clahe' : True, 'cutout' : True, 'normalize':True, 'resize' : True, 'size' : 224, 'num_classes' : 1, 'batch_size' : 2, 'epochs':30,'label_smoothing':False, 'pretrained':False, 'use_masking':True, 'model_name':args.name}
        train(train_args)
    elif mode == 'val':
        val_args = {'mode' : 'train', 'flip': False, 'noise' : False,'clahe' : False, 'cutout' : False, 'normalize':True, 'resize' : True, 'size' : 224, 'num_classes' : 1, 'batch_size' : 2, 'epochs':1,'label_smoothing':False, 'pretrained': True, 'use_masking':False}
        val(val_args)
    elif mode=='test':
        test_args = {'mode': 'test','normalize':True, 'resize':True, 'num_classes':1, 'batch_size':1,'size' : 224}

        test(test_args)