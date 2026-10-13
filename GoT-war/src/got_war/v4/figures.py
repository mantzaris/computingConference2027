"""Compact SVG/PDF portfolio from Graphviz layouts and validated model records."""
import html
import json
import math
from pathlib import Path
import shlex
import subprocess
import textwrap

from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.colors import HexColor

from ..v3.core import fingerprint, informative, verify_reported_result


def model_hash(record):
    # The same identifier survives removal of copyrighted quote text from the
    # public bundle; locations and quote hashes preserve the evidence identity.
    import hashlib
    def normalize(x):
        if isinstance(x,list):return [normalize(v) for v in x]
        if isinstance(x,dict):
            r={k:normalize(v) for k,v in x.items() if k!='quote'}
            if 'quote' in x:r['quote_sha256']=hashlib.sha256(x['quote'].encode()).hexdigest()
            return r
        return x
    return fingerprint({'representation':normalize(record['representation']),
        'functions':[s['typed_expressions'] for s in record['scenarios']],
        'queries':[q['do'] for q in record['queries']]})


def clean(s):
    return str(s).translate(str.maketrans({'’':"'",'‘':"'",'–':'-','—':'-','→':'->','×':'x','…':'...'}))


def lines(s,width=24):
    return '\n'.join(textwrap.wrap(clean(s),width,break_long_words=False))


class CanvasPair:
    def __init__(self,*canvases):self.canvases=canvases
    def __getattr__(self,name):
        def call(*args,**kwargs):
            results=[getattr(c,name)(*args,**kwargs) for c in self.canvases]
            return results[0]
        return call


class Drawing:
    portfolio=None
    def __init__(self,path,width,height):
        self.stem=Path(path);self.w=width;self.h=height
        self.single_pdf=Canvas(str(self.stem.with_suffix('.pdf')),pagesize=(width,height),pageCompression=1,invariant=1)
        if self.portfolio is not None:self.portfolio.setPageSize((width,height))
        self.pdf=CanvasPair(self.single_pdf,self.portfolio) if self.portfolio is not None else self.single_pdf
        self.pdf.setTitle(self.stem.stem)
        self.styles={}
        self.svg=['<svg xmlns="http://www.w3.org/2000/svg" width="%gpt" height="%gpt" viewBox="0 0 %g %g">'%(width,height,width,height),
                  '<style>text{font-family:Helvetica,Arial,sans-serif;fill:#203744}.edge{fill:none;stroke-width:1.1}</style>',
                  '<rect width="100%" height="100%" fill="white"/>']

    def text(self,x,y,text,size=11,color='#203744',anchor='middle',bold=False):
        text=clean(text)
        key=(size,color,anchor,bold)
        if key not in self.styles:self.styles[key]='t'+str(len(self.styles))
        self.svg.append('<text x="%.1f" y="%.1f" class="%s">%s</text>'%(x,self.h-y,self.styles[key],html.escape(text)))
        self.pdf.setFillColor(HexColor(color));self.pdf.setFont('Helvetica-Bold' if bold else 'Helvetica',size)
        if anchor=='middle':self.pdf.drawCentredString(x,y,text)
        elif anchor=='end':self.pdf.drawRightString(x,y,text)
        else:self.pdf.drawString(x,y,text)

    def block(self,x,y,text,size=11,color='#203744',anchor='middle',bold=False):
        for i,line in enumerate(str(text).split('\n')):self.text(x,y-i*(size+3),line,size,color,anchor,bold)

    def box(self,x,y,w,h,fill='#eef4f7',stroke='#587482'):
        self.svg.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="5" fill="%s" stroke="%s"/>'%(x,y and self.h-y-h or self.h-h,w,h,fill,stroke))
        self.pdf.setFillColor(HexColor(fill));self.pdf.setStrokeColor(HexColor(stroke));self.pdf.roundRect(x,y,w,h,5,stroke=1,fill=1)

    def path(self,points,color,dashed=False):
        p=self.pdf.beginPath();p.moveTo(*points[0]);d='M%.1f %.1f'%(points[0][0],self.h-points[0][1])
        for i in range(1,len(points),3):
            if i+2<len(points):
                a,b,c=points[i:i+3];p.curveTo(*a,*b,*c)
                d+='C%.1f %.1f %.1f %.1f %.1f %.1f'%(a[0],self.h-a[1],b[0],self.h-b[1],c[0],self.h-c[1])
        self.svg.append('<path class="edge" d="'+d+'" stroke="'+color+'"'+(' stroke-dasharray="4 3"' if dashed else '')+'/>')
        self.pdf.setStrokeColor(HexColor(color));self.pdf.setLineWidth(1.1);self.pdf.setDash(4,3) if dashed else self.pdf.setDash()
        self.pdf.drawPath(p)
        a,b=points[-2:];angle=math.atan2(b[1]-a[1],b[0]-a[0]);tip=(b[0]+5*math.cos(angle),b[1]+5*math.sin(angle))
        tri=[tip,(b[0]+2.5*math.sin(angle),b[1]-2.5*math.cos(angle)),(b[0]-2.5*math.sin(angle),b[1]+2.5*math.cos(angle))]
        self.svg.append('<polygon points="'+ ' '.join('%.1f,%.1f'%(x,self.h-y) for x,y in tri)+'" fill="'+color+'"/>')
        p=self.pdf.beginPath();p.moveTo(*tri[0]);p.lineTo(*tri[1]);p.lineTo(*tri[2]);p.close()
        self.pdf.setFillColor(HexColor(color));self.pdf.drawPath(p,stroke=0,fill=1);self.pdf.setDash()

    def save(self):
        css=''.join('.%s{font-size:%gpx;fill:%s;text-anchor:%s;%s}'%(name,size,color,anchor,'font-weight:bold' if bold else '') for (size,color,anchor,bold),name in self.styles.items())
        self.svg.insert(2,'<style>'+css+'</style>')
        self.svg.append('</svg>');self.stem.with_suffix('.svg').write_text(''.join(self.svg))
        self.pdf.showPage();self.single_pdf.save()


