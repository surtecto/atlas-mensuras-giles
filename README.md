# Atlas de Mensuras de Giles

Atlas histórico de consulta de las **191 carpetas de mensuras del partido de San Andrés de Giles** (Provincia de Buenos Aires), conservadas en el Archivo Histórico de Geodesia de la Provincia de Buenos Aires. Reúne en una sola página:

- **Mapa temporal (1825–1925):** polígonos georreferenciados de las mensuras, registro gráfico de c. 1874, planta urbana de 1884, caminos, ferrocarril, tranvía y telégrafo, y el poblamiento dibujado en los planos (casas, puestos, arrendatarios, pulperías, taperas). Las mensuras se pueden colorear por año, por agrimensor, por edificación o según su subdivisión en el registro de 1874. La **imagen satelital actual** queda siempre debajo (también se puede cambiar a OpenStreetMap o quitar el fondo), y cada capa histórica tiene su propia barra de transparencia, igual que el fondo, para leer el territorio de hoy a través de las mensuras del siglo XIX.
- **Carpetas:** carátula y plano de cada mensura, con visor de zoom y rotación, búsqueda y filtros.
- **Lecturas:** gráficos sobre la fragmentación parcelaria y el poblamiento, con preguntas abiertas.
- **Fuentes:** capas, método y advertencias.

Investigación doctoral de **Juan Patricio Addesso** (Doctorado en Geografía, Universidad del Salvador) sobre el paisaje pampeano y el Pago Gilense.

## Publicarlo con GitHub Pages

1. Creá un repositorio nuevo en GitHub (por ejemplo `atlas-mensuras-giles`).
2. Subí **todo el contenido de esta carpeta** a la raíz del repositorio, incluido el archivo oculto `.nojekyll`. Podés arrastrar los archivos en *Add file → Upload files* (GitHub acepta hasta 100 archivos por tanda, así que conviene subir las carpetas por partes) o usar la terminal:

   ```bash
   git init
   git add .
   git commit -m "Atlas de Mensuras de Giles"
   git branch -M main
   git remote add origin https://github.com/USUARIO/atlas-mensuras-giles.git
   git push -u origin main
   ```

3. En el repositorio: **Settings → Pages → Build and deployment → Source: Deploy from a branch → Branch: `main` / `(root)`** → Save.
4. En uno o dos minutos el atlas queda en `https://USUARIO.github.io/atlas-mensuras-giles/`.

La página carga sus datos con `fetch()`, así que **no funciona abriendo `index.html` con doble clic** desde el disco. Para probarla localmente, abrí una terminal en la carpeta y ejecutá `python3 -m http.server`, y después entrá a `http://localhost:8000`.

## Enlaces directos

- `…/#m57` abre el mapa centrado en la mensura de la carpeta 57.
- `…/#c57` abre el visor de carátula y plano de la carpeta 57.
- `…/#carpetas`, `#lecturas`, `#fuentes` abren cada sección.

## Estructura

```
index.html                  página completa (HTML + CSS + JS)
.nojekyll                   evita el procesamiento de Jekyll en GitHub Pages
lib/leaflet/                Leaflet 1.9.4 (BSD-2-Clause), incluido localmente
data/gis.json               todas las capas reunidas (WGS84), usadas por la página
data/catalog.json           ficha de cada carpeta: datos SIG, métricas, poblamiento, trazas e índice de transcripciones
data/geojson/*.geojson      las mismas capas por separado, para usarlas en QGIS u otro SIG
img/c/NNN.jpg               carátula de cada carpeta (1000 px)
img/p/NNN.jpg               plano de cada carpeta (1800 px)
img/sprite_ct.jpg           miniaturas de carátulas (16 × 12 celdas)
img/sprite_t.jpg            miniaturas de planos (16 × 12 celdas)
```

## Capas y procesamiento

| Capa | Elementos | Contenido |
|---|---|---|
| `mensuras_ahg` | 190 | Polígono de cada mensura: titular, año, agrimensor, edificado, superficie |
| `registro_grafico_1874` | 429 | Parcelario del partido; 72 polígonos con nomenclatura y titular actuales |
| `parcelas_urbanas_1884` | 488 | Planta del pueblo: propietario y ocupación |
| `caminos` | 114 | Caminos, ferrocarril, tranvía y telégrafo, con año y mensura de origen |
| `poblamiento_mensuras` | 732 | Casas, puestos, arrendatarios, pulperías, taperas dibujados en los planos |
| `estancias_puestos_1884` | 102 | Estancias, puestos, pulperías, postas y poblaciones de 1884 |

- Capas originales en POSGAR 2007 / Argentina faja 5 (EPSG:5347), reproyectadas a WGS84 (EPSG:4326). La capa urbana de 1884 declaraba WGS84 pero sus coordenadas estaban en POSGAR: se reproyectó igual.
- Superficies calculadas sobre la geometría proyectada, antes de simplificar para la web (tolerancia de 4 m en rurales y 0,5 m en urbanas).
- `frag` (en `catalog.json`): parcelas del registro 1874 con más de la mitad de su superficie dentro de la mensura. `cov`: fracción de la parcela 1874 dominante que cubre la mensura.
- Grafías de agrimensores unificadas: EQUIA → Eguía, ISACH → Ysach; Shuster y Carlos Schuster → Schuster.
- Carátulas fotografiadas apaisadas rotadas a vertical; los planos se muestran como fueron fotografiados (el visor permite girarlos).

## Advertencias

- Carpetas sin polígono en el SIG: 1, 14, 16, 122, 125, 167, 169, 176, 177, 178. Hay dos polígonos sin número.
- Números con más de un polígono: 17, 91, 100, 127, 138, 172.
- El SIG asigna el 127 al «Pueblo y Ejido de San Andrés de Giles» (Orlandini, 1884); la carpeta rotulada «Ejido» es la 137, que en el SIG corresponde a Casado.
- Carpeta 13: la ficha la registra a nombre de Bartolomé Saraví; el SIG, a nombre de Hipólito Quiroga.
- Carpeta 57: la carátula nombra al agrimensor Enrique Nelson (abril de 1870); en el SIG figura en blanco.
- Plano elegido con dudas: carpetas 39, 45, 48, 54 y 174. La carpeta 97 no tiene carátula identificable.
- No se incluye el parcelario catastral vigente completo (ARBA): la lectura «actual» se limita a los 72 polígonos cruzados con nomenclatura y titular.

## Créditos

- Documentos: Archivo Histórico de Geodesia, Ministerio de Infraestructura de la Provincia de Buenos Aires. Las reproducciones se publican con fines de investigación; consultá las condiciones del Archivo antes de reutilizarlas.
- Georreferenciación, transcripciones e interpretación: Juan Patricio Addesso — [Surtectura](https://www.surtectura.ar).
- Cartografía: [Leaflet](https://leafletjs.com); fondos © colaboradores de OpenStreetMap y Esri World Imagery.
