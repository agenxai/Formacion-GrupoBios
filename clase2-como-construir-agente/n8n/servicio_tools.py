"""Servicio liviano de tools para la Parte 2 (n8n) — spec 06, opción 1.

Expone las MISMAS cuatro funciones de `agente-transparente/tools.py` como un
endpoint HTTP, para que los nodos Tool del workflow de n8n las llamen. No hay
lógica duplicada: este archivo solo importa y despacha — la consulta SQL, el
whitelisting y el manejo de "no encontré" viven en `tools.py`, idénticos a los
que se proyectan en la Parte 1a.

Solo usa la librería estándar de Python (sin FastAPI ni Flask) para no agregar
dependencias al `requirements.txt` de la clase.

Uso:
    cd clase2-como-construir-agente
    python n8n/servicio_tools.py            # escucha en 0.0.0.0:8788
    TOOLS_PORT=9000 python n8n/servicio_tools.py

Endpoints:
    GET  /salud                → {"ok": true} — para verificar que está vivo
    POST /tools/<nombre>       → ejecuta la tool con el JSON del body como args

Ejemplo:
    curl -X POST http://localhost:8788/tools/consultar_inventario \
         -H "Content-Type: application/json" \
         -d '{"planta": "Itagüí", "materia_prima": "maíz"}'

Seguridad (mismas reglas de la clase):
· Solo expone las 4 tools de la clase 2 — nada de SQL arbitrario.
· La conexión a bios_ops.db es de SOLO LECTURA (la abre tools.py).
· Los datos son SINTÉTICOS — ningún dato real de Grupo Bios.
· Para que la instancia n8n cloud de Bios lo alcance, el servicio debe correr
  en una máquina accesible desde esa red (coordinar con TI de Bios) o
  exponerse por un túnel durante la clase. No dejarlo expuesto después.
"""

from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# Las tools viven en agente-transparente/ — se importan tal cual (ADR-003).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agente-transparente"))

from tools import TOOLS_FUNC, dispatch  # noqa: E402

PUERTO = int(os.getenv("TOOLS_PORT", "8788"))

_AVISO = "Datos sintéticos — bios_ops.db no representa datos reales de Grupo Bios."


class ManejadorTools(BaseHTTPRequestHandler):
    """Despacha POST /tools/<nombre> a la función correspondiente de tools.py."""

    def _responder(self, codigo: int, cuerpo: dict) -> None:
        datos = json.dumps(cuerpo, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(datos)))
        self.end_headers()
        self.wfile.write(datos)

    def do_GET(self) -> None:  # noqa: N802 — nombre exigido por http.server
        if self.path.rstrip("/") in ("", "/salud"):
            self._responder(200, {
                "ok": True,
                "tools": sorted(TOOLS_FUNC),
                "aviso": _AVISO,
            })
        else:
            self._responder(404, {"error": f"Ruta desconocida: {self.path}"})

    def do_POST(self) -> None:  # noqa: N802
        partes = self.path.strip("/").split("/")
        if len(partes) != 2 or partes[0] != "tools":
            self._responder(404, {"error": "Usa POST /tools/<nombre>."})
            return
        nombre = partes[1]
        if nombre not in TOOLS_FUNC:
            self._responder(404, {
                "error": f"Tool desconocida: {nombre}",
                "tools": sorted(TOOLS_FUNC),
            })
            return

        try:
            largo = int(self.headers.get("Content-Length", 0))
            args = json.loads(self.rfile.read(largo) or b"{}")
            if not isinstance(args, dict):
                raise ValueError("el body debe ser un objeto JSON")
        except (ValueError, json.JSONDecodeError) as e:
            self._responder(400, {"error": f"Body JSON inválido: {e}"})
            return

        # Los nodos Tool de n8n mandan los opcionales como cadena vacía cuando
        # el modelo no los usa — se limpian antes de llamar la función.
        args = {k: v for k, v in args.items() if v not in ("", None)}

        try:
            self._responder(200, dispatch(nombre, args))
        except TypeError as e:
            self._responder(400, {"error": f"Argumentos inválidos para {nombre}: {e}"})
        except Exception as e:  # la tool nunca debe tumbar el servicio
            self._responder(500, {"error": f"Fallo ejecutando {nombre}: {e}"})

    def log_message(self, formato: str, *args) -> None:
        print(f"[servicio_tools] {self.address_string()} — {formato % args}")


def main() -> None:
    print(_AVISO)
    print(f"[servicio_tools] Escuchando en http://0.0.0.0:{PUERTO}")
    print(f"[servicio_tools] Tools expuestas: {', '.join(sorted(TOOLS_FUNC))}")
    print("[servicio_tools] Ctrl+C para detener.")
    ThreadingHTTPServer(("0.0.0.0", PUERTO), ManejadorTools).serve_forever()


if __name__ == "__main__":
    main()
