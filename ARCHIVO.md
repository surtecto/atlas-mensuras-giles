# Archivo abierto · guía de mantenimiento

`archivo.html` es la segunda página del Atlas. El mapa (`index.html`) muestra dónde; el Archivo guarda qué dicen los documentos, quiénes aparecen, qué se investigó y qué aporta la gente. Todo su contenido está en `data/archivo/`, en archivos de texto que se editan con el Bloc de notas.

| Archivo | Qué es | Quién lo toca |
|---|---|---|
| `fichas/NNN.json` | Ficha completa de una carpeta (el mismo JSON con que se arma el Word) | se copia tal cual |
| `indice_base.json` | Resumen de fichas hechas que todavía no tienen su JSON completo en la web | se vacía a medida que llegan los JSON |
| `fichas.json`, `personas.json`, `busqueda/` | Índices | los genera `tools/construir_archivo.py` |
| `biblioteca.json` | Papers, tesis, libros y fuentes | a mano |
| `aportes.json` | Aportes del público ya aprobados | a mano, pegando el registro |
| `preguntas.json` | Preguntas abiertas | a mano |
| `config.json` | Correo, formulario, enlaces de las otras plataformas, Zenodo | a mano |
| `../../descargas/sig/` | Capas en SHP, GeoJSON y KML | las genera `tools/exportar_sig.py` |

## Formatos: tres clases de archivo, las mismas para subir y para bajar

| Clase | Formatos | Para qué |
|---|---|---|
| Imágenes | JPG, PNG, TIFF | Fotos; mapas o documentos escaneados como imagen |
| Textos con imágenes o mapas | PDF | Fichas, investigaciones, documentos de varias páginas, láminas |
| Información espacial | SHP (.zip), GeoJSON / JSON, KML / KMZ | Capas, recorridos, puntos y polígonos |

- **Bajar.** Cada ficha: «Ficha (PDF)», carátula y plano en JPG, y su polígono en GeoJSON y KML. Cada capa del mapa: SHP, GeoJSON y KML, en `descargas/sig/`. Los listados (índice, personas, biblioteca, aportes) salen en PDF y, como única excepción, en planilla CSV para abrir en Excel.
- **Subir.** El formulario de aportes sólo admite esos formatos. Revisa cada archivo antes de armar el registro: avisa si un Word tiene que pasarse a PDF, si a un Shapefile le falta el .prj o si un GeoJSON o KML viene vacío. Límite: 100 MB por archivo.
- **«Ficha (PDF)»** abre el diálogo de impresión del navegador con la ficha maquetada en A4; ahí se elige «Guardar como PDF». Si subís los PDF a Zenodo, pegá el enlace por ficha en `config.json` → `pdf` (igual que `docx`) y el botón descarga el archivo directamente.
- **Regenerar las capas** cuando cambie el SIG: `python3 tools/exportar_sig.py` (pide `pip install pyshp`). Lee `data/geojson/` y `data/parcelas_2024.json` y reescribe `descargas/sig/` en los tres formatos, en WGS84, con nombres de campo legibles.
- **Formulario de Google.** En la pregunta «Archivos» no restrinjas el tipo: Google no tiene la opción «zip» ni «kml» y los rechazaría.

## 1. Sumar una ficha transcripta

1. Copiar el JSON de la ficha a `data/archivo/fichas/` con el número en tres cifras (`048.json`).
2. En la carpeta del repositorio: `python3 tools/construir_archivo.py`. Rehace los índices, la búsqueda de texto completo y el resumen que usa el mapa.
3. Publicar con GitHub Desktop.

El volumen no es un problema: la página carga sólo el índice (unos 200 KB con las 191 fichas) y trae cada ficha cuando alguien la abre. El texto completo para buscar se parte en tandas de 25 fichas y se baja recién al tildar «buscar dentro de las transcripciones».

**Estado al 8/10/2026:** 47 fichas en el índice; sólo la 047 tiene su JSON completo en la web. Las otras 46 muestran el resumen. Sus JSON están en el proyecto de Claude (`claude/digitalizacion/CNNN.json`) y hay que bajarlos a esta carpeta.

## 2. Los Word (.docx) y Zenodo

Los Word pesan entre 5 y 12 MB cada uno: no van al repositorio. Se suben a Zenodo (zenodo.org, gratuito, con DOI):

1. Crear una cuenta y un *New upload* de tipo *Dataset*, por ejemplo «Mensuras de San Andrés de Giles: fichas 001-050».
2. Subir los .docx y el índice .xlsx. Licencia CC BY 4.0. Publicar: Zenodo asigna un DOI.
3. En `config.json`, pegar el enlace de la colección en `zenodo_coleccion` y, por ficha, el enlace directo en `docx`:
   `"docx": {"001": "https://zenodo.org/records/XXXX/files/Ficha 001 - Bagué (1825).docx"}`
   Cada ficha muestra entonces el botón «Word (.docx)».

Cada nueva tanda se sube como *New version* del mismo registro, y el DOI general sigue valiendo.

## 3. Recibir aportes del público

La página arma el registro del aporte (tipo, título, descripción, lugar, autor, licencia) en el mismo formato de `aportes.json`.

- **Sin configurar nada**, la persona copia el registro y lo manda con los archivos a `surtectura@gmail.com`.
- **Con formulario** (recomendado): crear un Formulario de Google con dos preguntas, «Registro del aporte» (párrafo) y «Archivos» (subir archivos, hasta 10, 100 MB). Los archivos quedan en una carpeta de tu Drive. Pegar el enlace del formulario en `config.json` → `formulario_aportes`. La subida de archivos de Google exige que la persona tenga cuenta de Google.

Para **publicar** un aporte aprobado:
1. Subir sus archivos a una carpeta pública (Drive con enlace, o Zenodo si es una investigación).
2. Pegar el registro en `aportes.json`, borrar la línea `contacto` y completar `archivos`:
   `"archivos": [{"nombre": "Foto 1", "url": "https://…"}]`
3. Publicar. Si el registro lleva `carpeta`, aparece también dentro de esa ficha.

## 4. Biblioteca

Agregar un bloque a `biblioteca.json`:

```json
{"id": "apellido2020clave", "tipo": "tesis", "autores": ["Apellido, Nombre"], "anio": "2020",
 "titulo": "…", "en": "Universidad…, Facultad…", "url": "https://…", "acceso": "abierto",
 "temas": ["…"], "nota": "Qué aporta para Giles."}
```

Tipos: `libro`, `articulo`, `tesis`, `ponencia`, `capitulo`, `fuente`, `recurso`, `informe`, `mapa`. La página lo exporta a PDF y a planilla CSV.

## 5. Enlazar las otras plataformas

En `config.json` → `plataformas`, completar `url` de Consulta Urbanística, Registro Patrimonial y Digesto Gilense con su dirección pública. Mientras esté vacío, la tarjeta dice «enlace público próximamente». Desde esas páginas conviene enlazar de vuelta:
- a una mensura en el mapa: `…/atlas-mensuras-giles/#m57`
- a una ficha: `…/atlas-mensuras-giles/archivo.html#f057`
- a una sección: `archivo.html#biblioteca`, `#aportes`, `#preguntas`, `#descargas`
