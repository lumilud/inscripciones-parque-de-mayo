# -*- coding: utf-8 -*-
"""
Reproduce la muestra de 200 producciones evaluada a mano en la hoja ETIQUETADO
de la planilla «Evaluación PLN · planilla unificada».

Qué hace, paso a paso:
  1. Lee la hoja 02_corpus_ordenado_con_rasgos exportada como CSV
     (Archivo > Descargar > Valores separados por comas, desde esa hoja).
  2. Toma la columna ID_FOTO en el orden en que aparece en la hoja.
  3. Elimina los ID repetidos y se queda con la primera aparición de cada uno.
     La hoja tiene 459 filas y 458 ID distintos, porque el ID 97 aparece dos
     veces (la segunda vez en el lugar donde debería estar el 92).
  4. Sortea 200 de esos 458 ID con pandas, Series.sample(n=200,
     random_state=2026). Es un muestreo aleatorio simple sin reposición
     (pandas usa replace=False por defecto) y sin estratificar: cada ID
     tiene la misma probabilidad de salir y no se controla la zona.
  5. Guarda los 200 ID en el orden en que salieron del sorteo. Ese orden es
     la columna ORDEN de ETIQUETADO.
  6. Si se le pasa también la hoja ETIQUETADO exportada como CSV, compara
     y dice si la muestra coincide ID por ID y en el mismo orden.

Uso (en Colab o en una terminal con Python y pandas):
  python reproducir_muestra.py 02_corpus_ordenado_con_rasgos.csv
  python reproducir_muestra.py 02_corpus_ordenado_con_rasgos.csv ETIQUETADO.csv

Probado con pandas 3.0.5 y numpy 2.5.3. Con la misma semilla, pandas da el
mismo resultado en distintas versiones, porque usa el generador clásico de
numpy (RandomState).
"""

import sys
import pandas as pd

SEMILLA = 2026
TAMANIO = 200


def ids_de_la_poblacion(ruta_02):
    """Devuelve la lista de ID_FOTO distintos, en el orden de la hoja 02."""
    corpus = pd.read_csv(ruta_02, dtype=str, keep_default_na=False)
    ids = corpus["ID_FOTO"].str.strip()
    ids = ids[ids != ""]                      # por si hay filas vacías al final
    distintos = list(dict.fromkeys(ids))      # quita repetidos, conserva el orden
    print(f"Filas en la hoja 02: {len(ids)}")
    print(f"ID distintos (población): {len(distintos)}")
    repetidos = ids[ids.duplicated()].tolist()
    if repetidos:
        print(f"ID repetidos: {', '.join(repetidos)}")
    return distintos


def sortear(ids):
    """Muestreo aleatorio simple sin reposición, con semilla fija."""
    return pd.Series(ids).sample(n=TAMANIO, random_state=SEMILLA).tolist()


def comparar(muestra, ruta_eval):
    """Compara el sorteo con el orden de ETIQUETADO (columnas ORDEN e ID_FOTO)."""
    ev = pd.read_csv(ruta_eval, dtype=str, keep_default_na=False)
    ev = ev[ev["ORDEN"] != ""]
    orden = ev.drop_duplicates("ORDEN")[["ORDEN", "ID_FOTO"]]
    orden = orden.sort_values("ORDEN", key=lambda s: s.astype(int))
    en_hoja = orden["ID_FOTO"].tolist()
    if en_hoja == muestra:
        print("Coincide: mismos 200 ID y en el mismo orden que ETIQUETADO.")
    elif set(en_hoja) == set(muestra):
        print("Mismos 200 ID, pero en otro orden.")
    else:
        print(f"No coincide: {len(set(en_hoja) & set(muestra))} ID en común.")


if __name__ == "__main__":
    poblacion = ids_de_la_poblacion(sys.argv[1])
    muestra = sortear(poblacion)
    salida = pd.DataFrame({"ORDEN": range(1, TAMANIO + 1), "ID_FOTO": muestra})
    salida.to_csv("muestra_200_ids.csv", index=False)
    print("Listo: muestra_200_ids.csv")
    print("Primeros diez:", ", ".join(muestra[:10]))
    if len(sys.argv) > 2:
        comparar(muestra, sys.argv[2])
