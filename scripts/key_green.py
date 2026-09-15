"""Key a clip on a flat chroma background (colour sampled from the frame borders). Usage: key_green.py <workdir> <A0> <A1> [thresh=50] [min_comp=40]
Mask = pixels further than thresh from the background colour, opening, components >= min_comp, holes filled. No pocket rules: nothing on the
character is background coloured by construction. Rim decontamination 3 px + outside repainted with nearest character colour."""
import numpy as np, glob, os, sys
from PIL import Image
from scipy import ndimage
W,A0,A1=sys.argv[1],int(sys.argv[2]),int(sys.argv[3]); TH=int(sys.argv[4]) if len(sys.argv)>4 else 50; MINC=int(sys.argv[5]) if len(sys.argv)>5 else 40; GX=int(os.environ.get('GX','40'))
fs=sorted(glob.glob(f"{W}/raw/*.png")); four=np.array([[0,1,0],[1,1,1],[0,1,0]]); os.makedirs(f"{W}/keyed",exist_ok=True)
r0=np.array(Image.open(fs[A0]).convert("RGB")).astype(int); bg=np.median(np.concatenate([r0[:6].reshape(-1,3),r0[-6:].reshape(-1,3),r0[:,:6].reshape(-1,3),r0[:,-6:].reshape(-1,3)]),axis=0).round().astype(int); print("background",bg.tolist())
sil=[]
for j in range(A0,A1):
    raw=np.array(Image.open(fs[j]).convert("RGB")).astype(int); d=np.abs(raw-bg).max(axis=2)
    gdom=(raw[...,1]-np.maximum(raw[...,0],raw[...,2]))>GX
    labg,ng=ndimage.label(gdom); border=set(np.unique(np.concatenate([labg[0],labg[-1],labg[:,0],labg[:,-1]])))-{0}
    green=gdom&(np.isin(labg,list(border))|(d<=45))   # background green = touches the frame edge OR is the screen colour; enclosed green of another shade is the character's own (eyes, highlights)
    m=(d>TH)&~green; m=ndimage.binary_opening(m,iterations=1); lab,n=ndimage.label(m); sizes=ndimage.sum(m,lab,range(1,n+1)); m=np.isin(lab,[i+1 for i in range(n) if sizes[i]>=MINC]); m=ndimage.binary_fill_holes(m)&~green
    core=ndimage.binary_erosion(m,structure=four,iterations=3,border_value=0); idx=ndimage.distance_transform_edt(~core,return_distances=False,return_indices=True); clean=raw[idx[0],idx[1]]
    out=raw.copy(); out[m&~core]=clean[m&~core]; out[~m]=clean[~m]
    o=np.zeros(raw.shape[:2]+(4,),np.uint8); o[...,:3]=np.clip(out,0,255); o[...,3]=m*255; Image.fromarray(o).save(f"{W}/keyed/{j:04d}.png"); sil.append(int(m.sum()))
print("keyed",A1-A0,"frames, silhouette px min/max",min(sil),max(sil))
