"""
J.A.R.V.I.S. — Autonomous Agent  (v2: Plan-first architecture)

Flujo nuevo:
1. ENTENDER — Leer el mensaje del usuario y comprender QUÉ quiere.
2. PLANIFICAR — Crear un plan de pasos concretos (usando pantalla + procedimientos).
3. EJECUTAR — Ir paso a paso, observando la pantalla después de cada acción.
4. SI NO SABE → PREGUNTAR AL USUARIO (no a ChatGPT: cada sitio es diferente).
5. APRENDER — Guardar el camino exitoso para la próxima vez.
"""

import json
import logging
import re
import ctypes
import time
from pathlib import Path
from typing import Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DATA_DIR

logger = logging.getLogger("jarvis.autonomous")

PROCEDURES_FILE = DATA_DIR / "procedures.json"
MAX_STEPS = 15  # Máximo de pasos antes de rendirse


class AutonomousAgent:
    """
    Agente autónomo con arquitectura Plan-first.

    1. Entiende el objetivo.
    2. Crea un plan (lista de pasos).
    3. Ejecuta cada paso, observando la pantalla.
    4. Si se atasca, pregunta al USUARIO.
    5. Guarda el procedimiento exitoso.
    """

    def __init__(self, brain, system_control, parser):
        self.brain = brain
        self.sc = system_control
        self.parser = parser
        self._procedures = self._load_procedures()
        self._pending_question = None
        self._pending_goal = None        # Goal actual cuando hay pregunta pendiente
        self._pending_plan = None        # Plan parcial cuando hay pregunta pendiente
        self._pending_executed = None    # Pasos ya ejecutados cuando hay pregunta
        self._screen_memory = []         # Últimas pantallas vistas (para contexto)
        self._jarvis_minimized = False
        logger.info(f"AutonomousAgent inicializado. {len(self._procedures)} procedimientos guardados.")

    # ─── Procedimientos guardados ─────────────────────────────

    def _load_procedures(self) -> list[dict]:
        try:
            if PROCEDURES_FILE.exists():
                with open(PROCEDURES_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Error cargando procedimientos: {e}")
        return []

    def _save_procedures(self):
        try:
            with open(PROCEDURES_FILE, "w", encoding="utf-8") as f:
                json.dump(self._procedures, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error guardando procedimientos: {e}")

    @staticmethod
    def _stem_es(word: str) -> str:
        """Stemming muy básico para español."""
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
            for kw in proc.get("keywords", []):
                kw_lower = kw.lower()
                if kw_lower in goal_lower:
                    score += 1.0
                elif self._stem_es(kw_lower) in goal_stems:
                    score += 0.8
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
        procedure = {
            "description": description,
            "keywords": keywords,
            "steps": steps,
            "site": site,
            "times_used": 0,
            "created_at": time.strftime("%Y-%m-%d %H:%M"),
        }
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
        """Aprende un procedimiento a partir de una explicación del usuario."""
        prompt = (
            "El usuario me está explicando cómo hacer algo en su ordenador. "
            "Extrae los pasos como una lista de acciones.\n\n"
            f"Explicación del usuario: \"{explanation}\"\n\n"
            "Responde SOLO con un JSON así (sin markdown, sin ```json):\n"
            '{"description": "qué se consigue", '
            '"keywords": ["palabra1", "palabra2", ...], '
            '"site": "nombre_sitio_o_app", '
            '"steps": ['
            '  {"action": "navigate_to_url|click_on_text|scroll_page|type_in_app|press_key|switch_tab|wait", '
            '"params": {"param": "valor"}}, '
            "...]}\n\n"
            "Acciones válidas:\n"
            "- navigate_to_url: {url: '...'}\n"
            "- click_on_text: {text: '...'}\n"
            "- scroll_page: {direction: 'down'|'up'}\n"
            "- type_in_app: {text: '...'}\n"
            "- press_key: {key: 'enter'|'tab'|...}\n"
            "- switch_tab: {text: 'título pestaña'}\n"
            "- wait: {seconds: N}\n"
        )
        messages = [
            {"role": "system", "content": "Eres un parser de instrucciones. Responde SOLO con JSON válido."},
            {"role": "user", "content": prompt},
        ]
        raw = self.brain.chat_raw(messages)
        try:
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

    # ═══════════════════════════════════════════════════════════
    #  FASE 1: ENTENDER + PLANIFICAR
    #  Analiza el mensaje del usuario + la pantalla actual y
    #  crea un plan de pasos concretos.
    # ═══════════════════════════════════════════════════════════

    def _understand_and_plan(self, goal: str, screen_text: str,
                              context: str = "") -> dict:
        """
        Pasa la petición al LLM y recibe una lista de pasos a ejecutar.

        Returns dict:
          understanding  — qué quiere el usuario
          already_found  — bool, si la info ya está completa en pantalla
          found_response — respuesta si already_found=true
          plan           — lista de pasos [{step, description, action, params}, ...]
          questions      — lista de preguntas para el usuario (si las hay)
        """
        screen_ctx = screen_text[:3000] if screen_text else "(no hay pantalla visible)"

        # Conversación reciente para entender referencias
        conv_ctx = ""
        if context:
            conv_ctx = (
                "\nConversación reciente:\n"
                + context[:500] + "\n"
            )

        prompt = (
            f"Me han pedido realizar esta tarea: \"{goal}\"\n\n"
            f"{conv_ctx}"
            f"Esto es lo que veo ahora en la pantalla del ordenador (texto extraído por OCR):\n"
            f"---\n{screen_ctx}\n---\n\n"
            "Hazme una lista por puntos de qué debería hacer para realizarla.\n"
            "Si hay algo que no sepas hacer al 100%, dime qué le tengo que "
            "preguntar a mi humano. Evita lo máximo posible hacer preguntas.\n\n"
            "IMPORTANTE:\n"
            "- Cada paso debe ser UNA acción mecánica concreta: hacer clic en algo, "
            "escribir texto, pulsar una tecla, abrir una app, navegar a una URL, etc.\n"
            "- Para hacer clic: usa el texto EXACTO que aparece en el OCR de arriba. "
            "NO uses frases inventadas ni el texto del usuario.\n"
            "- Si el elemento que busco ya está visible en el OCR, haz clic directamente. "
            "NO abras otras aplicaciones.\n"
            "- Si la información que pide el usuario ya está COMPLETA en el OCR, "
            "pon already_found=true y responde directamente.\n\n"
            "Responde SOLO con JSON válido (sin markdown, sin ```json):\n"
            "{\n"
            '  "understanding": "qué quiere el usuario",\n'
            '  "already_found": false,\n'
            '  "found_response": "",\n'
            '  "questions": [],\n'
            '  "plan": [\n'
            '    {"step": 1, "description": "qué hago", '
            '"action": "ACCION", "params": {"param": "valor"} }\n'
            "  ]\n"
            "}\n\n"
            "Acciones disponibles:\n"
            "- open_application: {app_name: 'chrome'|'explorer'|...}\n"
            "- navigate_to_url: {url: '...'}\n"
            "- click_on_text: {text: 'texto EXACTO del OCR'}\n"
            "- double_click: {text: 'texto EXACTO del OCR'}\n"
            "- right_click: {text: 'texto'}\n"
            "- scroll_page: {direction: 'down'|'up'}\n"
            "- type_in_app: {text: '...'}\n"
            "- press_key: {key: 'enter'|'tab'|'ctrl+f'|...}\n"
            "- search_in_page: {text: '...'} — buscar con Ctrl+F\n"
            "- focus_window: {app_name: '...'}\n"
            "- read_screen: {} — leer la pantalla y decirle al usuario lo que hay\n"
            "- wait: {seconds: N}\n"
            "- ask_user: {question: '¿...?'}\n"
        )

        messages = [
            {"role": "system", "content": (
                "Eres un asistente local de IA que controla un escritorio Windows. "
                "Tu trabajo es recibir una petición y devolver una lista de pasos "
                "mecánicos para realizarla: abrir apps, hacer clic, escribir, "
                "pulsar teclas, etc. "
                "Ves la pantalla del usuario por OCR. "
                "Si un elemento está visible en el OCR, haz clic en él directamente. "
                "NO abras aplicaciones que el usuario no ha pedido. "
                "Responde SOLO con JSON válido. "
                "Si no sabes algo, ponlo en 'questions' en vez de inventar."
            )},
            {"role": "user", "content": prompt},
        ]

        raw = self.brain.chat_raw(messages)
        try:
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```\w*\n?", "", cleaned)
                cleaned = re.sub(r"\n?```$", "", cleaned)
            result = json.loads(cleaned)
            logger.info(f"Entendimiento: {result.get('understanding', '?')[:80]}")
            logger.info(f"Plan: {len(result.get('plan', []))} pasos, "
                        f"already_found={result.get('already_found', False)}")
            return result
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Error en _understand_and_plan: {e}. Raw: {raw[:300]}")
            self._flush_logs()
            return {
                "understanding": goal,
                "already_found": False,
                "plan": [],
                "needs_navigation": False,
                "site": "",
            }
        except Exception as e:
            logger.error(f"Error fatal en _understand_and_plan: {e}", exc_info=True)
            self._flush_logs()
            return {
                "understanding": goal,
                "already_found": False,
                "plan": [],
                "needs_navigation": False,
                "site": "",
            }

    # (Evaluador de pasos eliminado — ejecución directa mecánica)

    # ═══════════════════════════════════════════════════════════
    #  EJECUTAR OBJETIVO  —  Punto de entrada principal
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def _flush_logs():
        """Fuerza el flush de todos los handlers del logger."""
        for handler in logging.getLogger().handlers:
            try:
                handler.flush()
            except Exception:
                pass

    def execute_goal(self, goal: str, initial_actions: list = None,
                     context: str = "") -> str:
        """
        Ejecuta un objetivo con la arquitectura Plan-first:
        1. Observar pantalla
        2. Entender + Planificar
        3. Ejecutar plan paso a paso (evaluar después de cada paso)
        4. Preguntar al usuario si se atasca
        5. Guardar procedimiento exitoso
        """
        logger.info(f"=== Agente autónomo v2: '{goal}' ===")
        self._flush_logs()
        self._screen_memory = []
        self._active_goal = goal  # Para filtrar del OCR
        try:
            self._minimize_jarvis()
            time.sleep(0.3)
            return self._execute_goal_inner(goal, initial_actions, context)
        except Exception as e:
            logger.error(f"Error fatal en agente autónomo: {e}", exc_info=True)
            self._flush_logs()
            return f"Error interno del agente, señor: {e}"
        finally:
            self._restore_jarvis()

    def _execute_goal_inner(self, goal: str, initial_actions: list = None,
                            context: str = "") -> str:
        """
        Flujo simple:
        1. Pasar petición al LLM → recibir lista de pasos
        2. Ejecutar cada paso mecánicamente
        3. Si hay preguntas → preguntar al usuario
        4. Confirmar que se ha hecho
        """

        # ¿Tenemos un procedimiento guardado?
        procedure = self.find_procedure(goal)
        if procedure:
            logger.info(f"Procedimiento encontrado: {procedure['description']}")
            procedure["times_used"] = procedure.get("times_used", 0) + 1
            self._save_procedures()
            already_nav = bool(initial_actions)
            result = self._execute_procedure(procedure, goal,
                                              already_navigated=already_nav)
            if result and not result.startswith("Error"):
                return result
            logger.info("Procedimiento falló, usando agente dinámico")

        # Si hay acciones iniciales (ya se abrió algo previamente)
        if initial_actions:
            time.sleep(2)

        # ── Ciclo principal: Planificar → Ejecutar → Verificar ──
        executed_steps = []
        total_steps = 0
        replan_count = 0
        MAX_REPLANS = 2

        while total_steps < MAX_STEPS and replan_count <= MAX_REPLANS:
            # 1. OBSERVAR pantalla
            screen_text = self._observe_screen()
            if not screen_text:
                # Reintentar una vez tras esperar
                logger.info("OCR vacío, reintentando tras 2s...")
                time.sleep(2)
                screen_text = self._observe_screen()
            if not screen_text:
                if total_steps == 0:
                    # Último intento: intentar leer el título de la ventana
                    title = self.sc.get_active_window_title()
                    if title:
                        screen_text = f"[Ventana activa: {title}]"
                        logger.info(f"OCR vacío pero tenemos título: {title}")
                    else:
                        return ("No pude leer la pantalla, señor. "
                                "Asegúrese de que el contenido esté visible.")
                else:
                    # No es el primer paso, seguir con lo que tenemos
                    logger.warning("OCR vacío en paso intermedio, continuando...")
                    replan_count += 1  # Contar como replan para no loopear
                    continue

            self._screen_memory.append(screen_text[:800])

            # 2. ENTENDER + PLANIFICAR
            understanding = self._understand_and_plan(goal, screen_text, context)

            # ¿Ya tenemos la respuesta directa?
            if understanding.get("already_found"):
                response = understanding.get("found_response", "")
                if response and len(response) > 20:
                    logger.info("Agente: info ya encontrada en pantalla")
                    return response

            # ¿Hay preguntas para el usuario?
            questions = understanding.get("questions", [])
            if questions:
                q_text = "\n".join(f"- {q}" for q in questions)
                logger.info(f"El LLM tiene preguntas: {questions}")
                self._pending_question = (
                    f"Señor, necesito aclarar algunas cosas antes de continuar:\n{q_text}"
                )
                self._pending_goal = goal
                self._pending_plan = understanding.get("plan", [])
                self._pending_executed = executed_steps
                return self._pending_question

            plan = understanding.get("plan", [])
            if not plan:
                logger.info("Sin plan generado. Preguntando al usuario.")
                self._pending_question = (
                    "Señor, estoy viendo la pantalla pero no sé cómo continuar. "
                    "¿Podría indicarme qué debo hacer?"
                )
                self._pending_goal = goal
                self._pending_plan = []
                self._pending_executed = executed_steps
                return self._pending_question

            # 3. EJECUTAR cada paso del plan mecánicamente
            plan_completed = True
            for idx, step_info in enumerate(plan):
                if total_steps >= MAX_STEPS:
                    plan_completed = False
                    break

                action = step_info.get("action", "")
                params = step_info.get("params", {})
                desc = step_info.get("description", action)
                total_steps += 1

                logger.info(f"Paso {total_steps}: {desc} → {action}({params})")

                # ── read_screen: leer y reportar al usuario ──
                if action == "read_screen":
                    time.sleep(1)
                    current = self._observe_screen()
                    if current:
                        self._screen_memory.append(current[:800])
                        summary = self._summarize_screen(goal, current)
                        if summary and len(summary) > 20:
                            self._maybe_save_procedure(goal, executed_steps,
                                                        screen_text)
                            return summary
                    continue

                # ── ask_user: preguntar al usuario ──
                if action == "ask_user":
                    question = params.get("question",
                                          "¿Qué debo hacer ahora?")
                    logger.info(f"Agente pregunta: {question}")
                    self._pending_question = question
                    self._pending_goal = goal
                    self._pending_plan = plan[idx + 1:]
                    self._pending_executed = executed_steps
                    return (
                        f"Señor, necesito su ayuda. {question}\n\n"
                        "(Indíqueme cómo continuar y lo recordaré para "
                        "futuras veces)"
                    )

                # ── Ejecutar la acción mecánicamente ──
                self._execute_action(action, params)
                executed_steps.append({
                    "action": action,
                    "params": params,
                    "description": desc,
                })

                # Espera: acciones rápidas 0.5s, resto 1.5s
                if action in self._FAST_ACTIONS:
                    time.sleep(0.5)
                else:
                    time.sleep(1.5)

                # ── Solo verificar pantalla en el ÚLTIMO paso ──
                # o si es un clic (para detectar si falló)
                remaining = plan[idx + 1:]
                is_click = action in {"click_on_text", "double_click",
                                       "search_in_page"}

                if not remaining or is_click:
                    new_screen = self._observe_screen()
                    if new_screen:
                        self._screen_memory.append(new_screen[:800])

                        # Si fue un clic, verificar que la pantalla cambió
                        if is_click and screen_text:
                            old_sig = set(screen_text.split())
                            new_sig = set(new_screen.split())
                            if old_sig and new_sig:
                                overlap = len(old_sig & new_sig) / max(len(old_sig), len(new_sig))
                                if overlap > 0.8:
                                    logger.info(f"Pantalla NO cambió tras {action} "
                                                f"(overlap={overlap:.0%}). Replanificando.")
                                    replan_count += 1
                                    plan_completed = False
                                    break

                    if not remaining:
                        logger.info("Último paso completado")
                        break

            if plan_completed:
                # Plan completado — confirmar al usuario
                if executed_steps:
                    descs = [s.get('description', s.get('action', '?'))
                             for s in executed_steps]
                    if len(descs) == 1:
                        result_msg = f"Listo, señor. {descs[0].capitalize()}."
                    else:
                        result_msg = f"Listo, señor. {'; '.join(descs)}."

                    # Si el objetivo era obtener información, leer la pantalla
                    if self._is_info_goal(goal):
                        time.sleep(1)
                        final_screen = self._observe_screen()
                        if final_screen:
                            summary = self._summarize_screen(goal, final_screen)
                            if summary and len(summary) > 20:
                                self._maybe_save_procedure(goal, executed_steps,
                                                            screen_text)
                                return summary

                    self._maybe_save_procedure(goal, executed_steps,
                                                screen_text)
                    return result_msg
                break

            # Si no se completó el plan por replan, el while vuelve arriba
            # y re-observa + re-planifica

        # Se acabaron los pasos o replans
        return (
            f"No pude completar la tarea tras {total_steps} pasos, señor. "
            f"¿Podría indicarme cómo continuar?"
        )

    # ─── Ejecutar procedimiento guardado ──────────────────────

    def _execute_procedure(self, procedure: dict, goal: str,
                            already_navigated: bool = False) -> str:
        """Ejecuta un procedimiento guardado paso a paso."""
        steps = procedure.get("steps", [])
        if not steps:
            return "Error: procedimiento sin pasos"

        logger.info(f"Ejecutando procedimiento: {procedure['description']} "
                     f"({len(steps)} pasos)")
        self._flush_logs()

        # Navegar al site si hace falta
        if not already_navigated:
            site = procedure.get("site", "").lower()
            if site:
                from core.command_parser import CommandParser
                url = CommandParser._KNOWN_SITES.get(site)
                if url:
                    try:
                        logger.info(f"Navegando a '{site}' → {url}")
                        self._flush_logs()
                        self.sc.open_application("chrome")
                        logger.info("Chrome abierto, esperando...")
                        self._flush_logs()
                        time.sleep(2.5)
                        self.sc.navigate_to_url(url)
                        logger.info(f"URL navegada: {url}")
                        self._flush_logs()
                        time.sleep(3)
                    except Exception as e:
                        logger.error(f"Error navegando a {site}: {e}", exc_info=True)
                        self._flush_logs()

        for i, step in enumerate(steps):
            action = step.get("action", "")
            params = step.get("params", {})
            if action == "manual":
                return (f"Este procedimiento requiere intervención manual: "
                        f"{params.get('instruction', '')}")
            if action == "wait":
                time.sleep(params.get("seconds", 2))
                continue
            try:
                logger.info(f"Procedimiento paso {i + 1}: {action}({params})")
                self._flush_logs()
                self._execute_action(action, params)
                time.sleep(2)
            except Exception as e:
                logger.error(f"Error en paso {i+1} ({action}): {e}", exc_info=True)
                self._flush_logs()

        # Leer y reportar
        time.sleep(2)
        screen_text = self._observe_screen()
        if screen_text:
            return self._summarize_screen(goal, screen_text)
        return "Procedimiento ejecutado, señor."

    def _maybe_save_procedure(self, goal: str, steps: list,
                               screen_text: str):
        """Guarda el procedimiento si fue exitoso y tiene pasos útiles."""
        # ── Validaciones para evitar guardar procedimientos rotos ──

        # Requiere al menos 2 pasos significativos
        if len(steps) < 2:
            logger.info(f"Auto-save rechazado: solo {len(steps)} paso(s), mínimo 2")
            return

        # No guardar si ya existe un procedimiento similar
        if self.find_procedure(goal):
            return

        # Extraer keywords significativas (> 3 chars, no stopwords)
        _stopwords = {
            'para', 'como', 'donde', 'mira', 'busca', 'quiero',
            'dime', 'revisa', 'enseña', 'muestra', 'hacer', 'tiene',
            'tiene', 'esta', 'esto', 'este', 'sobre', 'tarea',
            'entra', 'click', 'haga', 'quel', 'puedo', 'puedes',
            'algo', 'todo', 'nada', 'aqui', 'alla', 'dentro',
        }
        keywords = [
            w for w in re.findall(r'\w+', goal.lower())
            if len(w) > 3 and w not in _stopwords
        ]

        # Requiere al menos 2 keywords significativas para que la
        # descripción sea suficientemente específica
        if len(keywords) < 2:
            logger.info(f"Auto-save rechazado: solo {len(keywords)} keyword(s) "
                        f"significativa(s) en '{goal[:50]}', mínimo 2")
            return

        clean_steps = [{"action": s["action"], "params": s["params"]}
                       for s in steps]

        # Detectar site del contexto
        site = ""
        for site_name in ("aules", "classroom", "github", "drive", "gmail"):
            if (site_name in goal.lower()
                    or site_name in screen_text[:500].lower()):
                site = site_name
                break

        self.save_procedure(
            description=goal[:100],
            keywords=keywords[:8],
            steps=clean_steps,
            site=site,
        )
        logger.info(f"Procedimiento auto-guardado: {goal[:60]}")

    # ─── Observar y ejecutar ──────────────────────────────────

    def _filter_jarvis_ui(self, text: str) -> str:
        """Filtra las líneas del OCR que pertenecen a la UI de JARVIS.

        El OCR captura la propia ventana de JARVIS (chat, botones, HUD).
        Si el agente ve esas líneas, puede confundirlas con la aplicación
        objetivo (ej: hacer clic en el texto del propio mensaje del usuario).

        También filtra líneas que coinciden con el texto del objetivo actual
        del usuario, para evitar que el LLM copie el mensaje como target.
        """
        if not text:
            return text
        # Patrones que identifican texto de la UI de JARVIS
        _jarvis_ui_patterns = re.compile(
            r"(?:"
            r"J\.?A\.?R\.?V\.?I\.?S\.?"         # Nombre JARVIS
            r"|Escriba un mensaje"                     # Placeholder input
            r"|señor|Señor"                             # Fórmula de cortesía
            r"|CPU:\s*\d+%|RAM:\s*\d+%|Vol:\s*\d+%"  # HUD widgets
            r"|Listo$|Buenos d[ií]as"                   # Status / greeting
            r"|Usted$"                                  # Label "Usted"
            r"|Hecho,\s*señor"                          # Respuesta típica
            r"|Me temo que"                              # Respuesta típica
            r"|No pude completar"                        # Respuesta típica
            r")",
            re.IGNORECASE,
        )

        # Construir palabras clave del objetivo activo para detectar
        # el propio mensaje del usuario en la ventana de JARVIS
        _goal_words: set = set()
        active_goal = getattr(self, "_active_goal", "") or ""
        if active_goal:
            # Extraer palabras significativas (>3 chars) del objetivo
            _goal_words = {
                w.lower()
                for w in re.findall(r"[a-záéíóúñü]+", active_goal, re.IGNORECASE)
                if len(w) > 3
            }

        filtered_lines = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            # Descartar líneas que son claramente de la UI de JARVIS
            if _jarvis_ui_patterns.search(stripped):
                continue
            # Descartar líneas que parecen ser el mensaje del usuario
            # (>60% de las palabras del objetivo coinciden con la línea)
            if _goal_words and len(_goal_words) >= 3:
                line_words = {
                    w.lower()
                    for w in re.findall(r"[a-záéíóúñü]+", stripped, re.IGNORECASE)
                    if len(w) > 3
                }
                if line_words:
                    overlap = len(_goal_words & line_words)
                    ratio = overlap / min(len(_goal_words), len(line_words))
                    if ratio > 0.6:
                        logger.debug(f"Filtrada línea OCR (coincide con goal): {stripped[:60]}")
                        continue
            filtered_lines.append(line)
        result = "\n".join(filtered_lines)
        if len(result.strip()) < 10:
            # Si filtramos demasiado, devolver el original
            return text
        return result

    # ─── Clasificación del objetivo ───────────────────────────

    _INFO_GOAL_RE = re.compile(
        r"(?:qué|cuál|cuánto|dime|muestra|lee|consulta|busca\s+info|"
        r"comprueba|averigua|investiga|cuéntame|explica)",
        re.IGNORECASE,
    )

    def _is_info_goal(self, goal: str) -> bool:
        """True si el objetivo es OBTENER información (no solo ejecutar una acción)."""
        return bool(self._INFO_GOAL_RE.search(goal))

    # ─── Acciones rápidas (sin espera larga) ──────────────────

    _FAST_ACTIONS = frozenset({
        "press_key", "type_in_app", "scroll_page", "wait",
        "focus_window", "switch_tab",
    })

    def _observe_screen(self) -> str:
        """Lee el contenido visible de la pantalla via OCR.

        JARVIS ya debe estar minimizado por execute_goal().
        """
        try:
            text = self.sc.get_screen_text_full()
            if text and len(text.strip()) > 10:
                filtered = self._filter_jarvis_ui(text)
                logger.info(f"OCR: {len(text)} chars leídos, {len(filtered)} tras filtrar UI")
                return filtered
            else:
                logger.warning(f"OCR devolvió poco texto: {len(text) if text else 0} chars")
                return text or ""
        except Exception as e:
            logger.error(f"Error en OCR: {e}")
        return ""

    def _minimize_jarvis(self):
        """Minimiza la ventana de JARVIS (ctypes, instantáneo)."""
        try:
            user32 = ctypes.windll.user32
            hwnd = user32.FindWindowW(None, "J.A.R.V.I.S.")
            if hwnd:
                user32.ShowWindow(hwnd, 6)  # SW_MINIMIZE
                self._jarvis_minimized = True
        except Exception as e:
            logger.debug(f"No se pudo minimizar JARVIS: {e}")

    def _restore_jarvis(self):
        """Restaura la ventana de JARVIS (ctypes, instantáneo)."""
        try:
            user32 = ctypes.windll.user32
            hwnd = user32.FindWindowW(None, "J.A.R.V.I.S.")
            if hwnd:
                user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                self._jarvis_minimized = False
        except Exception as e:
            logger.debug(f"No se pudo restaurar JARVIS: {e}")

    def _summarize_screen(self, goal: str, screen_text: str) -> str:
        """Pide al LLM que resuma la pantalla en relación al objetivo."""
        try:
            screen_ctx = screen_text[:3000]
            prompt = (
                f"El usuario pidió: \"{goal}\"\n\n"
                f"Esto es lo que se ve en la pantalla (OCR):\n{screen_ctx}\n\n"
                "Resume la información relevante para el usuario de forma clara "
                "y concisa. Si hay lista de tareas, fechas límite, notas, "
                "enunciados, documentos, etc., inclúyelos. "
                "Si NO ves información relevante, dilo claramente."
            )
            messages = [
                {"role": "system", "content": (
                    "Eres JARVIS. Resume la pantalla para el usuario. "
                    "Sé conciso, llámale 'señor'."
                )},
                {"role": "user", "content": prompt},
            ]
            logger.info("Pidiendo resumen al LLM...")
            self._flush_logs()
            result = self.brain.chat_raw(messages)
            logger.info(f"Resumen recibido: {len(result) if result else 0} chars")
            self._flush_logs()
            return (result if result
                    else "No pude analizar el contenido de la pantalla, señor.")
        except Exception as e:
            logger.error(f"Error en _summarize_screen: {e}", exc_info=True)
            self._flush_logs()
            return f"Vi contenido en pantalla pero no pude analizarlo, señor. Error: {e}"

    def _execute_action(self, action: str, params: dict) -> bool:
        """Ejecuta una acción concreta en system_control.

        JARVIS ya está minimizado por execute_goal().
        """
        try:
            return self._execute_action_inner(action, params)
        except Exception as e:
            logger.error(f"Error ejecutando {action}: {e}")
            return False

    def _execute_action_inner(self, action: str, params: dict) -> bool:
        """Ejecuta la acción. Retorna True si éxito."""
        if action == "click_on_text":
            text = params.get("text", "")
            if not text:
                return False
            result = self.sc.click_on_text(text)
            # Si click_on_text falla, intentar fallbacks
            if result and ("no se encontró" in str(result).lower()
                           or "not found" in str(result).lower()):
                logger.info(f"click_on_text('{text}') falló. Intentando search_in_page...")
                self.sc.search_in_page(text)
                time.sleep(1)
                self.sc.press_key("enter")
                time.sleep(0.5)
                self.sc.press_key("escape")
            return True

        elif action == "double_click":
            text = params.get("text", "")
            if text:
                self.sc.double_click(text)
            return True

        elif action == "right_click":
            text = params.get("text", "")
            if text:
                self.sc.right_click(text)
            return True

        elif action == "describe_and_click":
            desc = params.get("description", "")
            if desc:
                self.sc.describe_and_click(desc)
            return True

        elif action == "scroll_page":
            self.sc.scroll_page(params.get("direction", "down"))
            return True

        elif action == "type_in_app":
            self.sc.type_in_app(params.get("text", ""))
            return True

        elif action == "press_key":
            self.sc.press_key(params.get("key", "enter"))
            return True

        elif action == "navigate_to_url":
            self.sc.navigate_to_url(params.get("url", ""))
            return True

        elif action == "open_application":
            app = params.get("app_name", "")
            if app:
                self.sc.open_application(app)
                time.sleep(2)
                # Verificar que se abrió
                title = self.sc.get_active_window_title()
                logger.info(f"Tras abrir '{app}', ventana activa: {title}")
            return True

        elif action == "focus_window":
            app = params.get("app_name", "")
            if app:
                self.sc.focus_window(app)
                time.sleep(0.5)
            return True

        elif action == "search_in_page":
            text = params.get("text", "")
            if text:
                self.sc.search_in_page(text)
            return True

        elif action == "switch_tab":
            tab_text = params.get("text", "")
            if tab_text:
                self.sc.click_on_text(tab_text)
            else:
                self.sc.press_key("ctrl+tab")
            return True

        elif action == "wait":
            time.sleep(params.get("seconds", 2))
            return True

        else:
            logger.warning(f"Acción desconocida: {action}")
            return False

    # ─── Gestión de preguntas pendientes ──────────────────────

    def has_pending_question(self) -> bool:
        return self._pending_question is not None

    def clear_pending(self):
        self._pending_question = None
        self._pending_goal = None
        self._pending_plan = None
        self._pending_executed = None

    def get_pending_question(self) -> Optional[str]:
        q = self._pending_question
        self._pending_question = None
        return q

    def answer_pending(self, user_answer: str, original_goal: str = "") -> str:
        """
        El usuario respondió a la pregunta del agente.
        Aprende de la respuesta y reintenta con la nueva info.
        """
        goal = self._pending_goal or original_goal or user_answer
        self._pending_question = None
        self._pending_plan = None

        # Aprender de la respuesta del usuario
        if original_goal and user_answer:
            self.learn_from_user(f"{original_goal}: {user_answer}")

        # Replanificar con la pantalla actual
        return self.execute_goal(
            goal=goal,
            context=f"El usuario instruyó: {user_answer}",
        )

    # ─── Info ─────────────────────────────────────────────────

    def list_procedures(self) -> str:
        if not self._procedures:
            return "No he aprendido ningún procedimiento todavía, señor."
        lines = ["Procedimientos aprendidos:"]
        for p in self._procedures:
            uses = p.get("times_used", 0)
            lines.append(f"  • {p['description']} (usado {uses}x)")
        return "\n".join(lines)

    def forget_procedure(self, description: str) -> str:
        desc_lower = description.lower()
        for i, p in enumerate(self._procedures):
            if desc_lower in p.get("description", "").lower():
                removed = self._procedures.pop(i)
                self._save_procedures()
                return f"Procedimiento '{removed['description']}' eliminado, señor."
        return "No encontré ese procedimiento, señor."
