"""Leer también está acotado: fuera del ámbito y de las carpetas conocidas, la puerta deniega.

Hallazgo de L39 M3 (H3): con un contrato E2, Yema leyó un secreto fuera de su ámbito y lo devolvió
en su resumen. El ámbito acotaba la escritura y las órdenes, pero no la lectura.
"""
import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apoyo_test import Entorno, aprobado, base, sellar  # noqa: E402
from nucleo import contrato  # noqa: E402


class Base(Entorno):
    def setUp(self):
        super().setUp()
        os.environ.pop("YEMA_CARPETAS", None)
        self.fuera = Path(self.tmp.name) / "fuera"
        self.fuera.mkdir()
        self.secreto = self.fuera / "secreto.txt"
        self.secreto.write_text("TOKEN-SINTETICO\n")
        (self.trabajo / "src/a.py").write_text("x = '/api/v1'\n")
        (self.yema / "nucleo/a.py").write_text("y = 1\n")

    def leer(self, herramienta, entrada, cwd=None):
        return self.decide(herramienta, entrada, cwd=cwd)[0]

    def b(self, cmd, cwd=None):
        return self.decide("Bash", {"command": cmd}, cwd=cwd)


class TestConContrato(Base):
    def setUp(self):
        super().setUp()
        self.activar(aprobado(self.trabajo))

    # Negativos: lo que en L39 se escapó, por cada vía.
    def test_read_ruta_absoluta_fuera(self):
        ok, motivo, _ = self.decide("Read", {"file_path": str(self.secreto)})
        self.assertFalse(ok)
        self.assertIn("lectura fuera del ámbito", motivo)
        self.assertIn("ambito.lectura", motivo)  # dice qué hacer

    def test_read_con_puntos(self):
        self.assertFalse(self.leer("Read", {"file_path": "../fuera/secreto.txt"}))

    def test_read_por_enlace_que_sale(self):
        (self.trabajo / "src/enlace.txt").symlink_to(self.secreto)
        self.assertFalse(self.leer("Read", {"file_path": str(self.trabajo / "src/enlace.txt")}))

    def test_grep_y_glob_hacia_fuera(self):
        self.assertFalse(self.leer("Grep", {"pattern": "TOKEN", "path": str(self.fuera)}))
        self.assertFalse(self.leer("Glob", {"pattern": "*", "path": str(self.fuera)}))
        self.assertFalse(self.leer("Glob", {"pattern": "../fuera/*"}))
        self.assertFalse(self.leer("Glob", {"pattern": "src/../../fuera/*"}))
        self.assertFalse(self.leer("Glob", {"pattern": str(self.fuera) + "/*"}))
        self.assertFalse(self.leer("Glob", {"pattern": "{" + str(self.fuera) + ",src}/*"}))
        self.assertFalse(self.leer("Glob", {"pattern": "/*"}))

    def test_grep_sobre_carpeta_con_enlace_que_sale(self):
        (self.trabajo / "src/salida").symlink_to(self.fuera)
        ok, motivo, _ = self.decide("Grep", {"pattern": "TOKEN", "path": str(self.trabajo)})
        self.assertFalse(ok)
        self.assertIn("enlace", motivo)

    def test_bash_lectores_hacia_fuera(self):
        for cmd in (f"cat {self.secreto}", "cat ../fuera/secreto.txt", f"head -n 3 {self.secreto}",
                    f"grep TOKEN {self.secreto}", f"tail {self.secreto} 2>/dev/null",
                    f"ls {self.fuera}", f"cd {self.fuera} && cat secreto.txt", "ls src | grep x ../fuera/secreto.txt",
                    f"diff src/a.py {self.secreto}", "cat src/a.py && cat ../fuera/secreto.txt"):
            with self.subTest(cmd=cmd):
                ok, motivo, _ = self.b(cmd)
                self.assertFalse(ok)
                self.assertIn("fuera", motivo)

    def test_llaves_y_comodines_hacia_fuera(self):
        (self.trabajo / "src/enlace.txt").symlink_to(self.secreto)
        for cmd in ("cat {src/a.py,../fuera/secreto.txt}", "cat src/{a.py,../../fuera/secreto.txt}",
                    "cat src/enl*", "head src/*.txt", "cat ../fue?a/*"):
            with self.subTest(cmd=cmd):
                self.assertFalse(self.b(cmd)[0])
        self.assertTrue(self.b("cat src/{a,b}.py")[0])
        self.assertTrue(self.b("cat src/*.py")[0])

    def test_grep_recursivo_hacia_fuera(self):
        for cmd in (f"grep -rn TOKEN {self.fuera}", "grep -r TOKEN ..", f"grep -rl TOKEN {self.tmp.name}"):
            with self.subTest(cmd=cmd):
                self.assertFalse(self.b(cmd)[0])

    def test_grep_que_sigue_enlaces_hacia_fuera(self):
        (self.trabajo / "src/salida").symlink_to(self.fuera)
        self.assertFalse(self.b("grep -R TOKEN .")[0])
        self.assertFalse(self.b("grep -Rn TOKEN src")[0])
        self.assertFalse(self.b("grep --dereference-recursive TOKEN .")[0])

    def test_aunque_el_contrato_liste_grep_como_orden(self):
        c = aprobado(self.trabajo)
        c["autoridad"]["ordenes"].append("grep")
        self.activar(sellar(c))
        self.assertFalse(self.b(f"grep -r TOKEN {self.fuera}")[0])

    # Positivos: dentro del ámbito se sigue trabajando igual.
    def test_dentro_del_ambito(self):
        self.assertTrue(self.leer("Read", {"file_path": str(self.trabajo / "src/a.py")}))
        self.assertTrue(self.leer("Read", {"file_path": "src/a.py"}))
        self.assertTrue(self.leer("Grep", {"pattern": "x", "path": str(self.trabajo)}))
        self.assertTrue(self.leer("Grep", {"pattern": "x"}))
        self.assertTrue(self.leer("Glob", {"pattern": "src/**/*.py"}))
        self.assertTrue(self.leer("Glob", {"pattern": str(self.trabajo) + "/src/*"}))
        for cmd in ("cat src/a.py", "head -n 5 src/a.py", "grep -rn x .", "grep -rn x src", "ls",
                    "grep '/api/v1' src/a.py", "grep -e /api src/a.py", "ls src | grep a", "cd src && cat a.py",
                    "find . -name '*.py'", "wc -l src/a.py"):
            with self.subTest(cmd=cmd):
                self.assertTrue(self.b(cmd)[0])

    def test_grep_r_no_sigue_enlaces_y_se_permite(self):
        (self.trabajo / "src/salida").symlink_to(self.fuera)
        self.assertTrue(self.b("grep -rn x .")[0])

    def test_enlace_que_apunta_dentro(self):
        (self.trabajo / "src/b.py").symlink_to(self.trabajo / "src/a.py")
        self.assertTrue(self.leer("Read", {"file_path": str(self.trabajo / "src/b.py")}))
        self.assertTrue(self.leer("Grep", {"pattern": "x", "path": str(self.trabajo)}))

    def test_carpetas_conocidas_con_contrato(self):
        self.assertTrue(self.leer("Read", {"file_path": str(self.yema / "nucleo/a.py")}))

    def test_lectura_declarada_en_el_contrato(self):
        c = aprobado(self.trabajo)
        c["ambito"]["lectura"] = [str(self.fuera)]
        self.activar(sellar(c))
        self.assertTrue(self.leer("Read", {"file_path": str(self.secreto)}))
        self.assertTrue(self.leer("Grep", {"pattern": "TOKEN", "path": str(self.fuera)}))
        self.assertTrue(self.b(f"cat {self.secreto}")[0])
        self.assertTrue(self.b(f"grep -rn TOKEN {self.fuera}")[0])
        hermana = Path(self.tmp.name) / "otra"
        hermana.mkdir()
        self.assertFalse(self.leer("Read", {"file_path": str(hermana)}))

    def test_lo_vetado_sigue_vetado_aunque_se_declare(self):
        (self.fuera / "x.env").write_text("A=1\n")
        c = aprobado(self.trabajo)
        c["ambito"]["lectura"] = [str(self.fuera)]
        self.activar(sellar(c))
        self.assertFalse(self.leer("Read", {"file_path": str(self.fuera / "x.env")}))
        self.assertFalse(self.b("cat {src/a.py,../fuera/x.env}")[0])  # tampoco escondido en unas llaves


