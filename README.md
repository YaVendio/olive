# Olive 🫒

[![Tests](https://github.com/YaVendio/olive/actions/workflows/tests.yml/badge.svg)](https://github.com/YaVendio/olive/actions/workflows/tests.yml)
[![codecov](https://codecov.yvd.io/gh/YaVendio/olive/graph/badge.svg?token=GBSWGDHRBB)](https://codecov.yvd.io/gh/YaVendio/olive)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Python Version](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2FYaVendio%2Folive%2Fmain%2Fpyproject.toml)](https://github.com/YaVendio/olive/blob/main/pyproject.toml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub release](https://img.shields.io/github/v/release/YaVendio/olive)](https://github.com/YaVendio/olive/releases)
[![GitHub stars](https://img.shields.io/github/stars/YaVendio/olive)](https://github.com/YaVendio/olive/stargazers)
[![GitHub issues](https://img.shields.io/github/issues/YaVendio/olive)](https://github.com/YaVendio/olive/issues)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/YaVendio/olive/pulls)

_[English documentation available](README_EN.md) / [Documentación en inglés disponible](README_EN.md)_

> Un framework minimalista para exponer endpoints de FastAPI como herramientas de LangChain con integración de Temporal para ejecución confiable y escalable.

## 📋 Tabla de Contenidos

- [Descripción General](#-descripción-general)
- [Características](#-características)
- [Arquitectura](#-arquitectura)
- [Instalación](#-instalación)
- [Inicio Rápido](#-inicio-rápido)
- [Uso Avanzado](#-uso-avanzado)
- [Configuración](#️-configuración)
- [Integración con Temporal](#-integración-con-temporal)
- [CLI](#-interfaz-de-línea-de-comandos-cli)
- [API Reference](#-api-reference)
- [Ejemplos](#-ejemplos)
- [Desarrollo](#-desarrollo)
- [Solución de Problemas](#-solución-de-problemas)
- [Contribuir](#-contribuir)
- [Licencia](#-licencia)

## 🌟 Descripción General

Olive es un framework que simplifica la exposición de funciones Python como herramientas remotas que pueden ser utilizadas por agentes de LangChain. Con solo agregar un decorador `@olive_tool` a tus funciones, estas se vuelven accesibles como herramientas remotas a través de una API RESTful.

### ¿Por qué Olive?

- **Simplicidad**: Un solo decorador transforma tus funciones en herramientas remotas
- **Confiabilidad**: Integración con Temporal para ejecución distribuida y tolerante a fallos
- **Flexibilidad**: Compatible con funciones síncronas y asíncronas
- **Type-Safe**: Extracción automática de esquemas desde type hints de Python
- **Escalable**: Diseñado para manejar cargas de trabajo empresariales

## ✨ Características

### Características Principales

- 🎯 **Decorador Simple**: Convierte funciones en herramientas con `@olive_tool`
- 🔧 **Type-Safe**: Validación automática con Pydantic y extracción de esquemas
- 🚀 **Async-First**: Soporte completo para programación asíncrona
- 🔗 **Integración con LangChain**: Conversión directa a herramientas de LangChain
- 📦 **Dependencias Mínimas**: Solo FastAPI, Pydantic, httpx, langchain-core y Temporal

### Características Avanzadas

- ⚡ **Integración con Temporal**: Ejecución distribuida y confiable
- 🔄 **Políticas de Reintentos**: Manejo automático de fallos con reintentos configurables
- ⏱️ **Timeouts Configurables**: Control de tiempo de ejecución por herramienta
- 📊 **Monitoreo**: Métricas y logs detallados de ejecución
- 🎨 **CLI Rica**: Interfaz de línea de comandos con animaciones y feedback visual
- 🔐 **Preparado para Producción**: Configuración vía archivos YAML o variables de entorno

## 🏗️ Arquitectura

Olive utiliza una arquitectura de tres capas:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Cliente       │────▶│   Servidor      │────▶│    Temporal     │
│  (OliveClient)  │     │   (FastAPI)     │     │    (Workers)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                        │                        │
        │                        │                        │
        ▼                        ▼                        ▼
   Agentes de              Endpoints API            Ejecución
   LangChain               /olive/tools           Distribuida
```

## 📦 Instalación

### Prerrequisitos

- Python 3.13 o superior
- [uv](https://github.com/astral-sh/uv) (gestor de paquetes recomendado)
- Temporal CLI (opcional, para desarrollo local)

### Instalación desde GitHub

```bash
# Instalar directamente desde Git
uv pip install git+ssh://git@github.com/YaVendio/olive.git

# O agregar a tu proyecto
uv add git+ssh://git@github.com/YaVendio/olive.git

# Instalar una versión específica
uv add git+ssh://git@github.com/YaVendio/olive.git@v1.1.3
```

### Instalación desde el Código Fuente

```bash
git clone git@github.com:YaVendio/olive.git
cd olive
uv pip install -e .
```

Para instrucciones detalladas de instalación, consulta [INSTALL_WITH_UV.md](INSTALL_WITH_UV.md).

## 🚀 Inicio Rápido

### 1. Crear Herramientas en el Servidor

```python
from olive import olive_tool, setup_olive
from fastapi import FastAPI

app = FastAPI()
setup_olive(app)  # Agrega los endpoints de Olive

@olive_tool
def traducir(texto: str, idioma_destino: str = "en") -> dict:
    """Traduce texto a otro idioma."""
    # Tu implementación aquí
    traducciones = {
        "en": f"[EN] {texto}",
        "fr": f"[FR] {texto}",
        "de": f"[DE] {texto}",
    }
    return {
        "original": texto,
        "traducido": traducciones.get(idioma_destino, texto),
        "idioma": idioma_destino
    }

@olive_tool(description="Analiza el sentimiento del texto")
async def analizar_sentimiento(texto: str, detallado: bool = False) -> dict:
    """Realiza análisis de sentimiento en el texto."""
    # Implementación asíncrona
    await asyncio.sleep(0.1)  # Simular procesamiento

    resultado = {
        "sentimiento": "positivo",
        "puntuación": 0.85,
        "texto": texto
    }

    if detallado:
        resultado["detalles"] = {
            "confianza": 0.95,
            "emociones": ["alegría", "optimismo"]
        }

    return resultado
```

### 2. Iniciar el Servidor

```bash
# Usando el CLI de Olive (recomendado)
olive dev

# O directamente con Python
python -m olive
```

### 3. Usar desde el Cliente

```python
from olive_client import OliveClient

# Conectar al servidor
async with OliveClient("http://localhost:8000") as client:
    # Listar herramientas disponibles
    herramientas = await client.get_tools()

    # Llamar una herramienta
    resultado = await client.call_tool("traducir", {
        "texto": "Hola mundo",
        "idioma_destino": "en"
    })
    print(resultado)  # {"original": "Hola mundo", "traducido": "[EN] Hola mundo", ...}
```

### 4. Integración con LangChain

```python
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent
from olive_client import OliveClient

# Obtener herramientas del servidor Olive
async with OliveClient("http://localhost:8000") as client:
    herramientas = await client.as_langchain_tools()

# Crear agente con las herramientas remotas
modelo = ChatAnthropic(model="claude-3-sonnet")
agente = create_react_agent(modelo, tools=herramientas)

# Usar de forma natural
respuesta = await agente.ainvoke({
    "messages": [{"role": "user", "content": "Traduce 'Buenos días' al inglés"}]
})
```

## 🔧 Uso Avanzado

### Inyección de Contexto (Annotated + Inject)

Olive soporta declarar parámetros que deben ser inyectados desde el contexto en tiempo de ejecución usando `typing.Annotated` y el marcador `Inject`.

- Los parámetros marcados con `Annotated[..., Inject("clave")]`:
  - No aparecen en el esquema público del tool (no los ve el LLM)
  - Se devuelven como metadatos `injections` en `GET /olive/tools`
  - Se auto-completan en el cliente con valores provenientes de `config.configurable`

**Nuevo en v1.2.0:** Inyección tanto desde `RunnableConfig` contextvar (cuando disponible) como desde campo `context` explícito en las llamadas HTTP, garantizando compatibilidad con `ToolNode` y otros mecanismos de invocación.

Servidor (definición del tool):

```python
from typing import Annotated
from olive import olive_tool, Inject

@olive_tool(description="Cambiar nombre del asistente")
def change_assistant_name(
    name: str,
    assistant_id: Annotated[str, Inject("assistant_id")],  # inyectado desde contexto
) -> dict:
    # ... implementar actualización remota ...
    return {"ok": True}
```

Respuesta de `GET /olive/tools` (extracto):

```json
[
  {
    "name": "change_assistant_name",
    "description": "Cambiar nombre del asistente",
    "input_schema": {
      "type": "object",
      "properties": { "name": { "type": "string" } },
      "required": ["name"]
    },
    "injections": [
      {
        "param": "assistant_id",
        "config_key": "assistant_id",
        "required": true
      }
    ]
  }
]
```

Cliente (inyectando desde `config.configurable`):

```python
from olive_client import OliveClient

async with OliveClient("http://localhost:8000") as client:
    tools = await client.as_langchain_tools_injecting(
        context_provider=lambda cfg: (
            cfg.configurable if hasattr(cfg, "configurable")
            else (getattr(cfg, "get", None) and cfg.get("configurable") or {})
        )
    )
    # 'assistant_id' se inyectará automáticamente; sólo pasas {"name": "Maia"}
```

La inyección funciona tanto si LangChain pasa `RunnableConfig` via contextvar (LCEL/ainvoke) como si no lo hace (`ToolNode`/coroutine). El cliente envía el contexto en el payload HTTP y el servidor lo fusiona con los argumentos del tool.

Nota:

- Valores de infraestructura como URLs o API keys del servidor pertenecen al entorno del servidor (variables de entorno) y no se inyectan desde el contexto del agente.

### Herramientas con Configuración Temporal Personalizada

```python
@olive_tool(
    description="Procesa documentos grandes con configuración personalizada",
    timeout_seconds=600,  # 10 minutos de timeout
    retry_policy={
        "max_attempts": 5,
        "initial_interval": 2,
        "backoff_coefficient": 2.0
    }
)
async def procesar_documento_grande(
    contenido: str,
    formato_salida: str = "markdown"
) -> dict:
    """Procesa documentos grandes con operaciones complejas."""
    # Esta función se ejecutará en Temporal con la configuración especificada
    resultado = await operacion_compleja(contenido)

    return {
        "contenido_procesado": resultado,
        "formato": formato_salida,
        "palabras": len(contenido.split()),
        "tiempo_procesamiento": "2.5s"
    }
```

### Manejo de Errores y Validación

```python
from pydantic import BaseModel, Field
from typing import Optional

class ParametrosTraduccion(BaseModel):
    texto: str = Field(..., min_length=1, max_length=5000)
    idioma_origen: Optional[str] = Field(default="auto", pattern="^[a-z]{2}$")
    idioma_destino: str = Field(..., pattern="^[a-z]{2}$")

@olive_tool
async def traducir_avanzado(params: ParametrosTraduccion) -> dict:
    """Traducción avanzada con validación de parámetros."""
    try:
        # La validación de Pydantic ocurre automáticamente
        resultado = await servicio_traduccion(
            params.texto,
            params.idioma_origen,
            params.idioma_destino
        )
        return {"exito": True, "traduccion": resultado}
    except Exception as e:
        # Temporal manejará reintentos automáticamente
        return {"exito": False, "error": str(e)}
```

## ⚙️ Configuración

### Archivo de Configuración (.olive.yaml)

```yaml
# Configuración de Temporal
temporal:
  address: localhost:7233
  namespace: default
  task_queue: olive-tools

  # Configuración para Temporal Cloud (producción)
  cloud_namespace: tu-namespace.a2dd6
  cloud_api_key: ${TEMPORAL_CLOUD_API_KEY}

# Configuración del servidor
server:
  host: 0.0.0.0
  port: 8000
  reload: true # Auto-reload en desarrollo

# Configuración por defecto de herramientas
tools:
  default_timeout: 300 # 5 minutos
  default_retry_attempts: 3
```

### Variables de Entorno

Todas las configuraciones pueden ser sobrescritas con variables de entorno:

```bash
# Temporal
export OLIVE_TEMPORAL_ADDRESS=localhost:7233
export OLIVE_TEMPORAL_NAMESPACE=default
export OLIVE_TEMPORAL_TASK_QUEUE=olive-tools

# Temporal Cloud
export OLIVE_TEMPORAL_CLOUD_NAMESPACE=tu-namespace.a2dd6
export OLIVE_TEMPORAL_CLOUD_API_KEY=tu-api-key

# Servidor
export OLIVE_SERVER_HOST=0.0.0.0
export OLIVE_SERVER_PORT=8000

# Herramientas
export OLIVE_TOOLS_DEFAULT_TIMEOUT=300
export OLIVE_TOOLS_DEFAULT_RETRY_ATTEMPTS=3
```

## 🔄 Integración con Temporal

Olive utiliza [Temporal](https://temporal.io) para proporcionar ejecución confiable y escalable de herramientas.

### Beneficios de Temporal

- **Tolerancia a Fallos**: Las tareas se reintentan automáticamente en caso de fallo
- **Durabilidad**: El estado se persiste, las tareas pueden continuar después de reinicios
- **Escalabilidad**: Distribuye la carga entre múltiples workers
- **Observabilidad**: UI integrada para monitorear ejecuciones

### Configuración de Workers

```python
# olive_workers.py
from olive import olive_tool
import asyncio

@olive_tool
async def tarea_pesada(datos: list[str]) -> dict:
    """Procesa grandes cantidades de datos."""
    resultados = []

    for item in datos:
        # Procesamiento paralelo
        resultado = await procesar_item(item)
        resultados.append(resultado)

    return {
        "procesados": len(resultados),
        "exitosos": sum(1 for r in resultados if r["exito"]),
        "resultados": resultados
    }

# Los workers se inician automáticamente con 'olive dev'
```

### Temporal Cloud para Producción

```yaml
# .olive.yaml para producción
temporal:
  cloud_namespace: produccion.a2dd6
  cloud_api_key: ${TEMPORAL_CLOUD_API_KEY}
  task_queue: olive-produccion
```

## 💻 Interfaz de Línea de Comandos (CLI)

Olive incluye una CLI rica con feedback visual:

```bash
# Iniciar en modo desarrollo (inicia Temporal, workers y servidor)
olive dev

# Opciones de desarrollo
olive dev --host 0.0.0.0 --port 8000 --reload

# Configuración personalizada
olive dev --config mi-config.yaml

# Ver herramientas registradas
olive tools list

# Información de una herramienta específica
olive tools info traducir

# Probar una herramienta
olive tools test traducir --data '{"texto": "Hola", "idioma_destino": "en"}'

# Verificar estado del sistema
olive status
```

## 📚 API Reference

### Endpoints del Servidor

| Método | Endpoint            | Descripción                              |
| ------ | ------------------- | ---------------------------------------- |
| GET    | `/olive/tools`      | Lista todas las herramientas disponibles |
| POST   | `/olive/tools/call` | Ejecuta una herramienta                  |
| GET    | `/olive/health`     | Estado de salud del servicio             |
| GET    | `/docs`             | Documentación interactiva de FastAPI     |

### Decorador @olive_tool

```python
@olive_tool(
    func: Callable = None,
    *,
    description: str = None,
    timeout_seconds: int = 300,
    retry_policy: dict = None
)
```

**Parámetros:**

- `func`: La función a decorar (automático cuando se usa sin paréntesis)
- `description`: Descripción personalizada (por defecto usa el docstring)
- `timeout_seconds`: Timeout de Temporal en segundos
- `retry_policy`: Política de reintentos personalizada

### Cliente OliveClient

```python
class OliveClient:
    def __init__(self, base_url: str, timeout: float = 30.0)

    async def get_tools(self) -> list[dict]
    async def call_tool(self, tool_name: str, arguments: dict) -> Any
    async def as_langchain_tools(self) -> list[StructuredTool]
```

## 📝 Ejemplos

### Ejemplo 1: API de Procesamiento de Texto

```python
# text_tools.py
from olive import olive_tool
import re

@olive_tool
def contar_palabras(texto: str) -> dict:
    """Cuenta palabras, caracteres y líneas en un texto."""
    return {
        "palabras": len(texto.split()),
        "caracteres": len(texto),
        "caracteres_sin_espacios": len(texto.replace(" ", "")),
        "lineas": len(texto.splitlines())
    }

@olive_tool
def extraer_emails(texto: str) -> list[str]:
    """Extrae direcciones de email del texto."""
    patron = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    return re.findall(patron, texto)

@olive_tool(description="Genera resumen del texto")
async def resumir_texto(
    texto: str,
    max_palabras: int = 50,
    estilo: str = "neutral"
) -> dict:
    """Genera un resumen del texto proporcionado."""
    # Simulación de resumen
    palabras = texto.split()[:max_palabras]
    resumen = " ".join(palabras) + "..."

    return {
        "resumen": resumen,
        "longitud_original": len(texto.split()),
        "longitud_resumen": len(palabras),
        "ratio_compresion": len(palabras) / len(texto.split()),
        "estilo": estilo
    }
```

### Ejemplo 2: Integración con Base de Datos

```python
# db_tools.py
from olive import olive_tool
from typing import Optional, List
import asyncpg

# Pool de conexiones global
db_pool: Optional[asyncpg.Pool] = None

@olive_tool(
    description="Busca usuarios en la base de datos",
    timeout_seconds=30
)
async def buscar_usuarios(
    nombre: Optional[str] = None,
    email: Optional[str] = None,
    activo: Optional[bool] = None,
    limite: int = 10
) -> List[dict]:
    """Busca usuarios con filtros opcionales."""
    query = "SELECT * FROM usuarios WHERE 1=1"
    params = []

    if nombre:
        params.append(nombre)
        query += f" AND nombre ILIKE ${len(params)}"

    if email:
        params.append(email)
        query += f" AND email ILIKE ${len(params)}"

    if activo is not None:
        params.append(activo)
        query += f" AND activo = ${len(params)}"

    query += f" LIMIT {limite}"

    async with db_pool.acquire() as conn:
        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]

@olive_tool(retry_policy={"max_attempts": 5})
async def crear_usuario(
    nombre: str,
    email: str,
    rol: str = "usuario"
) -> dict:
    """Crea un nuevo usuario en la base de datos."""
    async with db_pool.acquire() as conn:
        try:
            user_id = await conn.fetchval(
                """
                INSERT INTO usuarios (nombre, email, rol, activo)
                VALUES ($1, $2, $3, true)
                RETURNING id
                """,
                nombre, email, rol
            )
            return {
                "exito": True,
                "usuario_id": user_id,
                "mensaje": f"Usuario {nombre} creado exitosamente"
            }
        except asyncpg.UniqueViolationError:
            return {
                "exito": False,
                "error": f"El email {email} ya está registrado"
            }
```

### Ejemplo 3: Integración con APIs Externas

```python
# external_api_tools.py
from olive import olive_tool
import httpx
from typing import Optional

@olive_tool(
    description="Obtiene el clima actual de una ciudad",
    timeout_seconds=60
)
async def obtener_clima(
    ciudad: str,
    pais: Optional[str] = None,
    unidades: str = "metric"
) -> dict:
    """Obtiene información del clima usando OpenWeatherMap."""
    api_key = os.getenv("OPENWEATHER_API_KEY")

    params = {
        "q": f"{ciudad},{pais}" if pais else ciudad,
        "appid": api_key,
        "units": unidades,
        "lang": "es"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params=params
        )

        if response.status_code == 200:
            data = response.json()
            return {
                "ciudad": data["name"],
                "pais": data["sys"]["country"],
                "temperatura": data["main"]["temp"],
                "sensacion_termica": data["main"]["feels_like"],
                "descripcion": data["weather"][0]["description"],
                "humedad": data["main"]["humidity"],
                "viento_velocidad": data["wind"]["speed"]
            }
        else:
            return {
                "error": f"No se pudo obtener el clima: {response.status_code}"
            }

@olive_tool
async def convertir_moneda(
    cantidad: float,
    moneda_origen: str = "USD",
    moneda_destino: str = "EUR"
) -> dict:
    """Convierte entre diferentes monedas usando tasas actuales."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.exchangerate-api.com/v4/latest/{moneda_origen}"
        )

        if response.status_code == 200:
            data = response.json()
            tasa = data["rates"].get(moneda_destino)

            if tasa:
                resultado = cantidad * tasa
                return {
                    "cantidad_original": cantidad,
                    "moneda_origen": moneda_origen,
                    "cantidad_convertida": round(resultado, 2),
                    "moneda_destino": moneda_destino,
                    "tasa_cambio": tasa,
                    "fecha": data["date"]
                }
            else:
                return {"error": f"Moneda {moneda_destino} no encontrada"}

        return {"error": "No se pudo obtener las tasas de cambio"}
```

## 🛠️ Desarrollo

### Configurar Entorno de Desarrollo

```bash
# Clonar el repositorio
git clone git@github.com:YaVendio/olive.git
cd olive

# Crear entorno virtual con uv
uv venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate

# Instalar en modo desarrollo
uv pip install -e ".[dev]"

# Instalar pre-commit hooks
pre-commit install
```

### Ejecutar Tests

```bash
# Ejecutar todos los tests
pytest

# Con cobertura
pytest --cov=olive --cov-report=html

# Tests específicos
pytest tests/test_decorator.py -v

# Tests con salida detallada
pytest -vvs
```

### Estructura del Proyecto

```
olive/
├── olive/                  # Código principal
│   ├── __init__.py
│   ├── decorator.py       # Decorador @olive_tool
│   ├── registry.py        # Registro de herramientas
│   ├── router.py          # Endpoints FastAPI
│   ├── schemas.py         # Modelos Pydantic
│   ├── config.py          # Gestión de configuración
│   ├── cli.py             # Interfaz CLI
│   ├── server/            # Servidor FastAPI
│   └── temporal/          # Integración Temporal
├── olive_client/          # Biblioteca cliente
├── tests/                 # Tests unitarios
├── examples/              # Ejemplos de uso
├── docs/                  # Documentación
└── pyproject.toml         # Configuración del proyecto
```

## 🔍 Solución de Problemas

### Problemas Comunes

#### 1. Error: "Temporal server not running"

```bash
# Verificar si Temporal está ejecutándose
olive status

# Iniciar Temporal manualmente
temporal server start-dev

# O usar Docker
docker run -p 7233:7233 temporalio/temporalite:latest
```

#### 2. Error: "Tool not found"

```python
# Verificar que la herramienta esté registrada
olive tools list

# Asegurarse de que el archivo con @olive_tool se importe
# En tu main.py o app.py:
import tus_herramientas  # Importar antes de setup_olive()
```

#### 3. Timeout en herramientas

```python
# Aumentar timeout para operaciones largas
@olive_tool(timeout_seconds=1800)  # 30 minutos
async def operacion_larga():
    ...
```

#### 4. Problemas de conexión del cliente

```python
# Verificar la URL del servidor
client = OliveClient("http://localhost:8000")  # Sin trailing slash

# Aumentar timeout del cliente
client = OliveClient("http://localhost:8000", timeout=60.0)
```

### Logs y Debugging

```bash
# Habilitar logs detallados
export OLIVE_LOG_LEVEL=DEBUG
olive dev

# Ver logs de Temporal
temporal workflow list
temporal workflow show -w workflow-id

# Logs del servidor
uvicorn olive.server.app:app --log-level debug
```

## 🤝 Contribuir

¡Las contribuciones son bienvenidas! Por favor:

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/nueva-caracteristica`)
3. Commit tus cambios (`git commit -m 'Agrega nueva característica'`)
4. Push a la rama (`git push origin feature/nueva-caracteristica`)
5. Abre un Pull Request

### Guías de Estilo

- Código: Seguimos PEP 8 y usamos `ruff` para formateo
- Commits: Usa [Conventional Commits](https://www.conventionalcommits.org/)
- Documentación: Actualiza el README y docstrings cuando sea necesario

### Proceso de Release

1. Actualizar versión en `pyproject.toml`
2. Actualizar CHANGELOG.md
3. Crear tag: `git tag v1.1.3`
4. Push: `git push origin main --tags`

## 📄 Licencia

Este proyecto está licenciado bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para más detalles.

---

<p align="center">
  Hecho con ❤️ por <a href="https://github.com/YaVendio">YaVendio</a>
</p>

<p align="center">
  <a href="https://github.com/YaVendio/olive/issues">Reportar Bug</a> •
  <a href="https://github.com/YaVendio/olive/issues">Solicitar Feature</a> •
  <a href="https://github.com/YaVendio/olive/discussions">Discusiones</a>
</p>
