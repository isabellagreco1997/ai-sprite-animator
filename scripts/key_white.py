"""Key a Grok clip on a near-white background. Usage: key_white.py <workdir> <A0> <A1> <thresh> <collar_frac> [min_comp]
Keeps every component >= min_comp px (hearts, halos), fills holes, reopens paper pockets (60..1500 px, within 3 of paper) only below the collar line, rim decontamination 3 px, outside repainted."""
import numpy as np, glob, os, sys
from PIL import Image
from scipy import ndimage
W,A0,A1,TH,CF=sys.argv[1],int(sys.argv[2]),int(sys.argv[3]),int(sys.argv[4]),float(sys.argv[5]); MINC=int(sys.argv[6]) if len(sys.argv)>6 else 40
fs=sorted(glob.glob(f"{W}/raw/*.png")); four=np.array([[0,1,0],[1,1,1],[0,1,0]]); os.makedirs(f"{W}/keyed",exist_ok=True)
r0=np.array(Image.open(fs[A0]).convert("RGB")).astype(int); bg=np.median(np.concatenate([r0[:6].reshape(-1,3),r0[-6:].reshape(-1,3),r0[:,:6].reshape(-1,3),r0[:,-6:].reshape(-1,3)]),axis=0).round().astype(int); print("paper",bg.tolist())
pk=0; POCKD=int(os.environ.get("POCKD","4")); POCKM=float(os.environ.get("POCKM","3.0"))
for j in range(A0,A1):
    raw=np.array(Image.open(fs[j]).convert("RGB")).astype(int); d=np.abs(raw-bg).max(axis=2)
    m=d>TH; m=ndimage.binary_opening(m,iterations=1); lab,n=ndimage.label(m); sizes=ndimage.sum(m,lab,range(1,n+1)); m=np.isin(lab,[i+1 for i in range(n) if sizes[i]>=MINC]); m=ndimage.binary_fill_holes(m)
    ys=np.where(m)[0]; collar=ys.min()+int((ys.max()-ys.min())*CF)
    cand=m&(d<=POCKD); lab3,n3=ndimage.label(cand); sizes3=ndimage.sum(cand,lab3,range(1,n3+1))
    for i in range(1,n3+1):
        if 60<=sizes3[i-1]<=1500:
            h=lab3==i
            if np.where(h)[0].min()>=collar and np.abs(raw[h]-bg).max(axis=1).mean()<=POCKM: m=m&~h; pk+=1
    core=ndimage.binary_erosion(m,structure=four,iterations=3,border_value=0); idx=ndimage.distance_transform_edt(~core,return_distances=False,return_indices=True); clean=raw[idx[0],idx[1]]
    out=raw.copy(); out[m&~core]=clean[m&~core]; out[~m]=clean[~m]
    o=np.zeros(raw.shape[:2]+(4,),np.uint8); o[...,:3]=np.clip(out,0,255); o[...,3]=m*255; Image.fromarray(o).save(f"{W}/keyed/{j:04d}.png")
print("keyed",A1-A0,"frames, pockets reopened",pk)
