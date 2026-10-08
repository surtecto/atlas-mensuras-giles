#!/usr/bin/env python3
"""Convierte las fichas en Word («Ficha NNN - Titular (año).docx») al JSON que lee el Archivo abierto
y extrae sus fotografías a tamaño web.

Uso:  python3 tools/docx_a_ficha.py "<carpeta con los .docx>" [NNN ...]
Escribe data/archivo/fichas/NNN.json e img/f/NNN/NN.jpg.  Requiere Pillow (pip install pillow).
Después hay que correr tools/construir_archivo.py.
"""
import sys, os, re, json, glob, zipfile, io
import xml.etree.ElementTree as ET
from PIL import Image

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
RID = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANCHO, CALIDAD = 1100, 64

def run_info(r):
    pr = r.find(W + 'rPr'); g = lambda t: pr is not None and pr.find(W + t) is not None
    col = pr.find(W + 'color').get(W + 'val') if g('color') else ''
    va = pr.find(W + 'vertAlign').get(W + 'val') if g('vertAlign') else ''
    txt = ''.join((t.text or '') if t.tag == W + 't' else '\t' if t.tag == W + 'tab' else '\n' if t.tag == W + 'br' and t.get(W + 'type') != 'page' else '' for t in r)
    return dict(t=txt, b=g('b'), i=g('i'), s=g('strike'), sup=va == 'superscript', col=col)

def parrafo(p, ctx):
    ppr = p.find(W + 'pPr')
    st = ppr.find(W + 'pStyle').get(W + 'val') if ppr is not None and ppr.find(W + 'pStyle') is not None else ''
    borde = ppr is not None and ppr.find(W + 'pBdr') is not None
    runs = [run_info(r) for r in p.iter(W + 'r')]
    imgs = [b.get(RID) for b in p.iter('{http://schemas.openxmlformats.org/drawingml/2006/main}blip')]
    plano = ''.join(r['t'] for r in runs)
    d = dict(st=st, runs=runs, imgs=imgs, t=plano.strip(), borde=borde, **ctx)
    # renglón de transcripción: primer tramo = número en color B64926
    k = 0
    while k < len(runs) and runs[k]['col'] == 'B64926': k += 1
    if k and re.fullmatch(r'\s*\d+\s*', ''.join(r['t'] for r in runs[:k]).replace('\t', '')):
        out = ''
        for r in runs[k:]:
            t = r['t']
            if not t: continue
            if r['sup']: out += '^{%s}' % t
            elif r['s']: out += '~~%s~~' % t
            elif r['b']: out += '**%s**' % t
            else: out += t
        d['linea'] = out.lstrip('\t').rstrip()
    return d

def flujo(body):
    out, nt = [], [0]
    def tabla(tbl):
        nt[0] += 1; k = nt[0]
        for ri, tr in enumerate(tbl.findall(W + 'tr')):
            tcs = tr.findall(W + 'tc')
            for ci, tc in enumerate(tcs):
                for el in tc:
                    if el.tag == W + 'p': out.append(parrafo(el, dict(tb=k, r=ri, c=ci, nc=len(tcs))))
                    elif el.tag == W + 'tbl': tabla(el)
    for el in body:
        if el.tag == W + 'p': out.append(parrafo(el, dict(tb=0, r=0, c=0, nc=0)))
        elif el.tag == W + 'tbl': tabla(el)
    return out

def pares(ps):
    """filas de tablas de dos columnas → [[rótulo, valor]]"""
    filas = {}
    for p in ps:
        if p['nc'] == 2 and not p['imgs']: filas.setdefault((p['tb'], p['r']), ['', ''])[p['c']] += (' ' if filas[(p['tb'], p['r'])][p['c']] and p['t'] else '') + p['t']
    return [v for v in filas.values() if v[0] and not re.fullmatch(r'\d+[a-z]?', v[0])]

def textos(ps): return [p['t'] for p in ps if p['t']]

