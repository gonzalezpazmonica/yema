"""Órdenes concedidas aisladas por el kernel (Landlock): la puerta no ve dentro del proceso.

Réplica de L39: una orden autorizada (`python3 lee.py`) leía cualquier fichero del disco.
"""
import io
import json
import os
import shlex
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apoyo_test import AHORA, Entorno, aprobado, base, sellar  # noqa: E402
from nucleo import aislar, contrato, firma, puerta  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
AISLAR = RAIZ / "nucleo/aislar.py"
HAY_LANDLOCK = aislar.abi() >= 1
SECRETO = "no deberías verme"

LEE = ("import sys\ntry:\n    print(open(sys.argv[1]).read())\nexcept PermissionError as e:\n"
       "    print('EACCES', e.errno)\n    sys.exit(13)\n")
ESCRIBE = ("import sys\ntry:\n    open(sys.argv[1], 'w').write('x')\nexcept PermissionError as e:\n"
           "    print('EACCES', e.errno)\n    sys.exit(13)\n")


class Carpetas(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(os.path.realpath(self.tmp.name))
        self.ambito, self.fuera, self.extra = t / "ambito", t / "fuera", t / "extra"
        for d in (self.ambito, self.fuera, self.extra):
            d.mkdir()
        (self.ambito / "lee.py").write_text(LEE)
        (self.ambito / "escribe.py").write_text(ESCRIBE)
        (self.ambito / "dentro.txt").write_text("hola de dentro")
        (self.fuera / "secreto.txt").write_text(SECRETO)
        (self.extra / "dato.txt").write_text("dato de lectura")

    def tearDown(self):
        self.tmp.cleanup()

    def corre(self, *orden, lectura=(), extra=()):
        args = [sys.executable, str(AISLAR), "--raiz", str(self.ambito)]
        for p in lectura:
            args += ["--lee", str(p)]
        return subprocess.run(args + list(extra) + ["--", *orden], cwd=self.ambito, capture_output=True, text=True,
                              timeout=60)


@unittest.skipUnless(HAY_LANDLOCK, "el kernel no admite Landlock")
class TestLandlock(Carpetas):
    def test_dentro_del_ambito_funciona(self):
        r = self.corre(sys.executable, "lee.py", "dentro.txt")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("hola de dentro", r.stdout)

    def test_l39_script_concedido_no_lee_un_secreto_de_fuera(self):
        secreto = self.fuera / "secreto.txt"
        sin_aislar = subprocess.run([sys.executable, "lee.py", str(secreto)], cwd=self.ambito, capture_output=True,
                                    text=True)
        self.assertIn(SECRETO, sin_aislar.stdout)  # el hueco existe: sin aislar, lo lee
        for ruta in (str(secreto), "../fuera/secreto.txt"):
            r = self.corre(sys.executable, "lee.py", ruta)
            self.assertEqual(r.returncode, 13, r.stdout + r.stderr)
            self.assertIn("EACCES 13", r.stdout)
            self.assertNotIn(SECRETO, r.stdout + r.stderr)

    def test_un_enlace_dentro_del_ambito_no_saca_fuera(self):
        (self.ambito / "atajo.txt").symlink_to(self.fuera / "secreto.txt")
        r = self.corre(sys.executable, "lee.py", "atajo.txt")
        self.assertEqual(r.returncode, 13)
        self.assertNotIn(SECRETO, r.stdout + r.stderr)

    def test_los_hijos_heredan_el_encierro(self):
        r = self.corre("cat", str(self.fuera / "secreto.txt"))
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn(SECRETO, r.stdout + r.stderr)
        r = self.corre("ls", str(Path.home()))
        self.assertNotEqual(r.returncode, 0)

    def test_escribir_fuera_falla_y_dentro_funciona(self):
        r = self.corre(sys.executable, "escribe.py", str(self.fuera / "nuevo.txt"))
        self.assertEqual(r.returncode, 13, r.stdout + r.stderr)
        self.assertFalse((self.fuera / "nuevo.txt").exists())
        r = self.corre(sys.executable, "escribe.py", "nuevo.txt")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue((self.ambito / "nuevo.txt").exists())

    def test_carpeta_de_lectura_se_lee_pero_no_se_escribe(self):
        dato = str(self.extra / "dato.txt")
        self.assertEqual(self.corre(sys.executable, "lee.py", dato).returncode, 13)
        r = self.corre(sys.executable, "lee.py", dato, lectura=[self.extra])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("dato de lectura", r.stdout)
        r = self.corre(sys.executable, "escribe.py", dato, lectura=[self.extra])
        self.assertEqual(r.returncode, 13)
        self.assertEqual((self.extra / "dato.txt").read_text(), "dato de lectura")

    def test_tmp_propio_se_escribe_y_se_borra(self):
        (self.ambito / "tmp.py").write_text(
            "import os, tempfile\nd = tempfile.gettempdir()\nopen(os.path.join(d, 'x'), 'w').write('x')\nprint(d)\n")
        r = self.corre(sys.executable, "tmp.py")
        self.assertEqual(r.returncode, 0, r.stderr)
        tmp = r.stdout.strip()
        self.assertIn("yema-aislar-", tmp)
        self.assertFalse(os.path.exists(tmp))

    def test_asignaciones_delante_son_entorno(self):
        (self.ambito / "env.py").write_text("import os\nprint(os.environ['YEMA_X'])\n")
        r = self.corre("YEMA_X=hola", sys.executable, "env.py")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "hola")


