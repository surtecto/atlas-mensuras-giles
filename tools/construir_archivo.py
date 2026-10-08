#!/usr/bin/env python3
"""Reconstruye los índices del Archivo abierto del Atlas de Mensuras de Giles.

Uso (desde la raíz del repositorio):   python3 tools/construir_archivo.py

Lee
  data/archivo/fichas/NNN.json   ficha completa de cada carpeta transcripta (el mismo JSON
                                 con que se arma el Word; se copia tal cual, renombrado a tres cifras)
  data/archivo/indice_base.json  filas de resumen de fichas que todavía no tienen JSON completo
  data/catalog.json              catálogo del Atlas (trae el resumen `ix` de las primeras fichas)
Escribe
  data/archivo/fichas.json       índice liviano de todas las fichas (lo primero que carga la página)
  data/archivo/personas.json     índice de personas (biografías de todas las fichas)
  data/archivo/busqueda/cNN.json texto completo en tandas de 25 fichas (se cargan al buscar)
  data/catalog.json              agrega o actualiza el resumen `ix` de cada ficha, para que el mapa la muestre
No usa nada fuera de la biblioteca estándar de Python.
"""
import json, re, glob, os, datetime, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(ROOT, 'data', 'archivo')
TANDA = 25

def limpio(s):
    s = re.sub(r'\^\{([^}]*)\}', r'\1', s or '')
    s = re.sub(r'~~(.*?)~~', '', s)
    return s.replace('**', '')

def unir(lineas):
    """une los renglones; las palabras cortadas al final del renglón («ñan-» / «dubay», «Mor-» / «=gan») se rearman para poder buscarlas"""
    out = ''
    for l in lineas:
        l = limpio(l).strip()
        if out.endswith('-') and l[:1] not in ('', '[') and not out.endswith(' -'):
            out = out[:-1] + l.lstrip('=')
        else:
            out += (' ' if out else '') + l
    return out

def carga(p, defecto):
    try:
        with open(p, encoding='utf8') as f: return json.load(f)
    except FileNotFoundError:
        return defecto

filas = {}
CAT = carga(os.path.join(ROOT, 'data', 'catalog.json'), [])
for c in CAT:
    ix = c.get('ix')
    if ix:
        filas[c['n']] = dict(n=c['n'], prop=ix.get('prop', ''), ag=ix.get('ag', ''), y=str(ix.get('y', '')),
                             fecha=ix.get('fecha', ''), ubic=ix.get('ubic', ''), sup=ix.get('sup', ''),
                             agua=ix.get('agua', ''), hitos=ix.get('hitos', ''), lind=ix.get('lind', ''),
                             sint=ix.get('sint', ''), ref=ix.get('ref', ''))
for r in carga(os.path.join(A, 'indice_base.json'), []):
    filas[r['n']] = {**filas.get(r['n'], {}), **r}

personas, busq = [], {}
for p in sorted(glob.glob(os.path.join(A, 'fichas', '*.json'))):
    d = carga(p, None)
    n = int(d['carpeta'])
    if os.path.basename(p) != '%03d.json' % n:
        raise SystemExit('El archivo %s debería llamarse %03d.json' % (p, n))
    R, M = d.get('resumen', {}), d.get('metricas', {})
    fol = d.get('folios', [])
    filas[n] = {**filas.get(n, {}), 'n': n,
        'prop': d.get('titulo') or R.get('Propietario / solicitante', ''), 'ag': R.get('Agrimensor', ''), 'y': str(R.get('Año', '')),
        'fecha': R.get('Fecha de la diligencia', ''), 'ubic': R.get('Ubicación', ''),
        'sup': M.get('superficie_ha', ''), 'agua': M.get('aguas', ''), 'hitos': M.get('hitos', ''),
        'lind': R.get('Linderos citados', ''), 'sint': d.get('sintesis', ''), 'ref': R.get('Referencia de archivo', ''),
        'estado': d.get('estado', ''), 'full': True, 'folios': len(fol), 'planos': len(d.get('planos', [])),
        'renglones': sum(len(f.get('lineas', [])) for f in fol), 'docx_nombre': d.get('archivo', ''),
        'fotos': len(glob.glob(os.path.join(ROOT, 'img', 'f', '%03d' % n, '*.jpg'))),
        'pdf': os.path.exists(os.path.join(ROOT, 'descargas', 'fichas', 'Ficha_%03d.pdf' % n))}
    for b in d.get('biografias', []):
        personas.append(dict(nombre=b.get('nombre', ''), rol=b.get('rol', ''), texto=b.get('texto', ''),
                             fuentes=b.get('fuentes', ''), n=n))
    piezas = [dict(n=n, k='sint', t='Síntesis', x=d.get('sintesis', ''))]
    for i, f in enumerate(fol):
        piezas.append(dict(n=n, k='f%d' % i, t=f.get('titulo', ''),
                           x=unir(f.get('lineas', [])) + ' ¶ ' + f.get('interpretacion', '')))
    for i, pl in enumerate(d.get('planos', [])):
        piezas.append(dict(n=n, k='p%d' % i, t=pl.get('titulo', ''), x=pl.get('interpretacion', '') + ' ' +
                           ' '.join(a + ': ' + b for a, b in pl.get('referencias', []))))
    for i, o in enumerate(d.get('observaciones', [])):
        piezas.append(dict(n=n, k='o%d' % i, t=o.get('titulo', ''), x=o.get('texto', '')))
    busq.setdefault((n - 1) // TANDA, []).extend(piezas)

os.makedirs(os.path.join(A, 'busqueda'), exist_ok=True)
for f in glob.glob(os.path.join(A, 'busqueda', 'c*.json')): os.remove(f)
tandas = []
for k in sorted(busq):
    nombre = 'c%02d.json' % k
    json.dump(busq[k], open(os.path.join(A, 'busqueda', nombre), 'w', encoding='utf8'), ensure_ascii=False, separators=(',', ':'))
    tandas.append(nombre)

lista = [filas[k] for k in sorted(filas)]
json.dump(dict(generado=datetime.date.today().isoformat(), total_corpus=191, tandas=tandas, fichas=lista),
          open(os.path.join(A, 'fichas.json'), 'w', encoding='utf8'), ensure_ascii=False, separators=(',', ':'))
personas.sort(key=lambda p: unicodedata.normalize('NFD', p['nombre']).lower())
json.dump(personas, open(os.path.join(A, 'personas.json'), 'w', encoding='utf8'), ensure_ascii=False, separators=(',', ':'))
cambios = 0
for c in CAT:
    f = filas.get(c['n'])
    if f and (f.get('full') or not c.get('ix')):
        ix = {k: f[k] for k in ('prop', 'ag', 'y', 'fecha', 'ubic', 'lind', 'sup', 'hitos', 'agua', 'sint', 'ref') if f.get(k)}
        if ix != c.get('ix'): c['ix'] = ix; cambios += 1
if cambios:
    json.dump(CAT, open(os.path.join(ROOT, 'data', 'catalog.json'), 'w', encoding='utf8'), ensure_ascii=False, separators=(',', ':'))
print('catalog.json: %d resúmenes agregados o actualizados' % cambios)
print('%d fichas en el índice (%d con texto completo), %d biografías, %d tandas de búsqueda' %
      (len(lista), sum(1 for f in lista if f.get('full')), len(personas), len(tandas)))
