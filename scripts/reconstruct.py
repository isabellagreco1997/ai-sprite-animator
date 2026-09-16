"""reconstruct.py: pixelise keyed frames with Retro Diffusion's pixel-art-fixer at ONE forced cell size for every frame.
Usage: KEYDIR=keyed KILLCOV=0.6 BG=r,g,b python3 reconstruct.py <A0> <A1> <cellX> <cellY> 0 0 0 <outdir> 1
(positional 5..7 are legacy lock/keyframe/temporal-vote options, keep them 0 for a faithful build; last arg 1 = keep the fixer's own colours)
env: KEYDIR (keyed frames dir), BG (background colour used by the speck kill), KILLCOV (min source coverage for near-background cells), PIXELFIXER (path to pixel-art-fixer/python), TMPDIR,
     ANCHOR=feet|none (feet, the default, pins each frame's feet baseline to the cycle's median grid row when it is within ANCHOR_TOL=0.6 cells of it, bigger lifts snap to the nearest row; none = the fixer's own per frame phase)."""
import numpy as np, sys, os, shutil, json, subprocess
from PIL import Image
from scipy import ndimage
sys.path.insert(0,os.path.expanduser(os.environ.get("PIXELFIXER","~/Projects/pixel-art-fixer/python"))); from pixelfixer.reconstruct import reconstruct   # git clone https://github.com/Retro-Diffusion/pixel-art-fixer
KEYDIR=os.environ.get("KEYDIR","keyed"); A0,A1=int(sys.argv[1]),int(sys.argv[2]); SX,SY=float(sys.argv[3]),float(sys.argv[4]); LOCK=float(sys.argv[5]) if len(sys.argv)>5 else 0.7; KF=int(sys.argv[6]) if len(sys.argv)>6 else 0; TV=int(sys.argv[7]) if len(sys.argv)>7 else 0; OUT=sys.argv[8] if len(sys.argv)>8 else "out"; RAW=int(sys.argv[9]) if len(sys.argv)>9 else 0; KILLCOV=float(os.environ.get('KILLCOV','0')); BG=np.array([int(v) for v in os.environ.get('BG','249,249,251').split(',')])
shutil.rmtree(OUT,ignore_errors=True); os.makedirs(OUT+"/frames")
src=[np.array(Image.open(f"{KEYDIR}/{j:04d}.png").convert("RGBA")) for j in range(A0,A1)]; H,W=src[0].shape[:2]; cols,rows=int(round(W/SX)),int(round(H/SY))
def clean_palette(a,dist=32,min_share=0.002,outline_lum=40):
    s_=a[...,3]==255; px=a[s_][:,:3].astype(int); u,cnt=np.unique(px,axis=0,return_counts=True); order=np.argsort(-cnt); cents=[]; members=[]
    for i in order:
        c=u[i]; d=[np.abs(c-k).sum() for k in cents]
        if d and min(d)<=dist: members[int(np.argmin(d))].append((c,cnt[i]))
        else: cents.append(c.copy()); members.append([(c,cnt[i])])
    P=np.array([np.average([m[0] for m in ms],axis=0,weights=[m[1] for m in ms]).round() for ms in members]).astype(int); size=np.array([sum(m[1] for m in ms) for ms in members]); P=P[size>=min_share*size.sum()]
    lum=P.mean(axis=1); dark=lum<outline_lum
    if dark.any(): P=np.vstack([P[~dark],P[dark][lum[dark].argmin()][None]])
    return P
pal=clean_palette(src[0]); print("palette",len(pal),flush=True)
ANCHOR=os.environ.get("ANCHOR","feet")   # feet (default): shift each source frame so the feet baseline sits on a fixed grid row and the torso keeps its column phase. ANCHOR=none = the fixer picks its own phase per frame
def baseline(a):
    m=a[...,3]>128; rc=m.sum(axis=1); xs=np.where(m)[1]; need=max(3,int(0.02*(xs.max()-xs.min()+1))); ys=np.where(rc>=need)[0]; return int(ys.max())+1
def torso_cx(a):
    m=a[...,3]>128; ys,xs=np.where(m); top=ys.min(); s=ys<=top+int((ys.max()-top)*0.4); return float(xs[s].mean())
def shifted(a,dy,dx):
    o=np.zeros_like(a); H_,W_=a.shape[:2]; ys=slice(max(0,dy),min(H_,H_+dy)); xs=slice(max(0,dx),min(W_,W_+dx)); o[ys,xs]=a[max(0,-dy):max(0,-dy)+(ys.stop-ys.start),max(0,-dx):max(0,-dx)+(xs.stop-xs.start)]; return o
