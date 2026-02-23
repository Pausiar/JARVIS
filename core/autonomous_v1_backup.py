"""
J.A.R.V.I.S. — Autonomous Agent
Motor de ejecución autónoma: navega, lee la pantalla, decide qué hacer,
y sigue hasta completar la tarea o pedir ayuda al usuario.

Flujo:
1. Recibe un objetivo del usuario (ej: "mira las tareas pendientes en Aules")
2. Planifica los pasos iniciales (basándose en procedimientos guardados o LLM)
3. Ejecuta cada paso: acción → OCR → analizar → decidir siguiente
4. Si encuentra la info, reporta al usuario
5. Si se queda atascado, pregunta al usuario cómo continuar
6. Guarda el procedimiento exitoso para la próxima vez
"""

import json
import logging
import re
import time
from pathlib import Path
from typing import Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DATA_DIR

logger = logging.getLogger("jarvis.autonomous")

PROCEDURES_FILE = DATA_DIR / "procedures.json"
MAX_STEPS = 12  # Máximo de pasos antes de rendirse


class AutonomousAgent:
    """
    Agente autónomo que ejecuta tareas multi-paso leyendo la pantalla.
    
    Usa un ciclo de: Act → Observe → Think → Repeat.
    """

    def __init__(self, brain, system_control, parser):
        self.brain = brain
        self.sc = system_control
        self.parser = parser
        self._procedures = self._load_procedures()
        self._pending_question = None  # Pregunta para el usuario si se atasca
        logger.info(f"AutonomousAgent inicializado. {len(self._procedures)} procedimientos guardados.")

    # ─── Procedimientos guardados ─────────────────────────────

    def _load_procedures(self) -> list[dict]:
        """Carga procedimientos aprendidos."""
        try:
            if PROCEDURES_FILE.exists():
                with open(PROCEDURES_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Error cargando procedimientos: {e}")
        return []

    def _save_procedures(self):
        """Guarda los procedimientos a disco."""
        try:
            with open(PROCEDURES_FILE, "w", encoding="utf-8") as f:
                json.dump(self._procedures, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error guardando procedimientos: {e}")

    @staticmethod
    def _stem_es(word: str) -> str:
        """Stemming muy básico para español: quita sufijos comunes."""
        w = word.lower()
        for suffix in ("iones", "ción", "ando", "endo", "idad",
                        "entes", "ente", "ados", "idos", "adas", "idas",
                        "ado", "ido", "ada", "ida",
                        "ar", "er", "ir", "as", "es", "os", "a"):
            if len(w) > len(suffix) + 3 and w.endswith(suffix):
                return w[:-len(suffix)]
        return w

    def find_procedure(self, goal: str) -> Optional[dict]:
        """Busca un procedimiento guardado que coincida con el objetivo."""
        goal_lower = goal.lower()
        goal_words = [w for w in re.findall(r'\w+', goal_lower) if len(w) > 2]
        goal_stems = {self._stem_es(w) for w in goal_words}

        best_match = None
        best_score = 0

        for proc in self._procedures:
            score = 0.0
            # Coincidencia por keywords (con stemming)
            keywords = proc.get("keywords", [])
            for kw in keywords:
                kw_lower = kw.lower()
                kw_stem = self._stem_es(kw_lower)
                if kw_lower in goal_lower:
                    score += 1.0
                elif kw_stem in goal_stems:
                    score += 0.8  # coincidencia parcial por stem

            # Coincidencia parcial en la descripción (con stemming)
            desc = proc.get("description", "").lower()
            desc_stems = {self._stem_es(w) for w in re.findall(r'\w+', desc) if len(w) > 2}
            common_stems = goal_stems & desc_stems
            if common_stems:
                score += min(len(common_stems) * 0.5, 2.0)

            if score > best_score:
                best_score = score
                best_match = proc

        if best_match and best_score >= 2:
            logger.info(f"Procedimiento encontrado: '{best_match.get('description','')}' (score={best_score:.1f})")
            return best_match
        return None

    def save_procedure(self, description: str, keywords: list[str],
                       steps: list[dict], site: str = ""):
        """
        Guarda un procedimiento nuevo aprendido.
        
        Args:
            description: Qué hace el procedimiento (ej: "ver tareas pendientes en aules")
            keywords: Palabras clave para buscarlo (ej: ["tareas", "pendientes", "aules"])
            steps: Lista de pasos ejecutados [{"action": ..., "params": ...}, ...]
            site: Sitio/app donde se ejecuta (ej: "aules")
        """
        procedure = {
            "description": description,
            "keywords": keywords,
            "steps": steps,
            "site": site,
            "times_used": 0,
            "created_at": time.strftime("%Y-%m-%d %H:%M"),
        }

        # Evitar duplicados (actualizar si ya existe uno similar)
        for i, existing in enumerate(self._procedures):
            if existing.get("description", "").lower() == description.lower():
                self._procedures[i] = procedure
                self._save_procedures()
                logger.info(f"Procedimiento actualizado: {description}")
                return

        self._procedures.append(procedure)
        self._save_procedures()
        logger.info(f"Nuevo procedimiento guardado: {description}")

    def learn_from_user(self, explanation: str) -> str:
        """
        Aprende un procedimiento a partir de una explicación del usuario.
        Ej: "para ver las tareas en aules ve a cronología y filtra por próximas"
        """
        # Usar LLM para extraer pasos estructurados
        prompt = (
            "El usuario me está explicando cómo hacer algo en su ordenador. "
            "Extrae los pasos como una lista de acciones.\n\n"
            f"Explicación del usuario: \"{explanation}\"\n\n"
            "Responde SOLO con un JSON así (sin markdown, sin ```json):\n"
            '{"description": "qué se consigue", '
            '"keywords": ["palabra1", "palabra2", ...], '
            '"site": "nombre_sitio_o_app", '
            '"steps": ['
            '  {"action": "navigate_to_url|click_on_text|scroll_page|type_in_app|press_key", '
            '"params": {"param": "valor"}}, '
            "...]}\n\n"
            "Acciones válidas:\n"
            "- navigate_to_url: {url: '...'}\n"
            "- click_on_text: {text: '...'} — clic en un enlace/botón visible\n"
            "- scroll_page: {direction: 'down'|'up'}\n"
            "- type_in_app: {text: '...'} — escribir en un campo\n"
            "- press_key: {key: 'enter'|'tab'|...}\n"
            "- switch_tab: {text: 'título pestaña'} — cambiar de pestaña del navegador\n"
            "- wait: {seconds: N}\n"
        )

        messages = [
            {"role": "system", "content": "Eres un parser de instrucciones. Responde SOLO con JSON válido."},
            {"role": "user", "content": prompt},
        ]
        raw = self.brain.chat_raw(messages)
        
        try:
            # Limpiar posible markdown
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```\w*\n?", "", cleaned)
                cleaned = re.sub(r"\n?```$", "", cleaned)
            
            data = json.loads(cleaned)
            self.save_procedure(
                description=data.get("description", explanation[:80]),
                keywords=data.get("keywords", []),
                steps=data.get("steps", []),
                site=data.get("site", ""),
            )
            return (
                f"Entendido y guardado, señor. He aprendido cómo "
                f"\"{data.get('description', 'realizar esa tarea')}\". "
                f"La próxima vez lo haré automáticamente."
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Error parseando procedimiento del LLM: {e}. Raw: {raw[:200]}")
            # Fallback: guardar como procedimiento simple
            keywords = [w for w in explanation.lower().split() if len(w) > 3][:5]
            self.save_procedure(
                description=explanation[:100],
                keywords=keywords,
                steps=[{"action": "manual", "params": {"instruction": explanation}}],
            )
            return (
                "Entendido, señor. He guardado sus instrucciones. "
                "Las seguiré la próxima vez que me pida algo similar."
            )

    # ─── Ejecución autónoma ───────────────────────────────────

    def execute_goal(self, goal: str, initial_actions: list = None,
                     context: str = "") -> str:
        """
        Ejecuta un objetivo de forma autónoma usando un ciclo de Act-Observe-Think.
        
        Args:
            goal: Lo que el usuario quiere conseguir
            initial_actions: Acciones ya ejecutadas (ej: abrir chrome, navegar a aules)
            context: Contexto adicional (historial de conversación, etc.)
            
        Returns:
            Resultado final: información encontrada, resumen, o pregunta al usuario
        """
        logger.info(f"Agente autónomo iniciado. Objetivo: '{goal}'")

        # ¿Tenemos un procedimiento guardado?
        procedure = self.find_procedure(goal)
        if procedure:
            logger.info(f"Procedimiento encontrado: {procedure['description']}")
            procedure["times_used"] = procedure.get("times_used", 0) + 1
            self._save_procedures()
            # Si ya se ejecutaron acciones de navegación previas
            # (ej: compound parser abrió Chrome y navegó al site),
            # no necesitamos navegar de nuevo.
            already_nav = bool(initial_actions)
            result = self._execute_procedure(procedure, goal, already_navigated=already_nav)
            if result and not result.startswith("Error"):
                return result
            logger.info("Procedimiento guardado falló, usando agente dinámico")

        # Ejecutar con ciclo dinámico
        executed_steps = []
        screen_history = []

        # Si ya se ejecutaron acciones iniciales, esperamos a que cargue
        if initial_actions:
            time.sleep(2)

        for step_num in range(MAX_STEPS):
            logger.info(f"Agente autónomo paso {step_num + 1}/{MAX_STEPS}")

            # 1. OBSERVAR: leer la pantalla
            screen_text = self._observe_screen()
            if not screen_text:
                if step_num == 0:
                    return "No pude leer la pantalla, señor. Asegúrese de que el contenido esté visible."
                break

            screen_history.append(screen_text[:500])

            # 2. PENSAR: ¿hemos logrado el objetivo? ¿qué hacer?
            decision = self._think(goal, screen_text, executed_steps, step_num)

            if decision["status"] == "found":
                # ¡Encontramos la información!
                logger.info("Agente autónomo: objetivo completado")
                return decision["response"]

            elif decision["status"] == "action":
                # Ejecutar la siguiente acción
                action = decision["action"]
                params = decision["params"]
                logger.info(f"Agente ejecutando: {action}({params})")
                self._execute_action(action, params)
                executed_steps.append({"action": action, "params": params})
                time.sleep(decision.get("wait", 2))

            elif decision["status"] == "ask_user":
                # No sabemos cómo continuar → preguntar al usuario
                logger.info(f"Agente pregunta al usuario: {decision['question']}")
                self._pending_question = decision["question"]
                return (
                    f"Señor, necesito su ayuda. {decision['question']}\n\n"
                    f"(Dígame cómo continuar y lo recordaré para la próxima vez)"
                )

            elif decision["status"] == "done":
                # Tarea completada sin información específica que reportar
                return decision.get("response", "Tarea completada, señor.")

            elif decision["status"] == "stuck":
                break

        # Si llegamos aquí, se agotaron los pasos
        last_screen = screen_history[-1] if screen_history else "nada"
        return (
            f"No pude completar la tarea tras {MAX_STEPS} pasos, señor. "
            f"Lo último que vi en pantalla fue:\n{last_screen}\n\n"
            f"¿Podría indicarme cómo continuar?"
        )

    def _execute_procedure(self, procedure: dict, goal: str,
                            already_navigated: bool = False) -> str:
        """Ejecuta un procedimiento guardado paso a paso."""
        steps = procedure.get("steps", [])
        if not steps:
            return "Error: procedimiento sin pasos"

        logger.info(f"Ejecutando procedimiento: {procedure['description']} ({len(steps)} pasos)")

        # Si el procedimiento tiene un site asociado y no estamos ya ahí,
        # navegamos primero al site.
        if not already_navigated:
            site = procedure.get("site", "").lower()
            if site:
                from core.command_parser import CommandParser
                url = CommandParser._KNOWN_SITES.get(site)
                if url:
                    logger.info(f"Procedimiento necesita '{site}' → abriendo Chrome y navegando a {url}")
                    self.sc.open_application("chrome")
                    time.sleep(2.5)
                    self.sc.navigate_to_url(url)
                    time.sleep(3)  # Esperar carga de la página

        for i, step in enumerate(steps):
            action = step.get("action", "")
            params = step.get("params", {})

            if action == "manual":
                # Paso manual, no se puede automatizar
                return f"Este procedimiento requiere intervención manual: {params.get('instruction', '')}"

            if action == "wait":
                time.sleep(params.get("seconds", 2))
                continue

            logger.info(f"Procedimiento paso {i+1}: {action}({params})")
            self._execute_action(action, params)
            time.sleep(2)

        # Después de ejecutar todos los pasos, leer pantalla y reportar
        time.sleep(2)
        screen_text = self._observe_screen()
        if screen_text:
            # Pedir al LLM que resuma lo que ve en relación al objetivo
            summary = self._summarize_screen(goal, screen_text)
            return summary
        return "Procedimiento ejecutado, señor."

    def _observe_screen(self) -> str:
        """Lee el contenido visible de la pantalla via OCR."""
        try:
            text = self.sc.get_screen_text_full()
            if text and len(text.strip()) > 10:
                logger.info(f"OCR: {len(text)} chars leídos")
                return text
        except Exception as e:
            logger.error(f"Error en OCR: {e}")
        return ""

    def _think(self, goal: str, screen_text: str, 
               executed_steps: list, step_num: int) -> dict:
        """
        Decide qué hacer basándose en el objetivo y lo que se ve en pantalla.
        
        Returns:
            dict con:
            - status: "found" | "action" | "ask_user" | "done" | "stuck"
            - response/action/question según el status
        """
        # Truncar screen_text si es muy largo
        screen_context = screen_text[:3000] if len(screen_text) > 3000 else screen_text

        steps_desc = ""
        if executed_steps:
            steps_desc = "Pasos ya ejecutados:\n"
            for i, s in enumerate(executed_steps, 1):
                steps_desc += f"  {i}. {s['action']}({json.dumps(s['params'], ensure_ascii=False)})\n"

        prompt = (
            f"Soy un agente de automatización de escritorio. Mi objetivo es: \"{goal}\"\n\n"
            f"{steps_desc}\n"
            f"Esto es lo que veo en la pantalla ahora (OCR):\n"
            f"---\n{screen_context}\n---\n\n"
            f"Paso actual: {step_num + 1} de {MAX_STEPS}.\n\n"
            "Decide qué hacer. Responde SOLO con un JSON válido (sin markdown, sin ```json):\n\n"
            "Si YA ENCUENTRAS la información que busca el usuario en el texto de pantalla:\n"
            '{"status": "found", "response": "Señor, he encontrado lo siguiente: [resumen de lo que ves]"}\n\n'
            "Si necesitas hacer una ACCIÓN para encontrar la info:\n"
            '{"status": "action", "action": "click_on_text|scroll_page|type_in_app|press_key|navigate_to_url|switch_tab", '
            '"params": {"param": "valor"}, "wait": 2}\n\n'
            'Acciones: click_on_text({text}), scroll_page({direction:"down"|"up"}), '
            'type_in_app({text}), press_key({key}), navigate_to_url({url}), '
            'switch_tab({text:"título de la pestaña"}) — para cambiar de pestaña del navegador\n\n'
            "Si NO SABES cómo continuar y necesitas ayuda del usuario:\n"
            '{"status": "ask_user", "question": "¿Dónde puedo encontrar X?"}\n\n'
            "Si la tarea ya está COMPLETADA (ej: ya navegué donde querían):\n"
            '{"status": "done", "response": "He navegado a X, señor."}\n\n'
            "IMPORTANTE: Analiza el texto OCR cuidadosamente. Si el texto contiene "
            "la información que busca el usuario (tareas, fechas, notas, etc.), "
            "responde con 'found' y un resumen claro."
        )

        messages = [
            {"role": "system", "content": (
                "Eres el motor de decisión de un agente de automatización de escritorio. "
                "Analizas la pantalla (OCR) y decides la siguiente acción. "
                "Responde SOLO con JSON válido. Sé preciso con los textos de click_on_text "
                "(usa texto EXACTO que veas en el OCR). "
                "Si ves la información buscada, repórtala directamente."
            )},
            {"role": "user", "content": prompt},
        ]

        raw = self.brain.chat_raw(messages)

        try:
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```\w*\n?", "", cleaned)
                cleaned = re.sub(r"\n?```$", "", cleaned)
            
            decision = json.loads(cleaned)
            logger.info(f"Agente decisión: {decision.get('status', '???')}")
            return decision
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Error parseando decisión del agente: {e}. Raw: {raw[:300]}")
            # Intentar extraer al menos el status
            if "found" in raw.lower() and "response" in raw.lower():
                # El LLM probablemente dio la respuesta pero no en JSON limpio
                return {"status": "found", "response": raw}
            return {"status": "stuck", "response": "No pude decidir qué hacer"}

    def _summarize_screen(self, goal: str, screen_text: str) -> str:
        """Pide al LLM que resuma lo que se ve en pantalla en relación al objetivo."""
        screen_context = screen_text[:3000]
        prompt = (
            f"El usuario pidió: \"{goal}\"\n\n"
            f"Esto es lo que se ve en la pantalla (OCR):\n{screen_context}\n\n"
            "Resume la información relevante para el usuario de forma clara y concisa. "
            "Si hay una lista de tareas, fechas límite, notas, etc., inclúyelas."
        )
        messages = [
            {"role": "system", "content": "Eres JARVIS. Resume la pantalla para el usuario. Sé conciso, llámale 'señor'."},
            {"role": "user", "content": prompt},
        ]
        result = self.brain.chat_raw(messages)
        return result if result else "No pude analizar el contenido de la pantalla, señor."

    def _execute_action(self, action: str, params: dict):
        """Ejecuta una acción en system_control."""
        try:
            if action == "click_on_text":
                self.sc.click_on_text(params.get("text", ""))
            elif action == "scroll_page":
                self.sc.scroll_page(params.get("direction", "down"))
            elif action == "type_in_app":
                self.sc.type_in_app(params.get("text", ""))
            elif action == "press_key":
                self.sc.press_key(params.get("key", "enter"))
            elif action == "navigate_to_url":
                self.sc.navigate_to_url(params.get("url", ""))
            elif action == "switch_tab":
                # Cambiar de pestaña en el navegador
                tab_text = params.get("text", "")
                if tab_text:
                    # Intentar hacer clic en el texto de la pestaña
                    self.sc.click_on_text(tab_text)
                else:
                    # Ctrl+Tab para siguiente pestaña
                    self.sc.press_key("ctrl+tab")
            elif action == "wait":
                time.sleep(params.get("seconds", 2))
            else:
                logger.warning(f"Acción desconocida: {action}")
        except Exception as e:
            logger.error(f"Error ejecutando {action}: {e}")

    # ─── Gestión de preguntas pendientes ──────────────────────

    def has_pending_question(self) -> bool:
        """¿El agente tiene una pregunta pendiente para el usuario?"""
        return self._pending_question is not None

    def clear_pending(self):
        """Limpia la pregunta pendiente (ej: cambio de tema)."""
        self._pending_question = None

    def get_pending_question(self) -> Optional[str]:
        """Devuelve la pregunta pendiente y la limpia."""
        q = self._pending_question
        self._pending_question = None
        return q

    def answer_pending(self, user_answer: str, original_goal: str = "") -> str:
        """
        El usuario respondió a la pregunta del agente.
        Usa la respuesta para aprender y continuar.
        """
        self._pending_question = None

        # Aprender de la respuesta del usuario
        if original_goal:
            self.learn_from_user(f"{original_goal}: {user_answer}")

        # Intentar continuar con las instrucciones del usuario
        return self.execute_goal(
            goal=original_goal or user_answer,
            context=f"El usuario instruyó: {user_answer}"
        )

    # ─── Info ─────────────────────────────────────────────────

    def list_procedures(self) -> str:
        """Lista los procedimientos aprendidos."""
        if not self._procedures:
            return "No he aprendido ningún procedimiento todavía, señor."
        lines = ["Procedimientos aprendidos:"]
        for p in self._procedures:
            uses = p.get("times_used", 0)
            lines.append(f"  • {p['description']} (usado {uses}x)")
        return "\n".join(lines)

    def forget_procedure(self, description: str) -> str:
        """Elimina un procedimiento por descripción."""
        desc_lower = description.lower()
        for i, p in enumerate(self._procedures):
            if desc_lower in p.get("description", "").lower():
                removed = self._procedures.pop(i)
                self._save_procedures()
                return f"Procedimiento '{removed['description']}' eliminado, señor."
        return "No encontré ese procedimiento, señor."
