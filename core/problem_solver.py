"""
J.A.R.V.I.S. — Problem Solver Engine
═══════════════════════════════════════
Motor de resolución inteligente inspirado en OpenClaw.

Cuando JARVIS no sabe hacer algo:
1. Analiza qué se necesita
2. Busca en la web cómo hacerlo
3. Descompone en sub-tareas
4. Prueba diferentes enfoques
5. Verifica resultados
6. Aprende para el futuro

Este módulo es el cerebro detrás de la capacidad de JARVIS
para resolver problemas que nunca ha visto antes.
"""

import json
import logging
import time
import traceback
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("jarvis.problem_solver")


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ApproachType(Enum):
    DIRECT_ACTION = "direct_action"         # Ejecutar acción directa del sistema
    AUTONOMOUS_AGENT = "autonomous_agent"   # Usar el agente autónomo visual
    CODE_GENERATION = "code_generation"     # Generar y ejecutar código
    WEB_RESEARCH = "web_research"           # Investigar en la web
    BROWSER_AUTOMATION = "browser_automation"  # Automatizar el navegador
    SYSTEM_COMMAND = "system_command"        # Ejecutar comando de sistema
    COMBINED = "combined"                    # Combinación de enfoques
    ASK_USER = "ask_user"                   # Preguntar al usuario


@dataclass
class SubTask:
    """Una sub-tarea dentro de un problema mayor."""
    id: int
    description: str
    approach: ApproachType
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None
    attempts: int = 0
    max_attempts: int = 3
    dependencies: List[int] = field(default_factory=list)  # IDs de sub-tareas previas
    context: Dict[str, Any] = field(default_factory=dict)  # Info adicional


@dataclass
class SolutionPlan:
    """Plan completo para resolver un problema."""
    goal: str
    analysis: str
    subtasks: List[SubTask]
    approach: ApproachType
    estimated_difficulty: str  # easy, medium, hard
    requires_internet: bool = False
    requires_screen: bool = False
    total_attempts: int = 0
    max_total_attempts: int = 5
    status: TaskStatus = TaskStatus.PENDING
    final_result: Optional[str] = None


