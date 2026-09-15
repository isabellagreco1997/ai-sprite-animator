"""Intake analysis for a character clip. Usage: intake.py <video> <workdir>  -> extracts frames, contact sheet, scorecard json."""
import sys, os, glob, json, subprocess, numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
V,W=sys.argv[1],sys.argv[2]; os.makedirs(f"{W}/raw",exist_ok=True)
if not glob.glob(f"{W}/raw/*.png"): subprocess.run(["ffmpeg","-v","error","-y","-i",V,f"{W}/raw/%04d.png"],check=True)
fs=sorted(glob.glob(f"{W}/raw/*.png")); N=len(fs); R=lambda j: np.array(Image.open(fs[j]).convert("RGB")).astype(int)
def border_colour(r): return np.median(np.concatenate([r[:6].reshape(-1,3),r[-6:].reshape(-1,3),r[:,:6].reshape(-1,3),r[:,-6:].reshape(-1,3)]),axis=0).round().astype(int)
bgs=[border_colour(R(j)) for j in range(0,N,max(1,N//12))]; bg=np.median(np.array(bgs),axis=0).round().astype(int)
bg0=border_colour(R(0)); frame0_odd=bool(np.abs(bg0-bg).max()>30)
g_ex=int(bg[1]-max(bg[0],bg[2])); kind="green" if g_ex>60 else ("magenta" if (bg[0]>150 and bg[2]>150 and bg[1]<100) else ("white" if bg.min()>230 else ("black" if bg.max()<25 else "other")))
# masks
def mask(r):
    d=np.abs(r-bg).max(axis=2); m=d>40
    if kind=="green": m=m&~((r[...,1]-np.maximum(r[...,0],r[...,2]))>40)
    m=ndimage.binary_opening(m,iterations=1); lab,n=ndimage.label(m); sizes=ndimage.sum(m,lab,range(1,n+1)); m=np.isin(lab,[i+1 for i in range(n) if sizes[i]>=40]); return ndimage.binary_fill_holes(m)
start=1 if frame0_odd else 0; M=[mask(R(j)) for j in range(start,N)]; sil=np.array([m.sum() for m in M])
# collision: pixels inside the filled silhouette within 6 of bg (white/black only meaningful)
coll=[]
for j in range(0,len(M),max(1,len(M)//6)):
    r=R(start+j); d=np.abs(r-bg).max(axis=2); core=ndimage.binary_erosion(M[j],iterations=3); coll.append(int((core&(d<=6)).sum()))
collision=int(np.median(coll))
# shadow / ground line: low-sat pixels under the silhouette bottom that are not bg
r=R(start+len(M)//2); m=M[len(M)//2]; ys=np.where(m)[0]; bot=ys.max(); band=r[max(0,bot-25):min(r.shape[0],bot+15)]; sat=band.max(axis=2)-band.min(axis=2); d=np.abs(band-bg).max(axis=2)
shadow=int(((d>6)&(d<60)&(sat<30)).sum()) if kind in("white","black","other") else int(((d>6)&(d<60)).sum())
# drift
cx=np.array([np.where(mm)[1].mean() for mm in M]); cy=np.array([np.where(mm)[0].mean() for mm in M]); drift=float(cx.max()-cx.min())
# motion: mask diff autocorr
ref=len(M)//4; diff=np.array([(M[j]^M[ref]).sum() for j in range(len(M))]); mins=[j for j in range(ref+8,len(M)-1) if diff[j]<diff[j-1] and diff[j]<=diff[j+1] and diff[j]<0.35*diff[ref+1:].max()]
period=None
if len(mins)>=2: period=int(np.median(np.diff([ref]+mins)))
still=bool(diff[ref+1:].max()<0.02*sil.mean())
# grid: variance fit on 2 frames, cells 3..9
def fit(f,a,c,ox,oy):
    H,Wd=a.shape; xs_=((np.arange(Wd)-ox)//c).astype(int); ys_=((np.arange(H)-oy)//c).astype(int); cid=ys_[:,None]*100000+xs_[None,:]
    ids,cols=cid[a],f[a]; u,inv=np.unique(ids,return_inverse=True); cnt=np.bincount(inv); var=0
    for k in range(3): sm=np.bincount(inv,cols[:,k]); sq=np.bincount(inv,cols[:,k]**2); var=var+sq/cnt-(sm/cnt)**2
    return (var*cnt).sum()/cnt.sum()
res={}
for j in [len(M)//3, 2*len(M)//3]:
    r=R(start+j); a=M[j]; ys,xs=np.where(a); r=r[ys.min():ys.max()+1,xs.min():xs.max()+1].astype(float); a=a[ys.min():ys.max()+1,xs.min():xs.max()+1]
    for c in np.arange(3.0,9.01,0.5): res.setdefault(float(c),[]).append(min(fit(r,a,c,ox,oy) for ox in np.arange(0,c,1.0) for oy in np.arange(0,c,1.0)))
cs=sorted(res); sc=[np.mean(res[c]) for c in cs]; dips={cs[i]:(sc[i-1]+sc[i+1])/2-sc[i] for i in range(1,len(cs)-1)}; bestc=max(dips,key=dips.get); dip=dips[bestc]; rel=dip/np.mean(sc)
h=int(np.median([np.ptp(np.where(mm)[0]) for mm in M])); w=int(np.median([np.ptp(np.where(mm)[1]) for mm in M]))
out={"video":os.path.basename(V),"frames":N,"background":{"rgb":bg.tolist(),"kind":kind},"frame0_odd":frame0_odd,"collision_px":collision,"shadow_px":shadow,"drift_px":round(drift,1),
     "motion":{"still":still,"period":period,"kind":"still" if still else ("loop" if period else "one-shot")},"grid":{"cell":bestc,"dip_rel":round(float(rel),3),"clear":bool(rel>0.03)},"char_size_px":[w,h],"sprite_size_at_cell":[int(w/bestc),int(h/bestc)]}
json.dump(out,open(f"{W}/intake.json","w"),indent=1); print(json.dumps(out))
sel=list(range(0,N,max(1,N//24))); cols=8; im0=Image.open(fs[0]); w2,h2=im0.width//2,im0.height//2; rows=(len(sel)+cols-1)//cols; s=Image.new("RGB",(cols*w2,rows*h2))
for i,j in enumerate(sel):
    im=Image.open(fs[j]).resize((w2,h2)); ImageDraw.Draw(im).text((4,4),str(j),fill=(255,0,0)); s.paste(im,((i%cols)*w2,(i//cols)*h2))
s.save(f"{W}/contact.png")
