---
name: relevo-savia
description: Hacer algo que hoy hace Savia (sprints, backlog, Azure DevOps o Jira, informes, digestión de documentos, specs, roadmap) usando sus scripts como herramienta dentro de un contrato. Úsala cuando la persona pida trabajo de PM o algo que Yema aún no hace de forma nativa.
---

# Relevo de Savia

1. Mira `docs/relevo.md`: ¿la capacidad es nativa, con Savia como herramienta o pendiente?
2. Busca cómo lo hace Savia con `yema savia <palabras>`: devuelve las skills, comandos y scripts de su mapa de capacidades con la ruta. Lee la que encaje; no ejecutes nada todavía. Si necesitas contexto, la cúpula `savia-docs` (N2, con contrato).
3. Redacta un contrato (skill `contrato`) que liste las órdenes exactas de Savia que harán falta, por ejemplo `bash /home/<persona>/savia/scripts/sprint-status.sh`, con `ambito.raiz` en el repo de Savia o en el del proyecto, y el efecto `red` solo si el script habla con Azure DevOps o Jira.
4. Reglas de Savia que siguen valiendo dentro del contrato: el token de acceso siempre desde su fichero, nunca escrito; confirmar antes de escribir en Azure DevOps (es E3: efecto aparte); filtrar por iteración en las consultas.
5. Al terminar, anota en `~/.yema/memoria/relevo.md` tokens, tiempo y lo que fue incómodo: es la línea base para decidir si la capacidad pasa a nativa.
