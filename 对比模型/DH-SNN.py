import numpy as np
import torch
import torch.nn as nn
import math
import torch.nn.functional as F

surrograte_type = 'MG'
print('gradient type: ', surrograte_type)


gamma = 0.5
lens = 0.5
R_m = 1


beta_value = 1.8
b_j0_value = 0.01



def gaussian(x, mu=0., sigma=.5):
    return torch.exp(-((x - mu) ** 2) / (2 * sigma ** 2)) / (sigma * math.sqrt(2 * math.pi))

# define approximate firing function

class ActFun_adp(torch.autograd.Function):
    @staticmethod
    def forward(ctx, input):  # input = membrane potential- threshold
        ctx.save_for_backward(input)
        return input.gt(0).float()  # is firing ???

    @staticmethod
    def backward(ctx, grad_output):  # approximate the gradients
        input, = ctx.saved_tensors
        grad_input = grad_output.clone()
        # temp = abs(input) < lens
        scale = 6.0
        hight = .15
        if surrograte_type == 'G':
            temp = torch.exp(-(input**2)/(2*lens**2))/torch.sqrt(2*torch.tensor(math.pi))/lens
        #multi gaussian
        elif surrograte_type == 'MG':
            temp = gaussian(input, mu=0., sigma=lens) * (1. + hight) \
                - gaussian(input, mu=lens, sigma=scale * lens) * hight \
                - gaussian(input, mu=-lens, sigma=scale * lens) * hight
        elif surrograte_type =='linear':
            temp = F.relu(1-input.abs())
        elif surrograte_type == 'slayer':
            temp = torch.exp(-5*input.abs())
        elif surrograte_type == 'rect':
            temp = input.abs() < 0.5
        return grad_input * temp.float()*gamma
    

    
act_fun_adp = ActFun_adp.apply    



def mem_update_pra(inputs, mem, spike, v_th, tau_m, dt=1,device=None):
    """
    neural model with soft reset
    """   
    alpha = torch.sigmoid(tau_m)
    mem = mem * alpha  + (1 - alpha) * R_m * inputs-v_th*spike
    inputs_ = mem - v_th

    spike = act_fun_adp(inputs_)  
    return mem, spike


def mem_update_pra_noreset(inputs, mem, spike, v_th, tau_m, dt=1,device=None):
    """
    neural model without reset
    Args:
        input(float): soma input.
        mem(float): soma membrane potential
        spike(int): spike or not spike
        vth(float): threshold
        tau_m(float): time factors of soma
    """   
    alpha = torch.sigmoid(tau_m)
    #without reset
    mem = mem * alpha  + (1 - alpha) * R_m * inputs#-v_th*spike
    inputs_ = mem - v_th

    spike = act_fun_adp(inputs_)  
    return mem, spike
def mem_update_pra_hardreset(inputs, mem, spike, v_th, tau_m, dt=1,device=None):
    """
    neural model with hard reset
    Args:
        input(float): soma input.
        mem(float): soma membrane potential
        spike(int): spike or not spike
        vth(float): threshold
        tau_m(float): time factors of soma
    """   
    alpha = torch.sigmoid(tau_m)
    #hard reset
    mem = mem * alpha*(1-spike)  + (1 - alpha) * R_m * inputs#-v_th*spike
    inputs_ = mem - v_th

    spike = act_fun_adp(inputs_)  
    return mem, spike


def output_Neuron_pra(inputs, mem, tau_m, dt=1,device=None):
    """
    The read out neuron is leaky integrator without spike
    Args:
        input(float): soma input.
        mem(float): soma membrane potential
        tau_m(float): time factors of soma
    """
    alpha = torch.sigmoid(tau_m).to(device)
    mem = mem *alpha +  (1-alpha)*inputs
    return mem

import numpy as np
import torch
import torch.nn as nn
import math
from torch.autograd import Variable
import torch.nn.functional as F
from SNN_layers.spike_neuron import *#


