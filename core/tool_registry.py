"""
JARVIS Tool Registry — Sistema central de registro de herramientas
Inspirado en OpenClaw: cada módulo registra sus capacidades y el LLM
puede descubrir dinámicamente qué herramientas tiene disponibles.
"""

import inspect
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger("jarvis.tool_registry")


class ToolCategory(Enum):
    """Categorías de herramientas disponibles."""
    SYSTEM = "system"           # Control del sistema (apps, ventanas, hardware)
    FILE = "file"               # Gestión de archivos
    WEB = "web"                 # Búsqueda web y navegación
    MEDIA = "media"             # Control multimedia
    COMMUNICATION = "communication"  # Email, mensajes
    AUTOMATION = "automation"   # Rutinas y tareas programadas
    CALENDAR = "calendar"       # Calendario y eventos
    DOCUMENT = "document"       # Procesamiento de documentos
    CODE = "code"               # Ejecución de código
    VISION = "vision"           # Análisis visual / OCR
    MEMORY = "memory"           # Memoria y aprendizaje
    NOTIFICATION = "notification"  # Notificaciones
    PLUGIN = "plugin"           # Plugins externos
    BROWSER = "browser"         # Control del navegador
    LEARNING = "learning"       # Auto-aprendizaje


@dataclass
class ToolParameter:
    """Descripción de un parámetro de herramienta."""
    name: str
    description: str
    type: str = "str"           # str, int, float, bool, list, dict
    required: bool = True
    default: Any = None
    enum_values: Optional[List[str]] = None  # Valores posibles


@dataclass
class Tool:
    """Definición completa de una herramienta."""
    name: str                   # Nombre único (módulo.función)
    description: str            # Descripción para el LLM
    category: ToolCategory
    handler: Callable           # Función a ejecutar
    parameters: List[ToolParameter] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)  # Ejemplos de uso en lenguaje natural
    keywords: List[str] = field(default_factory=list)   # Palabras clave para matching
    requires_screen: bool = False   # ¿Necesita interacción visual?
    requires_internet: bool = False  # ¿Necesita conexión?
    risk_level: str = "low"     # low, medium, high (para confirmación)
    enabled: bool = True
    usage_count: int = 0
    success_count: int = 0
    last_error: Optional[str] = None

    def to_llm_description(self) -> str:
        """Genera descripción formateada para el LLM."""
        params_desc = ""
        if self.parameters:
            params_list = []
            for p in self.parameters:
                req = "requerido" if p.required else f"opcional, default={p.default}"
                enum = f", opciones: {p.enum_values}" if p.enum_values else ""
                params_list.append(f"    - {p.name} ({p.type}, {req}): {p.description}{enum}")
            params_desc = "\n" + "\n".join(params_list)

        examples_desc = ""
        if self.examples:
            examples_desc = "\n  Ejemplos: " + " | ".join(self.examples)

        return f"- **{self.name}**: {self.description}{params_desc}{examples_desc}"

    def to_compact_description(self) -> str:
        """Versión compacta para contextos con límite de tokens."""
        params_str = ", ".join(
            f"{p.name}:{'req' if p.required else 'opt'}"
            for p in self.parameters
        )
        return f"{self.name}({params_str}) — {self.description}"


