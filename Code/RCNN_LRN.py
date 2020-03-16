import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils import data
from torch.utils.data import DataLoader
from torch.autograd import Variable

import torchvision
from torchvision.datasets import mnist
import torchvision.transforms as transforms

import matplotlib.pyplot as plt

import torch.optim as optim
import numpy as np

class RCNN(torch.nn.Module):
    def __init__(self, in_channels, feature_num, feature_map_width, iter_time, device):
        super(RCNN,self).__init__()
        self.feature_num=feature_num

        self.iter_time=iter_time
        self.device=device
      
        self.conv1 = torch.nn.Conv2d(in_channels=in_channels, out_channels=feature_num, kernel_size=5, stride=1, padding=2) 
        #self.conv1 = RCL(in_channels=3,out_channels=feature_num,kernel_size=5,iter_time=0,feature_map_width=32,device=device,stride=1,padding=2)          
                
        self.relu=torch.nn.ReLU()
        self.bn=torch.nn.BatchNorm2d(feature_num)
        #self.bn=torch.nn.LayerNorm([feature_num,32,32])

        #Conv2d will automatically initialize weight and bias.
        #torch.nn.init.kaiming_uniform_(self.conv1[0].weight, a=0, mode='fan_in', nonlinearity='relu')
        #torch.nn.init.kaiming_uniform_(self.conv1[0].bias, a=0, mode='fan_in', nonlinearity='relu')
    
        #print(self.conv1[1].weight)
        #print(self.conv1[1].bias)

        self.mxp1 = nn.MaxPool2d(kernel_size=3,stride=2,padding=1)

        self.dropout1=torch.nn.Dropout(0.5)
        
        self.rconv2 = RCL(in_channels=feature_num,
                          out_channels=feature_num,
                          kernel_size=3,
                          iter_time=3,
                          feature_map_width=feature_map_width//2,
                          device=device,
                          stride=1,
                          padding=1)

        self.dropout2=torch.nn.Dropout(0.5)

        self.rconv3 = RCL(in_channels=feature_num,
                          out_channels=feature_num,
                          kernel_size=3,
                          iter_time=3,
                          feature_map_width=feature_map_width//2,
                          device=device,
                          stride=1,
                          padding=1)

        self.mxp3 = nn.MaxPool2d(kernel_size=3,stride=2,padding=1)
        feature_map_width=feature_map_width//2

        self.dropout3=torch.nn.Dropout(0.5)

        self.rconv4 = RCL(in_channels=self.feature_num,
                          out_channels=self.feature_num,
                          kernel_size=3,
                          iter_time=3,
                          feature_map_width=feature_map_width//2,
                          device=device,
                          stride=1,
                          padding=1)
        
        self.dropout4=torch.nn.Dropout(0.5)

        self.rconv5 = RCL(in_channels=self.feature_num,
                          out_channels=self.feature_num,
                          kernel_size=3,
                          iter_time=3,
                          feature_map_width=feature_map_width//2,
                          device=device,
                          stride=1,
                          padding=1)
        
        self.mxp5 = nn.MaxPool2d(kernel_size=3,stride=2)
        
        self.mlp6 = torch.nn.Linear(self.feature_num,10)

    def forward(self, x):
        x = self.conv1(x)
        x = self.bn(x)
        x = self.relu(x)
        x = self.mxp1(x)
        #x = self.dropout1(x)
        x = self.rconv2(x)
        x = self.dropout2(x)
        x = self.rconv3(x)
        x = self.mxp3(x)
        x = self.dropout3(x)
        x = self.rconv4(x)
        x = self.dropout4(x)
        x = self.rconv5(x)
        x = self.mxp5(x)
        y = torch.max(torch.max(x,3)[0],2)[0]
        y=self.mlp6(y)
        #CrossEntropyLoss already includes softmax.
        #y=F.softmax(y, dim=1)
        return y

class RCL(torch.nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size, iter_time, feature_map_width, device, stride=1, padding=0):
        super(RCL,self).__init__()
        self.stride=stride
        self.padding=padding
        self.kernel_size=kernel_size
        #self.forward_weight=torch.nn.Parameter(torch.zeros(out_channels, in_channels, kernel_size, kernel_size))
        #torch.nn.init.kaiming_uniform_(self.forward_weight, a=0, mode='fan_in', nonlinearity='relu')
    
        #self.recurrent_weight=torch.nn.Parameter(torch.zeros(out_channels, in_channels, kernel_size, kernel_size))
        #torch.nn.init.kaiming_uniform_(self.recurrent_weight, a=0, mode='fan_in', nonlinearity='relu')

        #self.forward_bias=torch.nn.Parameter(torch.zeros(out_channels))
 
        #self.recurrent_bias=torch.nn.Parameter(torch.zeros(out_channels))
        
        #self.ln=torch.nn.LayerNorm([96,feature_map_width,feature_map_width])

        self.relu=torch.nn.ReLU()

        self.conv_f=torch.nn.Conv2d(in_channels=in_channels, out_channels=out_channels, kernel_size=self.kernel_size, stride=self.stride, padding=self.padding)

        self.conv_r=torch.nn.Conv2d(in_channels=in_channels, out_channels=out_channels, kernel_size=self.kernel_size, bias=False, stride=self.stride, padding=self.padding)

        self.iter_time=iter_time

        self.feature_map_width=feature_map_width

        self.feature_map_num=out_channels
        self.inhiRange=self.feature_map_num//8+1

        inhiMat=torch.zeros(out_channels,out_channels)
        for i in range(0,out_channels):
            j_min=np.maximum(0,i-self.inhiRange//2)
            j_max=np.minimum(out_channels-1,i+self.inhiRange//2)+1
            for j in range(j_min,j_max):
                inhiMat[i,j]=1.0

        inhi=torch.zeros(128,out_channels,out_channels)

        for i in range(0,128):
            inhi[i]=inhiMat
        
        self.inhi=inhi.to(device)
        self.inhiMat=inhiMat.to(device)

    def forward(self, x):
        
        f=self.conv_f(x)
        r=self.relu(f)
        r=self.lrn(r)
        '''
        for i in range(0,self.iter_time):
            if(i==0):
                r=self.ln(r)
                r=self.relu(r)
            else:
                r=self.conv_r(r)
                r=torch.add(f,r)
                r=self.ln(r)
                r=self.relu(r)
        '''
        for i in range(0,self.iter_time):
            r=self.conv_r(r)
            r=torch.add(f,r)
            r=self.relu(r)
            r=self.lrn(r)
        return r
    def lrn(self,x):
        y=x.clone().detach()
        y=y**2
        y=y.view([y.size(0),y.size(1),self.feature_map_width*self.feature_map_width])
        y=torch.bmm(self.inhi,y)
        
        '''
        for i in range(0,y.size(0)):
            y[i]=torch.mm(self.inhiMat,y[i])
        '''
        y=y.view([x.size(0),x.size(1),self.feature_map_width,self.feature_map_width])
        y=y*0.001/self.inhiRange
        y=y+1.0
        y=y**0.75
        x=x/y
        return x