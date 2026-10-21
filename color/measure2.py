# Decode Canon IJ raster (ESC (F multiraster, ESC (e skip in blocks) from gutenprint or Canon driver.
# usage: measure2.py prn boxes.json out.json TOP LEFT   (offsets in px @600dpi)
import sys,json
prn,boxes_f,out=sys.argv[1:4]; TOP=int(sys.argv[4]); LEFT=int(sys.argv[5])
d=open(prn,'rb').read(); boxes=json.load(open(boxes_f)); lpb=8; BITS=[2,2,1,1]
def unpack(p):
    lines=[];cur=bytearray();i=0
    while i<len(p):
        b=p[i]
        if b==0x80: lines.append(cur);cur=bytearray();i+=1;continue
        if b<0x80: cur+=p[i+1:i+2+b]; i+=2+b
        else: cur+=bytes([p[i+1]])*(257-b); i+=2
    return lines
rows={}; i=0; blk=0; ch=0
while True:
    i=d.find(b'\x1b(',i)
    if i<0: break
    c=d[i+2]; L=d[i+3]|(d[i+4]<<8); p=d[i+5:i+5+L]
    if c==0x46:
        for k,ln in enumerate(unpack(p)[:lpb]): rows.setdefault(blk*lpb+k,[b'']*4)[ch]=bytes(ln)
        ch+=1
        if ch==4: ch=0; blk+=1
    elif c==0x65 and L==2 and ch==0:
        blk+=(p[0]<<8)|p[1]
    i+=5+L
def val(line,x,bits):
    bi=x*bits//8
    if x<0 or bi>=len(line): return 0
    return (line[bi]>>(8-bits-(x*bits%8)))&((1<<bits)-1)
if len(sys.argv)>6:   # report first inked row/col for calibration
    ys=sorted(r for r,v in rows.items() if any(v)); print('first row',ys[0])
    ln=rows[ys[0]+20]; xs=[x for x in range(6000) if any(val(ln[c],x,BITS[c]) for c in range(4))]; print('first col',xs[0] if xs else None); sys.exit()
res=[]
for r,g,b,cx,cy,sz in boxes:
    m=3
    x0=int((cx+m)*600/72)-LEFT; x1=int((cx+sz-m)*600/72)-LEFT
    y0=int((cy+m)*600/72)-TOP;  y1=int((cy+sz-m)*600/72)-TOP
    tot=[0,0,0,0]; n=0
    for y in range(y0,y1,2):
        ln=rows.get(y,[b'']*4)
        for x in range(x0,x1,2):
            for c in range(4): tot[c]+=val(ln[c],x,BITS[c])
            n+=1
    res.append([r,g,b]+[t/n for t in tot])
json.dump(res,open(out,'w'))
