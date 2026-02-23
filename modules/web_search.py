"""
J.A.R.V.I.S. — Web Search Module (Enhanced)
Búsqueda en internet con capacidades programáticas reales.
Inspirado en OpenClaw: extrae resultados, contenido de páginas web,
y puede investigar temas de forma autónoma.
"""

import logging
import re
import urllib.parse
import webbrowser
import time
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

logger = logging.getLogger("jarvis.web_search")


@dataclass
class SearchResult:
    """Resultado individual de búsqueda."""
    title: str
    url: str
    snippet: str
    source: str = ""
    
    def __str__(self) -> str:
        return f"• {self.title}\n  {self.url}\n  {self.snippet}"


@dataclass
class WebPage:
    """Contenido extraído de una página web."""
    url: str
    title: str
    content: str
    success: bool
    error: Optional[str] = None
    
    def summary(self, max_chars: int = 2000) -> str:
        """Resumen del contenido truncado."""
        if not self.success:
            return f"Error accediendo a {self.url}: {self.error}"
        text = self.content[:max_chars]
        if len(self.content) > max_chars:
            text += "... [truncado]"
        return f"## {self.title}\n{self.url}\n\n{text}"


class WebSearch:
    """
    Motor de búsqueda web con capacidades programáticas.
    
    Modos:
    1. search() — Búsqueda programática con DuckDuckGo (retorna resultados)
    2. search_browser() — Abre búsqueda en navegador (visual)
    3. fetch_page() — Extrae contenido de una URL
    4. research() — Investigación profunda multi-paso
    """

    def __init__(self):
        self._ddg = None
        self._httpx = None
        self._bs4 = None
        self._init_libraries()
        logger.info("WebSearch (Enhanced) inicializado.")

    def _init_libraries(self):
        """Inicializa librerías de búsqueda."""
        try:
            from duckduckgo_search import DDGS
            self._ddg = DDGS
            logger.info("DuckDuckGo Search disponible")
        except ImportError:
            logger.warning("duckduckgo-search no disponible, instalando...")
            try:
                import subprocess
                subprocess.run(["pip", "install", "duckduckgo-search"], 
                             capture_output=True, timeout=60)
                from duckduckgo_search import DDGS
                self._ddg = DDGS
            except Exception as e:
                logger.error(f"No se pudo instalar duckduckgo-search: {e}")
        
        try:
            import httpx
            self._httpx = httpx
        except ImportError:
            try:
                import requests
                self._httpx = None  # Usaremos requests como fallback
            except ImportError:
                pass
        
        try:
            from bs4 import BeautifulSoup
            self._bs4 = BeautifulSoup
        except ImportError:
            logger.warning("beautifulsoup4 no disponible para extracción de contenido")

    # ===========================
    # BÚSQUEDA PROGRAMÁTICA
    # ===========================

    def search(self, query: str, max_results: int = 8, **_kwargs) -> str:
        """
        Búsqueda programática que retorna resultados reales.
        Intenta DuckDuckGo primero, abre navegador como fallback.
        
        Args:
            query: Consulta de búsqueda
            max_results: Número máximo de resultados (default: 8)
        
        Returns:
            Resultados formateados como texto
        """
        results = self.search_programmatic(query, max_results)
        
        if results:
            formatted = f"🔍 Resultados para '{query}':\n\n"
            for i, r in enumerate(results, 1):
                formatted += f"{i}. **{r.title}**\n"
                formatted += f"   URL: {r.url}\n"
                formatted += f"   {r.snippet}\n\n"
            return formatted
        
        # Fallback: abrir en navegador
        return self.search_browser(query)

    def search_programmatic(self, query: str, max_results: int = 8) -> List[SearchResult]:
        """
        Búsqueda que retorna objetos SearchResult.
        Usa DuckDuckGo para obtener resultados reales.
        """
        results = []
        
        # Intentar DuckDuckGo
        if self._ddg:
            try:
                with self._ddg() as ddg:
                    ddg_results = ddg.text(query, max_results=max_results)
                    for r in ddg_results:
                        results.append(SearchResult(
                            title=r.get("title", ""),
                            url=r.get("href", r.get("link", "")),
                            snippet=r.get("body", r.get("snippet", "")),
                            source="duckduckgo"
                        ))
                logger.info(f"DuckDuckGo: {len(results)} resultados para '{query}'")
            except Exception as e:
                logger.error(f"Error en DuckDuckGo search: {e}")
        
        # Fallback: DuckDuckGo Instant Answer API
        if not results:
            try:
                results = self._search_ddg_instant(query)
            except Exception as e:
                logger.error(f"Error en DDG Instant API: {e}")
        
        return results

    def _search_ddg_instant(self, query: str) -> List[SearchResult]:
        """Búsqueda via DuckDuckGo Instant Answer API (sin dependencias)."""
        results = []
        try:
            import requests
            encoded = urllib.parse.quote_plus(query)
            url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1"
            resp = requests.get(url, timeout=10, headers={
                "User-Agent": "JARVIS/2.0 Personal Assistant"
            })
            data = resp.json()
            
            # Abstract
            if data.get("Abstract"):
                results.append(SearchResult(
                    title=data.get("Heading", query),
                    url=data.get("AbstractURL", ""),
                    snippet=data["Abstract"][:300],
                    source="ddg_instant"
                ))
            
            # Related topics
            for topic in data.get("RelatedTopics", [])[:5]:
                if isinstance(topic, dict) and "Text" in topic:
                    results.append(SearchResult(
                        title=topic.get("Text", "")[:80],
                        url=topic.get("FirstURL", ""),
                        snippet=topic.get("Text", "")[:200],
                        source="ddg_instant"
                    ))
        except Exception as e:
            logger.error(f"DDG Instant API error: {e}")
        
        return results

    def search_how_to(self, task: str, max_results: int = 5) -> List[SearchResult]:
        """
        Busca cómo realizar una tarea específica.
        Optimizada para encontrar tutoriales y guías.
        """
        queries = [
            f"how to {task} Windows",
            f"cómo {task} Windows tutorial",
            f"{task} step by step guide"
        ]
        
        all_results = []
        seen_urls = set()
        
        for q in queries:
            results = self.search_programmatic(q, max_results=max_results)
            for r in results:
                if r.url not in seen_urls:
                    seen_urls.add(r.url)
                    all_results.append(r)
            if len(all_results) >= max_results:
                break
        
        return all_results[:max_results]

    # ===========================
    # EXTRACCIÓN DE CONTENIDO WEB
    # ===========================

    def fetch_page(self, url: str, max_chars: int = 5000) -> WebPage:
        """
        Extrae el contenido de texto de una página web.
        
        Args:
            url: URL a extraer
            max_chars: Máximo de caracteres a retornar
            
        Returns:
            WebPage con el contenido extraído
        """
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        
        try:
            import requests
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            resp = requests.get(url, timeout=15, headers=headers)
            resp.raise_for_status()
            
            # Extraer texto con BeautifulSoup si disponible
            if self._bs4:
                soup = self._bs4(resp.text, "html.parser")
                
                # Eliminar scripts, styles, nav, footer
                for tag in soup(["script", "style", "nav", "footer", "header", 
                                "aside", "noscript", "iframe"]):
                    tag.decompose()
                
                title = soup.title.string if soup.title else ""
                
                # Extraer texto principal
                main = soup.find("main") or soup.find("article") or soup.find("body")
                if main:
                    text = main.get_text(separator="\n", strip=True)
                else:
                    text = soup.get_text(separator="\n", strip=True)
                
                # Limpiar líneas vacías múltiples
                text = re.sub(r'\n{3,}', '\n\n', text)
                text = text[:max_chars]
                
                return WebPage(url=url, title=title, content=text, success=True)
            else:
                # Sin BS4, extraer texto básico
                text = re.sub(r'<[^>]+>', ' ', resp.text)
                text = re.sub(r'\s+', ' ', text)[:max_chars]
                return WebPage(url=url, title="", content=text, success=True)
                
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return WebPage(url=url, title="", content="", success=False, error=str(e))

    def extract_instructions(self, url: str) -> str:
        """
        Extrae instrucciones paso a paso de una página web.
        Útil para aprender a hacer cosas nuevas.
        """
        page = self.fetch_page(url, max_chars=8000)
        if not page.success:
            return f"No pude acceder a {url}: {page.error}"
        
        # Buscar secciones con pasos numerados
        lines = page.content.split('\n')
        instructions = []
        capture = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detectar inicio de instrucciones
            if re.match(r'^(paso|step|[0-9]+[\.\)])', line, re.IGNORECASE):
                capture = True
            
            if capture:
                instructions.append(line)
                if len(instructions) > 50:
                    break
        
        if instructions:
            return "\n".join(instructions)
        
        # Si no encontramos pasos, retornar el contenido principal
        return page.content[:3000]

    # ===========================
    # INVESTIGACIÓN PROFUNDA
    # ===========================

    def research(self, topic: str, depth: int = 2) -> Dict[str, Any]:
        """
        Investigación profunda sobre un tema.
        Busca, extrae contenido de las mejores fuentes, y compila.
        
        Args:
            topic: Tema a investigar
            depth: Profundidad (1=búsqueda simple, 2=buscar+extraer, 3=multi-consulta)
            
        Returns:
            Dict con resultados estructurados
        """
        research_data = {
            "topic": topic,
            "search_results": [],
            "extracted_content": [],
            "summary_sources": [],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Paso 1: Búsqueda
        results = self.search_programmatic(topic, max_results=8)
        research_data["search_results"] = [
            {"title": r.title, "url": r.url, "snippet": r.snippet}
            for r in results
        ]
        
        if depth >= 2 and results:
            # Paso 2: Extraer contenido de las top 3 fuentes
            for result in results[:3]:
                if result.url:
                    page = self.fetch_page(result.url, max_chars=3000)
                    if page.success:
                        research_data["extracted_content"].append({
                            "url": page.url,
                            "title": page.title or result.title,
                            "content": page.content
                        })
                        research_data["summary_sources"].append(page.url)
        
        if depth >= 3:
            # Paso 3: Búsquedas adicionales con queries refinadas
            extra_queries = [
                f"{topic} tutorial",
                f"{topic} best practices",
                f"{topic} examples"
            ]
            for eq in extra_queries:
                extra_results = self.search_programmatic(eq, max_results=3)
                for r in extra_results:
                    if r.url not in {sr["url"] for sr in research_data["search_results"]}:
                        research_data["search_results"].append({
                            "title": r.title, "url": r.url, "snippet": r.snippet
                        })
        
        return research_data

    def research_formatted(self, topic: str, depth: int = 2) -> str:
        """Investigación con formato legible para el LLM/usuario."""
        data = self.research(topic, depth)
        
        output = f"📚 Investigación: {topic}\n"
        output += "=" * 50 + "\n\n"
        
        output += "## Resultados de búsqueda:\n"
        for i, r in enumerate(data["search_results"][:8], 1):
            output += f"{i}. {r['title']}\n   {r['snippet']}\n   🔗 {r['url']}\n\n"
        
        if data["extracted_content"]:
            output += "\n## Contenido extraído:\n"
            for content in data["extracted_content"]:
                output += f"\n### {content['title']}\n"
                output += f"Fuente: {content['url']}\n"
                output += f"{content['content'][:1500]}\n"
                output += "---\n"
        
        return output

    # ===========================
    # BÚSQUEDA EN NAVEGADOR (LEGACY)
    # ===========================

    def search_browser(self, query: str, **_kwargs) -> str:
        """Abre una pestaña del navegador con la búsqueda en Google."""
        try:
            encoded = urllib.parse.quote_plus(query)
            url = f"https://www.google.com/search?q={encoded}"
            webbrowser.open(url)
            logger.info(f"Búsqueda abierta en navegador: {query}")
            return f"He buscado '{query}' en Google."
        except Exception as e:
            logger.error(f"Error al abrir búsqueda: {e}")
            return f"Error al buscar '{query}': {e}"

    def search_news(self, query: str, **_kwargs) -> str:
        """Busca noticias abriendo Google News en el navegador."""
        try:
            encoded = urllib.parse.quote_plus(query)
            url = f"https://news.google.com/search?q={encoded}"
            webbrowser.open(url)
            logger.info(f"Noticias abiertas en navegador: {query}")
            return f"He buscado noticias sobre '{query}' en Google News."
        except Exception as e:
            logger.error(f"Error al abrir noticias: {e}")
            return f"Error al buscar noticias: {e}"

    def open_url(self, url: str) -> str:
        """Abre una URL en el navegador predeterminado."""
        try:
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            webbrowser.open(url)
            return f"URL abierta en el navegador: {url}"
        except Exception as e:
            return f"Error al abrir URL: {e}"

    def play_youtube(self, query: str, **_kwargs) -> str:
        """Busca y reproduce un vídeo en YouTube."""
        try:
            encoded = urllib.parse.quote_plus(query)
            url = f"https://www.youtube.com/results?search_query={encoded}"
            webbrowser.open(url)
            logger.info(f"YouTube abierto con búsqueda: {query}")
            return f"He buscado '{query}' en YouTube, señor."
        except Exception as e:
            logger.error(f"Error al abrir YouTube: {e}")
            return f"Error al buscar en YouTube: {e}"