class ToolRegistry:
    """
    Registro central de todas las herramientas de JARVIS.
    
    Permite al LLM descubrir qué puede hacer JARVIS y elegir
    la herramienta correcta para cada tarea.
    """

    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._categories: Dict[ToolCategory, List[str]] = {cat: [] for cat in ToolCategory}
        self._keyword_index: Dict[str, List[str]] = {}  # keyword → [tool_names]
        logger.info("ToolRegistry inicializado")

    def register(self, tool: Tool) -> None:
        """Registra una herramienta en el registro."""
        if tool.name in self._tools:
            logger.warning(f"Herramienta '{tool.name}' ya registrada, actualizando")
        
        self._tools[tool.name] = tool
        
        if tool.name not in self._categories[tool.category]:
            self._categories[tool.category].append(tool.name)
        
        # Indexar por keywords
        for kw in tool.keywords:
            kw_lower = kw.lower()
            if kw_lower not in self._keyword_index:
                self._keyword_index[kw_lower] = []
            if tool.name not in self._keyword_index[kw_lower]:
                self._keyword_index[kw_lower].append(tool.name)
        
        logger.debug(f"Herramienta registrada: {tool.name} [{tool.category.value}]")

    def register_function(
        self,
        func: Callable,
        name: str,
        description: str,
        category: ToolCategory,
        parameters: Optional[List[ToolParameter]] = None,
        examples: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None,
        requires_screen: bool = False,
        requires_internet: bool = False,
        risk_level: str = "low"
    ) -> None:
        """Atajo para registrar una función como herramienta."""
        tool = Tool(
            name=name,
            description=description,
            category=category,
            handler=func,
            parameters=parameters or [],
            examples=examples or [],
            keywords=keywords or [],
            requires_screen=requires_screen,
            requires_internet=requires_internet,
            risk_level=risk_level
        )
        self.register(tool)

    def get(self, name: str) -> Optional[Tool]:
        """Obtiene una herramienta por nombre."""
        return self._tools.get(name)

    def execute(self, name: str, **kwargs) -> Tuple[bool, Any]:
        """
        Ejecuta una herramienta por nombre.
        Retorna (success, result).
        """
        tool = self._tools.get(name)
        if not tool:
            return False, f"Herramienta '{name}' no encontrada"
        
        if not tool.enabled:
            return False, f"Herramienta '{name}' está deshabilitada"
        
        tool.usage_count += 1
        
        try:
            # Filtrar solo los parámetros que la función acepta
            sig = inspect.signature(tool.handler)
            valid_params = {}
            for param_name, param in sig.parameters.items():
                if param_name in kwargs:
                    valid_params[param_name] = kwargs[param_name]
                elif param_name == 'self':
                    continue
            
            result = tool.handler(**valid_params)
            tool.success_count += 1
            tool.last_error = None
            return True, result
        except Exception as e:
            tool.last_error = str(e)
            logger.error(f"Error ejecutando {name}: {e}")
            return False, str(e)

    def search(self, query: str, max_results: int = 10) -> List[Tool]:
        """
        Busca herramientas relevantes por query en lenguaje natural.
        Usa keywords, nombre y descripción.
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        scored: List[Tuple[float, Tool]] = []
        
        for tool in self._tools.values():
            if not tool.enabled:
                continue
            
            score = 0.0
            
            # Match por keywords (peso alto)
            for kw in tool.keywords:
                if kw.lower() in query_lower:
                    score += 3.0
                for word in query_words:
                    if word in kw.lower() or kw.lower() in word:
                        score += 1.5
            
            # Match por nombre
            name_lower = tool.name.lower()
            for word in query_words:
                if word in name_lower:
                    score += 2.0
            
            # Match por descripción
            desc_lower = tool.description.lower()
            for word in query_words:
                if len(word) > 2 and word in desc_lower:
                    score += 1.0
            
            # Match por ejemplos
            for example in tool.examples:
                for word in query_words:
                    if len(word) > 2 and word in example.lower():
                        score += 0.5
            
            # Bonus por éxito histórico
            if tool.usage_count > 0:
                success_rate = tool.success_count / tool.usage_count
                score *= (1 + success_rate * 0.2)
            
            if score > 0:
                scored.append((score, tool))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        return [tool for _, tool in scored[:max_results]]

    def search_by_category(self, category: ToolCategory) -> List[Tool]:
        """Obtiene todas las herramientas de una categoría."""
        names = self._categories.get(category, [])
        return [self._tools[n] for n in names if n in self._tools and self._tools[n].enabled]

    def get_all_tools_description(self, compact: bool = False) -> str:
        """
        Genera una descripción completa de todas las herramientas
        para incluir en el prompt del LLM.
        """
        sections = []
        for category in ToolCategory:
            tools = self.search_by_category(category)
            if not tools:
                continue
            
            category_names = {
                ToolCategory.SYSTEM: "🖥️ Control del Sistema",
                ToolCategory.FILE: "📁 Gestión de Archivos",
                ToolCategory.WEB: "🌐 Web y Búsqueda",
                ToolCategory.MEDIA: "🎵 Control Multimedia",
                ToolCategory.COMMUNICATION: "📧 Comunicación",
                ToolCategory.AUTOMATION: "⚙️ Automatización",
                ToolCategory.CALENDAR: "📅 Calendario",
                ToolCategory.DOCUMENT: "📄 Documentos",
                ToolCategory.CODE: "💻 Código",
                ToolCategory.VISION: "👁️ Visión",
                ToolCategory.MEMORY: "🧠 Memoria",
                ToolCategory.NOTIFICATION: "🔔 Notificaciones",
                ToolCategory.PLUGIN: "🔌 Plugins",
                ToolCategory.BROWSER: "🌍 Navegador",
                ToolCategory.LEARNING: "📚 Aprendizaje",
            }
            
            section_name = category_names.get(category, category.value)
            if compact:
                tools_desc = "\n".join(t.to_compact_description() for t in tools)
            else:
                tools_desc = "\n".join(t.to_llm_description() for t in tools)
            
            sections.append(f"\n### {section_name}\n{tools_desc}")
        
        return "\n".join(sections)

    def get_tools_for_llm(self, query: Optional[str] = None, max_tools: int = 20) -> str:
        """
        Genera la lista de herramientas relevantes para una query,
        optimizada para el contexto del LLM.
        """
        if query:
            tools = self.search(query, max_results=max_tools)
            if tools:
                desc = "\n".join(t.to_compact_description() for t in tools)
                return f"## Herramientas relevantes para tu tarea:\n{desc}"
        
        # Si no hay query o no hay resultados, dar todas en formato compacto
        return self.get_all_tools_description(compact=True)

    def get_tool_names(self) -> List[str]:
        """Retorna todos los nombres de herramientas registradas."""
        return list(self._tools.keys())

    def count(self) -> int:
        """Número total de herramientas registradas."""
        return len(self._tools)

    def get_stats(self) -> Dict[str, Any]:
        """Estadísticas del registro."""
        total = len(self._tools)
        enabled = sum(1 for t in self._tools.values() if t.enabled)
        by_category = {
            cat.value: len(tools)
            for cat, tools in self._categories.items()
            if tools
        }
        most_used = sorted(
            self._tools.values(),
            key=lambda t: t.usage_count,
            reverse=True
        )[:5]
        
        return {
            "total_tools": total,
            "enabled": enabled,
            "disabled": total - enabled,
            "by_category": by_category,
            "most_used": [
                {"name": t.name, "uses": t.usage_count, "success_rate": 
                 f"{t.success_count/t.usage_count*100:.0f}%" if t.usage_count > 0 else "N/A"}
                for t in most_used if t.usage_count > 0
            ]
        }

    def disable(self, name: str) -> bool:
        """Deshabilita una herramienta."""
        if name in self._tools:
            self._tools[name].enabled = False
            return True
        return False

    def enable(self, name: str) -> bool:
        """Habilita una herramienta."""
        if name in self._tools:
            self._tools[name].enabled = True
            return True
        return False


# Singleton global
_registry: Optional[ToolRegistry] = None

def get_registry() -> ToolRegistry:
    """Obtiene la instancia global del ToolRegistry."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


