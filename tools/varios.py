#!/usr/bin/env python3
"""Varios del Archivo Histórico de Geodesia: documentos que no son duplicados de mensura del partido
(hojas catastrales, planos de pueblo, croquis sueltos de las «Carpetas de Planos (Varios)»).

Uso, desde la raíz del repositorio:
  python3 tools/varios.py "<carpeta con los .docx>" [V01 V02 ...]   convierte esas fichas (sin códigos: todas las «Ficha Vnn»)
  python3 tools/varios.py --indice                                    sólo rehace índice, capa y PDF (sin convertir)
  agregar --sin-pdf para no generar los PDF.

Escribe:
  data/varios/fichas/Vnn.json     ficha completa (mismo formato que data/archivo/fichas/NNN.json)
  img/v/Vnn/NN.jpg                fotografías
  data/varios/varios.json         índice por temas, con el estado de georreferenciación de cada ficha
  data/varios/catastro_1938.geojson   capa: parcelas de 1938 ubicadas por su n.º de Guía y huella de cada hoja
  descargas/varios/Ficha_Vnn.pdf  ficha completa en PDF
  descargas/sig/varios_*.geojson / .kml

Georreferenciación. Las hojas catastrales anotan el «Guía N.º» de cada parcela, que es el número de partida
inmobiliaria que la parcela conserva hoy (094-00NNNN en el catastro 2024 de data/parcelas_2024.json; por ejemplo
la plaza Cutillas, Guía 2820, es la partida 094002820, zona EV). Cada parcela con Guía se ubica sobre el polígono
actual de esa partida; la huella de la hoja es la envolvente de sus parcelas ubicadas. Las coincidencias que caen a
más de 900 m de la mediana de la hoja se descartan como lecturas dudosas o partidas renumeradas.
"""
import sys, os, re, json, glob, shutil, tempfile, statistics, math

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
V = os.path.join(ROOT, 'data', 'varios')
TEMAS = [  # el primero cuyo patrón coincide con el título define el tema
    dict(id='catastro1938', patron=r'catastro urbano', titulo='Catastro urbano del pueblo (c. 1938)',
         texto='Juego de nueve hojas catastrales del pueblo de San Andrés de Giles a escala 1:1000, levantadas por la Dirección de Geodesia [y] Catastro de la provincia hacia 1938. Cada parcela lleva su titular, el asiento de dominio, la superficie según título y el n.º de Guía, que es la partida inmobiliaria que la parcela conserva hoy: por eso las hojas se pueden ubicar sobre el catastro actual.',
         juego=9),
    dict(id='otros', patron=r'.', titulo='Otros documentos', texto='Planos y documentos sueltos de las carpetas «Varios», como documentos de consulta.', juego=None),
]
LIM_M = 900       # descarte de coincidencias lejanas
RADIO, VEC = 150, 3  # coherencia local entre renglones vecinos
MIN_MAPA = 5     # parcelas ubicadas para considerar la hoja georreferenciada

def J(p, d=None):
    try:
        with open(p, encoding='utf8') as f: return json.load(f)
    except FileNotFoundError: return d

def W(p, obj, indent=1):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf8') as f: json.dump(obj, f, ensure_ascii=False, indent=indent)

# ---------- conversión del Word ----------
def convertir(path, cod):
    import docx_a_ficha as D
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, 'data', 'archivo', 'fichas'))
        src = os.path.join(tmp, 'Ficha 001 - x.docx'); shutil.copy(path, src)
        D.ROOT = tmp
        _, d, ni = D.convertir(src)
        dimg = os.path.join(ROOT, 'img', 'v', cod)
        if os.path.isdir(dimg): shutil.rmtree(dimg)
        shutil.copytree(os.path.join(tmp, 'img', 'f', '001'), dimg)
    fix = lambda s: s.replace('img/f/001/', 'img/v/%s/' % cod) if isinstance(s, str) else s
    d['caratula']['img'] = fix(d['caratula'].get('img'))
    if d.get('portadilla'): d['portadilla']['img'] = fix(d['portadilla'].get('img'))
    for x in d['folios'] + d['planos']: x['img'] = fix(x.get('img'))
    d.update(carpeta=cod, carpeta_nombre='Varios %s' % cod, archivo=os.path.basename(path))
    W(os.path.join(V, 'fichas', cod + '.json'), d)
    return d, ni

