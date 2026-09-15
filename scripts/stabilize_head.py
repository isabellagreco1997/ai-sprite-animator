"""Stabilise the head of a sprite sequence. Usage: stabilize_head.py <frames_json> <out_dir> [band=0.42] [lock=0.5] [mode=lock|copy]
lock: within the head band (top `band` of the silhouette), align frames by the head centroid, freeze every cell whose colour is the
same in >= lock of the frames (temporal mode), shift back. Body untouched. copy: paste frame 0's head onto every frame at its own head offset."""
import sys, os, json, shutil, numpy as np
from PIL import Image
from scipy import ndimage
J,OUT=sys.argv[1],sys.argv[2]; BAND=float(sys.argv[3]) if len(sys.argv)>3 else 0.42; LOCK=float(sys.argv[4]) if len(sys.argv)>4 else 0.5; MODE=sys.argv[5] if len(sys.argv)>5 else "lock"   # lock | copy | pin (copy the head AND remove the whole-body offset so the head never moves)
m=json.load(open(J)); base=os.path.dirname(J); F=[np.array(Image.open(os.path.join(base,f["file"])).convert("RGBA")) for f in m["frames"]]; K=len(F); H,W=F[0].shape[:2]
def head_box(a):
    al=a[...,3]>0; ys,xs=np.where(al); top=ys.min(); hb=top+int((ys.max()-top)*BAND); sel=ys<=hb; return hb,np.array([ys[sel].mean(),xs[sel].mean()])
hb0,c0=head_box(F[0]); PAD=12; B=np.zeros((K,H+2*PAD,W+2*PAD,4),np.uint8); off=[]
T=F[0][:hb0+1].astype(int); Tm=T[...,3]>0   # frame 0 head as template; best integer shift by masked colour difference
def best_shift(a):
    best=None
    for dy in range(-4,5):
        for dx in range(-4,5):
            y0,x0=dy,dx; sub=np.zeros_like(T); ys0,ys1=max(0,y0),min(H,hb0+1+y0); xs0,xs1=max(0,x0),min(W,W+x0)
            if ys1<=ys0 or xs1<=xs0: continue
            sub[ys0-y0:ys1-y0, xs0-x0:xs1-x0]=a[ys0:ys1, xs0:xs1]
            sc=np.abs(sub[...,:3]-T[...,:3]).sum(axis=2)[Tm].mean()+ (((sub[...,3]>0)!=Tm).mean()*300)
            if best is None or sc<best[0]: best=(sc,dy,dx)
    return np.array([best[1],best[2]])
for j in range(K):
    d=best_shift(F[j].astype(int)) if MODE in ("copy","pin","face") else np.rint(head_box(F[j])[1]-c0).astype(int); off.append(d); B[j,PAD-d[0]:PAD-d[0]+H,PAD-d[1]:PAD-d[1]+W]=F[j]
band=np.zeros(B.shape[1:3],bool); band[:hb0+PAD+1,:]=True   # head band rows in aligned space
FRONT=float(os.environ.get("FRONT","0.68"))   # share of the head width (from the face side) that gets copied; the back hair stays free
if FRONT<1:
    hb=B[0][...,3]>0; hb[hb0+PAD+1:,:]=False; cols=np.where(hb.any(axis=0))[0]; x0,x1=cols.min(),cols.max()
    facing=os.environ.get("FACING","right"); w=x1-x0
    if facing=="right": band[:, :int(x1-FRONT*w)]=False
    else: band[:, int(x0+FRONT*w):]=False
# stop at the chin: lowest row where frame 0's head band has face-coloured (light, low saturation... approximated as the band bottom) -> keep as is
if MODE=="face":   # pin the body, copy only the FACE patch (skin + eyes + mouth) of frame 0: hair and outline stay the frame's own
    a0=B[0].astype(int); al0=a0[...,3]>0; lum=a0[...,:3].mean(axis=2); sat=a0[...,:3].max(axis=2)-a0[...,:3].min(axis=2)
    hb=np.zeros(al0.shape,bool); hb[:hb0+PAD+1,:]=True
    skin=al0&hb&(lum>110)&(sat<90)   # light, low-saturation pixels in the head band = skin, eye whites, teeth
    lab,n=ndimage.label(skin,structure=np.ones((3,3))); sizes=ndimage.sum(skin,lab,range(1,n+1)); face=lab==(np.argmax(sizes)+1)
    face=ndimage.binary_closing(face,structure=np.ones((5,5))); face=ndimage.binary_fill_holes(face)   # include the eyes and mouth inside the skin blob
    ys,xs=np.where(face); box=np.zeros_like(face); box[ys.min():ys.max()+1,xs.min():xs.max()+1]=True; region=box&al0
    for j in range(K): B[j][region]=B[0][region]
    locked=int(region.sum()); print("face patch",int(xs.min()),int(ys.min()),int(xs.max()),int(ys.max()))
elif MODE in ("copy","pin"):
    for j in range(K): B[j][band]=B[0][band]; locked=int(band.sum())
else:
    key=(B[...,0].astype(np.int64)<<24)|(B[...,1].astype(np.int64)<<16)|(B[...,2].astype(np.int64)<<8)|(B[...,3]>0).astype(np.int64); locked=0
    for gy,gx in zip(*np.where(band)):
        col=key[:,gy,gx]; vals,cnt=np.unique(col,return_counts=True); k_=cnt.argmax()
        if cnt[k_]/K>=LOCK:
            src=np.where(col==vals[k_])[0][0]; B[:,gy,gx]=B[src,gy,gx]; locked+=1
shutil.rmtree(OUT,ignore_errors=True); os.makedirs(OUT+"/frames"); outF=[]
for j in range(K):
    d=off[j] if MODE not in ("pin","face") else np.array([0,0]); a=B[j,PAD-d[0]:PAD-d[0]+H,PAD-d[1]:PAD-d[1]+W]; Image.fromarray(a).save(f"{OUT}/frames/{os.path.basename(m['frames'][j]['file'])}"); outF.append(a)
m2=dict(m); m2["headStabilised"]={"mode":MODE,"band":BAND,"lock":LOCK,"cellsLocked":locked}; json.dump(m2,open(f"{OUT}/{os.path.basename(J)}","w"),indent=1)
print("frames",K,"head band rows",hb0+1,"locked cells",locked,"offsets",[tuple(int(v) for v in d) for d in off][::4])
