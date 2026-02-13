"""
J.A.R.V.I.S. — Learning Engine
Motor de autoaprendizaje: cuando JARVIS no sabe hacer algo,
investiga, prueba y recuerda cómo hacerlo para la próxima vez.
"""

import json
import logging
import datetime
import subprocess
import sys
import tempfile
import re
import os
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DATA_DIR

logger = logging.getLogger("jarvis.learner")

SKILLS_FILE = DATA_DIR / "learned_skills.json"
RESEARCH_LOG = DATA_DIR / "research_log.json"


class LearningEngine:
    """
    Motor de autoaprendizaje para JARVIS.

    Flujo:
    1. Cuando JARVIS no sabe hacer algo → research_and_learn(petición)
    2. Busca en su base de habilidades aprendidas
    3. Si no encuentra → investiga (vía LLM + web) → genera código Python
    4. Prueba el código en sandbox → si funciona, lo guarda
    5. La próxima vez que se pida algo similar, usa la habilidad aprendida
    """

    def __init__(self):
        self._brain = None  # Se inyecta desde el orchestrator
        self._skills = self._load_skills()
        logger.info(f"LearningEngine inicializado. {len(self._skills)} habilidades aprendidas.")

    def set_brain(self, brain):
        """Inyecta referencia al cerebro (LLM) para investigar."""
        self._brain = brain

    # ─── Base de habilidades ──────────────────────────────────

    def _load_skills(self) -> list[dict]:
        """Carga las habilidades aprendidas desde disco."""
        try:
            if SKILLS_FILE.exists():
                with open(SKILLS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Error cargando skills: {e}")
        return []

    def _save_skills(self):
        """Guarda las habilidades aprendidas a disco."""
        try:
            with open(SKILLS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._skills, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error guardando skills: {e}")

    def _log_research(self, entry: dict):
        """Log de investigaciones para debugging."""
        try:
            log = []
            if RESEARCH_LOG.exists():
                with open(RESEARCH_LOG, "r", encoding="utf-8") as f:
                    log = json.load(f)
            log.append(entry)
            # Mantener solo las últimas 50 investigaciones
            log = log[-50:]
            with open(RESEARCH_LOG, "w", encoding="utf-8") as f:
                json.dump(log, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ─── Búsqueda de habilidades ──────────────────────────────

    def find_skill(self, user_request: str) -> Optional[dict]:
        """
        Busca una habilidad aprendida que coincida con la petición.
        Usa coincidencia por palabras clave.
        """
        if not self._skills:
            return None

        request_lower = user_request.lower()
        request_words = set(re.findall(r'\w+', request_lower))

        best_match = None
        best_score = 0

        for skill in self._skills:
            # Comparar con triggers guardados
            for trigger in skill.get("triggers", []):
                trigger_words = set(re.findall(r'\w+', trigger.lower()))
                if not trigger_words:
                    continue

                # Score = palabras en común / total de palabras del trigger
                common = request_words & trigger_words
                score = len(common) / len(trigger_words)

                # Bonus si contiene las palabras clave principales
                keywords = skill.get("keywords", [])
                for kw in keywords:
                    if kw.lower() in request_lower:
                        score += 0.3

                if score > best_score and score >= 0.5:
                    best_score = score
                    best_match = skill

        if best_match:
            logger.info(
                f"Skill encontrada: '{best_match['name']}' "
                f"(score={best_score:.2f}, usos={best_match.get('times_used', 0)})"
            )
        return best_match

    # ─── Ejecución de habilidades aprendidas ──────────────────

    def execute_skill(self, skill: dict, user_request: str = "") -> str:
        """
        Ejecuta una habilidad aprendida.

        Args:
            skill: Diccionario de la habilidad aprendida.
            user_request: Petición original del usuario (para contexto).

        Returns:
            Resultado de la ejecución.
        """
        skill_type = skill.get("type", "python_code")
        solution = skill.get("solution", "")

        if not solution:
            return "La habilidad no tiene solución guardada."

        try:
            if skill_type == "python_code":
                result = self._execute_python(solution)
            elif skill_type == "system_action":
                # Devolver la acción para que el orchestrator la ejecute
                result = f"[LEARNED_ACTION]{solution}"
            elif skill_type == "instructions":
                result = solution
            else:
                result = f"Tipo de habilidad desconocido: {skill_type}"

            # Actualizar estadísticas
            skill["times_used"] = skill.get("times_used", 0) + 1
            skill["last_used"] = datetime.datetime.now().isoformat()
            self._save_skills()

            return result

        except Exception as e:
            logger.error(f"Error ejecutando skill '{skill['name']}': {e}")
            return f"Error ejecutando habilidad aprendida: {e}"

    # ─── Investigación y aprendizaje ──────────────────────────

    def research_and_learn(self, user_request: str, failure_context: str = "") -> str:
        """
        Investiga cómo hacer algo que JARVIS no sabe.

        Flujo:
        1. Pregunta al LLM cómo hacerlo programáticamente
        2. Si el LLM genera código Python → lo prueba
        3. Si funciona → lo guarda como habilidad
        4. Devuelve el resultado

        Args:
            user_request: Lo que el usuario pidió.
            failure_context: Por qué falló el intento anterior.

        Returns:
            Resultado de la investigación o mensaje de progreso.
        """
        if not self._brain:
            return "No puedo investigar sin acceso al LLM, señor."

        logger.info(f"Investigando cómo hacer: '{user_request}'")

        research_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "request": user_request,
            "failure_context": failure_context,
            "steps": [],
            "result": None,
        }

        try:
            # Paso 1: Preguntar al LLM cómo hacerlo
            research_prompt = self._build_research_prompt(user_request, failure_context)
            logger.info("Consultando al LLM para investigar...")
            llm_response = self._brain.chat(
                research_prompt,
                context="Investigación técnica para aprender nueva habilidad"
            )

            research_entry["steps"].append({
                "step": "llm_research",
                "response_length": len(llm_response),
            })

            if not llm_response or llm_response.startswith(("Me temo", "Error")):
                research_entry["result"] = "llm_failed"
                self._log_research(research_entry)
                return (
                    "No he podido investigar cómo hacerlo, señor. "
                    "¿Podría darme más detalles sobre lo que necesita?"
                )

            # Paso 2: Extraer código Python de la respuesta
            code_blocks = self._extract_code(llm_response)

            if code_blocks:
                # Paso 3: Probar el código
                logger.info(f"Encontrados {len(code_blocks)} bloques de código. Probando...")
                for i, code in enumerate(code_blocks):
                    logger.info(f"Probando bloque {i+1}...")
                    test_result = self._test_code(code)

                    research_entry["steps"].append({
                        "step": f"test_code_{i+1}",
                        "success": test_result["success"],
                        "output": test_result["output"][:200],
                    })

                    if test_result["success"]:
                        # Paso 4: ¡Funciona! Guardar como habilidad
                        skill = self._create_skill(
                            user_request, code, llm_response, test_result
                        )
                        self._skills.append(skill)
                        self._save_skills()

                        research_entry["result"] = "success"
                        self._log_research(research_entry)

                        logger.info(f"¡Nueva habilidad aprendida: '{skill['name']}'!")

                        # Ejecutar y devolver resultado
                        return (
                            f"He aprendido algo nuevo, señor. {test_result['output']}"
                        )

                # Ningún código funcionó — intentar solo con la explicación
                research_entry["result"] = "code_failed"
                self._log_research(research_entry)

                # Guardar como instrucciones (sin código ejecutable)
                skill = self._create_skill(
                    user_request, "", llm_response, None,
                    skill_type="instructions"
                )
                self._skills.append(skill)
                self._save_skills()

                return (
                    f"He investigado sobre esto, señor. No he conseguido "
                    f"ejecutarlo automáticamente, pero esto es lo que he encontrado:\n\n"
                    f"{llm_response[:800]}"
                )

            else:
                # Sin código — guardar como instrucciones textuales
                research_entry["result"] = "no_code_found"
                self._log_research(research_entry)

                skill = self._create_skill(
                    user_request, "", llm_response, None,
                    skill_type="instructions"
                )
                self._skills.append(skill)
                self._save_skills()

                return llm_response

        except Exception as e:
            logger.error(f"Error en investigación: {e}")
            research_entry["result"] = f"error: {e}"
            self._log_research(research_entry)
            return f"Error durante la investigación: {e}"

    # ─── Búsqueda web para investigación ──────────────────────

    def web_research(self, query: str) -> str:
        """
        Busca información en la web para aprender.
        Usa DuckDuckGo Instant Answer API (gratis, sin API key).

        Args:
            query: Búsqueda a realizar.

        Returns:
            Texto con los resultados relevantes.
        """
        import requests

        try:
            # DuckDuckGo Instant Answer API (gratis)
            params = {
                "q": query,
                "format": "json",
                "no_redirect": 1,
                "no_html": 1,
                "skip_disambig": 1,
            }
            resp = requests.get(
                "https://api.duckduckgo.com/",
                params=params,
                timeout=10,
                headers={"User-Agent": "JARVIS/1.0"}
            )

            if resp.status_code == 200:
                data = resp.json()
                results = []

                # Abstract (respuesta directa)
                if data.get("AbstractText"):
                    results.append(f"Respuesta: {data['AbstractText']}")

                # Respuesta instantánea
                if data.get("Answer"):
                    results.append(f"Respuesta directa: {data['Answer']}")

                # Temas relacionados
                for topic in data.get("RelatedTopics", [])[:3]:
                    if isinstance(topic, dict) and topic.get("Text"):
                        results.append(f"- {topic['Text'][:200]}")

                if results:
                    return "\n".join(results)
                return "No se encontraron resultados directos."

        except Exception as e:
            logger.warning(f"Error en búsqueda web: {e}")

        return "No pude buscar información en la web."

    # ─── Investigación mejorada: web + LLM ────────────────────

    def deep_research(self, user_request: str) -> str:
        """
        Investigación profunda: busca en la web Y consulta al LLM.
        Combina ambas fuentes para una respuesta más completa.
        """
        if not self._brain:
            return "No puedo investigar sin acceso al LLM, señor."

        # 1. Buscar en la web
        web_query = f"how to {user_request} Python Windows programmatically"
        web_results = self.web_research(web_query)

        # 2. Usar web results como contexto adicional para el LLM
        enhanced_prompt = (
            f"El usuario quiere: '{user_request}'\n\n"
            f"He buscado en internet y he encontrado esto:\n{web_results}\n\n"
            f"Basándote en esta información y tu conocimiento, "
            f"escribe código Python completo y funcional para lograrlo en Windows. "
            f"El código debe ser autónomo (no necesitar input del usuario). "
            f"Envuelve el código en ```python ... ```."
        )

        response = self._brain.chat(
            enhanced_prompt,
            context="Investigación profunda: web + LLM para aprender nueva habilidad"
        )

        return response

    # ─── Auto-aprendizaje vía ChatGPT/Claude en navegador ─────

    def ask_chatgpt_for_help(self, problem: str, failure_context: str = "") -> str:
        """
        Abre ChatGPT en el navegador, pega el problema, espera la respuesta,
        y la lee vía Ctrl+A Ctrl+C. Luego intenta ejecutar lo que sugiera.

        Flujo:
        1. Construir un prompt claro describiendo el problema
        2. Abrir ChatGPT en Chrome (nueva pestaña)
        3. Pegar el prompt en el textarea
        4. Esperar a que ChatGPT responda (~15-25s)
        5. Ctrl+A Ctrl+C para leer la respuesta entera
        6. Extraer código/pasos de la respuesta
        7. Probar el código → guardar como habilidad si funciona

        Args:
            problem: Descripción del problema a resolver.
            failure_context: Qué salió mal antes.

        Returns:
            Resultado o lo que ChatGPT respondió.
        """
        import pyautogui
        import time as _time
        import webbrowser

        logger.info(f"Preguntando a ChatGPT: '{problem[:80]}...'")

        # 1. Construir prompt para ChatGPT
        prompt_text = self._build_chatgpt_prompt(problem, failure_context)

        # 2. Copiar el prompt al portapapeles ANTES de abrir el navegador
        try:
            import base64
            raw = prompt_text.encode('utf-16-le')
            b64 = base64.b64encode(raw).decode('ascii')
            subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-EncodedCommand", b64],
                capture_output=True, text=True, timeout=5,
                input=None
            )
            # El EncodedCommand ejecuta el texto como script, necesitamos Set-Clipboard
            clip_script = f'Set-Clipboard -Value ([System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String("{base64.b64encode(prompt_text.encode("utf-8")).decode("ascii")}")))'
            clip_raw = clip_script.encode('utf-16-le')
            clip_b64 = base64.b64encode(clip_raw).decode('ascii')
            subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-EncodedCommand", clip_b64],
                capture_output=True, text=True, timeout=5
            )
            logger.info("Prompt copiado al portapapeles")
        except Exception as e:
            logger.error(f"Error copiando prompt: {e}")
            return f"No pude copiar el prompt al portapapeles: {e}"

        # 3. Abrir ChatGPT en el navegador
        try:
            webbrowser.open("https://chatgpt.com/")
            logger.info("ChatGPT abierto en navegador")
            _time.sleep(5.0)  # Esperar a que cargue la página
        except Exception as e:
            logger.error(f"Error abriendo ChatGPT: {e}")
            return f"No pude abrir ChatGPT: {e}"

        # 4. Hacer clic en el textarea de ChatGPT y pegar
        screen_w, screen_h = pyautogui.size()
        # El textarea de ChatGPT suele estar en la parte inferior central
        textarea_x = screen_w // 2
        textarea_y = int(screen_h * 0.85)
        pyautogui.click(textarea_x, textarea_y)
        _time.sleep(1.0)

        # Pegar con Ctrl+V
        pyautogui.hotkey('ctrl', 'v')
        _time.sleep(1.0)

        # 5. Enviar el mensaje (Enter)
        pyautogui.press('enter')
        logger.info("Prompt enviado a ChatGPT. Esperando respuesta...")

        # 6. Esperar a que ChatGPT termine de responder
        #    ChatGPT tarda ~10-30s dependiendo de la longitud
        _time.sleep(25.0)

        # 7. Leer la respuesta completa de ChatGPT (Ctrl+A Ctrl+C)
        pyautogui.hotkey('ctrl', 'a')
        _time.sleep(0.5)
        pyautogui.hotkey('ctrl', 'c')
        _time.sleep(0.5)

        # Deseleccionar
        pyautogui.click(screen_w // 2, screen_h // 2)
        _time.sleep(0.3)

        # 8. Leer portapapeles con la respuesta de ChatGPT
        try:
            clip_result = subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-Command", "Get-Clipboard"],
                capture_output=True, text=True, timeout=5
            )
            chatgpt_response = clip_result.stdout.strip()
            logger.info(f"Respuesta de ChatGPT: {len(chatgpt_response)} chars")
        except Exception as e:
            logger.error(f"Error leyendo respuesta de ChatGPT: {e}")
            return f"ChatGPT respondió pero no pude leer la respuesta: {e}"

        if not chatgpt_response or len(chatgpt_response) < 50:
            return "No pude obtener una respuesta clara de ChatGPT, señor."

        # 9. Extraer código de la respuesta
        code_blocks = self._extract_code(chatgpt_response)

        if code_blocks:
            logger.info(f"ChatGPT sugirió {len(code_blocks)} bloques de código")
            for i, code in enumerate(code_blocks):
                test_result = self._test_code(code)
                if test_result["success"]:
                    # ¡Funciona! Guardar como habilidad
                    skill = self._create_skill(
                        problem, code, chatgpt_response, test_result
                    )
                    skill["source"] = "chatgpt"
                    self._skills.append(skill)
                    self._save_skills()
                    logger.info(f"Nueva habilidad aprendida de ChatGPT: '{skill['name']}'")
                    return (
                        f"He consultado a ChatGPT y he aprendido algo nuevo, señor. "
                        f"{test_result['output']}"
                    )

            # Código no funcionó — guardar como instrucciones
            skill = self._create_skill(
                problem, "", chatgpt_response, None, skill_type="instructions"
            )
            skill["source"] = "chatgpt"
            self._skills.append(skill)
            self._save_skills()

        # 10. Devolver la respuesta de ChatGPT (resumida por nuestro LLM)
        if self._brain:
            summary = self._brain.chat(
                f"Resume esta respuesta de ChatGPT en máximo 3 párrafos. "
                f"Si hay pasos a seguir, lístalos. Si hay código, menciónalo:\n\n"
                f"{chatgpt_response[:3000]}",
                context="Resumiendo respuesta de ChatGPT"
            )
            return f"He consultado a ChatGPT, señor. Esto es lo que sugiere:\n\n{summary}"

        return f"Respuesta de ChatGPT:\n{chatgpt_response[:1000]}"

    def _build_chatgpt_prompt(self, problem: str, failure_context: str = "") -> str:
        """Construye un prompt optimizado para ChatGPT."""
        prompt = (
            f"Soy un asistente de escritorio (JARVIS) en Windows y necesito ayuda.\n\n"
            f"PROBLEMA: {problem}\n"
        )
        if failure_context:
            prompt += f"\nCONTEXTO DEL ERROR: {failure_context}\n"
        prompt += (
            f"\nNecesito una solucion practica. "
            f"Si es posible, dame codigo Python funcional para Windows. "
            f"Si no es codigo, dame pasos claros que pueda seguir automaticamente."
        )
        return prompt

    # ─── Helpers internos ─────────────────────────────────────

    def _build_research_prompt(self, user_request: str, failure_context: str = "") -> str:
        """Construye el prompt de investigación para el LLM."""
        prompt = (
            "Necesito aprender a hacer algo nuevo en Python para Windows 10/11.\n"
            f"El usuario ha pedido: '{user_request}'\n"
        )
        if failure_context:
            prompt += f"Contexto de error anterior: {failure_context}\n"

        prompt += (
            "\nNecesito que me des:\n"
            "1. Una explicación breve de cómo hacerlo\n"
            "2. Código Python COMPLETO y funcional que lo haga\n"
            "3. El código debe ser autónomo (sin pedir input al usuario)\n"
            "4. Usa librerías estándar o comunes (subprocess, os, ctypes, pyautogui, requests)\n"
            "5. El código debe funcionar en Windows\n"
            "6. Envuelve todo el código en ```python ... ```\n"
            "7. Si necesitas importar algo, incluye el import\n"
            "8. Incluye manejo de errores básico\n\n"
            "IMPORTANTE: Devuelve SOLO código Python en un bloque ```python```. "
            "Si no es posible hacerlo con código, explica por qué y da instrucciones textuales."
        )
        return prompt

    def _extract_code(self, text: str) -> list[str]:
        """Extrae bloques de código Python de una respuesta del LLM."""
        blocks = []

        # Buscar ```python ... ```
        pattern = r'```(?:python)?\s*\n(.*?)```'
        matches = re.findall(pattern, text, re.DOTALL)
        for match in matches:
            code = match.strip()
            if code and len(code) > 10:
                blocks.append(code)

        # Si no hay bloques con ```, buscar líneas que parecen código Python
        if not blocks:
            lines = text.split('\n')
            code_lines = []
            in_code = False
            for line in lines:
                stripped = line.strip()
                if stripped.startswith(('import ', 'from ', 'def ', 'class ', 'if ', 'for ', 'while ')):
                    in_code = True
                if in_code:
                    code_lines.append(line)
                    if stripped == '' and len(code_lines) > 3:
                        # Fin del bloque
                        code = '\n'.join(code_lines).strip()
                        if len(code) > 20:
                            blocks.append(code)
                        code_lines = []
                        in_code = False

            if code_lines and len('\n'.join(code_lines).strip()) > 20:
                blocks.append('\n'.join(code_lines).strip())

        return blocks

    def _test_code(self, code: str, timeout: int = 15) -> dict:
        """
        Prueba código Python en un proceso separado (sandbox).

        Returns:
            {"success": bool, "output": str, "error": str}
        """
        # Seguridad básica: bloquear operaciones destructivas
        dangerous = [
            'shutil.rmtree', 'os.remove', 'os.rmdir', 'os.unlink',
            'format("C:', "format('C:", 'deltree', 'rd /s',
            'os.system("del', "os.system('del", 'os.system("rd',
            '__import__', 'eval(input', 'exec(input',
        ]
        code_lower = code.lower()
        for d in dangerous:
            if d.lower() in code_lower:
                return {
                    "success": False,
                    "output": "",
                    "error": f"Código bloqueado por seguridad: contiene '{d}'",
                }

        try:
            # Escribir a archivo temporal
            with tempfile.NamedTemporaryFile(
                mode='w', suffix='.py', delete=False,
                encoding='utf-8', dir=str(DATA_DIR)
            ) as f:
                f.write(code)
                temp_file = f.name

            # Ejecutar en proceso separado
            result = subprocess.run(
                [sys.executable, temp_file],
                capture_output=True, text=True,
                timeout=timeout,
                cwd=str(DATA_DIR),
            )

            output = result.stdout.strip()
            error = result.stderr.strip()

            # Considerar éxito si no hay errores fatales
            success = result.returncode == 0 and not any(
                err in error.lower() for err in
                ['traceback', 'error', 'exception', 'modulenotfounderror']
            )

            return {
                "success": success,
                "output": output or "(ejecutado sin salida)",
                "error": error,
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "error": f"El código tardó más de {timeout}s en ejecutarse.",
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e),
            }
        finally:
            try:
                Path(temp_file).unlink(missing_ok=True)
            except Exception:
                pass

    def _create_skill(self, user_request: str, code: str, 
                      llm_response: str, test_result: Optional[dict],
                      skill_type: str = "python_code") -> dict:
        """Crea un registro de habilidad aprendida."""
        # Generar keywords del request
        stop_words = {
            'el', 'la', 'los', 'las', 'un', 'una', 'de', 'del', 'en',
            'a', 'y', 'o', 'que', 'es', 'se', 'me', 'mi', 'lo', 'le',
            'por', 'con', 'para', 'como', 'al', 'no', 'si', 'su',
            'te', 'tu', 'más', 'ya', 'este', 'esta', 'ese', 'esa',
            'hay', 'hacer', 'haz', 'pon', 'quiero', 'puedes', 'puede',
        }
        words = re.findall(r'\w+', user_request.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]

        # Generar nombre descriptivo
        name = " ".join(keywords[:5]) if keywords else user_request[:50]

        return {
            "name": name,
            "triggers": [user_request],
            "keywords": keywords,
            "type": skill_type,
            "solution": code if code else llm_response[:2000],
            "description": llm_response[:300],
            "times_used": 0,
            "success_rate": 1.0 if (test_result and test_result["success"]) else 0.0,
            "created_at": datetime.datetime.now().isoformat(),
            "last_used": None,
        }

    # ─── Gestión de habilidades ───────────────────────────────

    def list_skills(self) -> str:
        """Lista todas las habilidades aprendidas."""
        if not self._skills:
            return "Aún no he aprendido habilidades nuevas, señor."

        lines = ["Habilidades aprendidas:"]
        for i, skill in enumerate(self._skills, 1):
            status = "✅" if skill.get("success_rate", 0) > 0 else "📝"
            uses = skill.get("times_used", 0)
            lines.append(
                f"  {status} {i}. {skill['name']} "
                f"(tipo: {skill['type']}, usos: {uses})"
            )
        return "\n".join(lines)

    def forget_skill(self, skill_name: str) -> str:
        """Elimina una habilidad aprendida."""
        for i, skill in enumerate(self._skills):
            if skill_name.lower() in skill.get("name", "").lower():
                removed = self._skills.pop(i)
                self._save_skills()
                return f"Habilidad '{removed['name']}' eliminada, señor."
        return f"No encontré una habilidad llamada '{skill_name}'."

    def get_skill_count(self) -> int:
        """Devuelve el número de habilidades aprendidas."""
        return len(self._skills)
