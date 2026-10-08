#!/usr/bin/env python3
"""Exporta las capas espaciales del Atlas a los tres formatos de intercambio: GeoJSON, KML y Shapefile (zip).

Uso (desde la raíz del repositorio):   python3 tools/exportar_sig.py
Requiere pyshp para el Shapefile:      pip install pyshp
Lee data/geojson/*.geojson y data/parcelas_2024.json; escribe descargas/sig/<capa>.geojson|.kml|.shp.zip
Todas las capas salen en WGS84 (EPSG:4326), con nombres de campo legibles (máx. 10 letras, por el Shapefile).
"""
import json, os, io, zipfile
from xml.sax.saxutils import escape
try:
    import shapefile
except ImportError:
    shapefile = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'descargas', 'sig')
PRJ = 'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]]'
# capa: (archivo de origen, título, campo que da nombre a cada elemento, {clave original: nombre legible})
CAPAS = {
 'mensuras_ahg': ('data/geojson/mensuras_ahg.geojson', 'Mensuras del Archivo Histórico de Geodesia (1825-1923)', 'titular',
                  {'n': 'carpeta', 'tit': 'titular', 'y': 'anio', 'ag': 'agrimensor', 'ed': 'edificado', 'ha': 'ha', 'pc': 'pc'}),
 'registro_grafico_1874': ('data/geojson/registro_grafico_1874.geojson', 'Registro gráfico de c. 1874', 'titular',
                  {'t': 'titular', 'c': 'circ', 'p': 'parcela', 'ha': 'ha', 'sup': 'sup_m2'}),
 'parcelas_urbanas_1884': ('data/geojson/parcelas_urbanas_1884.geojson', 'Pueblo de San Andrés de Giles, 1884', 'propietar',
                  {'pr': 'propietar', 'oc': 'ocupacion', 'm2': 'm2'}),
 'caminos': ('data/geojson/caminos.geojson', 'Caminos, ferrocarril, tranvía y telégrafo', 'nombre',
                  {'nm': 'nombre', 't': 'tipo', 'y': 'anio', 'ob': 'origen', 'km': 'km'}),
 'poblamiento_mensuras': ('data/geojson/poblamiento_mensuras.geojson', 'Poblamiento dibujado en los planos de mensura', 'nombre',
                  {'d': 'nombre', 't': 'tipo', 'n': 'carpeta'}),
 'estancias_puestos_1884': ('data/geojson/estancias_puestos_1884.geojson', 'Estancias, puestos, postas y pulperías de 1884', 'nombre',
                  {'d': 'nombre', 't': 'tipo'}),
 'partido_contorno': ('data/geojson/partido_contorno.geojson', 'Contorno del partido de San Andrés de Giles', None, {}),
 'parcelas_2024': ('data/parcelas_2024.json', 'Parcelario catastral 2024 (sin titulares ni domicilios)', 'nomencla',
                  {'n': 'nomencla', 'pda': 'partida', 't': 'urb_rural', 'ha': 'ha', 'z': 'zona_cou'}),
}

def anillos(geom):
    t, c = geom['type'], geom['coordinates']
    return {'Polygon': [c], 'MultiPolygon': c}.get(t, [])

def kml_geom(g):
    co = lambda pts: ' '.join('%.6f,%.6f' % (p[0], p[1]) for p in pts)
    t, c = g['type'], g['coordinates']
    if t == 'Point': return '<Point><coordinates>%.6f,%.6f</coordinates></Point>' % (c[0], c[1])
    if t == 'LineString': return '<LineString><coordinates>%s</coordinates></LineString>' % co(c)
    if t == 'MultiLineString': return '<MultiGeometry>%s</MultiGeometry>' % ''.join('<LineString><coordinates>%s</coordinates></LineString>' % co(l) for l in c)
    pol = lambda p: '<Polygon><outerBoundaryIs><LinearRing><coordinates>%s</coordinates></LinearRing></outerBoundaryIs>%s</Polygon>' % (
        co(p[0]), ''.join('<innerBoundaryIs><LinearRing><coordinates>%s</coordinates></LinearRing></innerBoundaryIs>' % co(r) for r in p[1:]))
    ps = anillos(g)
    return pol(ps[0]) if len(ps) == 1 else '<MultiGeometry>%s</MultiGeometry>' % ''.join(pol(p) for p in ps)

def area(r): return sum(r[i][0] * r[i + 1][1] - r[i + 1][0] * r[i][1] for i in range(len(r) - 1))