class TestSinContrato(Base):
    def test_fuera_de_las_conocidas_se_deniega(self):
        self.assertFalse(self.leer("Read", {"file_path": str(self.secreto)}, cwd=self.yema))
        self.assertFalse(self.leer("Read", {"file_path": "../fuera/secreto.txt"}, cwd=self.yema))
        self.assertFalse(self.leer("Grep", {"pattern": "TOKEN", "path": str(self.fuera)}, cwd=self.yema))
        self.assertFalse(self.leer("Glob", {"pattern": "../fuera/*"}, cwd=self.yema))
        self.assertFalse(self.b(f"cat {self.secreto}", cwd=self.yema)[0])
        self.assertFalse(self.b(f"grep -rn TOKEN {self.fuera}", cwd=self.yema)[0])

    def test_la_carpeta_de_trabajo_no_conocida_tampoco(self):
        self.assertFalse(self.leer("Read", {"file_path": str(self.trabajo / "src/a.py")}))
        self.assertFalse(self.leer("Grep", {"pattern": "x"}))

    def test_carpetas_conocidas(self):
        self.assertTrue(self.leer("Read", {"file_path": str(self.yema / "nucleo/a.py")}, cwd=self.yema))
        self.assertTrue(self.leer("Grep", {"pattern": "y", "path": str(self.yema / "nucleo")}, cwd=self.yema))
        self.assertTrue(self.b("cat nucleo/a.py", cwd=self.yema)[0])
        self.assertTrue(self.b("grep -rn y nucleo", cwd=self.yema)[0])

    def test_carpeta_declarada_por_la_persona(self):
        os.environ["YEMA_CARPETAS"] = str(self.trabajo)
        try:
            self.assertTrue(self.leer("Read", {"file_path": str(self.trabajo / "src/a.py")}))
            self.assertTrue(self.b("cat src/a.py")[0])
            local = self.yema / ".claude"
            local.mkdir()
            (local / "settings.local.json").write_text(json.dumps({"permissions": {"additionalDirectories": [str(self.fuera)]}}))
            self.assertTrue(self.leer("Read", {"file_path": str(self.secreto)}))
        finally:
            os.environ.pop("YEMA_CARPETAS", None)


class TestEsquema(unittest.TestCase):
    def setUp(self):
        self.c = base(Path("/tmp/trabajo"))

    def test_lectura_debe_ser_absoluta_y_no_la_raiz(self):
        for malo in (["relativa"], ["/"], ["//"], "/tmp", [3]):
            with self.subTest(malo=malo):
                c = {**self.c, "ambito": {**self.c["ambito"], "lectura": malo}}
                self.assertTrue(any("ambito.lectura" in e for e in contrato.errores(c)))
        c = {**self.c, "ambito": {**self.c["ambito"], "lectura": ["/tmp/docs"]}}
        self.assertEqual(contrato.errores(c), [])

    def test_el_resumen_lo_ensena(self):
        c = {**self.c, "ambito": {**self.c["ambito"], "lectura": ["/tmp/docs"]}}
        self.assertIn("Puede leer además: /tmp/docs", contrato.resumen(c))
        self.assertNotIn("Puede leer además", contrato.resumen(self.c))


if __name__ == "__main__":
    unittest.main()
