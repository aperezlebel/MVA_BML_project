#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Make the curve of the loss after 10 epochs with respect to sigma_b on the EOC """

import argparse
import numpy as np
import torch
import torch.nn as nn
from torchvision.datasets import MNIST
from torchvision import transforms
from torch.utils.data import DataLoader
from torch.utils.data import random_split
from pytorch_lightning.loggers import TensorBoardLogger
import pytorch_lightning as pl
from pytorch_lightning.callbacks import ModelCheckpoint
import matplotlib.pyplot as plt

from eoc import get_eoc_by_name
from model import LinearModel

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='fig5B')
    parser.add_argument('--epochs', type=int, default=10, help='Number of epochs')
    parser.add_argument('--bs', type=int, default=64, help='Batch size')
    parser.add_argument('--nlayers', type=int, default=10, help='Number of layers')
    parser.add_argument('--nplayers', type=int, default=10, help='Number of neurons per layer')
    parser.add_argument('--rs', type=int, default=0, help='Random state')
    parser.add_argument('--sigb_max', type=float, default=0.1, help='maximum Sigma bias')
    parser.add_argument('--n_sigb', type=int, default=21, help='number of points on the curve (number of different sigma_b considere')
    parser.add_argument('--name', type=str, default='Exp', help='experiment name')
    parser.add_argument('--ns', type=float, default='0', help='negative slope of Leaky ReLU')
    parser.add_argument('--act', type=str, default='elu', help='Which activation to use')
    parser.add_argument('--n', type=int, default=500000, help='Number of samples to drawn for the computation of eoc')
    args = parser.parse_args()
    
    np.random.seed(args.rs)
    torch.manual_seed(args.rs)
    
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    
    dataset = MNIST('MNIST/', train=True, download=True, transform=transforms.ToTensor())
    mnist_train, mnist_val = random_split(dataset, [55000, 5000])
    
    #dataset.data = dataset.data.to(device)
    #dataset.targets = dataset.targets.to(device)

    train_loader = DataLoader(mnist_train, batch_size=args.bs)
    val_loader = DataLoader(mnist_val, batch_size=args.bs)
        
    if args.act == 'relu':
        activation = nn.ReLU()
    elif args.act == 'lrelu':
        activation = nn.LeakyReLU(negative_slope=args.ns)
    elif args.act == 'elu':
        activation = nn.ELU()
    else:
        raise ValueError(f'Unknown activation {args.act}')
        
    
    model = LinearModel(n_in=28*28, n_out=10, n_layers=args.nlayers,
                        n_per_layers=args.nplayers, activation=activation)
        
    # Liste of sigma on the abscisse
    
    sigma_liste = np.linspace(0,args.sigb_max,args.n_sigb)
    
    loss_liste = []
    
    for sigb in sigma_liste:
        
        # get sigma_w on the EOC and then train for 10 epochs
        
        sigw = get_eoc_by_name(args.act, sigb, args.n)[1]
        
        model.init_weights(sig_w=sigw, sig_b=sigb)
        logger = TensorBoardLogger("tb_logs/{}/".format(args.name), name="{}_{}_{}_{}".format(args.act,args.nlayers,args.nplayers,sigb))
        
        checkpoint_callback = ModelCheckpoint(dirpath='checkpoints/{}/'.format(args.name),
                                          filename='{sigb:.3f}-{epoch:02d}-{val_loss:.3f}',
                                          monitor='val_loss')
        
        trainer = pl.Trainer(max_epochs=args.epochs,
                         checkpoint_callback=checkpoint_callback,
                         logger=logger,
                         gpus='0')
        
        trainer.fit(model, train_loader, val_loader)
        
        # compute the loss on the validatoin set after the training
        
        with torch.no_grad():
            loss=torch.zeros(1).to(device)
            for x,y in val_loader:
                loss += nn.CrossEntropyLoss(reduction='sum')(model(x.view(x.size(0),-1).float()),y)
            loss/=5000
            print('loss for sigma_b={}:'.format(sigb),loss)
            loss_liste.append(loss.cpu().numpy())
    
    # plot and save
    
    plt.figure(figsize=(5,5))
    plt.plot(sigma_liste,loss_liste)
    plt.xlabel('sigma b')
    plt.ylabel('validation loss after 10 epochs')
    plt.grid(which='major')
    plt.savefig("figs/{}_{}_{}_{}".format(args.name,args.act,args.nlayers,args.nplayers))
    plt.show()
        
        
        
        