if ANCHOR=="feet":
    cx0=torso_cx(src[0]); bases=[baseline(a) for a in src]; med=float(np.median(bases)); yref=int(round(round(med/SY)*SY)); TOL=float(os.environ.get("ANCHOR_TOL","0.6"))*SY; shifts=[]
    for j,a in enumerate(src):
        b=bases[j]
        if abs(b-med)<=TOL: dy=yref-b   # y: within 0.6 cell of the cycle's median baseline = jitter, pin the feet to the median's lattice line
        else: dy=int(round(round(b/SY)*SY))-b   # a real lift (heel off the ground, jump) = snap to the nearest lattice line, kept as whole rows
        dx=cx0-torso_cx(a); dx=int(round(((dx+SX/2)%SX)-SX/2))   # x: only the sub cell phase of the head+torso, whole cell drift is kept
        src[j]=shifted(a,dy,dx); shifts.append((dy,dx))
    print("anchor feet: median baseline",med,"-> row",yref,"lifted frames",[j for j,b in enumerate(bases) if abs(b-med)>TOL],"shifts dy/dx",shifts[::6],flush=True)
idxs=[]; RAWCOL=[]
for j,a in enumerate(src):
    img=reconstruct(a,SX,SY,cols,rows) if ANCHOR=="none" else reconstruct(a,SX,SY,cols,rows,use_phase=False,use_snap=False)
    r=np.array(img) if not isinstance(img,np.ndarray) else img
    if r.shape[2]==3: r=np.dstack([r,np.full(r.shape[:2],255,np.uint8)])
    al=r[...,3]>128; rgb=r[...,:3].astype(int)
    if KILLCOV>0:   # speck kill: light cells whose source coverage is low = anti-aliased background bleeding in
        sa=a[...,3]/255.0; cov=np.zeros((rows,cols))
        for gy in range(rows):
            y0,y1=int(round(gy*SY)),int(round((gy+1)*SY))
            for gx in range(cols):
                x0,x1=int(round(gx*SX)),int(round((gx+1)*SX)); blk=sa[y0:y1,x0:x1]; cov[gy,gx]=blk.mean() if blk.size else 0
        nearbg=(np.abs(rgb-BG).max(axis=2)<70)&al; al=al&~(nearbg&(cov<KILLCOV))
        bgc=np.abs(rgb-BG).max(axis=2)<60; edge=al&~ndimage.binary_erosion(al,structure=np.array([[0,1,0],[1,1,1],[0,1,0]]),border_value=0); al=al&~(edge&bgc)
        f4=np.array([[0,1,0],[1,1,1],[0,1,0]])
        for _ in range(2):   # isolated light cells on the silhouette edge (no light 4-neighbours) are bleed, not her
            light2=al&(np.abs(rgb-BG).max(axis=2)<90); edge2=al&~ndimage.binary_erosion(al,structure=f4,border_value=0); nb=ndimage.convolve(light2.astype(int),f4,mode="constant")-light2.astype(int); al=al&~(edge2&light2&(nb<2))
        lab_,n_=ndimage.label(al); sz=ndimage.sum(al,lab_,range(1,n_+1))
        for i_,s_ in enumerate(sz):
            if s_<=2: al[lab_==i_+1]=False
    if RAW: RAWCOL.append(np.where(al[...,None],rgb,-1)); idx=np.where(al,0,-1)
    else: ks=np.argmin(np.abs(rgb[...,None,:]-pal[None,None,:,:]).sum(axis=3),axis=2); idx=np.where(al,ks,-1)
    idxs.append(idx)
    if j==0: print("native",idx.shape[::-1],flush=True)
K=len(idxs); ny,nx=idxs[0].shape; A=np.stack(idxs)
if RAW:   # build a shared colour table from all frames' raw colours so the rest of the pipeline can stay index based
    allc=np.concatenate([c[c[...,0]>=0] for c in RAWCOL]); pal,inv=np.unique(allc,axis=0,return_inverse=True); pal=pal.astype(int); print("raw colours",len(pal),flush=True)
    for j in range(K):
        c=RAWCOL[j]; m=c[...,0]>=0; key=c[m]; ks=np.array([np.searchsorted(np.arange(len(pal)),0)]*0)
        # map each pixel colour to its index in pal via a dict
        lut={tuple(p):i for i,p in enumerate(pal)}; A[j][m]=[lut[tuple(v)] for v in key]
if TV>1:   # circular temporal mode over TV frames: a cell state must persist to count
    h=TV//2; B2=A.copy()
    for j in range(K):
        win=np.stack([A[(j+o)%K] for o in range(-h,h+1)])
        for gy in range(ny):
            for gx in range(nx):
                v,c=np.unique(win[:,gy,gx],return_counts=True); B2[j,gy,gx]=v[c.argmax()]
    A=B2; print("temporal vote",TV,flush=True)
