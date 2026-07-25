"""Trazas pregrabadas para el modo replay (spec 09, Riesgo 2).

`trazas.json` NO se versiona con contenido inventado. Se graba ejecutando de
verdad, con `python -m backend.replay.grabar`, y DEBE regrabarse si cambian los
prompts o el modelo — si no, mostraría algo que ya no es cierto.

Presentar una traza pregrabada como si fuera ejecución en vivo está prohibido por
la spec 09: si el facilitador dice «miren cómo el agente decide» sobre una traza
grabada y alguien lo descubre, se pierde la credibilidad de todo el programa.
"""