## readout layer
class readout_integrator_test(nn.Module):
    def __init__(self,input_dim,output_dim,
                 tau_minitializer = 'uniform',low_m = 0,high_m = 4,device='cpu',bias=True,dt = 1):
        """
        Args:
            input_dim(int): input dimension.
            output_dim(int): the number of readout neurons
            tau_minitializer(str): the method of initialization of tau_m
            low_m(float): the low limit of the init values of tau_m
            high_m(float): the upper limit of the init values of tau_m
        """
        super(readout_integrator_test, self).__init__()
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.device = device
        self.dt = dt
        self.dense = nn.Linear(input_dim,output_dim,bias=bias)
        self.tau_m = nn.Parameter(torch.Tensor(self.output_dim))
        
        if tau_minitializer == 'uniform':
            nn.init.uniform_(self.tau_m,low_m,high_m)
        elif tau_minitializer == 'constant':
            nn.init.constant_(self.tau_m,low_m)

    
    def set_neuron_state(self, batch_size, device=None):
        device = device or self.device
        self.mem = torch.rand(batch_size, self.output_dim, device=device)

    def forward(self, input_spike):
        d_input = self.dense(input_spike.float())
        self.mem = output_Neuron_pra(d_input, self.mem, self.tau_m, self.dt, device=input_spike.device)
        return self.mem


