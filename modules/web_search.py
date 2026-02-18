"""
J.A.R.V.I.S. — Web Search Module
Búsqueda en internet: abre una pestaña real en el navegador con Google.
"""

import logging
import urllib.parse
import webbrowser
from typing import Optional

logger = logging.getLogger("jarvis.web_search")


class WebSearch:
    """Abre búsquedas en el navegador real (Google) como haría el usuario."""

    def __init__(self):
        logger.info("WebSearch inicializado.")

    def search(self, query: str, **_kwargs) -> str:
        """
        Abre una pestaña del navegador con la búsqueda en Google.

        Args:
            query: Consulta de búsqueda.

        Returns:
            Mensaje de confirmación.
        """
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
