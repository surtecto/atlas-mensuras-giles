#!/usr/bin/env python3
"""
Atlas de Mensuras de Giles · capa «Planos georreferenciados»
Convierte los planos rectificados (.img ERDAS, Gauss-Krüger faja 5, georreferenciados por
J. P. Addesso en 2012) en imágenes livianas para Leaflet (L.imageOverlay).

Uso:
  python3 -I preparar_planos_georef.py <carpeta_img> <mensuras_ahg.geojson> <salida_repo> N [N ...]
    <carpeta_img>  carpeta con los .img staged (busca también en subcarpeta «2 visita»)
    <salida_repo>  raíz del clon del atlas: escribe img/g/NNN_h.webp, img/g/NNN_r.webp
                   y fusiona data/planos_georef.json

Salidas por plano:
  NNN_h.webp  hoja completa, reproyectada a EPSG:3857, lado mayor ≤ 2400 px, fondo transparente
  NNN_r.webp  recorte: polígono de la mensura + 300 m, resolución nativa (≤ 3000 px)
  Contraste realzado (percentiles 1–99 sobre los píxeles válidos) porque las fotos de 2012 son oscuras.
El sistema de origen se asume EPSG:5347 (los .img no traen CRS; coordenadas ~5.5 M E / 6.2 M N).
"""
import sys, os, re, io, json, glob
import numpy as np, rasterio, shapely
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.features import geometry_mask
from shapely.geometry import shape, mapping
from pyproj import Transformer
from PIL import Image

SRC = 'EPSG:5347'
FW = Transformer.from_crs(4326, 3857, always_xy=True)
INV = Transformer.from_crs(3857, 4326, always_xy=True)

def candidatos(carpeta):
    """{n: [rutas .img]} ; el nombre empieza con «Mensura NNN»."""
    out = {}
    for p in glob.glob(os.path.join(carpeta, '**', '*.img'), recursive=True):
        m = re.match(r'Mensura (\d+)', os.path.basename(p))
        if m: out.setdefault(int(m.group(1)), []).append(p)
    return out

def elegir(rutas):
    """Varias versiones del mismo número: la más reciente (mtime). Las demás quedan anotadas."""
    rutas = sorted(rutas, key=os.path.getmtime, reverse=True)
    return rutas[0], rutas[1:]

def warp(src, A, maxpx=None):
    tr, w, h = calculate_default_transform(SRC, 'EPSG:3857', src.width, src.height, *src.bounds)
    if maxpx and max(w, h) > maxpx:
        s = max(w, h) / maxpx
        tr, w, h = calculate_default_transform(SRC, 'EPSG:3857', src.width, src.height, *src.bounds,
                                               dst_width=int(w / s), dst_height=int(h / s))
    out = np.zeros((3, h, w), np.uint8)
    for b in range(3):
        reproject(A[b], out[b], src_crs=SRC, src_transform=src.transform, dst_transform=tr,
                  dst_crs='EPSG:3857', resampling=Resampling.bilinear, src_nodata=0, dst_nodata=0)
    return out, tr

def realzar(arr, valid):
    o = arr.astype(np.float32)
    for b in range(3):
        v = o[b][valid]
        if v.size < 100: continue
        lo, hi = np.percentile(v, 1), np.percentile(v, 99)
        o[b] = (o[b] - lo) / max(hi - lo, 1) * 255
    return np.clip(o, 0, 255).astype(np.uint8)

def guardar(arr, alpha, tr, ruta, maxpx=None):
    ys, xs = np.where(alpha > 0)
    if not ys.size: return None
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    rgba = np.dstack([arr[0], arr[1], arr[2], alpha])[y0:y1, x0:x1]
    t2 = tr * rasterio.Affine.translation(x0, y0)
    im = Image.fromarray(rgba, 'RGBA')
    if maxpx and max(im.size) > maxpx:
        k = maxpx / max(im.size); im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    im.save(ruta, 'WEBP', quality=74, method=6)
    W, S = t2 * (0, rgba.shape[0]); E, N = t2 * (rgba.shape[1], 0)
    sw, ne = INV.transform(W, S), INV.transform(E, N)
    return {'b': [[round(sw[1], 6), round(sw[0], 6)], [round(ne[1], 6), round(ne[0], 6)]],
            'px': list(im.size), 'kb': round(os.path.getsize(ruta) / 1024)}

def procesar(n, ruta, feats, dest):
    src = rasterio.open(ruta); A = src.read()
    if A.shape[0] < 3: A = np.repeat(A[:1], 3, 0)
    rec = {'src': os.path.relpath(ruta).replace('\\', '/').split('/')[-1],
           'm_px': round(abs(src.transform.a), 2)}
    a, tr = warp(src, A, 2400); v = a.sum(0) > 0
    rec['h'] = guardar(realzar(a, v), np.where(v, 255, 0).astype(np.uint8), tr, f'{dest}/{n:03d}_h.webp')
    geoms = [shape(f['geometry']) for f in feats]
    if geoms:
        p3 = shapely.union_all([shapely.transform(g, lambda c: np.column_stack(FW.transform(c[:, 0], c[:, 1]))) for g in geoms])
        a, tr = warp(src, A); v = a.sum(0) > 0
        k = 1 / np.cos(np.radians(34.35))            # metros reales → metros Mercator
        m = ~geometry_mask([mapping(p3.buffer(300 * k))], out_shape=a.shape[1:], transform=tr)
        rec['r'] = guardar(realzar(a, v), np.where(m & v, 255, 0).astype(np.uint8), tr,
                           f'{dest}/{n:03d}_r.webp', 3000)
    else:
        rec['r'] = None                                # carpeta sin polígono en el SIG: solo hoja
    return rec

def main():
    carpeta, gj, repo = sys.argv[1:4]; nums = [int(x) for x in sys.argv[4:]]
    G = json.load(open(gj, encoding='utf-8'))
    por_n = {}
    for f in G['features']:
        por_n.setdefault(f['properties'].get('n'), []).append(f)
    dest = os.path.join(repo, 'img', 'g'); os.makedirs(dest, exist_ok=True)
    jpath = os.path.join(repo, 'data', 'planos_georef.json')
    J = json.load(open(jpath, encoding='utf-8')) if os.path.exists(jpath) else {}
    cand = candidatos(carpeta)
    for n in nums or sorted(cand):
        if n not in cand: print(f'{n:03d}\tSIN .img'); continue
        ruta, otras = elegir(cand[n])
        try:
            rec = procesar(n, ruta, por_n.get(n, []), dest)
            if otras: rec['alt'] = [os.path.basename(o) for o in otras]
            J[str(n)] = rec
            print(f"{n:03d}\tok\th={rec['h'] and rec['h']['kb']}KB\tr={rec['r'] and rec['r']['kb']}KB\t{rec['src']}"
                  + (f"\tALTERNATIVAS: {rec['alt']}" if otras else ''))
        except Exception as e:
            print(f'{n:03d}\tERROR\t{e}')
    J = dict(sorted(J.items(), key=lambda kv: int(kv[0])))
    json.dump(J, open(jpath, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))

if __name__ == '__main__':
    main()
