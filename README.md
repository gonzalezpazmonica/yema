# Yema

Ejecutora de ciclos largos gobernada por contratos. Hija de Savia.

Una especificación dice qué se espera. Un contrato dice qué está autorizado a ocurrir, por quién, con qué límites y hasta cuándo.
Yema trabaja horas dentro de un contrato aprobado por una persona, y una puerta fuera del modelo hace cumplir sus límites.

## Empezar

```bash
python3 -m unittest discover -s pruebas      # núcleo: contrato, puerta, evidencia, CLI
python3 nucleo/yema.py estado                 # contrato activo
python3 nucleo/yema.py validar ejemplos/contrato-ejemplo.json
```

Abrir Claude Code en esta carpeta carga `AGENTS.md`, la puerta (`.claude/settings.json`) y las cúpulas (`.mcp.json`).
Sin contrato activo, Yema solo lee y propone.

Antes de la primera sesión: `mkdir -p ~/.yema/{contratos/borradores,evidencia,memoria,buzon/entrada,buzon/salida,casa} && chmod 700 ~/.yema`.

## Aprobar un contrato (lo hace una persona, en su terminal)

```bash
python3 nucleo/yema.py admitir ~/.yema/contratos/borradores/C-0001.json
python3 nucleo/yema.py transicion C-0001 en_revision --por operadora --motivo "revisado"
python3 nucleo/yema.py transicion C-0001 aprobado --por operadora --motivo "aprobado"
python3 nucleo/yema.py transicion C-0001 aprovisionado --por operadora
python3 nucleo/yema.py activar C-0001 --por operadora
python3 nucleo/yema.py revocar C-0001 --por operadora --motivo "fin"     # en cualquier momento
```

## Mapa

| Fichero | Qué |
|---|---|
| `AGENTS.md` | Arranque (lo único que se carga siempre) |
| `ALMA.md` | Nombre, linaje, valores, voz |
| `docs/gobernanza.md` | Niveles E0-E4, contrato, ciclo de vida, garantías y límites |
| `docs/arquitectura.md` | Piezas, presupuesto de contexto, ciclos largos, arneses |
| `docs/criterio.md` | Cómo decide, cuándo para, lecciones heredadas |
| `docs/capacidades.md` | Qué sabe hacer y qué nunca |
| `docs/comunicacion.md` | Persona, Savia (buzón) y cúpulas |
| `docs/casa-space.md` | Savia Space: reglas de la casa y destino de Yema |
| `docs/poda.md` | Qué heredó de Savia y con qué criterio |
| `ROADMAP.md` | Fases con criterios de salida y de abandono |
| `nucleo/` | Código del núcleo (Python estándar, sin dependencias) |
| `ejemplos/` | Contrato de ejemplo |
| `~/.yema/` | Estado privado y local: contratos reales, evidencia, memoria, buzón (nunca en el repo) |