def graph(record,path,number,detail=False):
    rep=record['representation'];spec=record['scope'];edges=rep['edges'];nodes=rep['variables'];selected=None
    if not set(record['operative_edge_ids'])==set(record['displayed_edge_ids'])=={e['id'] for e in edges}:
        raise ValueError('Cannot display a model with silently withheld operative edges')
    if detail:
        child=record.get('detail_child',spec.get('detail_child'))
        if child is None:child=max(rep['mechanisms'],key=lambda m:len(m['parents']))['child']
        selected=next(m for m in rep['mechanisms'] if m['child']==child)
        keep={child,*selected['parents']}
        for e in edges:
            if e['child'] in selected['parents']:keep.add(e['parent'])
        edges=[e for e in edges if e['parent'] in keep and e['child'] in keep]
        nodes=[n for n in nodes if n['id'] in keep]
    q=lambda x:json.dumps(str(x))
    # Choose wrapping by usable font size in a 7 x 9.5 inch publication box.
    # This changes layout only; no edge or causal content is dropped.
    layouts=[];extra=170 if detail else 77
    for nw,ew in ([(14,17)] if detail else [(14,17),(18,23),(22,29),(25,34)]):
        dot=['digraph G { graph [rankdir=TB,nodesep=.16,ranksep=.25,splines=polyline,margin=0]; node [shape=box,fontname=Helvetica,fontsize=13,margin=".09,.06"]; edge [fontname=Helvetica,fontsize=11];']
        for n in nodes:
            label=lines(n['label'],nw)+('\n[factually absent]' if n['factual']==0 else '')
            dot.append(q(n['id'])+' [label='+q(label)+'];')
        for e in edges:
            if not informative(e['label']):raise ValueError('Uninformative display edge')
            dot.append(q(e['parent'])+' -> '+q(e['child'])+' [label='+q(lines(e['label'],ew)+'\n'+e['id'])+'];')
        dot.append('}')
        plain=subprocess.check_output(['dot','-Tplain'],input='\n'.join(dot).encode()).decode()
        parsed=[shlex.split(x) for x in plain.splitlines()];dims=parsed[0];gw,gh=float(dims[2])*72,float(dims[3])*72
        width=max(440,gw+28);height=gh+extra+65
        layouts.append((min(1,504/width,684/height),parsed,gw,gh,width,height,nw,ew))
    scale,parsed,gw,gh,width,height,nw,ew=max(layouts,key=lambda x:x[0]);d=Drawing(path,width,height)
    subtitle='mechanism detail' if detail else 'causal overview'
    title=lines('%02d | %s'%(number,clean(spec['title'])),int(width/7.4))
    d.block(width/2,height-17,title,13,bold=True)
    d.text(width/2,height-51,subtitle+' - generated TV interpretation',10.5)
    ox=(width-gw)/2;oy=extra
    for row in parsed:
        if row[0]=='edge':
            count=int(row[3]);coords=list(map(float,row[4:4+count*2]));pts=[(ox+coords[i]*72,oy+coords[i+1]*72) for i in range(0,len(coords),2)]
            e=next(e for e in edges if e['parent']==row[1] and e['child']==row[2])
            color={'explicit':'#247b77','contextual':'#9a652b'}.get(e['status'],'#8a5b86')
            d.path(pts,color,e['status'] not in ('explicit','contextual'))
            tail=row[4+count*2:]
            if len(tail)>=5:
                label,x,y=tail[:3];ls=label.replace('\\n','\n').split('\n')
                d.block(ox+float(x)*72,oy+float(y)*72+(len(ls)-1)*7-3,'\n'.join(ls),10.5,color)
    for row in parsed:
        if row[0]=='node':
            ident=row[1];x,y,w,h=map(float,row[2:6]);n=next(n for n in nodes if n['id']==ident)
            cx,cy=ox+x*72,oy+y*72
            fill='#dcedeb' if ident==rep['outcome'] else '#f8f0df' if n['boundary']=='fixed_context' else '#f1f5f8'
            if n['factual']==0:fill='#fae9e5'
            d.box(cx-w*36,cy-h*36,w*72,h*72,fill)
            text=row[6].replace('\\n','\n');ls=text.split('\n');d.block(cx,cy+(len(ls)-1)*8-4,text,12)
    if detail:
        d.text(20,extra-22,'Joint mechanism '+selected['id'],11,anchor='start',bold=True)
        d.block(20,extra-39,lines(selected['joint_description'],int((width-40)/5.6)),10.5,anchor='start')
        refs=', '.join(sorted({r['passage_id'] for r in selected['evidence']}))
        d.block(20,87,lines('Passages: '+refs,int((width-40)/5.3)),10,anchor='start')
        local=record['partial_family']['local'][selected['child']]
        d.text(20,55,'Partial function: 1 observed row; %d input rows remain unconstrained.'%(len(local['rows'])-1),10,anchor='start')
        d.text(20,40,'Local view. Full operative model: overview. References and tables: catalogue.',9,anchor='start')
    else:
        d.block(width/2,extra-22,lines('Outcome: '+spec['outcome'],int((width-35)/5.5)),10.5)
    d.text(width/2,23,'Teal: direct process evidence | Ochre: contextual inference | Dashed: hypothesis',9)
    d.text(width/2,9,'All complete functions add assumptions. Independent researcher review pending.',9)
    d.save()
    return {'number':number,'case':record['case'],'view':subtitle,'stem':Path(path).name,'width_pt':width,'height_pt':height,
        'minimum_body_font_at_7inch':10.5*min(1,504/width),'minimum_body_font_in_publication_box':10.5*scale,
        'layout_wrap':[nw,ew], 'edge_ids':[e['id'] for e in edges],
        'model_sha256':model_hash(record),'detail_child':selected['child'] if selected else None,
        'caption':spec['detail_caption'] if detail else spec['overview_caption']}