def register_tool(
    name: str,
    description: str,
    category: ToolCategory,
    parameters: Optional[List[ToolParameter]] = None,
    examples: Optional[List[str]] = None,
    keywords: Optional[List[str]] = None,
    requires_screen: bool = False,
    requires_internet: bool = False,
    risk_level: str = "low"
):
    """
    Decorador para registrar una función como herramienta.
    
    Uso:
        @register_tool(
            name="system.open_app",
            description="Abre una aplicación",
            category=ToolCategory.SYSTEM,
            keywords=["abrir", "ejecutar", "lanzar", "app"],
            examples=["abre Chrome", "ejecuta Notepad"]
        )
        def open_application(app_name: str) -> str:
            ...
    """
    def decorator(func: Callable) -> Callable:
        registry = get_registry()
        tool = Tool(
            name=name,
            description=description,
            category=category,
            handler=func,
            parameters=parameters or [],
            examples=examples or [],
            keywords=keywords or [],
            requires_screen=requires_screen,
            requires_internet=requires_internet,
            risk_level=risk_level
        )
        registry.register(tool)
        return func
    return decorator


def auto_register_module(module_instance: Any, module_name: str, category: ToolCategory) -> int:
    """
    Auto-registra todos los métodos públicos de un módulo como herramientas.
    Usa docstrings como descripción. Retorna el número de herramientas registradas.
    """
    registry = get_registry()
    count = 0
    
    for attr_name in dir(module_instance):
        if attr_name.startswith('_'):
            continue
        
        attr = getattr(module_instance, attr_name, None)
        if not callable(attr):
            continue
        
        # Obtener info de la función
        doc = attr.__doc__ or f"Ejecuta {attr_name}"
        doc_first_line = doc.strip().split('\n')[0]
        
        # Inferir parámetros del signature
        try:
            sig = inspect.signature(attr)
            params = []
            for pname, param in sig.parameters.items():
                if pname == 'self':
                    continue
                p_type = "str"
                if param.annotation != inspect.Parameter.empty:
                    p_type = param.annotation.__name__ if hasattr(param.annotation, '__name__') else str(param.annotation)
                
                p_required = param.default == inspect.Parameter.empty
                p_default = None if p_required else param.default
                
                params.append(ToolParameter(
                    name=pname,
                    description=f"Parámetro {pname}",
                    type=p_type,
                    required=p_required,
                    default=p_default
                ))
        except (ValueError, TypeError):
            params = []
        
        tool_name = f"{module_name}.{attr_name}"
        
        # Extraer keywords del nombre de la función
        keywords = attr_name.replace('_', ' ').split()
        
        tool = Tool(
            name=tool_name,
            description=doc_first_line,
            category=category,
            handler=attr,
            parameters=params,
            keywords=keywords
        )
        
        registry.register(tool)
        count += 1
    
    logger.info(f"Auto-registradas {count} herramientas de {module_name}")
    return count