# ---------- georreferenciación por n.º de Guía ----------
RX_GUIA = re.compile(r'Gu[ií]a\s*(?:N\.?\s*)?[°º.]?\s*(\d{2,5})(\s*\[\?\])?')
def m2(seg):
    s = seg.replace('[?]', '')
    m = re.search(r'=\s*([\d.]+(?:,\d+)?)\s*m²', s) or re.search(r'([\d.]+(?:,\d+)?)\s*m²', s)
    if m: return float(m.group(1).replace('.', '').replace(',', '.'))
    m = re.search(r'([\d]+(?:,\d+)?)\s*[×x]\s*([\d]+(?:,\d+)?)', s)
    return float(m.group(1).replace(',', '.')) * float(m.group(2).replace(',', '.')) if m else None

def registro(linea):
    segs = [x.strip() for x in re.split(r'\s+[·-]\s+', linea) if x.strip()]
    tit, sup, folio = [], None, ''
    for s in segs:
        if re.match(r'^(F[°º]|N[°º]\s*\d|Nº?\s*\d)', s): folio = folio or s; continue
        if re.search(r'Gu[ií]a', s): continue
        if re.match(r'^(s\.?s?\.?t\.?|St\.|Sup|sup\.|Reman)', s, re.I) or 'm²' in s or '×' in s:
            sup = sup or m2(s); continue
        if s.startswith('['): continue
        tit.append(s)
    return dict(titular=' · '.join(tit)[:160], folio=folio, m2_1938=sup)

def huella(pts):
    """envolvente convexa (monotone chain) de [(x, y)]"""
    pts = sorted(set(pts))
    if len(pts) < 3: return None
    cr = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cr(lo[-2], lo[-1], p) <= 0: lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cr(up[-2], up[-1], p) <= 0: up.pop()
        up.append(p)
    h = lo[:-1] + up[:-1]
    return [[round(x, 6), round(y, 6)] for x, y in h + [h[0]]]

def dist_m(a, b):
    return math.hypot((a[0] - b[0]) * 111320 * math.cos(math.radians(a[1])), (a[1] - b[1]) * 110540)

