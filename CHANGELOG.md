# Registro de cambios

Cada versión publicada tiene una entrada con lo que cambió y por qué. Los números siguen el esquema MAYOR.MENOR.CORRECCIÓN: la versión 1.0.0 será la primera que produjo resultados citados.

## 1.0.0 (18/11/2026)

Primera versión con la que se obtienen las cifras citadas en la ponencia del VII Congreso de la AAHD y en el artículo derivado: 459 producciones, 1181 tokens, 653 formas y 325 producciones en las que coinciden los cuatro tokenizadores.

- `ordenar_corpus.py`: `cargar()` reconoce si un archivo descargado como .csv es en realidad un Excel (empieza con «PK») y, si es un CSV, prueba tres codificaciones (utf-8-sig, cp1252, latin-1). Lee todo como texto y con `keep_default_na=False`, para que una celda que dice «NA» no se lea como vacía. La versión anterior leía cualquier archivo con `read_excel`, de modo que no podía abrir un CSV.
- `probar_freeling.py`: opción `--cfg` para elegir la configuración de FreeLing (`es.cfg`, general, o `es-ar.cfg`, español de la Argentina). La evaluación manual se hizo con `es-ar.cfg`, y el cuaderno de Colab ahora la usa.

Cómo se armó esta versión: el archivo del 28/10/2026 no se conservó. Los cambios se reconstruyeron a partir del documento «Cómo leer el programa ordenar_corpus.py comentado», que describe esa versión función por función. La reconstrucción se verificó sobre la hoja 02 de la planilla de evaluación (459 producciones). Con las tres fechas que Google Sheets había convertido a su propio formato devueltas a dd/mm/aaaa (ID 133, 308 y 337; la del ID 308 escrita «19/6/25»), el programa da 459 producciones, 1181 tokens, 653 formas, 325 coincidencias entre tokenizadores y las frecuencias del artículo («y» 55, «+» 39, «a» 32, «te» 29, «te amo» 13). Los números de línea no coinciden exactamente con los del documento comentado. `probar_freeling.py` no se volvió a correr con FreeLing después del cambio.

## 0.2.0 (18/11/2026)

- `reproducir_muestra.py`: reproduce el sorteo de las 200 producciones evaluadas a mano (muestreo aleatorio simple sin reposición, `random_state=2026`, sobre los 458 ID distintos de la hoja 02) y, si se le pasa la hoja ETIQUETADO, comprueba que coincida ID por ID y en el mismo orden.
- `CITATION.cff`: la versión pasa de 1.0.0 a 0.2.0, para coincidir con este registro.

## 0.1.0 (16/11/2026)

Primera versión publicada. Reúne el código tal como estaba en Drive entre el 23 y el 27 de octubre de 2026 y agrega la documentación para que otras personas puedan usarlo.

- README, licencias (MIT para el código, CC BY 4.0 para la documentación y los datos), `CITATION.cff` y `requirements.txt`.
- Cuaderno de Colab comentado línea por línea. Descarga el código desde GitHub y toma el corpus desde Drive.
- `datos/corpus_ejemplo.xlsx`: 30 producciones anonimizadas para probar los scripts.

## Historia previa

- 27/10/2026: `probar_deteccion_lengua.py`. Reemplaza la lista ad hoc de 12 palabras inglesas, que solo encontraba lo que ya se sabía que estaba, por detectores entrenados con datos ajenos al corpus (Lingua y langid), evaluados contra la columna LENGUA.
- 23/10/2026: `probar_freeling.py`. Etiqueta con FreeLing para comparar con spaCy. Agrega un punto al final de cada producción para que FreeLing las analice por separado.
- 23/10/2026: primera versión de `ordenar_corpus.py`. Lee la planilla con `read_excel`, de modo que solo funciona si el archivo es un Excel, aunque se llame `.csv`.
