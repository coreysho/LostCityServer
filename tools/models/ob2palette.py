#!/usr/bin/env python3
"""Dump a 377 .ob2 model's face colours and the RGB15 values a .obj config can
use as recolNs to target them.  Mirrors engine/src/util/ColorConversion.ts."""
import sys, os
from collections import Counter

def hsl24to16(h,s,l):
    if l>243: s>>=4
    elif l>217: s>>=3
    elif l>192: s>>=2
    elif l>179: s>>=1
    return (((h&0xff)>>2)<<10)+((s>>5)<<7)+(l>>1)

def rgb_to_hsl(r,g,b):
    mn=min(r,g,b); mx=max(r,g,b)
    h=0.0; s=0.0; l=(mn+mx)/2.0
    if mn!=mx:
        s=(mx-mn)/(mx+mn) if l<0.5 else (mx-mn)/(2.0-mx-mn)
        if r==mx: h=(g-b)/(mx-mn)
        elif g==mx: h=(b-r)/(mx-mn)+2.0
        else: h=(r-g)/(mx-mn)+4.0
    h/=6.0
    hue=int(h*256.0); sat=int(s*256.0); lig=int(l*256.0)
    sat=max(0,min(255,sat)); lig=max(0,min(255,lig))
    return hsl24to16(hue,sat,lig)

def rgb15_to_hsl16(v):
    return rgb_to_hsl(((v>>10)&31)/31.0, ((v>>5)&31)/31.0, (v&31)/31.0)

TABLE=[rgb15_to_hsl16(v) for v in range(32768)]
REV={}
for v,h in enumerate(TABLE): REV.setdefault(h,[]).append(v)

def rgb15(v): return ((v>>10)&31,(v>>5)&31,v&31)
def hex24(v):
    r,g,b=rgb15(v); return '#%02x%02x%02x'%(r<<3,g<<3,b<<3)

def g2(b,p): return (b[p]<<8)|b[p+1], p+2
def g1(b,p): return b[p], p+1

def face_colours(path):
    b=open(path,'rb').read(); p=len(b)-18
    vcount,p=g2(b,p); fcount,p=g2(b,p); tcount,p=g1(b,p)
    var6,p=g1(b,p); var7,p=g1(b,p); var8,p=g1(b,p); var9,p=g1(b,p); var10,p=g1(b,p)
    var11,p=g2(b,p); var12,p=g2(b,p); var13,p=g2(b,p); var14,p=g2(b,p)
    off=vcount+fcount
    if var7==255: off+=fcount
    if var9==1: off+=fcount
    if var6==1: off+=fcount
    if var10==1: off+=vcount
    if var8==1: off+=fcount
    col=off+var14
    total=col+fcount*2+tcount*6+var11+var12+var13
    if total!=len(b)-18: raise ValueError(f'{path}: length check failed ({total} vs {len(b)-18})')
    return vcount,fcount,Counter((b[col+i*2]<<8)|b[col+i*2+1] for i in range(fcount))

def target(rgb):           # rgb15 value -> what to write as recolNd
    return rgb

if __name__=='__main__':
    args=sys.argv[1:]
    if args and args[0]=='--to':      # --to R G B  -> rgb15 value for recolNd
        r,g,b=(int(x) for x in args[1:4])
        v=(r<<10)|(g<<5)|b
        print(f'recolNd={v}   rgb555=({r},{g},{b})  {hex24(v)}  hsl16={TABLE[v]}')
        sys.exit()
    for path in args:
        v,f,c=face_colours(path)
        print(f'== {os.path.basename(path)}  verts={v} faces={f}')
        for hsl,n in c.most_common():
            cands=REV.get(hsl,[])
            pick=max(cands, key=lambda x: sum(rgb15(x))) if cands else None
            samples=', '.join(str(x) for x in cands[:6])
            print(f'   hsl16={hsl:<6} faces={n:<4} recolNs= {pick}   (any of: {samples}{" ..." if len(cands)>6 else ""})')