def georref(fichas):
    P = J(os.path.join(ROOT, 'data', 'parcelas_2024.json'))['features']
    by = {}
    for f in P:
        if f['properties'].get('pda'): by.setdefault(f['properties']['pda'], f)
    parc, hojas, est = [], [], {}
    for cod, d in sorted(fichas.items()):
        regs = []
        for fo in d['folios']:
            for i, l in enumerate(fo['lineas']):
                for m in RX_GUIA.finditer(l):
                    pda = '094' + m.group(1).zfill(6)
                    regs.append(dict(guia=m.group(1), dudosa=bool(m.group(2)) or '[?]' in l[max(0, m.start() - 30):m.end() + 4], pda=pda,
                                     hoja=cod, hoja_titulo=d['titulo'], folio_ficha=fo['titulo'], renglon=re.sub(r'\*\*|~~|\^\{|\}', '', l)[:400], **registro(l)))
        loc = [r for r in regs if r['pda'] in by]
        if loc:
            mx = statistics.median(by[r['pda']]['properties']['lx'] for r in loc); my = statistics.median(by[r['pda']]['properties']['ly'] for r in loc)
            xy = lambda r: (by[r['pda']]['properties']['lx'], by[r['pda']]['properties']['ly'])
            cerca = [r for r in loc if dist_m(xy(r), (mx, my)) <= LIM_M]
            # coherencia local: los renglones vecinos de la hoja describen parcelas vecinas; una partida que no tiene
            # ninguna de las de sus ±VEC renglones a menos de RADIO metros se descarta (lectura dudosa o partida renumerada)
            ok = [r for i, r in enumerate(cerca) if any(dist_m(xy(r), xy(s)) <= RADIO for s in cerca[max(0, i - VEC):i] + cerca[i + 1:i + 1 + VEC] if s['pda'] != r['pda'])]
        else: ok = []
        pts = []
        for r in ok:
            g = by[r['pda']]; pr = g['properties']; ha24 = pr.get('ha')
            r.update(nomenclatura_2024=pr.get('n'), ha_2024=ha24)
            if r['m2_1938'] and ha24:
                q = r['m2_1938'] / (ha24 * 10000); r['coincide_sup'] = 'sí' if 0.8 <= q <= 1.25 else 'no (subdividida o mal leída)'
            else: r['coincide_sup'] = ''
            parc.append(dict(type='Feature', properties={k: v for k, v in r.items() if v not in (None, '')}, geometry=g['geometry']))
            geo = g['geometry']; rings = geo['coordinates'] if geo['type'] == 'Polygon' else [p[0] for p in geo['coordinates']]
            for ring in (rings if geo['type'] == 'MultiPolygon' else rings[:1]): pts += [tuple(c) for c in ring]
        h = huella(pts) if len(ok) >= MIN_MAPA else None
        if h: hojas.append(dict(type='Feature', properties=dict(hoja=cod, titulo=d['titulo'], ubicacion=d['resumen'].get('Ubicación', ''), anio=d['resumen'].get('Año', ''),
                                                                 parcelas_ubicadas=len(ok), metodo='envolvente de las parcelas ubicadas por n.º de Guía = partida actual (aproximada)'),
                                     geometry=dict(type='Polygon', coordinates=[h])))
        est[cod] = dict(guias=len(regs), ubicadas=len(ok), descartadas=len(loc) - len(ok), sin_partida=len(regs) - len(loc),
                        sup_coincide=sum(1 for r in ok if r.get('coincide_sup') == 'sí'), sup_comparable=sum(1 for r in ok if r.get('coincide_sup')),
                        mapa=bool(h), centro=[round(statistics.mean(p[0] for p in pts), 6), round(statistics.mean(p[1] for p in pts), 6)] if h else None)
    return parc, hojas, est

def kml(name, feats, label):
    import html
    e = lambda s: html.escape(str(s))
    def geom(g):
        rings = lambda p: ''.join('<Polygon><outerBoundaryIs><LinearRing><coordinates>%s</coordinates></LinearRing></outerBoundaryIs></Polygon>' % ' '.join('%s,%s' % (c[0], c[1]) for c in r[0]) for r in p)
        return rings([g['coordinates']] if g['type'] == 'Polygon' else g['coordinates']) if g['type'] == 'Polygon' else '<MultiGeometry>%s</MultiGeometry>' % rings(g['coordinates'])
    return '<?xml version="1.0" encoding="UTF-8"?>\n<kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>%s</name>\n%s\n</Document></kml>\n' % (e(name), '\n'.join(
        '<Placemark><name>%s</name><ExtendedData>%s</ExtendedData>%s</Placemark>' % (e(label(f['properties'])), ''.join('<Data name="%s"><value>%s</value></Data>' % (e(k), e(v)) for k, v in f['properties'].items()), geom(f['geometry'])) for f in feats))

# ---------- PDF ----------
def pdf(d, tmp):
    import generar_descargas as G
    cod = d['carpeta']; dd = dict(d, carpeta='1')
    G.cita = lambda _d, _n: ('Addesso, Juan Patricio (%d). «%s: %s». Transcripción e interpretación de un documento de las Carpetas de Planos (Varios), '
                             'Archivo Histórico de Geodesia de la Provincia de Buenos Aires. Atlas de Mensuras de Giles, Varios. %svarios.html#%s') % (
                             G.HOY.year, 'Varios ' + cod, d.get('titulo', ''), G.SITIO, cod)
    h = G.ficha_html(dd, tmp).replace('Ficha de mensura n.º 001', 'Varios del AHG · documento %s' % cod).replace('Ficha 001', 'Varios ' + cod)
    dst = os.path.join(ROOT, 'descargas', 'varios', 'Ficha_%s.pdf' % cod)
    G.a_pdf(h, dst, tmp); return dst

