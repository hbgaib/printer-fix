# grid of N^3 RGB patches, 27 per row; writes grid.ps and grid.json (patch boxes in pt from top-left)
import json,sys
N=int(sys.argv[1]); lv=[round(i*255/(N-1)) for i in range(N)]
cols=[(r,g,b) for r in lv for g in lv for b in lv]
per=24; size=18.0; gap=4.0; x0=40; y0=40
ps=['%!PS','<< /PageSize [595.2756 841.8898] >> setpagedevice']; boxes=[]
for k,(r,g,b) in enumerate(cols):
    cx=x0+(k%per)*(size+gap); cy=y0+(k//per)*(size+gap)
    ps.append(f'{r/255:.5f} {g/255:.5f} {b/255:.5f} setrgbcolor {cx:.2f} {841.8898-cy-size:.2f} {size} {size} rectfill')
    boxes.append([r,g,b,cx,cy,size])
ps.append('showpage'); open('grid.ps','w').write('\n'.join(ps)); json.dump(boxes,open('grid.json','w'))