def interventions(record,path,number):
    w,h=560,455;d=Drawing(path,w,h);spec=record['scope']
    d.text(w/2,h-22,'%02d | %s'%(number,clean(spec['title'])),14,bold=True)
    d.text(w/2,h-41,'What changes under the declared alternatives?',12)
    d.block(20,h-62,lines(spec['outcome'],91),10.5,anchor='start')
    d.text(20,h-98,'Observed outcome: YES. Scenario answers below are conditional.',11,anchor='start',bold=True)
    cols=[20,294,390,490];heads=['Selected question','Partial family','Scenario A','Scenario B']
    for x,t in zip(cols,heads):d.text(x,h-122,t,10,anchor='start')
    for i,q in enumerate(record['queries']):
        y=h-144-i*65;d.box(15,y-49,w-30,60,'#f5f8fa','#d9e0e5')
        d.block(22,y+1,lines(q['question'],44),10.5,anchor='start')
        vals=q['partial_result']['values'];shown='Unknown' if len(vals)!=1 else ('Yes' if vals==[1] else 'No')
        d.text(cols[1],y-17,shown,11,anchor='start',bold=True)
        for j,r in enumerate(q['conditional'][:2]):
            vals=r['result']['values'];text='Yes' if vals==[1] else 'No' if vals==[0] else 'Unknown'
            d.text(cols[j+2],y-17,text,12,'#247b77' if text=='Yes' else '#a64c43' if text=='No' else '#8a5b86',anchor='start',bold=True)
    y=108
    for label,s in zip(['A','B'],record['scenarios'][:2]):
        d.block(20,y,lines(label+': '+s['interpretation'],94),10,anchor='start');y-=42
    d.text(w/2,12,'Same mechanisms/background reused; no probabilities or natural counterfactual gold.',9)
    d.save()
    return {'number':number,'case':record['case'],'view':'intervention sensitivity','stem':Path(path).name,
        'width_pt':w,'height_pt':h,'minimum_body_font_at_7inch':10.5*504/w,
        'model_sha256':model_hash(record),'query_ids':[q['id'] for q in record['queries']],
        'caption':spec['intervention_caption']}