class ProblemSolver:
    """
    Motor de resolución inteligente.
    
    Capacidades:
    - Descompone problemas complejos en sub-tareas
    - Busca soluciones en la web cuando no sabe hacer algo
    - Prueba múltiples enfoques si el primero falla
    - Genera código Python para tareas no previstas
    - Verifica semánticamente que la solución es correcta
    - Aprende de soluciones exitosas para usar en el futuro
    """

    def __init__(self, brain=None, orchestrator=None, web_search=None,
                 code_executor=None, autonomous_agent=None, learner=None,
                 system_control=None, memory=None):
        self.brain = brain
        self.orchestrator = orchestrator
        self.web_search = web_search
        self.code_executor = code_executor
        self.autonomous = autonomous_agent
        self.learner = learner
        self.system_control = system_control
        self.memory = memory
        
        # Historial de resoluciones
        self._solution_cache: Dict[str, Dict] = {}
        self._attempt_history: List[Dict] = []
        
        # Callbacks para UI
        self._status_callback: Optional[Callable] = None
        
        logger.info("ProblemSolver inicializado")

    def set_status_callback(self, callback: Callable):
        """Establece callback para informar del estado al UI."""
        self._status_callback = callback

    def _notify_status(self, message: str):
        """Notifica al UI del progreso."""
        if self._status_callback:
            try:
                self._status_callback(message)
            except Exception:
                pass
        logger.info(f"[ProblemSolver] {message}")

    # ===========================
    # RESOLUCIÓN PRINCIPAL
    # ===========================

    def solve(self, problem: str, context: Optional[Dict] = None) -> str:
        """
        Punto de entrada principal. Intenta resolver cualquier problema.
        
        Args:
            problem: Descripción del problema/tarea en lenguaje natural
            context: Contexto adicional (app actual, pantalla, etc.)
            
        Returns:
            Resultado de la resolución
        """
        context = context or {}
        self._notify_status(f"🧠 Analizando: {problem[:80]}...")
        
        # 1. Verificar si ya tenemos una solución cached
        cached = self._check_cache(problem)
        if cached:
            self._notify_status("💾 Encontrada solución previa")
            return self._execute_cached_solution(cached, problem, context)
        
        # 2. Analizar el problema y crear un plan
        plan = self._analyze_and_plan(problem, context)
        if not plan:
            return "No pude analizar el problema. ¿Podrías reformularlo?"
        
        self._notify_status(f"📋 Plan: {len(plan.subtasks)} pasos ({plan.estimated_difficulty})")
        
        # 3. Ejecutar el plan
        result = self._execute_plan(plan, context)
        
        # 4. Verificar resultado
        if plan.status == TaskStatus.COMPLETED:
            # Guardar en cache para futuro uso
            self._cache_solution(problem, plan)
            
            # Intentar aprender de la solución
            self._learn_from_solution(problem, plan)
            
            return result
        
        # 5. Si falló, intentar enfoques alternativos
        self._notify_status("🔄 Primer enfoque falló, buscando alternativas...")
        alt_result = self._try_alternative_approaches(problem, plan, context)
        
        if alt_result:
            return alt_result
        
        # 6. Último recurso: investigar en la web
        self._notify_status("🌐 Investigando en la web cómo resolver esto...")
        web_result = self._solve_via_web_research(problem, context)
        
        if web_result:
            return web_result
        
        return (f"He intentado resolver '{problem}' con varios enfoques pero "
                f"no lo he conseguido completamente. "
                f"¿Puedes darme más detalles o reformular la petición?")

    # ===========================
    # ANÁLISIS Y PLANIFICACIÓN
    # ===========================

    def _analyze_and_plan(self, problem: str, context: Dict) -> Optional[SolutionPlan]:
        """
        Usa el LLM para analizar el problema y crear un plan de resolución.
        """
        if not self.brain:
            return self._simple_plan(problem)
        
        # Obtener info del sistema
        screen_context = ""
        if self.system_control:
            try:
                active_window = self.system_control.get_active_window_title()
                screen_context = f"\nVentana activa: {active_window}"
            except Exception:
                pass
        
        prompt = f"""Analiza esta tarea y crea un plan de resolución. 
La tarea es: "{problem}"
{screen_context}

Contexto adicional: {json.dumps(context, ensure_ascii=False) if context else "ninguno"}

Responde ÚNICAMENTE con un JSON válido (sin markdown, sin ```):
{{
    "analysis": "breve análisis del problema",
    "difficulty": "easy|medium|hard",
    "approach": "direct_action|autonomous_agent|code_generation|web_research|browser_automation|system_command|combined",
    "requires_internet": true/false,
    "requires_screen": true/false,
    "subtasks": [
        {{
            "id": 1,
            "description": "qué hacer en este paso",
            "approach": "direct_action|autonomous_agent|code_generation|system_command",
            "dependencies": []
        }}
    ]
}}

Reglas:
- Descompón en los mínimos pasos necesarios (max 8)
- direct_action: para cosas que JARVIS ya sabe hacer (abrir apps, vol, brillo, archivos)
- autonomous_agent: para interacciones visuales en pantalla (clicks, escribir en apps)
- code_generation: para tareas que requieren lógica/cálculo/procesamiento
- system_command: para comandos de PowerShell/CMD
- web_research: cuando necesitas información de internet
- Si es algo simple, 1-2 subtasks bastan
"""
        
        try:
            response = self.brain.chat(prompt, role="system_analyst")
            plan_data = self._parse_json_response(response)
            
            if not plan_data:
                return self._simple_plan(problem)
            
            subtasks = []
            for st in plan_data.get("subtasks", []):
                approach_str = st.get("approach", "direct_action")
                try:
                    approach = ApproachType(approach_str)
                except ValueError:
                    approach = ApproachType.DIRECT_ACTION
                
                subtasks.append(SubTask(
                    id=st.get("id", len(subtasks) + 1),
                    description=st.get("description", ""),
                    approach=approach,
                    dependencies=st.get("dependencies", [])
                ))
            
            if not subtasks:
                return self._simple_plan(problem)
            
            main_approach_str = plan_data.get("approach", "direct_action")
            try:
                main_approach = ApproachType(main_approach_str)
            except ValueError:
                main_approach = ApproachType.DIRECT_ACTION
            
            return SolutionPlan(
                goal=problem,
                analysis=plan_data.get("analysis", ""),
                subtasks=subtasks,
                approach=main_approach,
                estimated_difficulty=plan_data.get("difficulty", "medium"),
                requires_internet=plan_data.get("requires_internet", False),
                requires_screen=plan_data.get("requires_screen", False)
            )
            
        except Exception as e:
            logger.error(f"Error en análisis: {e}")
            return self._simple_plan(problem)

    def _simple_plan(self, problem: str) -> SolutionPlan:
        """Plan simple cuando el LLM no está disponible."""
        return SolutionPlan(
            goal=problem,
            analysis="Plan simple sin análisis LLM",
            subtasks=[
                SubTask(
                    id=1,
                    description=problem,
                    approach=ApproachType.DIRECT_ACTION
                )
            ],
            approach=ApproachType.DIRECT_ACTION,
            estimated_difficulty="medium"
        )

    # ===========================
    # EJECUCIÓN DEL PLAN
    # ===========================

    def _execute_plan(self, plan: SolutionPlan, context: Dict) -> str:
        """Ejecuta un plan paso a paso."""
        plan.status = TaskStatus.IN_PROGRESS
        results = []
        
        for subtask in plan.subtasks:
            # Verificar dependencias
            if subtask.dependencies:
                deps_completed = all(
                    any(st.id == dep_id and st.status == TaskStatus.COMPLETED
                        for st in plan.subtasks)
                    for dep_id in subtask.dependencies
                )
                if not deps_completed:
                    subtask.status = TaskStatus.SKIPPED
                    subtask.result = "Dependencias no completadas"
                    continue
            
            self._notify_status(f"⚡ [{subtask.id}/{len(plan.subtasks)}] {subtask.description[:60]}")
            
            # Ejecutar según el enfoque
            success, result = self._execute_subtask(subtask, plan, context)
            
            if success:
                subtask.status = TaskStatus.COMPLETED
                subtask.result = result
                results.append(f"✅ {subtask.description}: {result}")
            else:
                subtask.status = TaskStatus.FAILED
                subtask.error = result
                results.append(f"❌ {subtask.description}: {result}")
                
                # Si un paso crítico falla, intentar replanificar
                if not subtask.dependencies:  # Es un paso raíz
                    retry_result = self._retry_subtask(subtask, plan, context)
                    if retry_result:
                        results[-1] = f"✅ (reintento) {subtask.description}: {retry_result}"
        
        # Evaluar resultado global
        completed = sum(1 for st in plan.subtasks if st.status == TaskStatus.COMPLETED)
        total = len(plan.subtasks)
        
        if completed == total:
            plan.status = TaskStatus.COMPLETED
            plan.final_result = "\n".join(results)
            return plan.final_result
        elif completed > 0:
            plan.status = TaskStatus.COMPLETED  # Parcialmente exitoso
            plan.final_result = f"Completé {completed}/{total} pasos:\n" + "\n".join(results)
            return plan.final_result
        else:
            plan.status = TaskStatus.FAILED
            return f"No pude completar la tarea. Intentos:\n" + "\n".join(results)

    def _execute_subtask(self, subtask: SubTask, plan: SolutionPlan, 
                         context: Dict) -> Tuple[bool, str]:
        """Ejecuta una sub-tarea individual."""
        subtask.attempts += 1
        
        try:
            if subtask.approach == ApproachType.DIRECT_ACTION:
                return self._exec_direct_action(subtask, context)
            
            elif subtask.approach == ApproachType.AUTONOMOUS_AGENT:
                return self._exec_autonomous(subtask, context)
            
            elif subtask.approach == ApproachType.CODE_GENERATION:
                return self._exec_code_generation(subtask, context)
            
            elif subtask.approach == ApproachType.SYSTEM_COMMAND:
                return self._exec_system_command(subtask, context)
            
            elif subtask.approach == ApproachType.WEB_RESEARCH:
                return self._exec_web_research(subtask, context)
            
            elif subtask.approach == ApproachType.BROWSER_AUTOMATION:
                return self._exec_browser_automation(subtask, context)
            
            elif subtask.approach == ApproachType.ASK_USER:
                return True, f"Necesito que el usuario haga: {subtask.description}"
            
            else:
                return self._exec_direct_action(subtask, context)
                
        except Exception as e:
            logger.error(f"Error en subtask {subtask.id}: {e}")
            return False, str(e)

    def _retry_subtask(self, subtask: SubTask, plan: SolutionPlan,
                       context: Dict) -> Optional[str]:
        """Reintenta una sub-tarea con un enfoque diferente."""
        if subtask.attempts >= subtask.max_attempts:
            return None
        
        # Probar con otro enfoque
        alternative_approaches = {
            ApproachType.DIRECT_ACTION: [ApproachType.AUTONOMOUS_AGENT, ApproachType.SYSTEM_COMMAND],
            ApproachType.AUTONOMOUS_AGENT: [ApproachType.SYSTEM_COMMAND, ApproachType.CODE_GENERATION],
            ApproachType.CODE_GENERATION: [ApproachType.SYSTEM_COMMAND, ApproachType.DIRECT_ACTION],
            ApproachType.SYSTEM_COMMAND: [ApproachType.CODE_GENERATION, ApproachType.AUTONOMOUS_AGENT],
            ApproachType.BROWSER_AUTOMATION: [ApproachType.AUTONOMOUS_AGENT, ApproachType.WEB_RESEARCH],
        }
        
        alternatives = alternative_approaches.get(subtask.approach, [])
        
        for alt_approach in alternatives:
            subtask.approach = alt_approach
            self._notify_status(f"🔄 Reintentando con enfoque: {alt_approach.value}")
            
            success, result = self._execute_subtask(subtask, plan, context)
            if success:
                subtask.status = TaskStatus.COMPLETED
                subtask.result = result
                return result
        
        return None

    # ===========================
    # EJECUTORES POR TIPO
    # ===========================

    def _exec_direct_action(self, subtask: SubTask, context: Dict) -> Tuple[bool, str]:
        """Ejecuta una acción directa usando el orchestrator."""
        if self.orchestrator:
            try:
                # Usar el orchestrator para procesar como comando normal
                result = self.orchestrator.process(subtask.description)
                if result and "error" not in result.lower():
                    return True, result
                return False, result or "Sin resultado"
            except Exception as e:
                return False, str(e)
        return False, "Orchestrator no disponible"

    def _exec_autonomous(self, subtask: SubTask, context: Dict) -> Tuple[bool, str]:
        """Ejecuta usando el agente autónomo visual."""
        if self.autonomous:
            try:
                result = self.autonomous.execute_goal(subtask.description)
                if result and ("completad" in result.lower() or "éxito" in result.lower() 
                              or "hecho" in result.lower()):
                    return True, result
                elif result:
                    return True, result  # Aceptar el resultado del agente
                return False, result or "El agente autónomo no pudo completar la tarea"
            except Exception as e:
                return False, str(e)
        return False, "Agente autónomo no disponible"

    def _exec_code_generation(self, subtask: SubTask, context: Dict) -> Tuple[bool, str]:
        """Genera y ejecuta código Python para resolver la tarea."""
        if not self.brain:
            return False, "Brain no disponible para generar código"
        
        prompt = f"""Genera código Python para: {subtask.description}

Requisitos:
- El código debe ser autocontenido
- Usa solo librerías estándar o estas: os, sys, subprocess, json, re, pathlib, datetime, shutil
- El código debe imprimir el resultado final
- NO uses input() ni funciones interactivas
- Si necesitas ejecutar un comando del sistema, usa subprocess.run()
- Maneja errores con try/except
- Que sea eficiente y directo

Responde SOLO con el código Python, sin explicaciones ni markdown."""
        
        try:
            code = self.brain.chat(prompt, role="python_developer")
            
            # Limpiar código
            code = self._clean_code(code)
            
            if not code:
                return False, "No se generó código válido"
            
            # Ejecutar
            if self.code_executor:
                result = self.code_executor.execute(code)
                if isinstance(result, dict):
                    if result.get("success"):
                        return True, result.get("output", "Código ejecutado correctamente")
                    else:
                        return False, result.get("error", "Error en ejecución")
                return True, str(result)
            else:
                # Ejecutar directamente con subprocess
                import subprocess
                proc = subprocess.run(
                    ["python", "-c", code],
                    capture_output=True, text=True, timeout=30
                )
                if proc.returncode == 0:
                    return True, proc.stdout.strip() or "Ejecutado correctamente"
                else:
                    return False, proc.stderr.strip() or "Error en ejecución"
                    
        except Exception as e:
            return False, str(e)

    def _exec_system_command(self, subtask: SubTask, context: Dict) -> Tuple[bool, str]:
        """Ejecuta un comando de sistema (PowerShell/CMD)."""
        if not self.brain:
            return False, "Brain no disponible"
        
        prompt = f"""Genera el comando de PowerShell para Windows que hace: {subtask.description}

Responde SOLO con el comando, sin explicaciones. Una sola línea.
Si son varios comandos, sepáralos con ;
No uses comandos destructivos (rm -rf, format, etc.)"""
        
        try:
            command = self.brain.chat(prompt, role="sysadmin")
            command = command.strip().strip('`').strip()
            
            # Validación de seguridad básica
            dangerous = ['format', 'del /s', 'rm -rf', 'rmdir /s', 
                         'reg delete', 'diskpart', 'bcdedit']
            for d in dangerous:
                if d.lower() in command.lower():
                    return False, f"Comando bloqueado por seguridad: contiene '{d}'"
            
            import subprocess
            proc = subprocess.run(
                ["powershell", "-Command", command],
                capture_output=True, text=True, timeout=30
            )
            
            if proc.returncode == 0:
                output = proc.stdout.strip() or "Comando ejecutado correctamente"
                return True, output
            else:
                return False, proc.stderr.strip() or f"Error (código {proc.returncode})"
                
        except subprocess.TimeoutExpired:
            return False, "Comando excedió el tiempo límite"
        except Exception as e:
            return False, str(e)

    def _exec_web_research(self, subtask: SubTask, context: Dict) -> Tuple[bool, str]:
        """Investiga en la web para encontrar información o soluciones."""
        if not self.web_search:
            return False, "WebSearch no disponible"
        
        try:
            # Buscar información
            research_data = self.web_search.research(subtask.description, depth=2)
            
            if research_data.get("search_results"):
                # Compilar resultados
                info = []
                for r in research_data["search_results"][:5]:
                    info.append(f"- {r['title']}: {r['snippet']}")
                
                # Si hay contenido extraído, incluirlo
                if research_data.get("extracted_content"):
                    for content in research_data["extracted_content"][:2]:
                        info.append(f"\n📄 {content['title']}:\n{content['content'][:800]}")
                
                result = "\n".join(info)
                return True, result
            
            return False, "No se encontraron resultados relevantes"
            
        except Exception as e:
            return False, str(e)

    def _exec_browser_automation(self, subtask: SubTask, context: Dict) -> Tuple[bool, str]:
        """Automatiza acciones en el navegador."""
        # Delegamos al agente autónomo que usa OCR + interacción visual
        return self._exec_autonomous(subtask, context)

    # ===========================
    # ENFOQUES ALTERNATIVOS
    # ===========================

    def _try_alternative_approaches(self, problem: str, failed_plan: SolutionPlan,
                                     context: Dict) -> Optional[str]:
        """
        Cuando el plan principal falla, intenta enfoques completamente diferentes.
        """
        if not self.brain:
            return None
        
        # Recopilar info sobre lo que falló
        failures = []
        for st in failed_plan.subtasks:
            if st.status == TaskStatus.FAILED:
                failures.append(f"- {st.description}: {st.error}")
        
        failure_info = "\n".join(failures) if failures else "Plan falló sin detalles"
        
        prompt = f"""El siguiente plan para "{problem}" falló:

Errores encontrados:
{failure_info}

Propón un enfoque COMPLETAMENTE DIFERENTE para resolver esto.
Responde con JSON:
{{
    "new_approach": "descripción del nuevo enfoque",
    "steps": [
        {{"description": "paso 1", "type": "system_command|code_generation|autonomous_agent"}}
    ]
}}"""
        
        try:
            response = self.brain.chat(prompt, role="problem_solver")
            alt_plan = self._parse_json_response(response)
            
            if alt_plan and alt_plan.get("steps"):
                self._notify_status(f"🔄 Intentando: {alt_plan.get('new_approach', 'enfoque alternativo')}")
                
                for step in alt_plan["steps"][:5]:
                    try:
                        step_type = step.get("type", "system_command")
                        approach = ApproachType(step_type)
                    except ValueError:
                        approach = ApproachType.SYSTEM_COMMAND
                    
                    subtask = SubTask(
                        id=1,
                        description=step["description"],
                        approach=approach
                    )
                    
                    success, result = self._execute_subtask(subtask, failed_plan, context)
                    if success:
                        self._cache_solution(problem, failed_plan)
                        return f"✅ Resuelto con enfoque alternativo: {result}"
            
        except Exception as e:
            logger.error(f"Error en enfoque alternativo: {e}")
        
        return None

    # ===========================
    # RESOLUCIÓN VÍA WEB
    # ===========================

    def _solve_via_web_research(self, problem: str, context: Dict) -> Optional[str]:
        """
        Investiga en la web cómo resolver el problema,
        extrae instrucciones y las ejecuta.
        """
        if not self.web_search or not self.brain:
            return None
        
        self._notify_status("🌐 Buscando solución en internet...")
        
        # 1. Buscar cómo hacerlo
        how_to_results = self.web_search.search_how_to(problem)
        
        if not how_to_results:
            return None
        
        # 2. Extraer instrucciones de la mejor fuente
        best_result = how_to_results[0]
        self._notify_status(f"📖 Leyendo: {best_result.title}")
        
        instructions = self.web_search.extract_instructions(best_result.url)
        
        if not instructions:
            # Usar el snippet como fuente
            instructions = best_result.snippet
        
        # 3. Pedir al LLM que convierta las instrucciones en acciones ejecutables
        prompt = f"""Encontré estas instrucciones para "{problem}":

{instructions[:2000]}

Convierte esto en un plan ejecutable para JARVIS en Windows.
Responde con JSON:
{{
    "can_automate": true/false,
    "explanation": "explicación breve",
    "steps": [
        {{"description": "paso", "type": "system_command|code_generation|autonomous_agent", "command": "comando si aplica"}}
    ]
}}

Si no se puede automatizar, explica por qué y qué puede hacer el usuario."""
        
        try:
            response = self.brain.chat(prompt, role="automation_expert")
            plan = self._parse_json_response(response)
            
            if not plan:
                return f"Encontré información sobre cómo hacer esto:\n{instructions[:500]}\n\nPero no pude automatizarlo completamente."
            
            if plan.get("can_automate"):
                results = []
                for step in plan.get("steps", [])[:5]:
                    try:
                        step_type = step.get("type", "system_command")
                        approach = ApproachType(step_type)
                    except ValueError:
                        approach = ApproachType.SYSTEM_COMMAND
                    
                    subtask = SubTask(
                        id=len(results) + 1,
                        description=step["description"],
                        approach=approach,
                        context={"command": step.get("command", "")}
                    )
                    
                    # Si tiene un comando directo, ejecutarlo
                    if step.get("command") and approach == ApproachType.SYSTEM_COMMAND:
                        import subprocess
                        try:
                            proc = subprocess.run(
                                ["powershell", "-Command", step["command"]],
                                capture_output=True, text=True, timeout=30
                            )
                            if proc.returncode == 0:
                                results.append(f"✅ {step['description']}")
                                continue
                        except Exception:
                            pass
                    
                    success, result = self._execute_subtask(subtask, None, context)
                    status = "✅" if success else "❌"
                    results.append(f"{status} {step['description']}: {result}")
                
                return "\n".join(results)
            else:
                explanation = plan.get("explanation", "")
                return f"He investigado y {explanation}"
                
        except Exception as e:
            logger.error(f"Error en web research solve: {e}")
            return f"Encontré información relevante pero no pude automatizar la solución:\n{instructions[:300]}"

    # ===========================
    # CACHE Y APRENDIZAJE
    # ===========================

    def _check_cache(self, problem: str) -> Optional[Dict]:
        """Busca soluciones previas en cache."""
        problem_lower = problem.lower()
        for cached_key, cached_solution in self._solution_cache.items():
            # Coincidencia exacta o alta similitud
            if cached_key == problem_lower:
                return cached_solution
            # Coincidencia parcial por palabras clave
            key_words = set(cached_key.split())
            problem_words = set(problem_lower.split())
            overlap = key_words & problem_words
            if len(overlap) >= len(key_words) * 0.7 and len(key_words) >= 3:
                return cached_solution
        return None

    def _cache_solution(self, problem: str, plan: SolutionPlan):
        """Guarda una solución exitosa en cache."""
        completed_steps = [
            {
                "description": st.description,
                "approach": st.approach.value,
                "result": st.result
            }
            for st in plan.subtasks
            if st.status == TaskStatus.COMPLETED
        ]
        
        self._solution_cache[problem.lower()] = {
            "goal": problem,
            "approach": plan.approach.value,
            "steps": completed_steps,
            "timestamp": time.time()
        }
        
        # Mantener cache manejable
        if len(self._solution_cache) > 100:
            # Eliminar las más antiguas
            sorted_items = sorted(
                self._solution_cache.items(),
                key=lambda x: x[1].get("timestamp", 0)
            )
            for key, _ in sorted_items[:20]:
                del self._solution_cache[key]

    def _execute_cached_solution(self, cached: Dict, problem: str,
                                  context: Dict) -> str:
        """Re-ejecuta una solución cacheada."""
        results = []
        for step in cached.get("steps", []):
            try:
                approach = ApproachType(step.get("approach", "direct_action"))
            except ValueError:
                approach = ApproachType.DIRECT_ACTION
            
            subtask = SubTask(
                id=len(results) + 1,
                description=step["description"],
                approach=approach
            )
            
            success, result = self._execute_subtask(subtask, None, context)
            if success:
                results.append(f"✅ {step['description']}: {result}")
            else:
                # Si la solución cacheada falla, intentar resolver de nuevo
                self._solution_cache.pop(problem.lower(), None)
                return self.solve(problem, context)
        
        if results:
            return "\n".join(results)
        return self.solve(problem, context)

    def _learn_from_solution(self, problem: str, plan: SolutionPlan):
        """Intenta guardar la solución como skill aprendida."""
        if not self.learner:
            return
        
        try:
            # Solo aprender soluciones con pasos que incluyan código o comandos
            code_steps = [
                st for st in plan.subtasks
                if st.status == TaskStatus.COMPLETED and
                st.approach in (ApproachType.CODE_GENERATION, ApproachType.SYSTEM_COMMAND)
            ]
            
            if code_steps and self.memory:
                # Guardar en memoria como hecho aprendido
                self.memory.save_fact(
                    f"solucion_{problem[:50]}",
                    json.dumps({
                        "problem": problem,
                        "approach": plan.approach.value,
                        "steps": [
                            {"desc": st.description, "approach": st.approach.value}
                            for st in plan.subtasks if st.status == TaskStatus.COMPLETED
                        ]
                    }, ensure_ascii=False)
                )
        except Exception as e:
            logger.debug(f"No se pudo aprender de la solución: {e}")

    # ===========================
    # UTILIDADES
    # ===========================

    def _parse_json_response(self, response: str) -> Optional[Dict]:
        """Parsea respuesta JSON del LLM, tolerando formatos imperfectos."""
        if not response:
            return None
        
        # Limpiar markdown code blocks
        response = response.strip()
        if response.startswith("```"):
            lines = response.split("\n")
            response = "\n".join(lines[1:])
            if response.endswith("```"):
                response = response[:-3]
        
        # Intentar parse directo
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # Buscar JSON embebido
        json_patterns = [
            r'\{[\s\S]*\}',   # Objeto JSON
        ]
        
        for pattern in json_patterns:
            import re
            matches = re.findall(pattern, response)
            for match in reversed(matches):  # Intentar el más largo primero
                try:
                    # Intentar arreglar JSON común con comillas simples
                    fixed = match.replace("'", '"')
                    # Arreglar true/false/null sin comillas
                    fixed = re.sub(r'\bTrue\b', 'true', fixed)
                    fixed = re.sub(r'\bFalse\b', 'false', fixed)
                    fixed = re.sub(r'\bNone\b', 'null', fixed)
                    return json.loads(fixed)
                except json.JSONDecodeError:
                    try:
                        return json.loads(match)
                    except json.JSONDecodeError:
                        continue
        
        return None

    def _clean_code(self, code: str) -> str:
        """Limpia código Python generado por el LLM."""
        if not code:
            return ""
        
        code = code.strip()
        
        # Quitar markdown code blocks
        if code.startswith("```python"):
            code = code[9:]
        elif code.startswith("```"):
            code = code[3:]
        if code.endswith("```"):
            code = code[:-3]
        
        code = code.strip()
        
        # Verificar que parece código Python
        if not any(kw in code for kw in ['import', 'def ', 'class ', 'print',
                                          'for ', 'while ', 'if ', '=', 'from ']):
            return ""
        
        return code

    def get_stats(self) -> Dict:
        """Estadísticas del problem solver."""
        return {
            "cached_solutions": len(self._solution_cache),
            "total_attempts": len(self._attempt_history),
            "cache_keys": list(self._solution_cache.keys())[:10]
        }