def convertir(path):
    n = int(re.search(r'Ficha (\d+)', os.path.basename(path)).group(1))
    z = zipfile.ZipFile(path)
    rels = {r.get('Id'): r.get('Target') for r in ET.fromstring(z.read('word/_rels/document.xml.rels'))}
    P = flujo(ET.fromstring(z.read('word/document.xml')).find(W + 'body'))
    dimg = os.path.join(ROOT, 'img', 'f', '%03d' % n); os.makedirs(dimg, exist_ok=True)
    for f in glob.glob(os.path.join(dimg, '*.jpg')): os.remove(f)
    hechas = {}
    def imagen(rid):
        if not rid: return ''
        if rid not in hechas:
            im = Image.open(io.BytesIO(z.read('word/' + rels[rid]))).convert('RGB')
            if max(im.size) > ANCHO: im.thumbnail((ANCHO, ANCHO), Image.LANCZOS)
            nombre = '%02d.jpg' % (len(hechas) + 1)
            im.save(os.path.join(dimg, nombre), 'JPEG', quality=CALIDAD, optimize=True, progressive=True)
            hechas[rid] = 'img/f/%03d/%s' % (n, nombre)
        return hechas[rid]
    # secciones por Heading1
    idx = [i for i, p in enumerate(P) if p['st'] in ('Heading1', 'Ttulo1')]
    port, secs = P[:idx[0]], [P[a:b] for a, b in zip(idx, idx[1:] + [len(P)])]
    d = dict(carpeta=str(n), carpeta_nombre='Carpeta %d' % n, archivo=os.path.basename(path))
    # portada
    tit = next(p['t'] for p in port if p['st'] in ('Title', 'Ttulo'))
    d['resumen'] = dict(pares(port))
    d['metricas'] = {}
    for p in port:
        for k, c in (('Superficie:', 'superficie_ha'), ('Hitos:', 'hitos'), ('Aguas:', 'aguas')):
            if p['t'].startswith(k): d['metricas'][c] = re.sub(r'\s*ha$', '', p['t'][len(k):].strip()) if c == 'superficie_ha' else p['t'][len(k):].strip()
    ts = textos(port)
    d['sintesis'] = ts[ts.index('SÍNTESIS INTERPRETATIVA') + 1] if 'SÍNTESIS INTERPRETATIVA' in ts else ''
    rid0 = next((p['imgs'][0] for p in port if p['imgs']), '')
    d['caratula'] = dict(img=imagen(rid0), fuente='', campos=[])
    d['folios'], d['planos'], d['observaciones'], d['biografias'] = [], [], [], []
    anexo = {}
    for s in secs:
        h = s[0]; Hm = ''.join(r['t'] for r in h['runs'] if r['col'] != 'FFE6C7').strip(); sub = ''.join(r['t'] for r in h['runs'] if r['col'] == 'FFE6C7').strip(); H = Hm.upper()
        cuerpo = s[1:]
        # el número de sección («02») de la sección siguiente queda al final: se descarta
        while cuerpo and (not cuerpo[-1]['t'] or re.fullmatch(r'\d+[a-z]?', cuerpo[-1]['t'])) and not cuerpo[-1]['imgs']: cuerpo = cuerpo[:-1]
        rid = next((p['imgs'][0] for p in cuerpo if p['imgs']), '')
        lineas = [p['linea'] for p in cuerpo if 'linea' in p]
        if H.startswith('CARÁTULA'):
            d['caratula']['campos'] = pares(cuerpo)
            cap = next((p['t'] for p in cuerpo if 'IMG' in p['t'] and '·' in p['t'] and p['nc'] != 2), '')
            d['caratula']['fuente'] = cap.split('·')[-1].strip()
        elif H.startswith('PORTADILLA'):
            d['portadilla'] = dict(img=imagen(rid), fuente=sub, lineas=lineas)
        elif H.startswith('PLANIMETRÍA'):
            ts = textos(cuerpo); fu = next((t for t in ts if t.startswith('Fuente:')), '')
            fuente, _, orient = fu[7:].strip().partition(' — ')
            i = ts.index('LECTURA DEL PLANO') if 'LECTURA DEL PLANO' in ts else -1
            d['planos'].append(dict(titulo=sub, img=imagen(rid), fuente=fuente, orientacion=orient,
                                    interpretacion='\n'.join(ts[i + 1:]) if i >= 0 else '', referencias=[]))
        elif H.startswith('REFERENCIAS'):
            if d['planos']:
                k = re.search(r'LÁMINA (\d+)', H); k = int(k.group(1)) - 1 if k else len(d['planos']) - 1
                d['planos'][min(k, len(d['planos']) - 1)]['referencias'] = pares(cuerpo)
        elif H.startswith('OBSERVACIONES'):
            for p in cuerpo:
                if not p['t']: continue
                if p['borde'] and p['runs'] and p['runs'][0]['b']: d['observaciones'].append(dict(titulo=p['t'].capitalize(), texto=''))
                elif d['observaciones']: d['observaciones'][-1]['texto'] += ('\n' if d['observaciones'][-1]['texto'] else '') + p['t']
        elif H.startswith('PERSONAS'):
            for p in cuerpo:
                if not p['t']: continue
                r = p['runs']
                if r and r[0]['col'] == 'B22600' and r[0]['b']:
                    d['biografias'].append(dict(nombre=''.join(x['t'] for x in r if x['col'] == 'B22600').strip(), rol=''.join(x['t'] for x in r if x['col'] != 'B22600').strip().capitalize(), texto='', fuentes=''))
                elif d['biografias']:
                    if p['t'].startswith('Fuentes:'): d['biografias'][-1]['fuentes'] = p['t'][8:].strip()
                    else: d['biografias'][-1]['texto'] += ('\n' if d['biografias'][-1]['texto'] else '') + p['t']
        elif H.startswith('ANEXO'):
            ult = ''
            for p in cuerpo:
                if p['imgs']: ult = p['imgs'][0]
                elif p['t'] and ult: anexo[p['t']] = ult; ult = ''
        elif H.endswith('· INTERPRETACIÓN'):
            base = H[:-len('· INTERPRETACIÓN')].strip()
            fo = next((f for f in reversed(d['folios']) if f['_H'] == base), None)
            ts = [p['t'] for p in cuerpo if p['t'] and not p['t'].startswith(('INTERPRETACIÓN ·', 'Facsímil'))]
            if fo is not None:
                fo['interpretacion'] = '\n'.join(ts); fo['_rid'] = rid or fo['_rid']
        else:  # folio u otra hoja transcripta
            fuente = re.sub(r'^transcripción\s*·\s*', '', sub)
            ts = [p for p in cuerpo if p['t']]
            nota, interp, modo = [], [], 'nota'
            for p in ts:
                if 'linea' in p: modo = 'lin'; continue
                if p['t'].startswith('INTERPRETACIÓN ·'): modo = 'int'; continue
                if p['t'].startswith('Facsímil') or p['imgs']: continue
                (nota if modo == 'nota' else interp).append(p['t'])
            d['folios'].append(dict(titulo=Hm, img='', fuente=fuente, nota=' '.join(nota), lineas=lineas, interpretacion='\n'.join(interp), _H=H, _rid=rid))
    # títulos con mayúsculas y minúsculas e imágenes: salen de los epígrafes del anexo
    for f in d['folios']:
        for cap, rid in anexo.items():
            c = cap.split(' · IMG')[0] if ' · IMG' in cap else cap.rsplit(' · ', 1)[0]
            if cap.upper().startswith(f['_H']) or c.upper() == f['_H']:
                f['titulo'] = cap[:len(f['_H'])]; f['_rid'] = f['_rid'] or rid; break
        else:
            if f['titulo'].isupper(): f['titulo'] = f['titulo'].capitalize()
        f['img'] = imagen(f.pop('_rid')); f.pop('_H')
    d['titulo'] = tit
    d['estado'] = 'Transcripta (%d hojas, %d renglones), %d lámina%s' % (len(d['folios']), sum(len(f['lineas']) for f in d['folios']), len(d['planos']), '' if len(d['planos']) == 1 else 's')
    json.dump(d, open(os.path.join(ROOT, 'data', 'archivo', 'fichas', '%03d.json' % n), 'w', encoding='utf8'), ensure_ascii=False, indent=1)
    return n, d, len(hechas)

if __name__ == '__main__':
    carpeta, cuales = sys.argv[1], set(sys.argv[2:])
    for path in sorted(glob.glob(os.path.join(carpeta, 'Ficha [0-9][0-9][0-9]*.docx'))):
        num = re.search(r'Ficha (\d+)', os.path.basename(path)).group(1)
        if cuales and num not in cuales: continue
        n, d, ni = convertir(path)
        sin = sum(1 for f in d['folios'] if not f['img'])
        print('%03d %-42s folios %2d renglones %4d sin_interp %d sin_foto %d · planos %d · obs %d · bio %2d · resumen %2d · carát %2d · fotos %2d' % (
            n, d['titulo'][:42], len(d['folios']), sum(len(f['lineas']) for f in d['folios']), sum(1 for f in d['folios'] if not f['interpretacion']), sin,
            len(d['planos']), len(d['observaciones']), len(d['biografias']), len(d['resumen']), len(d['caratula']['campos']), ni))
