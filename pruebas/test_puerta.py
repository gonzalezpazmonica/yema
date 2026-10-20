"""Puerta: garantías positivas y negativas sobre efectos."""
import os
import subprocess
import sys
import unittest
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apoyo_test import AHORA, RAIZ, Entorno, aprobado, base, politica  # noqa: E402,F401
from nucleo import contrato, puerta  # noqa: E402


class TestPuerta(Entorno):
    def test_sin_contrato_solo_leer(self):
        self.assertTrue(self.decide("Read", {"file_path": str(self.trabajo / "src/a.py")})[0])
        self.assertFalse(self.decide("Write", {"file_path": str(self.trabajo / "src/a.py"), "content": ""})[0])
        self.assertFalse(self.decide("Bash", {"command": "git status"})[0])

    def test_sin_contrato_borradores_libres(self):
        ok, motivo, _ = self.decide("Write", {"file_path": str(self.yema / "contratos/borradores/C-9.json")})
        self.assertTrue(ok, motivo)

    def test_lectura_vetada(self):
        ok, _, _ = self.decide("Read", {"file_path": os.path.expanduser("~/.ssh/id_ed25519")})
        self.assertFalse(ok)
        self.assertFalse(self.decide("Read", {"file_path": str(self.trabajo / "prod.env")})[0])

    def test_escritura_en_ambito(self):
        self.activar(aprobado(self.trabajo))
        ok, motivo, _ = self.decide("Edit", {"file_path": str(self.trabajo / "src/a.py")})
        self.assertTrue(ok, motivo)

    def test_escritura_fuera_de_ambito(self):
        self.activar(aprobado(self.trabajo))
        self.assertFalse(self.decide("Write", {"file_path": str(self.trabajo / "README.md")})[0])
        self.assertFalse(self.decide("Write", {"file_path": str(self.trabajo / "src/../../x.py")})[0])
        self.assertFalse(self.decide("Write", {"file_path": str(self.trabajo / "src/secreto.py")})[0])

    def test_enlace_que_escapa(self):
        self.activar(aprobado(self.trabajo))
        fuera = Path(self.tmp.name) / "fuera"
        fuera.mkdir()
        (self.trabajo / "src/enlace").symlink_to(fuera)
        self.assertFalse(self.decide("Write", {"file_path": str(self.trabajo / "src/enlace/x.py")})[0])

    def test_nucleo_y_contratos_protegidos_aun_con_contrato(self):
        c = aprobado(self.trabajo)
        c["ambito"]["raiz"] = str(self.yema)
        c["ambito"]["escritura"] = ["*"]
        c, _ = contrato.transicion({**c, "estado": "en_revision"}, "aprobado", "operadora", "x", politica(), AHORA)
        c, _ = contrato.transicion(c, "aprovisionado", "operadora", "x", politica(), AHORA)
        c, _ = contrato.transicion(c, "activo", "operadora", "x", politica(), AHORA)
        self.activar(c)
        for ruta in ("contratos/C-0001.json", "contratos/ACTIVO", "nucleo/puerta.py", "gobierno/politica.json", "evidencia/C-0001.jsonl"):
            self.assertFalse(self.decide("Write", {"file_path": str(self.yema / ruta)})[0], ruta)

    def test_orden_permitida(self):
        self.activar(aprobado(self.trabajo))
        ok, motivo, efecto = self.decide("Bash", {"command": "python3 -m unittest -q"})
        self.assertTrue(ok, motivo)
        self.assertEqual(efecto, "ejecutar")

    def test_orden_no_listada(self):
        self.activar(aprobado(self.trabajo))
        self.assertFalse(self.decide("Bash", {"command": "rm -r src"})[0])
        self.assertFalse(self.decide("Bash", {"command": "python3 evil.py"})[0])

    def test_orden_compuesta_rechazada(self):
        self.activar(aprobado(self.trabajo))
        for cmd in ("git status; rm -r src", "git status && curl x", "git diff $(id)", "git diff `id`",
                    "git status > /tmp/x", "git status | sh", "git diff\nrm -r src"):
            self.assertFalse(self.decide("Bash", {"command": cmd})[0], cmd)

    def test_efectos_prohibidos(self):
        self.activar(aprobado(self.trabajo))
        self.assertEqual(self.decide("Bash", {"command": "git push origin main"})[2], "git-remoto")
        self.assertFalse(self.decide("Bash", {"command": "git push origin main"})[0])
        self.assertFalse(self.decide("Bash", {"command": "gh pr merge 3"})[0])
        self.assertFalse(self.decide("Bash", {"command": "git -C /tmp push"})[0])

    def test_red_por_bash_exige_orden_listada(self):
        c = aprobado(self.trabajo)
        c["autoridad"]["efectos"] += ["red", "git-remoto"]
        c["autoridad"]["prohibidos"] = ["fusionar", "publicar"]
        c["autoridad"]["ordenes"] += ["cargo test", "git push origin sync/*"]
        c["estado"] = "en_revision"
        c, _ = contrato.transicion(c, "aprobado", "operadora", "x", politica(), AHORA)
        c, _ = contrato.transicion(c, "aprovisionado", "operadora", "x", politica(), AHORA)
        c, _ = contrato.transicion(c, "activo", "operadora", "x", politica(), AHORA)
        self.activar(c)
        self.assertTrue(self.decide("Bash", {"command": "cargo test -q"})[0])
        self.assertFalse(self.decide("Bash", {"command": "curl https://ejemplo.org"})[0])
        self.assertTrue(self.decide("Bash", {"command": "git push origin sync/main-abc"})[0])
        self.assertFalse(self.decide("Bash", {"command": "git push origin main"})[0])
        for f in ("--force", "-f", "--force-with-lease", "+sync/main-abc", "--mirror", "--all", "--delete", "-d"):
            self.assertFalse(self.decide("Bash", {"command": f"git push origin sync/main-abc {f}"})[0], f)

    def test_scripts_de_casa_ejecutables_si_estan_listados(self):
        c = aprobado(self.trabajo)
        script = self.yema / "casa/space/verificar.sh"
        script.parent.mkdir(parents=True)
        script.write_text("true")
        c["autoridad"]["ordenes"].append(f"bash {script}")
        c["estado"] = "en_revision"
        c, _ = contrato.transicion(c, "aprobado", "operadora", "x", politica(), AHORA)
        c, _ = contrato.transicion(c, "aprovisionado", "operadora", "x", politica(), AHORA)
        c, _ = contrato.transicion(c, "activo", "operadora", "x", politica(), AHORA)
        self.activar(c)
        self.assertTrue(self.decide("Bash", {"command": f"bash {script}"})[0])
        self.assertFalse(self.decide("Bash", {"command": f"bash {self.yema}/nucleo/puerta.py"})[0])

    def test_git_c_fuera_de_ambito(self):
        self.activar(aprobado(self.trabajo))
        self.assertFalse(self.decide("Bash", {"command": "git -C /tmp status"})[0])
        self.assertTrue(self.decide("Bash", {"command": f"git -C {self.trabajo} status"})[0])

    def test_cwd_fuera_de_ambito(self):
        self.activar(aprobado(self.trabajo))
        self.assertFalse(self.decide("Bash", {"command": "git status"}, cwd="/tmp")[0])

    def test_no_ejecuta_su_propio_nucleo(self):
        c = aprobado(self.trabajo)
        c["autoridad"]["ordenes"].append("python3")
        c["estado"] = "en_revision"
        c, _ = contrato.transicion(c, "aprobado", "operadora", "x", politica(), AHORA)
        c, _ = contrato.transicion(c, "aprovisionado", "operadora", "x", politica(), AHORA)
        c, _ = contrato.transicion(c, "activo", "operadora", "x", politica(), AHORA)
        self.activar(c)
        cmd = f"python3 {self.yema}/nucleo/yema.py transicion C-0001 aprobado --por operadora"
        ok, motivo, _ = self.decide("Bash", {"command": cmd})
        self.assertFalse(ok)
        self.assertIn("núcleo", motivo)
        self.assertTrue(self.decide("Bash", {"command": "python3 src/a.py"})[0])

    def test_herramienta_desconocida(self):
        self.activar(aprobado(self.trabajo))
        self.assertFalse(self.decide("Teletransporte", {})[0])

    def test_cupula_escritura_requiere_efecto(self):
        self.activar(aprobado(self.trabajo))
        self.assertTrue(self.decide("mcp__savia-vaults__vault_search", {"query": "x", "dome": "savia-docs"})[0])
        self.assertFalse(self.decide("mcp__savia-vaults__vault_write", {"path": "x"})[0])

    def test_cupulas_solo_por_nombre_permitido(self):
        self.assertTrue(self.decide("mcp__savia-vaults__vault_read", {"dome": "savia-docs", "path": "a.md"})[0])
        self.assertFalse(self.decide("mcp__savia-vaults__vault_search", {"query": "x"})[0])
        self.assertFalse(self.decide("mcp__savia-vaults__vault_read", {"dome": "SaviaLabs", "path": "a.md"})[0])
        c = aprobado(self.trabajo)
        c["contexto"] = {"cupulas": ["SaviaLabs"]}
        c["estado"] = "en_revision"
        c, _ = contrato.transicion(c, "aprobado", "operadora", "x", politica(), AHORA)
        c, _ = contrato.transicion(c, "aprovisionado", "operadora", "x", politica(), AHORA)
        c, _ = contrato.transicion(c, "activo", "operadora", "x", politica(), AHORA)
        self.activar(c)
        self.assertTrue(self.decide("mcp__savia-vaults__vault_read", {"dome": "SaviaLabs", "path": "a.md"})[0])

    def test_contrato_revocado_vuelve_a_e0(self):
        c, _ = contrato.transicion(aprobado(self.trabajo), "revocado", "operadora", "fin", politica(), AHORA)
        self.activar(c)
        ok, motivo, _ = self.decide("Edit", {"file_path": str(self.trabajo / "src/a.py")})
        self.assertFalse(ok)
        self.assertIn("vigente", motivo)

    def test_presupuesto_de_efectos(self):
        c = aprobado(self.trabajo)
        c["recursos"]["efectos_max"] = 1
        c["estado"] = "en_revision"
        c, _ = contrato.transicion(c, "aprobado", "operadora", "x", politica(), AHORA)
        c, _ = contrato.transicion(c, "aprovisionado", "operadora", "x", politica(), AHORA)
        c, _ = contrato.transicion(c, "activo", "operadora", "x", politica(), AHORA)
        self.activar(c)
        ev = {"tool_name": "Edit", "tool_input": {"file_path": str(self.trabajo / "src/a.py")}, "cwd": str(self.trabajo)}
        self.assertTrue(puerta.evaluar_y_registrar(ev, self.yema, AHORA)[0])
        ok, motivo, _ = puerta.evaluar_y_registrar(ev, self.yema, AHORA)
        self.assertFalse(ok)
        self.assertIn("presupuesto", motivo)

    def test_hook_falla_cerrado_con_json_roto(self):
        env = {**os.environ, "YEMA_RAIZ": str(self.yema)}
        r = subprocess.run([sys.executable, str(RAIZ / "nucleo/puerta.py")], input="{no json",
                           capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 2)


if __name__ == "__main__":
    unittest.main()