if LOCK>0:   # head+torso aligned static lock, as keyframes.py PIN=3
    PAD=8; B=np.full((K,ny+2*PAD,nx+2*PAD),-1,int); off=[]
    def cen(idx):
        ys,xs=np.where(idx>=0); by=ys.min()+int((ys.max()-ys.min())*0.4); s=ys<=by; return np.array([ys[s].mean(),xs[s].mean()])
    c0=cen(A[0])
    for j in range(K):
        d=np.rint(cen(A[j])-c0).astype(int); off.append(d); B[j,PAD-d[0]:PAD-d[0]+ny,PAD-d[1]:PAD-d[1]+nx]=A[j]
    L=np.zeros(B.shape[1:],bool); MODE=np.full(B.shape[1:],-1,int); SHARE=np.zeros(B.shape[1:])
    for gy in range(B.shape[1]):
        for gx in range(B.shape[2]):
            col=B[:,gy,gx]; vals,cnt=np.unique(col,return_counts=True); k_=cnt.argmax(); MODE[gy,gx]=vals[k_]; SHARE[gy,gx]=cnt[k_]/K
            if MODE[gy,gx]>=0 and SHARE[gy,gx]>=LOCK: L[gy,gx]=True
    four=np.array([[0,1,0],[1,1,1],[0,1,0]])
    for _ in range(2): L|=~L&ndimage.binary_dilation(L,structure=four)&(SHARE>=0.5)
    for gy,gx in zip(*np.where(L)): B[:,gy,gx]=MODE[gy,gx]
    for j in range(K): d=off[j]; A[j]=B[j,PAD-d[0]:PAD-d[0]+ny,PAD-d[1]:PAD-d[1]+nx]
    print("locked",int(L.sum()),"offsets",[tuple(int(v) for v in d) for d in off][::6],flush=True)
# crop to union bbox
un=(A>=0).any(axis=0); ys,xs=np.where(un); y0,y1,x0,x1=ys.min(),ys.max()+1,xs.min(),xs.max()+1; A=A[:,y0:y1,x0:x1]; ny,nx=A.shape[1:]
if KF and KF<K:
    sel=[int(round(i*K/KF)) for i in range(KF)]; A=A[sel]; K=KF; print("key frames",sel,flush=True)
FPS=24 if not KF else int(round(24*KF/len(src)))
def render(idx):
    o=np.zeros((ny,nx,4),np.uint8); m=idx>=0; o[m,:3]=pal[idx[m]]; o[m,3]=255; return Image.fromarray(o)
ims=[render(A[j]) for j in range(K)]; sheet=Image.new("RGBA",(K*nx,ny))
for j,im in enumerate(ims): im.save(f"{OUT}/frames/grok_walk_{j:02d}.png"); sheet.paste(im,(j*nx,0))
sheet.save(f"{OUT}/grok_walk_sheet_1x.png"); sheet.resize((K*nx*4,ny*4),Image.NEAREST).save(f"{OUT}/grok_walk_sheet_4x.png")
json.dump({"name":"grok_walk","loop":True,"fps":FPS,"cell":{"w":int(nx),"h":int(ny)},"gridPx":[SX,SY],"sourceFrames":[A0,A1],"frames":[{"file":f"frames/grok_walk_{j:02d}.png","durationMs":int(round(1000/FPS))} for j in range(K)],"palette":pal.tolist()},open(f"{OUT}/grok_walk.json","w"),indent=1)
print("sprite",nx,ny,"frames",K,"distinct",len(set(im.tobytes() for im in ims)),flush=True)
Z=4; d=os.path.join(os.environ.get("TMPDIR","/tmp"),"gk"); shutil.rmtree(d,ignore_errors=True); os.makedirs(d); n=0
Wc=W+nx*Z+60; Hc=max(H,ny*Z)+40; Wc+=Wc%2; Hc+=Hc%2
for _ in range(6):
    for j in range(K):
      for _r in range(24//FPS):
        can=Image.new("RGBA",(Wc,Hc),(38,40,51,255)); can.alpha_composite(Image.fromarray(src[sel[j] if KF and KF<len(src) else j]),(20,20)); can.alpha_composite(ims[j].resize((nx*Z,ny*Z),Image.NEAREST),(W+40,20)); can.convert("RGB").save(f"{d}/{n:05d}.png"); n+=1
subprocess.run(["ffmpeg","-y","-v","error","-framerate","24","-i",f"{d}/%05d.png","-c:v","libx264","-pix_fmt","yuv420p","-crf","18",f"{OUT}/grok_walk_vs_video.mp4"],check=True)
shutil.rmtree(d); os.makedirs(d); n=0; W2,H2=nx*Z+80,ny*Z+80; W2+=W2%2; H2+=H2%2
for _ in range(12):
    for j in range(K):
      for _r in range(24//FPS):
        can=Image.new("RGBA",(W2,H2),(38,40,51,255)); can.alpha_composite(ims[j].resize((nx*Z,ny*Z),Image.NEAREST),(40,40)); can.convert("RGB").save(f"{d}/{n:05d}.png"); n+=1
subprocess.run(["ffmpeg","-y","-v","error","-framerate","24","-i",f"{d}/%05d.png","-c:v","libx264","-pix_fmt","yuv420p","-crf","18",f"{OUT}/grok_walk_loop_4x.mp4"],check=True); print("done")
