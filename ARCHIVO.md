# Archivo abierto · guía de mantenimiento

`archivo.html` es la segunda página del Atlas. El mapa (`index.html`) muestra dónde; el Archivo guarda qué dicen los documentos, quiénes aparecen, qué se investigó y qué aporta la gente. Todo su contenido está en `data/archivo/`, en archivos de texto que se editan con el Bloc de notas.

| Archivo | Qué es | Quién lo toca |
|---|---|---|
| `fichas/NNN.json` | Ficha completa de una carpeta | lo genera `tools/docx_a_ficha.py` desde el Word |
| `fichas.json`, `personas.json`, `busqueda/` | Índices | los genera `tools/construir_archivo.py` |
| `biblioteca.json` | Papers, tesis, libros y fuentes | a mano |
| `aportes.json` | Aportes del público ya aprobados | a mano, pegando el registro |
| `preguntas.json` | Preguntas abiertas | a mano |
| `config.json` | Correo, formulario, enlaces de las otras plataformas, Zenodo | a mano |
| `../../descargas/sig/` | Capas en SHP, GeoJSON y KML | las genera `tools/exportar_sig.py` |

## Formatos: cuatro clases de archivo, las mismas para subir y para bajar

| Clase | Formatos | Qué se baja |
|---|---|---|
| Textos con imágenes o mapas | PDF | Cada ficha completa con sus fotografías (`descargas/fichas/Ficha_NNN.pdf`); índice de fichas, personas y biblioteca |
| Datos en tabla | Excel (XLSX) | Un solo libro, `descargas/atlas_giles_datos.xlsx`, con las hojas Fichas, Hojas, Renglones, Láminas, Personas, Biblioteca y Aportes |
| Imágenes | JPG, PNG, TIFF | La fotografía de cada hoja (`img/f/NNN/`), carátula y plano de cada carpeta |
| Información espacial | SHP (.zip), GeoJSON / JSON, KML / KMZ | Las capas del mapa (`descargas/sig/`) y el polígono de cada mensura |

Los PDF y el Excel no los arma el navegador: son archivos ya maquetados, con la paleta y la tipografía de las fichas en Word. El formulario de aportes admite sólo estos formatos y revisa cada archivo (Word → PDF, Shapefile sin .prj, GeoJSON o KML vacío). Límite: 100 MB por archivo. En el Formulario de Google, no restrinjas el tipo de archivo: no tiene la opción «zip» ni «kml».

## 1. Sumar fichas transcriptas

La fuente son los Word de la carpeta `Transcripciones`. Cuatro pasos, desde la carpeta del repositorio:

1. `python3 tools/docx_a_ficha.py "RUTA\Transcripciones" 048 049` — lee cada Word y escribe `data/archivo/fichas/NNN.json` y las fotografías en `img/f/NNN/` (1100 px). Sin números, convierte todas.
2. `python3 tools/construir_archivo.py` — rehace el índice, las personas, la búsqueda de texto completo y el resumen que usa el mapa.
3. `python3 tools/generar_descargas.py 048 049` — arma el PDF de esas fichas y rehace los índices en PDF y el libro de Excel. Necesita Chrome o Chromium, `pip install openpyxl pillow`.
4. `python3 tools/construir_archivo.py` otra vez (registra los PDF nuevos) y publicar con GitHub Desktop.

Es más cómodo pedírselo a Claude al terminar cada tanda de transcripción: «actualizá el Archivo abierto con las fichas nuevas».

**Estado al 8/10/2026:** 47 fichas completas en línea: 405 hojas, 11.793 renglones, 107 láminas, 395 notas biográficas y 590 fotografías.

**Peso.** Cada ficha suma en promedio 1,4 MB de fotos y 1,2 MB de PDF. Con las 191 el sitio rondará los 600 MB; GitHub Pages admite hasta 1 GB. Si hiciera falta, los PDF pueden mudarse a Zenodo sin tocar la página.

**Capas del SIG.** Cuando cambien: `python3 tools/exportar_sig.py` (pide `pip install pyshp`); reescribe `descargas/sig/` en SHP, GeoJSON y KML.

## 2. Los Word (.docx) y Zenodo (opcional)

Los PDF de las fichas ya están en el sitio. Si además querés ofrecer los Word editables y tener un DOI citable, se suben a Zenodo (zenodo.org, gratuito):

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

Tipos: `libro`, `articulo`, `tesis`, `ponencia`, `capitulo`, `fuente`, `recurso`, `informe`, `mapa`. `generar_descargas.py` la lleva al PDF y al Excel.

## 5. Enlazar las otras plataformas

Ya están cargadas en `config.json` → `plataformas`: Consulta Urbanística (`Consulta-COUSAG2024`), Registro del Patrimonio Cultural (`WEB-Patrimonio`) y Digesto Gilense (`HCD-SAG-Digesto2026`). Desde esas páginas conviene enlazar de vuelta:
- a una mensura en el mapa: `…/atlas-mensuras-giles/#m57`
- a una ficha: `…/atlas-mensuras-giles/archivo.html#f057`
- a una sección: `archivo.html#biblioteca`, `#aportes`, `#preguntas`, `#descargas`
