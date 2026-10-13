"""Reassess archived stories and render compact, model-linked publication views.

Run from GoT-war: python3 scripts/publication_figures.py
No inference; no original result, generation, or figure is overwritten.
"""
import copy
import hashlib
import html
import json
import os
import re
from pathlib import Path
import shlex
import subprocess
import sys
import textwrap

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from got_war.simple_stories import frozen, load_records, verify_references
from got_war.story_reassessment import write_audit
from got_war.v3.core import fingerprint, verify_reported_result
from got_war.v4.figures import Drawing, model_hash
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from reportlab.pdfgen.canvas import Canvas
from v4_reproduce import load, restore_models

WIDTH_MM = 122  # svproc.cls text width; override via --width-mm for another venue
PT_PER_MM = 72/25.4
WORK = ROOT/'.private/publication_work'


def fonts():
    for name, family, style in [('PubTimes', 'Times New Roman', 'Regular'),
                                ('PubBold', 'Times New Roman', 'Bold'),
                                ('PubMath', 'DejaVu Serif', 'Book')]:
        path = subprocess.check_output(['fc-match', '-f', '%{file}', family+':style='+style], text=True).strip()
        pdfmetrics.registerFont(TTFont(name, path))


def compact_pdf(path):
    """Subset embedded fonts without rasterizing; keep previews/build files local."""
    temp = WORK/(path.stem+'_compact.pdf')
    subprocess.run(['gs','-q','-dBATCH','-dNOPAUSE','-sDEVICE=pdfwrite',
        '-dCompatibilityLevel=1.5','-dEmbedAllFonts=true','-dSubsetFonts=true',
        '-dCompressFonts=true','-dOmitInfoDate=true','-dOmitID=true',
        '-sOutputFile='+str(temp),str(path)], check=True, capture_output=True)
    path.write_bytes(temp.read_bytes())
    font_report = subprocess.check_output(['pdffonts',str(path)], text=True)
    rows = [r.split() for r in font_report.splitlines()[2:] if r.strip()]
    # The trailing columns are emb/sub/uni/object/ID, irrespective of font type.
    if not rows or any(r[-5] != 'yes' for r in rows):
        raise ValueError('Every PDF font must be embedded: '+str(path))
    return font_report


class PublicationDrawing(Drawing):
    """Reuse vector graph primitives, with embedded serif fonts and tight bounds."""
    def __init__(self, path, width, height):
        self.stem, self.w, self.h = Path(path), width, height
        self.single_pdf = Canvas(str(self.stem.with_suffix('.pdf')), pagesize=(width,height),
            pageCompression=1, invariant=1, initialFontName='PubTimes', initialFontSize=9)
        self.pdf = self.single_pdf
        self.pdf.setTitle(self.stem.stem)
        self.styles = {}
        self.svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="%gpt" height="%gpt" viewBox="0 0 %g %g">' %
                    (width,height,width,height), '<style>.edge{fill:none;stroke-width:1.1}</style>',
                    '<rect width="100%" height="100%" fill="white"/>']
        self.text_bounds = []

    def text(self, x, y, text, size=9, color='#111111', anchor='middle', bold=False, math_font=False):
        text = str(text)
        font = 'PubMath' if math_font else 'PubBold' if bold else 'PubTimes'
        family = 'DejaVu Serif' if math_font else 'Times New Roman'
        self.svg.append('<text x="%.2f" y="%.2f" style="font-family:%s,serif;font-size:%.2fpx;text-anchor:%s;fill:%s;%s">%s</text>' %
            (x, self.h-y, family, size, anchor, color, 'font-weight:bold;' if bold else '', html.escape(text)))
        self.pdf.setFillColor(HexColor(color)); self.pdf.setFont(font, size)
        w = pdfmetrics.stringWidth(text, font, size)
        left = x-w/2 if anchor == 'middle' else x-w if anchor == 'end' else x
        self.text_bounds.append([left, y-size*.25, left+w, y+size*.85])
        self.pdf.drawString(left, y, text)

    def box(self, x, y, w, h, fill='#ffffff', stroke='#555555'):
        self.svg.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="%s" stroke="%s" stroke-width=".65"/>' %
                        (x, self.h-y-h, w, h, fill, stroke))
        self.pdf.setFillColor(HexColor(fill)); self.pdf.setStrokeColor(HexColor(stroke)); self.pdf.setLineWidth(.65)
        self.pdf.rect(x, y, w, h, stroke=1, fill=1)

    def rule(self, x1, x2, y):
        self.svg.append('<path d="M%g %g H%g" fill="none" stroke="#555" stroke-width=".5"/>' % (x1, self.h-y, x2))
        self.pdf.setStrokeColor(HexColor('#555555')); self.pdf.setLineWidth(.5); self.pdf.line(x1, y, x2, y)

    def save(self):
        if any(x1 < -.2 or x2 > self.w+.2 or y1 < 0 or y2 > self.h for x1,y1,x2,y2 in self.text_bounds):
            raise ValueError('Text exceeds publication crop: '+str(self.stem))
        super().save()


