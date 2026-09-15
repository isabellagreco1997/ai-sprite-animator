import sys, json, os, shutil, subprocess
from PIL import Image, ImageDraw
w,name=sys.argv[1],sys.argv[2]; it=json.load(open(f"{w}/intake.json")); bg=",".join(map(str,it["background"]["rgb"])); per=it["motion"]["period"]; A0=24; A1=A0+2*per
cells=["1.0","2.0","3.0","3.5","4.0","4.5","6.0"]
for c in cells:
    if not os.path.exists(f"{w}/out_c{c}/grok_walk.json"):
        subprocess.run(["python3",os.path.join(os.path.dirname(os.path.abspath(__file__)),"reconstruct.py"),str(A0),str(A1),c,c,"0","0","0",f"out_c{c}","1"],cwd=w,env=dict(os.environ,KEYDIR="keyed",KILLCOV="0.6",BG=bg,TMPDIR=f"/tmp/{name}_c{c}"),check=True,capture_output=True)
sets={c:[Image.open(f"{w}/out_c{c}/"+f["file"]).convert("RGBA") for f in json.load(open(f"{w}/out_c{c}/grok_walk.json"))["frames"]] for c in cells}
K=len(sets["4.0"]); sel=list(range(0,K,3)); target=380; panels=[]
for c in cells:
    nx,ny=sets[c][0].size; Z=max(1,round(target/ny)); panels.append((c,Z,nx*Z,ny*Z))
W=sum(p[2] for p in panels)+40*(len(panels)+1); H=max(p[3] for p in panels)+90; W+=W%2; H+=H%2
t=f"/tmp/{name}_gc"; shutil.rmtree(t,ignore_errors=True); os.makedirs(t); n=0
for _ in range(8):
    for j in sel:
        for _r in range(3):
            can=Image.new("RGBA",(W,H),(38,40,51,255)); dr=ImageDraw.Draw(can); x=40
            for (c,Z,pw,ph) in panels:
                im=sets[c][j]; can.alpha_composite(im.resize((pw,ph),Image.NEAREST),(x,H-40-ph)); nx,ny=im.size; dr.text((x,H-30),f"{c} px -> {nx}x{ny}",fill=(220,220,220,255)); x+=pw+40
            can.convert("RGB").save(f"{t}/{n:05d}.png"); n+=1
subprocess.run(["ffmpeg","-y","-v","error","-framerate","24","-i",f"{t}/%05d.png","-c:v","libx264","-pix_fmt","yuv420p","-crf","18",f"{w}/{name}_grid_sizes_every3.mp4"],check=True); print(name,"ok",len(sel),"frames")