#DH-SFNN layer
class spike_dense_test_denri_wotanh_R(nn.Module):
    def __init__(self,input_dim,output_dim,tau_minitializer = 'uniform',low_m = 0,high_m = 4,
                 tau_ninitializer = 'uniform',low_n = 0,high_n = 4,vth = 0.5,dt = 1,branch = 4,device='cpu',bias=True,test_sparsity = False,sparsity=0.5,mask_share=1):
        """
        Args:
            input_dim(int): input dimension.
            output_dim(int): the number of readout neurons
            tau_minitializer(str): the method of initialization of tau_m
            low_m(float): the low limit of the init values of tau_m
            high_m(float): the upper limit of the init values of tau_m
            tau_ninitializer(str): the method of initialization of tau_n
            low_n(float): the low limit of the init values of tau_n
            high_n(float): the upper limit of the init values of tau_n
            vth(float): threshold
            branch(int): the number of dendritic branches
            test_sparsity(bool): if testing the sparsity of connection pattern 
            sparsity(float): the sparsity ratio
            mask_share(int): the number of neuron share the same connection pattern 
        """
        super(spike_dense_test_denri_wotanh_R, self).__init__()
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.device = device
        self.vth = vth
        self.dt = dt
        if test_sparsity:
            self.sparsity = sparsity 
        else:
            self.sparsity = 1/branch
        
        #group size for hardware implementation
        self.mask_share = mask_share
        self.pad = ((input_dim)//branch*branch+branch-(input_dim)) % branch
        self.dense = nn.Linear(input_dim+self.pad,output_dim*branch)
        #sparsity
        self.overlap = 1/branch
        self.tau_m = nn.Parameter(torch.Tensor(self.output_dim))
        self.tau_n = nn.Parameter(torch.Tensor(self.output_dim,branch))
        self.test_sparsity = test_sparsity
        
        #the number of dendritic branch
        self.branch = branch

        self.create_mask()
        
        # timing factor of membrane potential
        if tau_minitializer == 'uniform':
            nn.init.uniform_(self.tau_m,low_m,high_m)
        elif tau_minitializer == 'constant':
            nn.init.constant_(self.tau_m,low_m)
            
            
        # timing factor of dendritic branches
        if tau_ninitializer == 'uniform':
            nn.init.uniform_(self.tau_n,low_n,high_n)
        elif tau_ninitializer == 'constant':
            nn.init.constant_(self.tau_n,low_n)

    

    def set_neuron_state(self, batch_size, device=None):
        device = device or self.device
        self.mem = Variable(torch.rand(batch_size, self.output_dim, device=device))
        self.spike = Variable(torch.rand(batch_size, self.output_dim, device=device))
        if self.branch == 1:
            self.d_input = Variable(torch.rand(batch_size, self.output_dim, self.branch, device=device))
        else:
            self.d_input = Variable(torch.zeros(batch_size, self.output_dim, self.branch, device=device))
        self.v_th = Variable(torch.ones(batch_size, self.output_dim, device=device) * self.vth)

    #create connection pattern
    def create_mask(self):
        
        input_size = self.input_dim+self.pad
        self.mask = torch.zeros(self.output_dim*self.branch,input_size).to(self.device)
        for i in range(self.output_dim//self.mask_share):
            seq = torch.randperm(input_size)
            # j as the branch index
            for j in range(self.branch):
                if self.test_sparsity:
                    if j*input_size // self.branch+int(input_size * self.sparsity)>input_size:
                        for k in range(self.mask_share):
                            self.mask[(i*self.mask_share+k)*self.branch+j,seq[j*input_size // self.branch:-1]] = 1
                            self.mask[(i*self.mask_share+k)*self.branch+j,seq[:j*input_size // self.branch+int(input_size * self.sparsity)-input_size]] = 1
                    else: 
                        for k in range(self.mask_share):
                            self.mask[(i*self.mask_share+k)*self.branch+j,seq[j*input_size // self.branch:j*input_size // self.branch+int(input_size * self.sparsity)]] = 1
                else:
                    for k in range(self.mask_share):
                        self.mask[(i*self.mask_share+k)*self.branch+j,seq[j*input_size // self.branch:(j+1)*input_size // self.branch]] = 1
    def apply_mask(self):
        self.dense.weight.data = self.dense.weight.data*self.mask
    def forward(self, input_spike):
        beta = torch.sigmoid(self.tau_n)
        padding = torch.zeros(input_spike.size(0), self.pad, device=input_spike.device)
        k_input = torch.cat((input_spike.float(), padding), 1)
        self.d_input = beta * self.d_input + (1 - beta) * self.dense(k_input).reshape(-1, self.output_dim, self.branch)
        l_input = self.d_input.sum(dim=2, keepdim=False)
        self.mem, self.spike = mem_update_pra(l_input, self.mem, self.spike, self.v_th, self.tau_m, self.dt, device=input_spike.device)
        return self.mem, self.spike
    
    
#Vanilla SFNN layer
class spike_dense_test_origin(nn.Module):
    def __init__(self,input_dim,output_dim,
                 tau_minitializer = 'uniform',low_m = 0,high_m = 4,vth = 0.5,dt = 4,device='cpu',bias=True):
        """
        Args:
            input_dim(int): input dimension.
            output_dim(int): the number of readout neurons
            tau_minitializer(str): the method of initialization of tau_m
            low_m(float): the low limit of the init values of tau_m
            high_m(float): the upper limit of the init values of tau_m
            vth(float): threshold
        """
        super(spike_dense_test_origin, self).__init__()
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.device = device
        self.vth = vth
        self.dt = dt

        self.dense = nn.Linear(input_dim,output_dim)
        self.tau_m = nn.Parameter(torch.Tensor(self.output_dim))

        if tau_minitializer == 'uniform':
            nn.init.uniform_(self.tau_m,low_m,high_m)
        elif tau_minitializer == 'constant':
            nn.init.constant_(self.tau_m,low_m)

    def set_neuron_state(self,batch_size):

        self.mem = Variable(torch.rand(batch_size,self.output_dim)).to(self.device)
        self.spike = Variable(torch.rand(batch_size,self.output_dim)).to(self.device)

        self.v_th = Variable(torch.ones(batch_size,self.output_dim)*self.vth).to(self.device)
    def forward(self,input_spike):
        k_input = input_spike.float()

        d_input = self.dense(k_input)
        self.mem,self.spike = mem_update_pra(d_input,self.mem,self.spike,self.v_th,self.tau_m,self.dt,device=self.device)    
        return self.mem,self.spike
    
#Vanilla SFNN layer without reset 
class spike_dense_test_origin_noreset(nn.Module):
    def __init__(self,input_dim,output_dim,
                 tau_minitializer = 'uniform',low_m = 0,high_m = 4,vth = 0.5,dt = 4,device='cpu',bias=True):
        """
        Args:
            input_dim(int): input dimension.
            output_dim(int): the number of readout neurons
            tau_minitializer(str): the method of initialization of tau_m
            low_m(float): the low limit of the init values of tau_m
            high_m(float): the upper limit of the init values of tau_m
            vth(float): threshold
        """
        super(spike_dense_test_origin_noreset, self).__init__()
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.device = device
        self.vth = vth
        self.dt = dt

        self.dense = nn.Linear(input_dim,output_dim)
        self.tau_m = nn.Parameter(torch.Tensor(self.output_dim))

        if tau_minitializer == 'uniform':
            nn.init.uniform_(self.tau_m,low_m,high_m)
        elif tau_minitializer == 'constant':
            nn.init.constant_(self.tau_m,low_m)

    def set_neuron_state(self,batch_size):
        # self.mem = (torch.rand(batch_size,self.output_dim)*self.b_j0).to(self.device)
        self.mem = Variable(torch.rand(batch_size,self.output_dim)).to(self.device)
        self.spike = Variable(torch.rand(batch_size,self.output_dim)).to(self.device)

        self.v_th = Variable(torch.ones(batch_size,self.output_dim)*self.vth).to(self.device)
    def forward(self,input_spike):
        k_input = input_spike.float()
        d_input = self.dense(k_input)
        
        # neural model without reset
        self.mem,self.spike = mem_update_pra_noreset(d_input,self.mem,self.spike,self.v_th,self.tau_m,self.dt,device=self.device)
        
        return self.mem,self.spike

#Vanilla SFNN layer with hard reset 
class spike_dense_test_origin_hardreset(nn.Module):
    def __init__(self,input_dim,output_dim,
                 tau_minitializer = 'uniform',low_m = 0,high_m = 4,vth = 0.5,dt = 4,device='cpu',bias=True):
        """
        Args:
            input_dim(int): input dimension.
            output_dim(int): the number of readout neurons
            tau_minitializer(str): the method of initialization of tau_m
            low_m(float): the low limit of the init values of tau_m
            high_m(float): the upper limit of the init values of tau_m
            vth(float): threshold
        """
        super(spike_dense_test_origin_hardreset, self).__init__()
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.device = device
        self.vth = vth
        self.dt = dt

        self.dense = nn.Linear(input_dim,output_dim)
        self.tau_m = nn.Parameter(torch.Tensor(self.output_dim))

        if tau_minitializer == 'uniform':
            nn.init.uniform_(self.tau_m,low_m,high_m)
        elif tau_minitializer == 'constant':
            nn.init.constant_(self.tau_m,low_m)

    def set_neuron_state(self,batch_size):
        # self.mem = (torch.rand(batch_size,self.output_dim)*self.b_j0).to(self.device)
        self.mem = Variable(torch.rand(batch_size,self.output_dim)).to(self.device)
        self.spike = Variable(torch.rand(batch_size,self.output_dim)).to(self.device)

        self.v_th = Variable(torch.ones(batch_size,self.output_dim)*self.vth).to(self.device)
    def forward(self,input_spike):
        k_input = input_spike.float()
        d_input = self.dense(k_input)
        # neural model with hard reset
        self.mem,self.spike = mem_update_pra_hardreset(d_input,self.mem,self.spike,self.v_th,self.tau_m,self.dt,device=self.device)
        
        return self.mem,self.spike


# DH-SFNN for multitimescale_xor task
class spike_dense_test_denri_wotanh_R_xor(nn.Module):
    def __init__(self,input_dim,output_dim,tau_minitializer = 'uniform',low_m = 0,high_m = 4,
                 tau_ninitializer = 'uniform',low_n = 0,high_n = 4,low_n1 = 2,high_n1 = 6,low_n2 = -4,high_n2 = 0,vth = 0.5,dt = 4,branch = 4,device='cpu',bias=True):
        """
        Args:
            input_dim(int): input dimension.
            output_dim(int): the number of readout neurons
            tau_minitializer(str): the method of initialization of tau_m
            low_m(float): the low limit of the init values of tau_m
            high_m(float): the upper limit of the init values of tau_m
            tau_ninitializer(str): the method of initialization of tau_n
            low_n(float): the low limit of the init values of tau_n
            high_n(float): the upper limit of the init values of tau_n
            low_n1(float): the low limit of the init values of tau_n in branch 1 for the beneficial initializaiton
            high_n1(float): the upper limit of the init values of tau_n in branch 1 for the beneficial initializaiton
            low_n2(float): the low limit of the init values of tau_n in branch 2 for the beneficial initializaiton
            high_n2(float): the upper limit of the init values of tau_n in branch 2 for the beneficial initializaiton
            vth(float): threshold
            branch(int): the number of dendritic branches
        """
        super(spike_dense_test_denri_wotanh_R_xor, self).__init__()
        self.input_dim = input_dim
        self.output_dim = output_dim
        #self.is_adaptive = is_adaptive
        self.device = device
        self.vth = vth
        self.dt = dt
        mask_rate = 1/branch

        self.pad = ((input_dim)//branch*branch+branch-(input_dim)) % branch
        self.dense = nn.Linear(input_dim+self.pad,output_dim*branch,bias=bias)

        self.tau_m = nn.Parameter(torch.Tensor(self.output_dim))
        self.tau_n = nn.Parameter(torch.Tensor(self.output_dim,branch))

        self.branch = branch

        self.create_mask()
        if tau_minitializer == 'uniform':
            nn.init.uniform_(self.tau_m,low_m,high_m)
        elif tau_minitializer == 'constant':
            nn.init.constant_(self.tau_m,low_m)

        if tau_ninitializer == 'uniform':
            nn.init.uniform_(self.tau_n,low_n,high_n)
        elif tau_ninitializer == 'constant':
            nn.init.constant_(self.tau_n,low_n)
        # init different branch with different scale
        elif tau_ninitializer  == 'seperate':
            nn.init.uniform_(self.tau_n[:,0],low_n1,high_n1)
            nn.init.uniform_(self.tau_n[:,1],low_n2,high_n2)

    

    
    def set_neuron_state(self,batch_size):

        self.mem = Variable(torch.rand(batch_size,self.output_dim)).to(self.device)
        self.spike = Variable(torch.rand(batch_size,self.output_dim)).to(self.device)
        self.d_input = Variable(torch.zeros(batch_size,self.output_dim,self.branch)).to(self.device)

        self.v_th = Variable(torch.ones(batch_size,self.output_dim)*self.vth).to(self.device)

    def create_mask(self):
        input_size = self.input_dim+self.pad
        self.mask = torch.zeros(self.output_dim*self.branch,input_size).to(self.device)
        for i in range(self.output_dim):
            for j in range(self.branch):
                self.mask[i*self.branch+j,j*input_size // self.branch:(j+1)*input_size // self.branch] = 1
    def apply_mask(self):
        self.dense.weight.data = self.dense.weight.data*self.mask
    def forward(self,input_spike):

        beta = torch.sigmoid(self.tau_n)
        padding = torch.zeros(input_spike.size(0),self.pad).to(self.device)
        k_input = torch.cat((input_spike.float(),padding),1)
        self.d_input = beta*self.d_input+(1-beta)*self.dense(k_input).reshape(-1,self.output_dim,self.branch)

        l_input = (self.d_input).sum(dim=2,keepdim=False)
        self.mem,self.spike = mem_update_pra(l_input,self.mem,self.spike,self.v_th,self.tau_m,self.dt,device=self.device)
        
        return self.mem,self.spike


# -------------------------
# 核心配置
# -------------------------
INPUT_DIM = 72      # 8*9
OUTPUT_DIM = 3
SEQ_LENGTH = 4
HIDDEN_DIM = 256
BRANCH_NUM = 8
V_THRESHOLD = 0.5
DEVICE = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

# -------------------------
# 模型
# -------------------------
class Dense_test(nn.Module):
    def __init__(self, input_dim, hidden_dim, output_dim, branch_num, v_threshold):
        super().__init__()
        is_bias = True

        self.dense_1 = spike_dense_test_denri_wotanh_R(
            input_dim, hidden_dim,
            vth=v_threshold, dt=1, branch=branch_num,
            tau_ninitializer='uniform', low_n=-4, high_n=4,
            device=DEVICE, bias=is_bias, test_sparsity=False
        )

        self.dense_2 = readout_integrator_test(
            hidden_dim, output_dim, dt=1, device=DEVICE, bias=is_bias
        )

        torch.nn.init.xavier_normal_(self.dense_2.dense.weight)
        if is_bias:
            torch.nn.init.constant_(self.dense_2.dense.bias, 0)

    def forward(self, x):
        b, t, h, w = x.shape
        x = x.view(b, t, -1)
        self.dense_1.set_neuron_state(b, device=x.device)
        self.dense_2.set_neuron_state(b, device=x.device)
        output = torch.zeros(b, OUTPUT_DIM, device=x.device)
        for i in range(t):
            input_x = x[:, i, :]
            mem1, spk1 = self.dense_1(input_x)
            mem2 = self.dense_2(spk1)
            if i > 0:
                output += mem2
        return F.log_softmax(output / t, dim=1)

# -------------------------
# 一次随机输入
# -------------------------
if __name__ == "__main__":
    model = Dense_test(INPUT_DIM, HIDDEN_DIM, OUTPUT_DIM, BRANCH_NUM, V_THRESHOLD).to(DEVICE)
    model.eval()

    x = torch.randn(1, 4, 8, 9, device=DEVICE)  # (1,4,8,9)

    with torch.no_grad():
        y = model(x)

    print("Input shape :", tuple(x.shape))
    print("Output shape:", tuple(y.shape))  # 期望 (1, 3)
    print("Output      :", y)