# ---------- índice ----------
def indice(con_pdf, cuales):
    fichas = {os.path.basename(p)[:-5]: J(p) for p in sorted(glob.glob(os.path.join(V, 'fichas', 'V*.json')))}
    parc, hojas, est = georref(fichas)
    W(os.path.join(V, 'catastro_1938.geojson'), dict(type='FeatureCollection', name='catastro_1938', features=hojas + parc), None)
    sig = os.path.join(ROOT, 'descargas', 'sig')
    for nom, fs, lab in (('varios_catastro1938_hojas', hojas, lambda p: '%s · %s' % (p['hoja'], p['titulo'])),
                         ('varios_catastro1938_parcelas', parc, lambda p: '%s · Guía %s · %s' % (p['hoja'], p['guia'], p.get('titular', '')))):
        W(os.path.join(sig, nom + '.geojson'), dict(type='FeatureCollection', name=nom, features=fs), None)
        with open(os.path.join(sig, nom + '.kml'), 'w', encoding='utf8') as f: f.write(kml(nom, fs, lab))
    if con_pdf:
        with tempfile.TemporaryDirectory() as tmp:
            for cod, d in fichas.items():
                if cuales and cod not in cuales and os.path.exists(os.path.join(ROOT, 'descargas', 'varios', 'Ficha_%s.pdf' % cod)): continue
                dst = pdf(d, tmp); print('PDF %s  %.1f MB' % (cod, os.path.getsize(dst) / 1048576), flush=True)
    temas = []
    for t in TEMAS:
        temas.append(dict(id=t['id'], titulo=t['titulo'], texto=t['texto'], juego=t['juego'], fichas=[]))
    for cod, d in fichas.items():
        t = next(x for x, y in zip(temas, TEMAS) if re.search(y['patron'], d['titulo'], re.I))
        R = d['resumen']; e = est[cod]
        t['fichas'].append(dict(cod=cod, titulo=d['titulo'], doc=R.get('Documento', ''), y=R.get('Año', ''), autor=R.get('Autor', ''), escala=R.get('Escala', ''),
            ubic=R.get('Ubicación', ''), sint=d.get('sintesis', ''), folios=len(d['folios']), renglones=sum(len(f['lineas']) for f in d['folios']),
            planos=len(d['planos']), fotos=len(glob.glob(os.path.join(ROOT, 'img', 'v', cod, '*.jpg'))),
            pdf=os.path.exists(os.path.join(ROOT, 'descargas', 'varios', 'Ficha_%s.pdf' % cod)), geo=e,
            estado='georreferenciada' if e['mapa'] else 'documento de consulta'))
    temas = [t for t in temas if t['fichas']]
    W(os.path.join(V, 'varios.json'), dict(temas=temas, capas=dict(hojas=len(hojas), parcelas=len(parc))))
    for cod, e in sorted(est.items()):
        print('%s  guías %3d · ubicadas %3d · descartadas %2d · sin partida %2d · superficie coincide %d/%d · %s' % (
            cod, e['guias'], e['ubicadas'], e['descartadas'], e['sin_partida'], e['sup_coincide'], e['sup_comparable'], 'MAPA' if e['mapa'] else 'consulta'))

if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]; sin_pdf = '--sin-pdf' in sys.argv
    cuales = set()
    if '--indice' not in sys.argv:
        carpeta, pedidas = a[0], {x.upper() for x in a[1:]}
        for path in sorted(glob.glob(os.path.join(carpeta, 'Ficha V[0-9]*.docx'))):
            cod = re.search(r'Ficha (V\d+)', os.path.basename(path)).group(1).upper()
            if pedidas and cod not in pedidas: continue
            d, ni = convertir(path, cod); cuales.add(cod)
            print('%s %-40s hojas %2d renglones %4d sin_interp %d sin_foto %d · planos %d · fotos %d' % (cod, d['titulo'][:40], len(d['folios']),
                  sum(len(f['lineas']) for f in d['folios']), sum(1 for f in d['folios'] if not f['interpretacion']), sum(1 for f in d['folios'] if not f['img']), len(d['planos']), ni))
    indice(not sin_pdf, cuales)
