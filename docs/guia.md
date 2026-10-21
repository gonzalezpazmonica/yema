# Guía de uso

## 1. Instalar

```bash
git clone https://github.com/gonzalezpazmonica/yema.git ~/yema && cd ~/yema
mkdir -p ~/.yema/{contratos/borradores,evidencia,memoria,buzon/entrada,buzon/salida,casa,aprobaciones} && chmod 700 ~/.yema
mkdir -p ~/.local/bin && ln -s ~/yema/bin/yema ~/.local/bin/yema
python3 -m unittest discover -s pruebas
yema cuidado
```

Carpetas de trabajo: Yema lee sin preguntar (con sus órdenes de lectura validadas) dentro de su proyecto, su estado privado y las carpetas que declares en `additionalDirectories` de `.claude/settings.local.json` (o en `YEMA_CARPETAS`, separadas por `:`). Fuera de ahí, pregunta el arnés.

Cúpulas (opcional): define `SAVIA_VAULTS_NODE`, `SAVIA_VAULTS_DIR` y `SAVIA_VAULTS_DOMES` si no usas las rutas por defecto de `.mcp.json`. Las cúpulas que puede leer sin contrato están en `gobierno/politica.json` (`cupulas_lectura`).

## 2. Primera conversación

Abre el arnés en la carpeta de Yema (`claude`). Ella arranca sin contrato: puede leer, investigar y proponer. Prueba:

- «Yema, preséntate y dime qué puedes hacer ahora mismo.»
- «¿Cómo está la casa?»
- «Lee el README de ~/mi-proyecto y dime qué harías primero.»

## 3. Primer contrato

1. Pide algo que cambie cosas: «arregla los tests rotos de ~/mi-proyecto».
2. Yema te enseña un borrador en lenguaje llano, con su huella. Pregunta lo que quieras: «¿por qué necesitas red?», «quita el push».
3. Cuando te guste, di «sí». Aparece el diálogo de permisos del arnés con el resumen: compruébalo y permite.
4. Yema trabaja. Puedes seguir hablando con ella mientras tanto.

En tu terminal también puedes aprobar: `yema resumen C-0001` y `yema aprobar C-0001 <huella>`.

## 4. Día a día

| Quieres… | Dile… | O en la terminal |
|---|---|---|
| Saber qué hace | «¿cómo vas?» | `yema estado` |
| Ver el contrato | «enséñame el contrato» | `yema resumen <id>` |
| Ampliar el encargo | «añade X» (te propone una enmienda) | — |
| Parar | «para» / «revoca» | `yema revocar <id> --por <tú> --motivo …` |
| Comprobar lo hecho | «enséñame la evidencia» | `yema evidencia <id>` |
| Revisar la casa | «¿cómo está la casa?» | `yema cuidado` |
| Hacer copia | «haz copia» | `yema copia` |

## 5. Cerrar un contrato

Al terminar, Yema ejecuta las postcondiciones, pasa el contrato a `validando` y te entrega qué hizo, la evidencia, qué no hizo y qué tienes que decidir. Tú lo cierras (`yema transicion <id> cerrado --por <tú>` en tu terminal) o le pides que siga con una enmienda.

## 6. Si algo va mal

| Síntoma | Causa probable | Arreglo |
|---|---|---|
| «sin contrato activo» al pedir un cambio | No hay contrato vigente | Pide que te proponga uno |
| «orden no listada en el contrato» | Falta esa orden | Enmienda, o era un error de Yema |
| «la huella no casa» | El contrato cambió tras enseñártelo | Que te lo vuelva a enseñar |
| «el modo … no pregunta» | El arnés está en un modo sin diálogos | Cambia a modo normal o aprueba en tu terminal |
| «aprobar exige una persona» | No hubo diálogo ni terminal (o pasaron más de 5 min) | Repite la aprobación |
| «cadena ROTA» en la evidencia | Alguien tocó los recibos | Revisa `~/.yema/evidencia` y restaura de `~/.yema-copias` |
| La puerta bloquea todo con «puerta en error» | Falta `gobierno/politica.json` o es ilegible | Restaura el fichero desde el repo |

## 7. Restaurar el estado

```bash
ls ~/.yema-copias/
tar -xzf ~/.yema-copias/yema-estado-AAAAMMDD-HHMMSS.tar.gz -C /tmp/restauracion
# revisa y copia lo que necesites a ~/.yema
```
