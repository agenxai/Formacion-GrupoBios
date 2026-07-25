"""Configuración del laboratorio, tipada y validada al arrancar.

Spec 02: `config.py` DEBE validar las variables de entorno con pydantic-settings y
fallar al arrancar con un mensaje legible si algo es inconsistente. No se descubren
errores de configuración a mitad de la demo.

Spec 09, Riesgo 5: este módulo lee la API key pero NUNCA la registra en logs ni la
expone en `resumen()`. Todo lo que sale de acá hacia la UI está filtrado.
"""

from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

RAIZ = Path(__file__).resolve().parent.parent

# Placeholders del .env.example. Si la key es uno de estos, es que nadie la editó:
# se trata como ausente en lugar de fallar con un 401 en medio de la clase.
PLACEHOLDERS_KEY = (
    "sk-proj-reemplaza-esto-con-tu-key",
    "sk-reemplaza-esto-con-tu-key",
    "tu-key-aqui",
    "",
)

VERSION = "1.0.0"


class Config(BaseSettings):
    """Variables de entorno del laboratorio. Nombres iguales a `.env.example`."""

    model_config = SettingsConfigDict(
        env_file=RAIZ / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # 1 · Credenciales
    openai_api_key: str = ""

    # 2 · Modelo
    openai_model: str = "gpt-4o-mini"
    modelo_supervisor: str = ""

    # 3 · Modo de ejecución
    modo: Literal["vivo", "replay", "auto"] = "auto"

    # 4 · Control de costo y de la API compartida
    tope_usd: float = Field(default=10.0, ge=0)
    max_concurrencia: int = Field(default=4, ge=1, le=32)
    cache_activo: bool = True
    precio_entrada_por_1m: float = Field(default=0.0, ge=0)
    precio_salida_por_1m: float = Field(default=0.0, ge=0)

    # 5 · Datos
    semilla_datos: int = 42
    fecha_referencia: str = ""

    # 6 · Red
    puerto_tablero: int = Field(default=8000, ge=1, le=65535)
    puerto_notebook: int = Field(default=8888, ge=1, le=65535)

    @field_validator("modo", mode="before")
    @classmethod
    def _normalizar_modo(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip().lower()
        return v

    @field_validator("openai_model", "modelo_supervisor", mode="before")
    @classmethod
    def _limpiar_modelo(cls, v: object) -> object:
        return v.strip() if isinstance(v, str) else v

    @field_validator("fecha_referencia")
    @classmethod
    def _validar_fecha(cls, v: str) -> str:
        v = v.strip()
        if not v:
            return v
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError(
                f"FECHA_REFERENCIA='{v}' no tiene el formato YYYY-MM-DD. "
                "Déjala vacía para usar la fecha de hoy."
            ) from exc
        return v

    # --- Derivados ------------------------------------------------------------

    @property
    def key_presente(self) -> bool:
        """True si hay una key que parece real (no el placeholder del ejemplo)."""
        return self.openai_api_key.strip() not in PLACEHOLDERS_KEY

    @property
    def modelo_del_supervisor(self) -> str:
        """Modelo de N5. Vacío en el entorno = el mismo de los demás niveles."""
        return self.modelo_supervisor or self.openai_model

    @property
    def costo_configurado(self) -> bool:
        """False si nadie puso las tarifas.

        Spec 09, Riesgo 3: con precios en 0 el tablero NO muestra `$0.00` —
        muestra «costo no configurado» y compara por tokens. Enseñar en silencio
        que un supervisor multiagente cuesta lo mismo que una sola llamada sería
        peor que no mostrar nada.
        """
        return self.precio_entrada_por_1m > 0 or self.precio_salida_por_1m > 0

    @property
    def fecha_base(self) -> date:
        """Fecha de referencia del dataset. Vacía en el entorno = hoy."""
        if self.fecha_referencia:
            return datetime.strptime(self.fecha_referencia, "%Y-%m-%d").date()
        return date.today()

    @property
    def ruta_db(self) -> Path:
        return RAIZ / "bios_ops.db"

    @property
    def ruta_cache(self) -> Path:
        return RAIZ / ".cache_llm"

    @property
    def ruta_trazas(self) -> Path:
        return RAIZ / "backend" / "replay" / "trazas.json"

    def modo_inicial(self) -> Literal["vivo", "replay"]:
        """Resuelve `MODO=auto` al arrancar.

        `auto` sin key es replay: el tablero arranca igual y nunca muestra una
        pantalla de error como primera impresión (spec 07).
        """
        if self.modo == "replay":
            return "replay"
        if self.modo == "vivo":
            return "vivo"
        return "vivo" if self.key_presente else "replay"

    def costo_usd(self, tokens_in: int, tokens_out: int) -> float:
        """Costo de una llamada. 0.0 si no hay tarifas configuradas.

        Quien consuma esto DEBE consultar `costo_configurado` antes de mostrarlo
        como dinero.
        """
        return (
            tokens_in * self.precio_entrada_por_1m
            + tokens_out * self.precio_salida_por_1m
        ) / 1_000_000

    def resumen(self) -> dict:
        """Estado publicable. NO incluye la key, solo si está presente."""
        return {
            "modo_configurado": self.modo,
            "modelo": self.openai_model,
            "modelo_supervisor": self.modelo_del_supervisor,
            "key_presente": self.key_presente,
            "tope_usd": self.tope_usd,
            "max_concurrencia": self.max_concurrencia,
            "cache_activo": self.cache_activo,
            "costo_configurado": self.costo_configurado,
            "semilla_datos": self.semilla_datos,
            "fecha_referencia": self.fecha_base.isoformat(),
            "version": VERSION,
        }


def _cargar() -> Config:
    """Carga la configuración o muere con un mensaje que dice qué arreglar."""
    try:
        cfg = Config()
    except ValidationError as exc:
        print("\n✕ Configuración inválida. Revisa tu archivo .env:\n", file=sys.stderr)
        for err in exc.errors():
            campo = ".".join(str(p) for p in err["loc"]) or "(raíz)"
            print(f"  · {campo.upper()}: {err['msg']}", file=sys.stderr)
        print(
            "\n  Plantilla de referencia: .env.example"
            "\n  Copia:                   cp .env.example .env\n",
            file=sys.stderr,
        )
        raise SystemExit(2) from exc

    # Inconsistencias que pydantic no puede ver campo por campo.
    if cfg.modo == "vivo" and not cfg.key_presente:
        print(
            "\n✕ MODO=vivo pero OPENAI_API_KEY está vacía o sigue con el "
            "placeholder del ejemplo."
            "\n  Opciones:"
            "\n    · pega la key real en .env, o"
            "\n    · usa MODO=auto (cae a replay solo) o MODO=replay\n",
            file=sys.stderr,
        )
        raise SystemExit(2)

    return cfg


config = _cargar()