class TestFalloCerrado(Carpetas):
    """Sin Landlock en el kernel (simulado), la orden no corre, salvo que el contrato lo declare."""

    def main(self, *args):
        err = io.StringIO()
        with redirect_stderr(err):
            rc = aislar.main(["--raiz", str(self.ambito), *args], version=0)
        return rc, err.getvalue()

    def test_sin_landlock_no_corre(self):
        marca = self.ambito / "marca"
        rc, err = self.main("--", "touch", str(marca))
        self.assertEqual(rc, 126)
        self.assertIn("Landlock", err)
        self.assertFalse(marca.exists())

    def test_sin_landlock_corre_solo_si_el_contrato_lo_declara(self):
        marca = self.ambito / "marca"
        rc, err = self.main("--sin-kernel-ejecuta", "--", "touch", str(marca))
        self.assertEqual(rc, 0, err)
        self.assertIn("SIN aislar", err)
        self.assertTrue(marca.exists())

    def test_abi_cero_si_la_llamada_falla(self):
        original = aislar._sys

        def falla(*_):
            raise OSError(38, "Function not implemented")
        aislar._sys = falla
        try:
            self.assertEqual(aislar.abi(), 0)
        finally:
            aislar._sys = original

    def test_preparar_no_crea_un_ruleset_vacio(self):
        with self.assertRaises(aislar.Rechazo):
            aislar.preparar([], [], 0)

    def test_opciones_desconocidas_o_sin_raiz(self):
        err = io.StringIO()
        with redirect_stderr(err):
            self.assertEqual(aislar.main(["--", "true"], version=0), 2)
            self.assertEqual(aislar.main(["--raiz", str(self.ambito), "--todo", "--", "true"], version=0), 2)


class TestContratoAislamiento(unittest.TestCase):
    def test_valor_desconocido_es_invalido(self):
        c = base("/tmp/x")
        c["ambito"]["aislamiento"] = "nunca"
        self.assertTrue(any("aislamiento" in e for e in contrato.errores(c)))
        c["ambito"]["aislamiento"] = "si_hay"
        self.assertEqual(contrato.errores(c), [])

    def test_resumen_dice_si_corre_sin_aislar(self):
        c = base("/tmp/x")
        self.assertIn("sin Landlock en el kernel, no corren", contrato.resumen(c))
        self.assertNotIn("SIN AISLAR", contrato.resumen(c))
        c["ambito"]["aislamiento"] = "si_hay"
        c["ambito"]["lectura"] = ["/opt/datos"]
        texto = contrato.resumen(c)
        self.assertIn("SIN AISLAR", texto)
        self.assertIn("/opt/datos", texto)


