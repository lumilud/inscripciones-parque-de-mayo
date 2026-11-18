# Registro de cambios

Cada versión publicada tiene una entrada con lo que cambió y por qué. Los números siguen el esquema MAYOR.MENOR.CORRECCIÓN: la versión 1.0.0 será la primera que produjo resultados citados.

## Sin publicar

- Incorporar la versión del 28/10/2026 de `ordenar_corpus.py`, con la que se obtuvieron las cifras de la ponencia en el VII Congreso de la AAHD (459 producciones, 1181 tokens, 653 formas). En esa versión, `cargar()` reconoce si la planilla es en realidad un Excel y, si es un CSV, prueba tres codificaciones.
- Incorporar la versión de `probar_freeling.py` con la opción `--cfg`, para elegir entre `es.cfg` y `es-ar.cfg`.

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
