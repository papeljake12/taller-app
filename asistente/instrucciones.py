"""Las instrucciones fijas del asistente (el "system prompt").

Carril B (T29). Texto fijo: sin fecha, sin taller y sin nada que cambie entre preguntas o
entre talleres, para que Claude lo guarde en caché. La fecha, el taller y la pantalla van en
el mensaje `role: "system"` de cada pregunta (asistente/conversacion.py).
"""

INSTRUCCIONES = ""
