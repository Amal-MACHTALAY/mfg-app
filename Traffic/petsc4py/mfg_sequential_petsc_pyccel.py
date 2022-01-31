##!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct 19 15:43:29 2021
@author: amal
"""

import numpy as np
import time
from modules import (compute_jacobian, compute_FF)
from tools import initialguess

'''************************ inputs ************************************'''
T=3.0 # horizon length  
u_max=1.0 # free flow speed
rho_jam=1.0 # jam density
L=1 # road length
CFL=0.75    # CFL<1
rho_a=0.05; rho_b=0.95; gama=0.1 
mu=0.0 # viscosity coefficient 
EPS=0.45

####################### grid's inputs
multip=3 # mutiple for interpolation
tol = 1e-10
Nx=60; Nt=60; use_interp = 0 # spatial-temporal grid sizes, use interpolation
if use_interp :
    Nx=Nx*multip; Nt=Nt*multip
dx=L/Nx # spatial step size
if mu==0.0:
    dt=min(T/Nt,(CFL*dx)/u_max) # temporal step size
    eps=0.0
else:
    dt=min(T/Nt,CFL*dx/abs(u_max),EPS*(dx**2)/mu) # temporal step size
    eps=mu*dt/(dx**2) 
x=np.linspace(0,L,Nx+1)
t=np.arange(0,T+dt,dt)
Nt=len(t)-1
print('Nx={Nx}, Nt={Nt}'.format(Nx=Nx,Nt=Nt))
print('dx={dx}, dt={dt}'.format(dx=round(dx,4),dt=round(dt,4)))

def formFunction(snes, w, F, Nt, Nx, dt, dx, eps, u_max, rho_jam, x):
    
    FF = F.array
    w = w.array
    
    compute_FF(w, FF, Nt, Nx, dt, dx, eps, u_max, rho_jam, x)

row = np.zeros(10*Nt*Nx+2*Nx, dtype=np.int64); col = np.zeros(10*Nt*Nx+2*Nx, dtype=np.int64); data = np.zeros(10*Nt*Nx+2*Nx);
def formJacobian(snes, w, J, P):
    P.zeroEntries()
    
    compute_jacobian(w.array, row, col, data, Nt, Nx, dt, dx, eps)
    
    P.setType("mpiaij")
    P.setFromOptions()
    P.setPreallocationNNZ(10)
    # P.setOption(option=19, flag=0)
    
    for i in range(len(data)):
        P.setValues(row[i], col[i], data[i], addv=False)
    
    P.assemble()
    if J != P:
        J.assemble()
            
    return PETSc.Mat.Structure.SAME_NONZERO_PATTERN

def formInitguess(snes, X):
    X.array = initialguess(Nt, Nx, multip)
    

 
# """************************ solve in grid 1***************************** """
from petsc4py import PETSc

t0 = time.process_time()   ###
shap=(3*Nt*Nx+2*Nx,3*Nt*Nx+2*Nx)

# create nonlinear solver
snes = PETSc.SNES()
snes.create()

da = PETSc.DMDA().create(dim = 1,
                         boundary_type=(PETSc.DMDA.BoundaryType.NONE,),
                         sizes = (shap[0],), dof = 1, stencil_width = 1)

da.setFromOptions()
da.setUp()
snes.setDM(da)

F = da.createGlobalVec()

b = None
xx = da.createGlobalVec()

args = [Nt, Nx, dt, dx, eps, u_max, rho_jam, x]
snes.setFunction(formFunction, F, args)
snes.setJacobian(formJacobian)

if use_interp:
    snes.setInitialGuess(formInitguess)
    # X = initialguess(Nt, Nx, multip)
    # snes.getInitialGuess()[0](snes, xx)
    # xx.setArray(X)


snes.getKSP().setType('gmres')

ksp = snes.getKSP()
pc = ksp.getPC()
pc.setFactorSolverType("mumps")
opts = PETSc.Options()
ksp.setTolerances(rtol=tol)
opts["pc_type"] = "lu"
# opts["ksp_viewer"]= 1
# opts["ksp_monitor"]= 1
ksp.setInitialGuessNonzero(True)
ksp.setFromOptions()

snes.setTolerances(rtol = tol)
snes.setFromOptions()

# t0 = time.process_time()   ###
snes.solve(b, xx)
t1 = time.process_time()   ###
time2=t1-t0
print("Time spent:",time2)


its = snes.getIterationNumber()
lits = snes.getLinearSolveIterations()

print ("Number of SNES iterations = :", its)
print ("Number of Linear iterations =" , lits)


if not use_interp:
    import os
    filename = ("sol.dat")
    if os.path.exists(filename):
        os.remove(filename)
    
    with open(filename, "a") as text_file:
        text_file.write(str(Nx))
        text_file.write("\n")
        text_file.write(str(Nt))
        text_file.write("\n")
        np.savetxt(text_file, xx.array)


#Free petsc elements
xx.destroy()      
F.destroy()                                     
snes.destroy()
ksp.destroy()