os.makedirs(OUT, exist_ok=True)
resumen = []
for capa, (src, titulo, nombre, campos) in CAPAS.items():
    fc = json.load(open(os.path.join(ROOT, src), encoding='utf8'))
    feats = []
    for f in fc['features']:
        if not f.get('geometry'): continue
        feats.append({'type': 'Feature', 'properties': ({campos[k]: v for k, v in f['properties'].items() if k in campos} if campos else {'nombre': titulo}), 'geometry': f['geometry']})
    tipo = feats[0]['geometry']['type']
    # GeoJSON
    json.dump({'type': 'FeatureCollection', 'name': capa, 'title': titulo, 'features': feats},
              open(os.path.join(OUT, capa + '.geojson'), 'w', encoding='utf8'), ensure_ascii=False, separators=(',', ':'))
    # KML
    with open(os.path.join(OUT, capa + '.kml'), 'w', encoding='utf8') as k:
        k.write('<?xml version="1.0" encoding="UTF-8"?>\n<kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>%s</name>\n' % escape(titulo))
        k.write('<Style id="s"><LineStyle><color>ff794e1f</color><width>1.5</width></LineStyle><PolyStyle><color>33794e1f</color></PolyStyle></Style>\n')
        for f in feats:
            p = f['properties']
            k.write('<Placemark><name>%s</name><styleUrl>#s</styleUrl><ExtendedData>%s</ExtendedData>%s</Placemark>\n' % (
                escape(str(p.get(nombre) or '' if nombre else titulo)),
                ''.join('<Data name="%s"><value>%s</value></Data>' % (a, escape(str(b))) for a, b in p.items() if b not in ('', None)),
                kml_geom(f['geometry'])))
        k.write('</Document></kml>\n')
    # Shapefile
    if shapefile:
        bufs = {e: io.BytesIO() for e in ('shp', 'shx', 'dbf')}
        w = shapefile.Writer(shp=bufs['shp'], shx=bufs['shx'], dbf=bufs['dbf'], encoding='utf8')
        orden = list(dict.fromkeys(campos.values())) or ['nombre']
        texto = set()
        for c in orden:
            vals = [f['properties'].get(c) for f in feats if f['properties'].get(c) not in ('', None)]
            if vals and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in vals):
                w.field(c, 'N', 18, 0 if all(isinstance(v, int) for v in vals) else 4)
            else:
                texto.add(c)
                w.field(c, 'C', min(254, max([len(str(v).encode('utf8')) for v in vals] + [1])))
        for f in feats:
            g = f['geometry']; t, c = g['type'], g['coordinates']
            if t == 'Point': w.point(c[0], c[1])
            elif t == 'LineString': w.line([c])
            elif t == 'MultiLineString': w.line(c)
            else:  # el Shapefile pide anillos exteriores en sentido horario
                rs = []
                for p in anillos(g):
                    for i, r in enumerate(p):
                        horario = area(r) < 0
                        rs.append(r if horario == (i == 0) else r[::-1])
                w.poly(rs)
            w.record(*[('' if (c in texto and f['properties'].get(c) is None) else f['properties'].get(c)) for c in orden])
        w.close()
        with zipfile.ZipFile(os.path.join(OUT, capa + '.shp.zip'), 'w', zipfile.ZIP_DEFLATED) as z:
            for e, b in bufs.items(): z.writestr('%s.%s' % (capa, e), b.getvalue())
            z.writestr(capa + '.prj', PRJ); z.writestr(capa + '.cpg', 'UTF-8')
            z.writestr('LEAME.txt', '%s\nAtlas de Mensuras de Giles · WGS84 (EPSG:4326)\nCampos: %s\n' % (titulo, ', '.join(orden)))
    resumen.append(dict(id=capa, titulo=titulo, n=len(feats), geom=tipo,
                        kb={e: round(os.path.getsize(os.path.join(OUT, capa + '.' + e)) / 1024) for e in ('geojson', 'kml', 'shp.zip')
                            if os.path.exists(os.path.join(OUT, capa + '.' + e))}))
    print('%-24s %6d %s' % (capa, len(feats), resumen[-1]['kb']))
json.dump(resumen, open(os.path.join(OUT, 'capas.json'), 'w', encoding='utf8'), ensure_ascii=False, indent=1)
if not shapefile: print('AVISO: sin pyshp no se generaron los Shapefile (pip install pyshp)')