def wrap(s, chars):
    return '\n'.join(textwrap.wrap(s, chars, break_long_words=False, break_on_hyphens=False))


def check_display_equations(lines, equation_sets):
    """Every displayed equation is an exact notational rewrite of an archive rule."""
    for line in lines:
        pieces = re.split(r';| versus ', line)
        child = None
        for piece in pieces:
            if '=' in piece:
                child, expr = map(str.strip, piece.split('=', 1))
            else:
                expr = piece.strip()
            normalized = expr.replace('∧', 'and').replace('∨', 'or').replace('¬', 'not ')
            normalize = lambda s: re.sub(r'\s+', '', s)
            if child is None or not any(child in eqs and normalize(eqs[child]) == normalize(normalized)
                                        for eqs in equation_sets):
                raise ValueError('Displayed equation has no archived counterpart: '+piece)


def layout(spec, width):
    """Optimize wrapping without reducing the final 9/8.5-point typography."""
    candidates = []
    for node_wrap, edge_wrap in [(26,24),(24,24),(22,22),(20,20),(18,18),(18,16),(16,14),(14,13),(13,12),(12,11),(11,10)]:
        dot = ['digraph G { graph [rankdir='+spec.get('rankdir','TB')+', nodesep=.15, ranksep=.14, splines=spline, margin=0, pad=0];',
               'node [shape=box, fontname="Times-Roman", fontsize=9, margin=".045,.035", height=0, width=0];',
               'edge [fontname="Times-Roman", fontsize=8.5, arrowsize=.5];']
        for ident, label in spec['nodes'].items():
            dot.append(json.dumps(ident)+' [label='+json.dumps(wrap(label, node_wrap))+'];')
        for e in spec['edges']:
            padded = '\n'.join('  '+line+'  ' for line in wrap(e['label'], edge_wrap).split('\n'))
            dot.append(json.dumps(e['parent'])+' -> '+json.dumps(e['child'])+
                       ' [label='+json.dumps(padded)+'];')
        for rank in spec.get('ranks', []):
            dot.append('{rank=same; '+';'.join(json.dumps(x) for x in rank)+';}')
        dot.append('}')
        source = '\n'.join(dot)
        plain = subprocess.check_output(['dot', '-Tplain'], input=source, text=True)
        parsed = [shlex.split(line) for line in plain.splitlines()]
        gw, gh = map(lambda n:float(n)*72, parsed[0][2:4])
        if gw <= width-6:
            candidates.append((gh, gw, parsed, source, [node_wrap, edge_wrap]))
    if not candidates:
        raise ValueError('Graph cannot fit at readable type size: '+spec['stem'])
    return min(candidates, key=lambda x: x[0])


def draw_graph(d, spec, parsed, gw, ox, oy):
    for row in parsed:
        if row[0] != 'edge':
            continue
        count = int(row[3]); coords = list(map(float, row[4:4+count*2]))
        points = [(ox+coords[i]*72, oy+coords[i+1]*72) for i in range(0, len(coords), 2)]
        edge = next(e for e in spec['edges'] if e['parent'] == row[1] and e['child'] == row[2])
        d.path(points, '#555555', edge.get('status') == 'contextual')
        label, x, y = row[4+count*2:7+count*2]
        lines = label.replace('\\n', '\n').split('\n')
        for i, line in enumerate(lines):
            d.text(ox+float(x)*72, oy+float(y)*72+(len(lines)-1)*4.75-2.9-i*9.5, line, 8.5)
    for row in parsed:
        if row[0] != 'node':
            continue
        ident = row[1]; x,y,w,h = [float(v)*72 for v in row[2:6]]
        d.box(ox+x-w/2, oy+y-h/2, w, h, '#eeeeee' if ident == spec['focus'] else '#ffffff')
        lines = row[6].replace('\\n', '\n').split('\n')
        for i, line in enumerate(lines):
            d.text(ox+x, oy+y+(len(lines)-1)*5.1-3.1-i*10.2, line, 9)