class TestPuertaEnvuelve(Entorno):
    def ev(self, cmd):
        return {"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": str(self.trabajo)}

    def test_la_orden_concedida_se_reescribe_aislada(self):
        self.activar(aprobado(self.trabajo))
        nueva = puerta.envoltorio(self.ev("python3 -m unittest"), self.yema, AHORA)
        toks = shlex.split(nueva)
        self.assertEqual(toks[:2], [sys.executable, str(self.yema / "nucleo/aislar.py")])
        self.assertEqual(toks[toks.index("--raiz") + 1], str(self.trabajo))
        self.assertEqual(toks[toks.index("--") + 1:], ["python3", "-m", "unittest"])
        self.assertNotIn("--sin-kernel-ejecuta", toks)

    def test_conserva_el_cd_y_pasa_lectura_y_si_hay(self):
        c = base(self.trabajo)
        c["ambito"]["lectura"] = ["/opt/datos"]
        c["ambito"]["aislamiento"] = "si_hay"
        self.activar(sellar(c))
        nueva = puerta.envoltorio(self.ev(f"cd {self.trabajo} && python3 -m unittest"), self.yema, AHORA)
        self.assertTrue(nueva.startswith(f"cd {self.trabajo} && "), nueva)
        toks = shlex.split(nueva.split("&&", 1)[1])
        self.assertEqual(toks[toks.index("--lee") + 1], "/opt/datos")
        self.assertIn("--sin-kernel-ejecuta", toks)

    def test_sin_contrato_no_hay_envoltorio(self):
        self.assertIsNone(puerta.envoltorio(self.ev("python3 -m unittest"), self.yema, AHORA))


class TestPorElHookReal(unittest.TestCase):
    """El aislamiento cableado de verdad: hook de .claude/settings.json → updatedInput → bash."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(os.path.realpath(self.tmp.name))
        self.estado, self.trabajo, self.fuera = t / "estado", t / "trabajo", t / "fuera"
        (self.estado / "contratos/borradores").mkdir(parents=True)
        self.trabajo.mkdir()
        self.fuera.mkdir()
        (self.trabajo / "lee.py").write_text(LEE)
        (self.fuera / "secreto.txt").write_text(SECRETO)
        ajustes = json.loads((RAIZ / ".claude/settings.json").read_text())
        self.orden = [h["command"] for g in ajustes["hooks"]["PreToolUse"] for h in g["hooks"]
                      if "puerta.py" in h["command"]][0]
        c = base(self.trabajo)
        c["autoridad"]["ordenes"] = ["python3", "git status"]
        c["autoridad"]["caduca"] = "2999-01-01T00:00:00+00:00"
        c = sellar(c)
        c["autoridad"]["aprobacion"]["politica"] = puerta.huella_politica(
            json.loads((RAIZ / "gobierno/politica.json").read_text()))
        c["autoridad"]["aprobacion"]["firma"] = firma.firmar(c, firma.clave(self.estado, crear=True))
        (self.estado / "contratos/C-0001.json").write_text(json.dumps(c))
        (self.estado / "contratos/ACTIVO").write_text("C-0001")
        self.env = {**os.environ, "CLAUDE_PROJECT_DIR": str(RAIZ), "YEMA_ESTADO": str(self.estado)}

    def tearDown(self):
        self.tmp.cleanup()

    def hook(self, cmd):
        ev = {"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": str(self.trabajo),
              "permission_mode": "default"}
        r = subprocess.run(self.orden, shell=True, input=json.dumps(ev), capture_output=True, text=True, env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)["hookSpecificOutput"]

    def test_ejecutar_sale_con_la_orden_aislada(self):
        salida = self.hook("python3 lee.py ../fuera/secreto.txt")
        self.assertEqual(salida["permissionDecision"], "allow")
        self.assertIn(str(AISLAR), salida["updatedInput"]["command"])

    def test_git_no_se_reescribe(self):
        salida = self.hook("git status")
        self.assertEqual(salida["permissionDecision"], "allow")
        self.assertNotIn("updatedInput", salida)

    @unittest.skipUnless(HAY_LANDLOCK, "el kernel no admite Landlock")
    def test_l39_de_punta_a_punta(self):
        for cmd in ("python3 lee.py ../fuera/secreto.txt", f"cd {self.trabajo} && python3 lee.py {self.fuera}/secreto.txt"):
            nueva = self.hook(cmd)["updatedInput"]["command"]
            r = subprocess.run(["bash", "-c", nueva], cwd=self.trabajo, capture_output=True, text=True, timeout=60)
            self.assertEqual(r.returncode, 13, r.stdout + r.stderr)
            self.assertNotIn(SECRETO, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
