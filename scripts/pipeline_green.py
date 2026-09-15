"""Full green-screen pipeline: key -> cycle -> reconstruct -> speck kill -> every3 -> head copy -> sheets/videos. Usage: pipeline_green.py <workdir> <name>"""
import sys, os, json, shutil, subprocess, numpy as np
from PIL import Image
W,NAME=sys.argv[1],sys.argv[2]; here=os.path.dirname(os.path.abspath(__file__)); it=json.load(open(f"{W}/intake.json")); bg=it["background"]["rgb"]; cell=it["grid"]["cell"]; per=it["motion"]["period"] or 24
A0=24; A1=A0+2*per if 2*per>=16 else A0+4*per
if A1>it["frames"]: A0=it["frames"]-2*per-1; A1=it["frames"]-1
subprocess.run(["python3",f"{here}/key_green.py",W,str(A0),str(A1),"50","40"],check=True)
shutil.copy(f"{here}/reconstruct.py",f"{W}/run.py"); env=dict(os.environ,KEYDIR="keyed",KILLCOV="0.6",BG=",".join(map(str,bg)),TMPDIR=f"/tmp/{NAME}_tmp")
subprocess.run(["python3","run.py",str(A0),str(A1),str(cell),str(cell),"0","0","0","out","1"],cwd=W,env=env,check=True)
for src in ["out"]:
    d=f"{W}/{src}"; m=json.load(open(f"{d}/grok_walk.json")); F=[Image.open(f"{d}/"+f["file"]).convert("RGBA") for f in m["frames"]]; nx,ny=F[0].size; K=len(F)
    Z=3; cols=12; rws=(K+cols-1)//cols; s=Image.new("RGBA",(cols*nx*Z,rws*ny*Z),(255,0,255,255))
    for j,im in enumerate(F): s.alpha_composite(im.resize((nx*Z,ny*Z),Image.NEAREST),((j%cols)*nx*Z,(j//cols)*ny*Z))
    s.save(f"{d}/all_frames_magenta.png")
    sel=list(range(0,K,3)); e=f"{d}/every3"; shutil.rmtree(e,ignore_errors=True); os.makedirs(e+"/frames"); G=[F[j] for j in sel]
    for i,im in enumerate(G): im.save(f"{e}/frames/{NAME}_{i:02d}.png")
    sheet=Image.new("RGBA",(len(G)*nx,ny)); [sheet.paste(im,(i*nx,0)) for i,im in enumerate(G)]; sheet.save(f"{e}/{NAME}_sheet_1x.png"); sheet.resize((len(G)*nx*4,ny*4),Image.NEAREST).save(f"{e}/{NAME}_sheet_4x.png")
    json.dump({"name":NAME,"loop":True,"fps":8,"cell":{"w":nx,"h":ny},"gridPx":cell,"sourceFramesKept":sel,"frames":[{"file":f"frames/{NAME}_{i:02d}.png","durationMs":125} for i in range(len(G))]},open(f"{e}/{NAME}.json","w"),indent=1)
    t=f"/tmp/{NAME}_e3"; shutil.rmtree(t,ignore_errors=True); os.makedirs(t); n=0; Zv=4; Wc,Hc=nx*Zv+80,ny*Zv+80; Wc+=Wc%2; Hc+=Hc%2
    for _ in range(12):
        for im in G:
            for _r in range(3):
                c=Image.new("RGBA",(Wc,Hc),(38,40,51,255)); c.alpha_composite(im.resize((nx*Zv,ny*Zv),Image.NEAREST),(40,40)); c.convert("RGB").save(f"{t}/{n:05d}.png"); n+=1
    subprocess.run(["ffmpeg","-y","-v","error","-framerate","24","-i",f"{t}/%05d.png","-c:v","libx264","-pix_fmt","yuv420p","-crf","18",f"{e}/{NAME}_loop_4x_8fps.mp4"],check=True)
print(NAME,"done: cycle",A0,A1,"cell",cell)