def render(spec, width):
    if spec.get('panels'):
        return render_panels(spec, width)
    gh, gw, parsed, dot, wraps = layout(spec, width)
    base = 13*len(spec['equations'])+9
    table = 106 if spec.get('comparison') else 0
    panel = 14 if table else 0
    height = gh+base+table+panel+6
    stem = ROOT/'figures/publication'/spec['folder']/spec['stem']
    stem.parent.mkdir(parents=True, exist_ok=True)
    d = PublicationDrawing(stem, width, height)
    if table:
        d.text(3, height-9, '(a) Encirclement and relief', 9, anchor='start', bold=True)
    draw_graph(d, spec, parsed, gw, (width-gw)/2, base+table)
    for i, eq in enumerate(spec['equations']):
        d.text(width/2, table+base-12-i*13, eq, 9, math_font=True)
    if table:
        d.rule(3, width-3, table-2)
        d.text(3, table-16, '(b) Starks take Winterfell?', 9, anchor='start', bold=True)
        cols = [4, width*.64, width*.87]
        d.text(cols[1], table-32, 'Relief', 8.5); d.text(cols[1], table-42, 'required', 8.5)
        d.text(cols[2], table-32, 'Untrapped', 8.5); d.text(cols[2], table-42, 'advance', 8.5)
        d.rule(3, width-3, table-47)
        for i, r in enumerate(spec['comparison']):
            y = table-61-i*18
            d.text(cols[0], y, r['label'], 9, anchor='start')
            for x, v in zip(cols[1:], r['values']):
                d.text(x, y, 'Yes' if v else 'No', 9)
    d.save()
    compact_pdf(stem.with_suffix('.pdf'))
    (WORK/(spec['stem']+'.dot')).write_text(dot)
    subprocess.run(['pdftocairo', '-png', '-singlefile', '-r', '160', str(stem.with_suffix('.pdf')),
                    str(WORK/spec['stem'])], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    return {'stem': str(stem.relative_to(ROOT)), 'width_mm': width/PT_PER_MM,
        'height_mm': height/PT_PER_MM, 'node_font_pt': 9, 'edge_font_pt': 8.5,
        'equation_font_pt': 9, 'layout_wrap': wraps, 'nodes': list(spec['nodes']),
        'edges': [{k:e[k] for k in ('parent','child','label','status') if k in e} for e in spec['edges']],
        'equations': spec['equations'], 'model_sha256': spec['model_sha256'],
        'provenance': spec['provenance'], 'comparison': spec.get('comparison'),
        'source_figure_numbers': spec.get('source_figure_numbers'),
        'files': {ext: {'bytes': stem.with_suffix(ext).stat().st_size,
                       'sha256': hashlib.sha256(stem.with_suffix(ext).read_bytes()).hexdigest()} for ext in ('.svg','.pdf')}}


def render_panels(spec, width):
    """Cut a large graph into explicit views, retaining every edge exactly once."""
    panels = []
    displayed = []
    for p in spec['panels']:
        keep = set(p['keep']); s = dict(spec, nodes={k:v for k,v in spec['nodes'].items() if k in keep},
            edges=[e for e in spec['edges'] if e['parent'] in keep and e['child'] in keep], rankdir=p['rankdir'])
        displayed.extend((e['parent'],e['child']) for e in s['edges'])
        panels.append((p['title'], s, layout(s, width)))
    if sorted(displayed) != sorted((e['parent'],e['child']) for e in spec['edges']):
        raise ValueError('Panel partition drops or duplicates an operative edge')
    base = len(spec['equations'])*13+8
    height = sum(v[2][0]+20 for v in panels)+base+4
    stem = ROOT/'figures/publication'/spec['folder']/spec['stem']; stem.parent.mkdir(parents=True,exist_ok=True)
    d = PublicationDrawing(stem, width, height); top = height
    for i,(title,s,(gh,gw,parsed,dot,wraps)) in enumerate(panels):
        d.text(3, top-9, title, 9, anchor='start', bold=True)
        draw_graph(d, s, parsed, gw, (width-gw)/2, top-15-gh)
        (WORK/(spec['stem']+'_'+str(i)+'.dot')).write_text(dot)
        top -= gh+20
    for i,eq in enumerate(spec['equations']):
        d.text(width/2, base-10-i*13, eq, 9, math_font=True)
    d.save()
    compact_pdf(stem.with_suffix('.pdf'))
    subprocess.run(['pdftocairo','-png','-singlefile','-r','160',str(stem.with_suffix('.pdf')),str(WORK/spec['stem'])],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    return {'stem':str(stem.relative_to(ROOT)), 'width_mm':width/PT_PER_MM, 'height_mm':height/PT_PER_MM,
            'node_font_pt':9, 'edge_font_pt':8.5, 'equation_font_pt':9, 'nodes':list(spec['nodes']),
            'edges':spec['edges'], 'panels':spec['panels'], 'equations':spec['equations'],
            'model_sha256':spec['model_sha256'], 'provenance':spec['provenance'],
            'source_figure_numbers':spec['source_figure_numbers'],
            'files':{ext:{'bytes':stem.with_suffix(ext).stat().st_size,
                    'sha256':hashlib.sha256(stem.with_suffix(ext).read_bytes()).hexdigest()} for ext in ('.svg','.pdf')}}


def specifications():
    stories = frozen(ROOT)['stories']; references = load_records(ROOT)
    verify_references({'stories': stories})
    labels = {
        'humpty': {'F':'Humpty falls (F)', 'D':'Initial damage (D)', 'A':'Helpers attempt repair (A)',
                   'E':'Effective method available (E)', 'R':'Repair succeeds (R)', 'Y':'Damage remains (Y)'},
        'wolf': {'F':'Earlier false alarms (F)', 'L':'Villagers distrust boy (L)', 'W':'Real wolf appears (W)',
                 'N':'New warning (N)', 'V':'Timely response (V)', 'H':'Flock harmed (H)'},
        'crow': {'I':'Pitcher intact (I)', 'S':'Enough stones available (S)', 'B':'Water initially reachable (B)',
                 'A':'Enough stones added (A)', 'R':'Water raised (R)', 'T':'Water now reachable (T)', 'D':'Crow drinks (D)'}}
    phrases = {
        'humpty': ['Damages Humpty','Provides damage to repair','Carries out repair','Makes repair effective',
                   'Persists without repair','Removes damage'],
        'wolf': ['Erodes trust','Prompts warning','Calls for help','Blocks response','Threatens flock','Prevents harm'],
        'crow': ['Permits adding stones','Retains raised water','Lifts water','Preserves access',
                 'Provides initial reach','Brings water within reach','Enables drinking']}
    equations = {'humpty':['D = F;   R = D ∧ A ∧ E;   Y = D ∧ ¬R'],
                 'wolf':['L = F;   N = W;   V = N ∧ ¬L;   H = W ∧ ¬V'],
                 'crow':['A = S;   R = I ∧ A;   T = I ∧ (B ∨ R);   D = T']}
    specs = []
    for story in stories:
        ident = story['id']; ref = story['reference']; edges = []
        for pair, phrase in zip(references['figure_annotations'][ident]['edges'], phrases[ident]):
            p,c = pair.split('__'); edges.append({'parent':p, 'child':c, 'label':phrase, 'status':'explicit'})
        # Edge list must be exactly the reference equation's declared inputs.
        expected = {(p,v['id']) for v in ref['variables'] for p in v['parents']}
        assert {(e['parent'],e['child']) for e in edges} == expected
        check_display_equations(equations[ident], [{v['id']:v['equation'] for v in ref['variables'] if v['equation'] is not None}])
        specs.append(dict(stem=ident, folder='simple_stories', nodes=labels[ident], edges=edges,
            equations=equations[ident], focus=ref['outcome'], model_sha256=fingerprint(ref),
            provenance='Author reference model for the frozen controlled adaptation; not generated or corrected model.'))
    data = load()
    config = {
      'blackwater': dict(stem='blackwater_mechanism', focus='D', source_figure_numbers=[8],
        nodes={'W':'Tyrion controls wildfire (W)', 'T':'Wildfire released (T)', 'S':'Tyrion signals (S)',
               'I':'Bronn ignites trap (I)', 'B':'Fleet enters trap (B)', 'D':'Fleet suffers fire losses (D)'},
        phrases={'e1':'Supplies fire trap','e2':'Signals the shot','e3':'Fuels explosion',
                 'e4':'Ignites the trap','e5':'Exposes ships to blast'},
        equations=['T = W;   I = S;   D = T ∧ I ∧ B']),
      'red_wedding': dict(stem='red_wedding_mechanism', focus='X', source_figure_numbers=[11],
        nodes={'G':'Walder holds grievance (G)', 'A':'Tywin gives assurances (A)', 'T':'Ambush prepared (T)',
               'N':'Replacement marriage agreed (N)', 'H':'Guest protection promised (H)',
               'P':'Coalition stays for wedding (P)', 'X':'Hall ambush launched (X)'},
        phrases={'e4':'Motivates retaliation','e5':"Lowers Frey's risk in betraying Robb",'e6':'Brings guests to wedding',
                 'e7':'Offers safety to guests','e8':'Prepares concealed attack','e9':'Puts leaders within reach'},
        equations=['P = N ∧ H;   X = T ∧ P', 'T = G ∧ A  versus  T = A']),
      'bolton': dict(stem='bolton_mechanism_interventions', focus='H', source_figure_numbers=[14,15],
        nodes={'J':"Jon's rescue becomes charge (J)", 'S':'Bolton shields ready (S)', 'E':'Stark force encircled (E)',
               'A':'Sansa arranges Vale aid (A)', 'V':'Vale cavalry available (V)', 'R':'Vale relief arrives (R)',
               'H':'Encirclement persists (H)'},
        phrases={'e2':'Commits host to melee','e3':'Closes enclosure','e4':'Secures outside aid',
                 'e5':'Supplies relief force','e6':'Keeps survivors trapped','e7':'Breaks shield enclosure'},
        equations=['E = J ∧ S;   R = A ∧ V;   H = E ∧ ¬R']),
      'astapor': dict(stem='astapor_overview', focus='Y', source_figure_numbers=[16],
        nodes={'O':'Dragon offered (O)', 'B':'Bargain accepted (B)', 'C':'Daenerys gains command (C)',
               'Q':'Masters targeted by order (Q)', 'U':'Guards defeated (U)', 'D':'Drogon ordered to burn (D)',
               'F':'Kraznys killed (F)', 'S':"Masters' armed control broken (S)",
               'E':'Freedom and exit offered (E)', 'R':'Unsullied choose to stay (R)',
               'Y':'Departure with freed troops (Y)'},
        phrases={'e1':'Meets price','e2':'Transfers command','e3':'Makes orders actionable',
                 'e4':'Directs soldiers to attack','e5':'Triggers dragonfire','e6':'Overwhelms guards',
                 'e7':'Removes Kraznys','e8':'Invites voluntary service','e9':"Removes masters' restraint",
                 'e10':'Clears armed obstacles','e11':'Changes troop status','e12':'Retains freed soldiers'},
        panels=[{'title':'(a) Purchase and command', 'keep':['O','B','C'], 'rankdir':'LR'},
                {'title':'(b) Attack, emancipation and departure', 'keep':['C','Q','U','D','F','S','E','R','Y'], 'rankdir':'TB'}],
        equations=['B = O;  C = B;  U = C ∧ Q;  F = D',
                   'S = U ∧ F  versus  S = U;   R = E ∧ S', 'Y = S ∧ E ∧ R'])}
    for compact in data['records']:
        if compact['case'] not in config:
            continue
        r = restore_models(compact); spec = copy.deepcopy(config[r['case']]); rep = r['representation']
        if set(r['operative_edge_ids']) != set(r['displayed_edge_ids']):
            raise ValueError('Withheld operative edge requires explicit treatment')
        keep = set(spec['nodes'])
        spec['edges'] = [dict(parent=e['parent'],child=e['child'],label=spec['phrases'][e['id']],
                              status=e['status']) for e in rep['edges'] if e['parent'] in keep and e['child'] in keep]
        if len(spec['edges']) != len(spec['phrases']):
            raise ValueError('Publication subgraph does not match its archived selection')
        spec.update(folder='got', model_sha256=model_hash(r),
            provenance='Codex-assisted v4 narrative hypothesis, unchanged equations; independent researcher adjudication pending.')
        check_display_equations(spec['equations'], [s['equations'] for s in data['generation_drafts'][r['case']]['scenarios']])
        if r['case'] == 'bolton':
            spec['comparison'] = []
            for label, q in zip(['No Vale relief', 'No Rickon bait', 'Neither bait nor relief'], r['queries']):
                vals = []
                for a in q['conditional']:
                    scenario = next(s for s in r['scenarios'] if s['id'] == a['scenario'])
                    assert verify_reported_result(rep, scenario['family'], q['do'], a['result'])['passed']
                    vals.append(a['result']['values'][0])
                spec['comparison'].append({'label':label,'do':q['do'],'values':vals,
                                           'partial_values':q['partial_result']['values']})
        specs.append(spec)
    return specs


def main():
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--width-mm', type=float, default=WIDTH_MM)
    p.add_argument('--compile', action='store_true', help='Also compile/verify the actual-class inclusion proof')
    args = p.parse_args()
    WORK.mkdir(parents=True, exist_ok=True); fonts()
    audit = write_audit(ROOT)
    items = [render(s, args.width_mm*PT_PER_MM) for s in specifications()]
    out = ROOT/'figures/publication/manifest.json'
    out.write_text(json.dumps({'template':'paper/template/svproc.cls', 'width_mm':args.width_mm,
        'figure_count':len(items), 'items':items}, indent=2, ensure_ascii=False)+'\n')
    if args.compile:
        if args.width_mm != WIDTH_MM:
            raise ValueError('The inclusion proof matches svproc at 122 mm; adjust example.tex before using another target width')
        env = dict(os.environ, TEXINPUTS=str(ROOT/'paper/template')+os.pathsep+os.environ.get('TEXINPUTS',''))
        for i in range(2):
            run = subprocess.run(['pdflatex','-interaction=nonstopmode','-halt-on-error','example.tex'],
                cwd=ROOT/'paper/publication',env=env,text=True,capture_output=True,check=True)
            (WORK/('latex_pass'+str(i+1)+'.txt')).write_text(run.stdout)
        log = (ROOT/'paper/publication/example.log').read_text()
        if 'Overfull' in log:
            raise ValueError('Inclusion example has an overfull box')
        font_report = compact_pdf(ROOT/'paper/publication/example.pdf')
        subprocess.run(['pdftocairo','-png','-r','120',str(ROOT/'paper/publication/example.pdf'),str(WORK/'page')],check=True)
        verification = {'inference_requests':0, 'generated_tokens':0, 'gpu_use':'none',
            'archived_results_modified':False,
            'strict_original_models_accepted':audit['strict_acceptance']['original'],
            'strict_normalized_models_accepted':audit['strict_acceptance']['normalized'],
            'reference_interventions_reproduced':len(verify_references(frozen(ROOT))),
            'conditional_bolton_answers_reproduced':sum(len(q['values']) for i in items for q in i.get('comparison',[]) or []),
            'figure_count':len(items),'pdf_fonts_embedded':True,'overfull_tex_boxes':False,
            'template_text_width_tex_pt':float(re.search(r'PUBLICATION-TEXTWIDTH: ([\d.]+)pt',log).group(1)),
            'figure_width_mm':args.width_mm,
            'minimum_figure_font_pdf_pt':min(i['edge_font_pt'] for i in items),
            'proof_pdf_fonts':font_report,
            'visual_review':'Inspect the exported PDFs/SVGs and compiled pages at 122 mm; the assistant inspection record is in README.md.',
            'independent_researcher_review':'pending'}
        (ROOT/'paper/publication/verification.json').write_text(json.dumps(verification,indent=2)+'\n')
    print(json.dumps({'strict_acceptance':audit['strict_acceptance'],
                      'figures':[{k:v for k,v in r.items() if k in ('stem','width_mm','height_mm')} for r in items]}, indent=2))


if __name__ == '__main__':
    main()
