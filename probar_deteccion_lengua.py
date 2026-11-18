"""
probar_deteccion_lengua.py
==========================
Pone a prueba la identificación automática de lengua sobre el corpus y la
compara con la anotación manual de la columna LENGUA.

Por qué existe: la primera versión usaba una lista de 12 palabras inglesas
armada mirando el propio corpus (rasgo lista_inglés_ad_hoc). Esa lista solo
puede encontrar lo que ya se sabía que estaba, de modo que medir con ella es
circular. Aquí se usan detectores entrenados con datos ajenos al corpus, y se
miden sus aciertos y errores contra la lectura humana:

  lingua_5      Lingua (lingua-language-detector), restringido a español,
                inglés, portugués, italiano y francés. Lingua está diseñado
                para textos breves; devuelve un valor de confianza.
  lingua_75     Lingua con sus 75 lenguas, sin restricción.
  langid        py3langid (reimplementación de langid.py, Lui y Baldwin 2012),
                97 lenguas, entrenado con legislación europea, páginas web,
                Wikipedia, noticias y traducciones de software.
  lista_12      la lista ad hoc, como línea de base.

Antes de detectar se quitan marcas de transcripción ([corazón]), usuarios,
etiquetas y fechas, que no aportan información de lengua. Las producciones
sin letras quedan sin lengua asignada.

Uso:
    pip install lingua-language-detector py3langid
    python probar_deteccion_lengua.py corpus.csv --salida resultados

Salida en resultados/:
    11_deteccion_lengua.csv              una fila por producción, con la
                                         columna REVISION vacía para decidir
                                         cada discrepancia
    12_evaluacion_deteccion_lengua.csv   aciertos, falsos positivos y omisiones
                                         de cada detector para el inglés

Advertencia sobre la evaluación: LENGUA está vacía en muchas producciones por
decisión metodológica (nombres, siglas, etiquetas). Un "falso positivo" contra
una celda vacía no prueba que el detector se equivocó: hay que revisarlo.
"""

import argparse
import re
from pathlib import Path

import pandas as pd

from ordenar_corpus import cargar, separar_filas_ajenas, RASGOS, COL_ID, COL_ZONA, COL_TRANS

# La lista ad hoc se llama posible_inglés en versiones anteriores de ordenar_corpus.py
LISTA_12 = RASGOS.get("lista_inglés_ad_hoc") or RASGOS["posible_inglés"]
LIMPIAR = re.compile(r"\[[^\]]*\]|@[\w.\-]+|#\w+|\d+[/\-.]\d+(?:[/\-.]\d+)?")
TIENE_LETRAS = re.compile(r"[a-záéíóúüñ]", re.I)


def limpiar(texto: str) -> str:
    return " ".join(LIMPIAR.sub(" ", texto).split())


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("archivo")
    ap.add_argument("--salida", default="resultados")
    a = ap.parse_args()
    out = Path(a.salida)
    out.mkdir(exist_ok=True)

    from lingua import Language, LanguageDetectorBuilder
    import py3langid as langid

    cinco = LanguageDetectorBuilder.from_languages(
        Language.SPANISH, Language.ENGLISH, Language.PORTUGUESE,
        Language.ITALIAN, Language.FRENCH).with_preloaded_language_models().build()
    todas = LanguageDetectorBuilder.from_all_languages().with_preloaded_language_models().build()

    def lingua(det, t):
        r = det.compute_language_confidence_values(t)
        return r[0].language.iso_code_639_1.name.lower(), round(r[0].value, 2)

    corpus, _ = separar_filas_ajenas(cargar(a.archivo))
    d = corpus[corpus[COL_ZONA].str.strip().isin([str(n) for n in range(1, 15)])
               & (corpus[COL_TRANS].str.strip() != "")].copy()
    if "LENGUA" not in d:
        d["LENGUA"] = ""

    filas = []
    for _, r in d.iterrows():
        t = r[COL_TRANS]
        limpio = limpiar(t)
        fila = {COL_ID: r[COL_ID], COL_ZONA: r[COL_ZONA], COL_TRANS: t,
                "texto_analizado": limpio, "LENGUA_manual": r["LENGUA"],
                "lista_12": "en" if LISTA_12.search(t) else ""}
        if TIENE_LETRAS.search(limpio):
            fila["lingua_5"], fila["confianza_5"] = lingua(cinco, limpio)
            fila["lingua_75"], fila["confianza_75"] = lingua(todas, limpio)
            fila["langid"] = langid.classify(limpio)[0]
            mezcla = {s.language.iso_code_639_1.name.lower()
                      for s in cinco.detect_multiple_languages_of(limpio)}
            fila["lingua_segmentos"] = ", ".join(sorted(mezcla))
        else:
            fila.update(lingua_5="", confianza_5="", lingua_75="", confianza_75="",
                        langid="", lingua_segmentos="")
        fila["N_PALABRAS"] = len(re.findall(r"[^\W\d_]+", limpio))
        fila["REVISION"] = ""
        filas.append(fila)
    res = pd.DataFrame(filas)
    res.to_csv(out / "11_deteccion_lengua.csv", index=False)

    humano = res["LENGUA_manual"].str.lower().str.contains("ingl")
    total_h = int(humano.sum())
    ev = []
    for nombre, marca in [("lista ad hoc (12 palabras)", res.lista_12 == "en"),
                          ("Lingua, 5 lenguas", res.lingua_5 == "en"),
                          ("Lingua, 5 lenguas, confianza >= 0,8",
                           (res.lingua_5 == "en") & (pd.to_numeric(res.confianza_5, errors="coerce") >= 0.8)),
                          ("Lingua, 75 lenguas", res.lingua_75 == "en"),
                          ("langid, 97 lenguas", res.langid == "en"),
                          ("Lingua por segmentos (texto mixto)",
                           res.lingua_segmentos.str.contains("en"))]:
        tp, fp = int((marca & humano).sum()), int((marca & ~humano).sum())
        ev.append({"detector": nombre, "marcadas_como_inglés": int(marca.sum()),
                   "coinciden_con_anotación": tp, "falsos_positivos_a_revisar": fp,
                   "omitidas": total_h - tp,
                   "precisión": round(tp / marca.sum(), 2) if marca.sum() else 0,
                   "exhaustividad": round(tp / total_h, 2) if total_h else 0})
    ev = pd.DataFrame(ev)
    ev.to_csv(out / "12_evaluacion_deteccion_lengua.csv", index=False)

    con_letras = res[res.lingua_5 != ""]
    print(f"Producciones: {len(res)} | sin letras tras limpiar: {len(res) - len(con_letras)}")
    print(f"Palabras por producción (mediana): {res.N_PALABRAS.median():.0f}")
    print(f"Anotadas como inglés (o con inglés) en LENGUA: {total_h}")
    print(ev.to_string(index=False))
    print("\nLenguas más asignadas por langid:",
          con_letras.langid.value_counts().head(8).to_dict())
    print(f"Resultados en: {out.resolve()}")


if __name__ == "__main__":
    main()