def render_case(root,record,index):
    root=Path(root);folder=root/'figures/v4';folder.mkdir(parents=True,exist_ok=True);items=[]
    for q in record['queries']:
        for answer in q['conditional']:
            s=next(s for s in record['scenarios'] if s['id']==answer['scenario'])
            if not verify_reported_result(record['representation'],s['family'],q['do'],answer['result'])['passed']:
                raise ValueError('Figure result disagrees with its operative model')
    for offset,view in enumerate(['overview','detail','interventions']):
        number=index*3+offset+1;path=folder/('%02d_%s_%s'%(number,record['case'],view))
        item=interventions(record,path,number) if view=='interventions' else graph(record,path,number,view=='detail')
        # PNGs are local previews and stay ignored under the existing storage policy.
        subprocess.run(['pdftoppm','-png','-singlefile','-scale-to','1200',str(path.with_suffix('.pdf')),str(path)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        items.append(item)
    return items


if __name__=='__main__':
    import sys
    root=Path(sys.argv[1]);case=sys.argv[2];cfg=json.loads((root/'configs/v4_campaign.json').read_text())
    i=next(i for i,c in enumerate(cfg['cases']) if c['id']==case)
    record=json.loads((root/'runs/application_v4_20261013'/case/'validated.json').read_text())
    record['scope']=cfg['cases'][i]
    print(json.dumps(render_case(root,record,i)))
