import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext

# ==============================================================
#  IMPORTACIONES DEL BACKEND
# ==============================================================
from base import Estado, Transicion, EPSILON, reiniciar_contador_estados
from afn import AFN
from afd import AFD, EdoAFD
from AnLex import AnalizadorLexico
from AnSint import AnalizadorSintactico
from CalculadoraAS import AccSemCalc
from GramLL1 import SimbGram, ElemArrGram, Gramatica, TablaLL1
from AnalizadorLL1 import AnalizadorLL1
from AnalizadorLR0 import AnalizadorLR0

if not hasattr(Gramatica, "EPSILON"):
    Gramatica.EPSILON = EPSILON


# ==============================================================
#  MEMORIA GLOBAL DE AUTÓMATAS
# ==============================================================
afns_en_memoria = {}   # {id_str: AFN}
afds_en_memoria = {}   # {id_str: AFD}


# ==============================================================
#  MOTOR DE DESCENSO RECURSIVO: EXPRESIÓN REGULAR -> AFN
# ==============================================================
class DescRecER_AFN:
    """
    Analizador sintáctico por descenso recursivo que convierte una
    expresión regular (e.r.) en un AFN usando las operaciones de Thompson.
    Gramática sin recursividad por la izquierda:
        E  -> T E'
        E' -> '|' T E' | ε
        T  -> C T'
        T' -> '&' C T' | C T' | ε
        C  -> F C'
        C' -> '*' C' | '+' C' | '?' C' | ε
        F  -> '(' E ')' | '[' Rango ']' | simb
    """

    def __init__(self, expr: str):
        self.expr = expr
        self.pos = 0
        self.traza = []

    def _peek(self):
        while self.pos < len(self.expr) and self.expr[self.pos] in ("\n", "\r"):
            self.pos += 1
        if self.pos >= len(self.expr):
            return None
        return self.expr[self.pos]

    def _consume(self):
        ch = self.expr[self.pos]
        self.pos += 1
        return ch

    def analizar(self) -> AFN:
        if not self.expr:
            raise ValueError("La expresión regular está vacía.")
        afn_res = self.E()
        if self._peek() is not None:
            raise ValueError(f"Símbolo inesperado '{self._peek()}' en la posición {self.pos}.")
        return afn_res

    def E(self) -> AFN:
        self.traza.append("E -> T E'")
        f = self.T()
        return self.Ep(f)

    def Ep(self, f1: AFN) -> AFN:
        if self._peek() == "|":
            self._consume()
            self.traza.append("E' -> '|' T E'  [UnirAFN]")
            f2 = self.T()
            f1.UnirAFN(f2)
            return self.Ep(f1)
        self.traza.append("E' -> ε")
        return f1

    def T(self) -> AFN:
        self.traza.append("T -> C T'")
        f = self.C()
        return self.Tp(f)

    def Tp(self, f1: AFN) -> AFN:
        nxt = self._peek()
        if nxt == "&":
            self._consume()
            self.traza.append("T' -> '&' C T'  [Concatenar]")
            f2 = self.C()
            f1.Concatenar(f2)
            return self.Tp(f1)
        if nxt is not None and nxt not in ("|", ")", "*", "+", "?"):
            self.traza.append("T' -> C T'  [Concatenar implícito]")
            f2 = self.C()
            f1.Concatenar(f2)
            return self.Tp(f1)
        self.traza.append("T' -> ε")
        return f1

    def C(self) -> AFN:
        self.traza.append("C -> F C'")
        f = self.F()
        return self.Cp(f)

    def Cp(self, f1: AFN) -> AFN:
        nxt = self._peek()
        if nxt == "*":
            self._consume()
            self.traza.append("C' -> '*' C'  [cerraduraKleen]")
            f1.cerraduraKleen()
            return self.Cp(f1)
        elif nxt == "+":
            self._consume()
            self.traza.append("C' -> '+' C'  [cerraduraPos]")
            f1.cerraduraPos()
            return self.Cp(f1)
        elif nxt == "?":
            self._consume()
            self.traza.append("C' -> '?' C'  [Opcional]")
            f1.Opcional()
            return self.Cp(f1)
        self.traza.append("C' -> ε")
        return f1

    def F(self) -> AFN:
        nxt = self._peek()
        if nxt is None:
            raise ValueError("Fin inesperado de la expresión regular; se esperaba un operando.")

        if nxt == "(":
            self._consume()
            self.traza.append("F -> '(' E ')'")
            f = self.E()
            if self._peek() != ")":
                raise ValueError(f"Se esperaba ')' de cierre en la posición {self.pos}.")
            self._consume()
            return f

        if nxt == "[":
            return self._parsear_corchetes()

        if nxt == "'":
            self._consume()
            if self.pos >= len(self.expr):
                raise ValueError("Comilla simple sin cerrar.")
            ch = self._consume()
            if ch == "\\" and self.pos < len(self.expr):
                esc = self._consume()
                ch = {"t": "\t", "n": "\n"}.get(esc, esc)
            if self._peek() != "'":
                raise ValueError("Se esperaba comilla simple de cierre (').")
            self._consume()
            self.traza.append(f"F -> '{ch}'  [CrearBasico('{ch}')]")
            return AFN().CrearBasico(ch)

        if nxt == "\\":
            self._consume()
            if self.pos >= len(self.expr):
                raise ValueError("Carácter de escape incompleto al final de la expresión.")
            esc = self._consume()
            ch = {"t": "\t", "n": "\n", "s": " "}.get(esc, esc)
            self.traza.append(f"F -> \\{esc}  [CrearBasico({repr(ch)})]")
            return AFN().CrearBasico(ch)

        if nxt in ("|", ")", "*", "+", "?", "&"):
            raise ValueError(f"Operador '{nxt}' sin operando izquierdo en la posición {self.pos}.")

        ch = self._consume()
        self.traza.append(f"F -> {repr(ch)}  [CrearBasico({repr(ch)})]")
        return AFN().CrearBasico(ch)

    def _parsear_corchetes(self) -> AFN:
        self._consume()
        contenido = ""
        while self.pos < len(self.expr) and self.expr[self.pos] != "]":
            contenido += self._consume()
        if self._peek() != "]":
            raise ValueError("Corchete '[' sin cerrar.")
        self._consume()

        if not contenido:
            raise ValueError("Clase de caracteres '[]' vacía.")

        partes = []
        i = 0
        while i < len(contenido):
            if i + 2 < len(contenido) and contenido[i + 1] == "-":
                c1, c2 = contenido[i], contenido[i + 2]
                partes.append(AFN().CrearBasico(c1, c2))
                self.traza.append(f"F -> [{c1}-{c2}]  [CrearBasico('{c1}', '{c2}')]")
                i += 3
            else:
                c1 = contenido[i]
                partes.append(AFN().CrearBasico(c1))
                self.traza.append(f"F -> [{c1}]  [CrearBasico('{c1}')]")
                i += 1

        afn_clase = partes[0]
        for extra in partes[1:]:
            afn_clase.UnirAFN(extra)
        return afn_clase


# ==============================================================
#  AUXILIARES PARA GRAMÁTICAS LL(1) Y LR(0)
# ==============================================================
def construir_gramatica_desde_texto(texto: str) -> Gramatica:
    texto_limpio = texto.replace(";", "\n")
    lineas = [ln.strip() for ln in texto_limpio.splitlines() if ln.strip() and not ln.strip().startswith("#")]

    if not lineas:
        raise ValueError("No se ingresaron reglas gramaticales.")

    producciones_crudas = []
    no_terminales_orden = []

    for ln in lineas:
        if "->" not in ln:
            raise ValueError(f"Formato inválido en regla (falta '->'): {ln}")
        izq_str, der_total = ln.split("->", 1)
        izq = izq_str.strip()
        if not izq:
            raise ValueError(f"Lado izquierdo vacío en regla: {ln}")
        if izq not in no_terminales_orden:
            no_terminales_orden.append(izq)

        alternativas = [alt.strip() for alt in der_total.split("|")]
        for alt in alternativas:
            if not alt:
                raise ValueError(f"Producción vacía después de '|' en: {ln}")
            tokens_der = alt.split()
            producciones_crudas.append((izq, tokens_der))

    vn_set = set(no_terminales_orden)
    terminales_orden = []
    arr_reglas = []

    for izq, tokens_der in producciones_crudas:
        simb_izq = SimbGram(izq, 0, False)
        lista_der = []
        for tok in tokens_der:
            if tok in ("EPSILON", "ε", "epsilon"):
                lista_der.append(SimbGram(EPSILON, -1, True))
            elif tok in vn_set:
                lista_der.append(SimbGram(tok, 0, False))
            else:
                lista_der.append(SimbGram(tok, 0, True))
                if tok not in terminales_orden and tok != "$":
                    terminales_orden.append(tok)
        arr_reglas.append(ElemArrGram(simb_izq, lista_der))

    g = Gramatica()
    g.ArrReglas = arr_reglas
    g.NumReglas = len(arr_reglas)
    g.no_terminales = no_terminales_orden
    g.terminales = terminales_orden

    def _first_secuencia_seguro(secuencia: list) -> set:
        nodos = [
            SimbGram(sim, -1 if sim == EPSILON else 0, sim not in vn_set)
            for sim in secuencia
        ]
        return {s.Simbolo for s in g.First(nodos)}

    g.first_secuencia = _first_secuencia_seguro
    return g


def construir_automatas_desde_patrones(patrones_tokens: list):
    """
    Construye el AFN global con transiciones EPSILON hacia cada patrón
    (er_o_afn, token) y lo convierte a AFD. Retorna (afn_global, afd).
    """
    reiniciar_contador_estados()
    afn_global = AFN()
    edo_ini = Estado()
    afn_global.EdoIni = edo_ini
    afn_global.EdosAFN.add(edo_ini)

    for item, token in patrones_tokens:
        if isinstance(item, str):
            afn_pat = DescRecER_AFN(item).analizar()
        else:
            afn_pat = item

        for edo in afn_pat.EdosAcept:
            edo.EdoAcept = True
            edo.Token = token

        edo_ini.Transiciones.add(Transicion(EPSILON, afn_pat.EdoIni))
        afn_global.EdosAFN.update(afn_pat.EdosAFN)
        afn_global.EdosAcept.update(afn_pat.EdosAcept)
        afn_global.Alfabeto.update(afn_pat.Alfabeto)

    return afn_global, afn_global.Convertir_a_AFD()


def parsear_mapa_tokens(texto_mapa: str) -> dict:
    mapa = {}
    for ln in texto_mapa.splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        sep = ":" if ":" in ln else ("=" if "=" in ln else None)
        if sep is None:
            raise ValueError(f"Formato inválido en mapa de tokens (use 'token: terminal'): {ln}")
        k_str, v_str = ln.split(sep, 1)
        mapa[int(k_str.strip())] = v_str.strip()
    return mapa


def ejecutar_analisis_ll1(analizador: AnalizadorLL1, g: Gramatica, tokens_entrada: list):
    if not g.no_terminales:
        return False, [(1, "$", " ".join(tokens_entrada), "ERROR: Gramática sin no terminales")]

    simb_ini = g.no_terminales[0]
    pila = ["$", simb_ini]
    entrada = list(tokens_entrada) + ["$"]
    idx = 0
    pasos = []
    paso_num = 1

    while len(pila) > 0:
        tope = pila[-1]
        actual = entrada[idx] if idx < len(entrada) else "$"
        pila_str = " ".join(pila)
        entrada_str = " ".join(entrada[idx:])

        if tope not in analizador.tabla or actual not in analizador.tabla[tope]:
            pasos.append((paso_num, pila_str, entrada_str, f"ERROR: Símbolo inesperado '{actual}' en tope '{tope}'"))
            return False, pasos

        accion = analizador.tabla[tope][actual]

        if accion == "Aceptar":
            pasos.append((paso_num, pila_str, entrada_str, "Aceptar"))
            return True, pasos

        elif accion == "POP":
            pasos.append((paso_num, pila_str, entrada_str, f"POP ({actual})"))
            pila.pop()
            idx += 1

        elif accion.isdigit():
            num_regla = int(accion)
            izq, der = g.reglas[num_regla - 1]
            regla_txt = f"Regla {num_regla}: {izq} -> {' '.join(der)}"
            pasos.append((paso_num, pila_str, entrada_str, regla_txt))
            pila.pop()
            if der != [EPSILON]:
                for sim in reversed(der):
                    pila.append(sim)

        else:
            motivo = f"CONFLICTO ({accion})" if "/" in accion else f"ERROR en celda [{tope}, {actual}]"
            pasos.append((paso_num, pila_str, entrada_str, motivo))
            return False, pasos

        paso_num += 1

    return False, pasos


# ==============================================================
#  CONFIGURACIÓN DE RESULTADOS DE EJECUCIÓN
# ==============================================================
CONFIG_ER_LL1 = {
    "gramatica": (
        "I  -> T I'\n"
        "I' -> cont T I' | EPSILON\n"
        "T  -> F T'\n"
        "T' -> or F T' | EPSILON\n"
        "F  -> S F'\n"
        "F' -> and S F' | EPSILON\n"
        "S  -> not P | P\n"
        "P  -> par_i I par_d | true | false"
    ),
    "sigma": "~(t@f)|(f&t)",
    "patrones": [
        ("@", 10),
        ("'|'", 20),
        ("'&'", 30),
        ("~", 40),
        ("'('", 50),
        ("')'", 60),
        ("t", 70),
        ("f", 80),
        ("' '", 20001),
    ],
    "mapa_tokens": (
        "10: cont\n"
        "20: or\n"
        "30: and\n"
        "40: not\n"
        "50: par_i\n"
        "60: par_d\n"
        "70: true\n"
        "80: false"
    ),
}

CONFIG_LR0 = {
    "gramatica": (
        "block -> begin decs pc stmts end pc\n"
        "decs  -> d | decs pc d\n"
        "stmts -> s | stmts pc s"
    ),
    "sigma": "begin d; d; s; s; s end;",
    "patrones": [
        ("b&e&g&i&n", 10),
        (";", 20),
        ("e&n&d", 30),
        ("d", 40),
        ("s", 50),
        ("' '", 20001),
    ],
    "mapa_tokens": (
        "10: begin\n"
        "20: pc\n"
        "30: end\n"
        "40: d\n"
        "50: s"
    ),
}


# ==============================================================
#  INTERFAZ GRÁFICA PRINCIPAL (viGeneral.py)
# ==============================================================
class InterfazCompilador:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Proyecto de Compiladores — Léxico, Descenso Recursivo, LL(1) y LR(0)")
        self.root.geometry("1120x740")
        self.root.minsize(960, 640)

        self.crear_menu()

        self.main_frame = tk.Frame(self.root, padx=20, pady=15)
        self.main_frame.pack(fill="both", expand=True)

        self.mostrar_bienvenida()

    def limpiar_frame(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

    # ----------------------------------------------------------
    #  BARRA DE MENÚS
    # ----------------------------------------------------------
    def crear_menu(self):
        menubar = tk.Menu(self.root)

        # Menú 1: AFN's y Thompson + Descenso Recursivo E.R. -> AFN
        menu_afn = tk.Menu(menubar, tearoff=0)
        menu_afn.add_command(label="Crear AFN Básico", command=self.mostrar_vista_crear_basico)
        menu_afn.add_separator()
        menu_afn.add_command(label="Unir AFNs (|)", command=self.mostrar_vista_unir)
        menu_afn.add_command(label="Concatenar AFNs (&)", command=self.mostrar_vista_concatenar)
        menu_afn.add_command(label="Cerradura Positiva (+)", command=self.mostrar_vista_cerradura_pos)
        menu_afn.add_command(label="Cerradura de Kleene (*)", command=self.mostrar_vista_cerradura_kleene)
        menu_afn.add_command(label="Operación Opcional (?)", command=self.mostrar_vista_opcional)
        menu_afn.add_separator()
        menu_afn.add_command(label="Descenso Recursivo: E.R. -> AFN", command=self.mostrar_vista_er_a_afn)
        menu_afn.add_separator()
        menu_afn.add_command(label="Ver AFN (Graphviz)", command=self.mostrar_vista_ver_afn)
        menu_afn.add_command(label="Unión para Analizador Léxico", command=self.mostrar_vista_union_lexico)
        menubar.add_cascade(label="AFN's", menu=menu_afn)

        # Menú 2: AFD y Analizador Léxico
        menu_afd = tk.Menu(menubar, tearoff=0)
        menu_afd.add_command(label="Convertir AFN a AFD", command=self.mostrar_vista_convertir_afd)
        menu_afd.add_command(label="Probar Analizador Léxico (σ)", command=self.mostrar_vista_probar_lexico)
        menu_afd.add_separator()
        menu_afd.add_command(label="Calculadora Descenso Recursivo", command=self.mostrar_vista_calculadora)
        menubar.add_cascade(label="AFD y Léxico", menu=menu_afd)

        # Menú 3: Analizador LL(1)
        menu_ll1 = tk.Menu(menubar, tearoff=0)
        menu_ll1.add_command(
            label="Tabla LL(1) y Análisis de Cadena σ",
            command=lambda: self.mostrar_vista_ll1(mostrar_resultado=False),
        )
        menubar.add_cascade(label="Analizador LL(1)", menu=menu_ll1)

        # Menú 4: Analizador LR(0)
        menu_lr0 = tk.Menu(menubar, tearoff=0)
        menu_lr0.add_command(
            label="Analizador LR(0): Tabla y Cadena σ",
            command=lambda: self.mostrar_vista_lr0(mostrar_resultado=False),
        )
        menubar.add_cascade(label="Analizador LR(0)", menu=menu_lr0)

        # Menú 5: Resultados
        menu_resultados = tk.Menu(menubar, tearoff=0)
        menu_resultados.add_command(
            label="Resultado e.r y LL(1)",
            command=lambda: self.mostrar_vista_ll1(mostrar_resultado=True),
        )
        menu_resultados.add_command(
            label="Resultado LR(0)",
            command=lambda: self.mostrar_vista_lr0(mostrar_resultado=True),
        )
        menubar.add_cascade(label="Últimas pruebas", menu=menu_resultados)

        self.root.config(menu=menubar)

    # ----------------------------------------------------------
    #  VISTA INICIAL
    # ----------------------------------------------------------
    def mostrar_bienvenida(self):
        self.limpiar_frame()
        tk.Label(
            self.main_frame,
            text="SISTEMA DE COMPILADORES — LÉXICO Y SINTÁCTICO",
            font=("Arial", 15, "bold"),
        ).pack(anchor="w", pady=(10, 15))

        resumen = (
            "Selecciona un módulo en la barra superior para trabajar:\n\n"
            "  • AFN's: Creación de AFNs básicos, operaciones de Thompson, Descenso Recursivo (E.R. -> AFN),\n"
            "    visualización Graphviz y Unión Léxica.\n"
            "  • AFD y Léxico: Conversión AFN -> AFD (tabla y exportación .txt), escaneo de σ con yylex()\n"
            "    y calculadora aritmética por descenso recursivo.\n"
            "  • Analizador LL(1): Cálculo de FIRST/FOLLOW, construcción de Tabla LL(1) y análisis de cadena σ.\n"
            "  • Analizador LR(0): Reglas numeradas, colección de estados Sj, Tabla LR(0) y análisis de cadena σ.\n"
        )
        tk.Label(self.main_frame, text=resumen, justify="left", font=("Arial", 10)).pack(anchor="w", pady=5)

    # ----------------------------------------------------------
    #  1. CREAR AFN BÁSICO
    # ----------------------------------------------------------
    def mostrar_vista_crear_basico(self):
        self.limpiar_frame()
        tk.Label(self.main_frame, text="CREAR AFN BÁSICO", font=("Arial", 12, "bold")).grid(
            row=0, column=0, columnspan=2, pady=(0, 20), sticky="w"
        )

        tk.Label(self.main_frame, text="Símbolo 1 (Inferior):").grid(row=1, column=0, pady=8, sticky="e")
        entry_s1 = tk.Entry(self.main_frame, width=18)
        entry_s1.grid(row=1, column=1, padx=10, pady=8, sticky="w")

        tk.Label(self.main_frame, text="Símbolo 2 (Opcional / Rango):").grid(row=2, column=0, pady=8, sticky="e")
        entry_s2 = tk.Entry(self.main_frame, width=18)
        entry_s2.grid(row=2, column=1, padx=10, pady=8, sticky="w")

        tk.Label(self.main_frame, text="ID del AFN:").grid(row=3, column=0, pady=8, sticky="e")
        entry_id = tk.Entry(self.main_frame, width=18)
        entry_id.insert(0, f"AFN_{len(afns_en_memoria) + 1}")
        entry_id.grid(row=3, column=1, padx=10, pady=8, sticky="w")

        def accion_crear():
            s1 = entry_s1.get()
            s2 = entry_s2.get()
            id_afn = entry_id.get().strip()

            if s1 == "\\t":
                s1 = "\t"
            if s2 == "\\t":
                s2 = "\t"

            if not s1 or len(s1) != 1:
                messagebox.showerror("Error", "Símbolo 1 debe ser exactamente 1 carácter (o '\\t').")
                return
            if s2 and len(s2) != 1:
                messagebox.showerror("Error", "Símbolo 2 debe ser 1 carácter o dejarse vacío.")
                return
            if not id_afn:
                messagebox.showerror("Error", "Debes especificar un ID para el AFN.")
                return

            if not afns_en_memoria:
                reiniciar_contador_estados()

            nuevo_afn = AFN().CrearBasico(s1, s2 if s2 else None)
            afns_en_memoria[id_afn] = nuevo_afn
            messagebox.showinfo("Éxito", f"AFN '{id_afn}' creado correctamente ({len(nuevo_afn.EdosAFN)} estados).")
            self.mostrar_vista_crear_basico()

        tk.Button(self.main_frame, text="CREAR", command=accion_crear, width=18).grid(
            row=4, column=0, columnspan=2, pady=20
        )

    # ----------------------------------------------------------
    #  2. OPERACIONES DE THOMPSON
    # ----------------------------------------------------------
    def _vista_operacion_doble(self, titulo: str, operacion: str):
        self.limpiar_frame()
        tk.Label(self.main_frame, text=titulo, font=("Arial", 12, "bold")).grid(
            row=0, column=0, columnspan=2, pady=(0, 20), sticky="w"
        )

        opciones = list(afns_en_memoria.keys())

        tk.Label(self.main_frame, text="AFN 1 (Destino):").grid(row=1, column=0, pady=8, sticky="e")
        combo1 = ttk.Combobox(self.main_frame, values=opciones, state="readonly", width=20)
        combo1.grid(row=1, column=1, padx=10, pady=8, sticky="w")

        tk.Label(self.main_frame, text="AFN 2:").grid(row=2, column=0, pady=8, sticky="e")
        combo2 = ttk.Combobox(self.main_frame, values=opciones, state="readonly", width=20)
        combo2.grid(row=2, column=1, padx=10, pady=8, sticky="w")

        tk.Label(self.main_frame, text="ID Resultante:").grid(row=3, column=0, pady=8, sticky="e")
        entry_id = tk.Entry(self.main_frame, width=22)
        entry_id.grid(row=3, column=1, padx=10, pady=8, sticky="w")

        def aplicar():
            id1, id2 = combo1.get(), combo2.get()
            id_res = entry_id.get().strip() or id1
            if not id1 or not id2:
                messagebox.showerror("Error", "Selecciona ambos AFNs.")
                return
            if id1 == id2:
                messagebox.showerror("Error", "Selecciona dos AFNs distintos.")
                return

            f1 = afns_en_memoria[id1]
            f2 = afns_en_memoria[id2]

            if operacion == "unir":
                f1.UnirAFN(f2)
            elif operacion == "concatenar":
                f1.Concatenar(f2)

            if id_res != id1:
                afns_en_memoria[id_res] = f1
                del afns_en_memoria[id1]
            if id2 in afns_en_memoria:
                del afns_en_memoria[id2]

            messagebox.showinfo("Éxito", f"Operación aplicada. Resultado almacenado en '{id_res}'.")
            self._vista_operacion_doble(titulo, operacion)

        tk.Button(self.main_frame, text="APLICAR", command=aplicar, width=18).grid(
            row=4, column=0, columnspan=2, pady=20
        )

    def _vista_operacion_simple(self, titulo: str, operacion: str):
        self.limpiar_frame()
        tk.Label(self.main_frame, text=titulo, font=("Arial", 12, "bold")).grid(
            row=0, column=0, columnspan=2, pady=(0, 20), sticky="w"
        )

        opciones = list(afns_en_memoria.keys())

        tk.Label(self.main_frame, text="Seleccionar AFN:").grid(row=1, column=0, pady=8, sticky="e")
        combo = ttk.Combobox(self.main_frame, values=opciones, state="readonly", width=20)
        combo.grid(row=1, column=1, padx=10, pady=8, sticky="w")

        tk.Label(self.main_frame, text="ID Resultante:").grid(row=2, column=0, pady=8, sticky="e")
        entry_id = tk.Entry(self.main_frame, width=22)
        entry_id.grid(row=2, column=1, padx=10, pady=8, sticky="w")

        def aplicar():
            id_sel = combo.get()
            id_res = entry_id.get().strip() or id_sel
            if not id_sel:
                messagebox.showerror("Error", "Selecciona un AFN.")
                return

            f = afns_en_memoria[id_sel]
            if operacion == "pos":
                f.cerraduraPos()
            elif operacion == "kleene":
                f.cerraduraKleen()
            elif operacion == "opcional":
                f.Opcional()

            if id_res != id_sel:
                afns_en_memoria[id_res] = f
                del afns_en_memoria[id_sel]

            messagebox.showinfo("Éxito", f"Operación aplicada. Resultado almacenado en '{id_res}'.")
            self._vista_operacion_simple(titulo, operacion)

        tk.Button(self.main_frame, text="APLICAR", command=aplicar, width=18).grid(
            row=3, column=0, columnspan=2, pady=20
        )

    def mostrar_vista_unir(self):
        self._vista_operacion_doble("UNIR AFNs (A | B)", "unir")

    def mostrar_vista_concatenar(self):
        self._vista_operacion_doble("CONCATENAR AFNs (A & B)", "concatenar")

    def mostrar_vista_cerradura_pos(self):
        self._vista_operacion_simple("CERRADURA POSITIVA (A+)", "pos")

    def mostrar_vista_cerradura_kleene(self):
        self._vista_operacion_simple("CERRADURA DE KLEENE (A*)", "kleene")

    def mostrar_vista_opcional(self):
        self._vista_operacion_simple("OPERACIÓN OPCIONAL (A?)", "opcional")

    # ----------------------------------------------------------
    #  3. DESCENSO RECURSIVO: E.R. -> AFN
    # ----------------------------------------------------------
    def mostrar_vista_er_a_afn(self):
        self.limpiar_frame()
        tk.Label(
            self.main_frame,
            text="DESCENSO RECURSIVO: EXPRESIÓN REGULAR (e.r.) -> AFN",
            font=("Arial", 12, "bold"),
        ).pack(anchor="w", pady=(0, 10))

        ayuda = (
            "Operadores soportados: Unión (|), Concatenación (& o implícita), Kleene (*), Positiva (+), "
            "Opcional (?), Agrupación ( ), Rangos ([a-z], [0-9]) y literales ('(', '\\t', etc.)."
        )
        tk.Label(self.main_frame, text=ayuda, fg="#333333").pack(anchor="w", pady=(0, 10))

        frm_in = tk.Frame(self.main_frame)
        frm_in.pack(fill="x", pady=5)

        tk.Label(frm_in, text="Expresión Regular (e.r.):").grid(row=0, column=0, sticky="e", pady=5)
        entry_er = tk.Entry(frm_in, width=42, font=("Consolas", 11))
        entry_er.insert(0, "([a-z]|[A-Z])&([a-z]|[A-Z]|[0-9])*")
        entry_er.grid(row=0, column=1, padx=8, pady=5, sticky="w")

        tk.Label(frm_in, text="ID del AFN resultante:").grid(row=1, column=0, sticky="e", pady=5)
        entry_id = tk.Entry(frm_in, width=22)
        entry_id.insert(0, f"AFN_ER_{len(afns_en_memoria) + 1}")
        entry_id.grid(row=1, column=1, padx=8, pady=5, sticky="w")

        lbl_info = tk.Label(self.main_frame, text="", font=("Arial", 10, "bold"), fg="#0b5394")
        lbl_info.pack(anchor="w", pady=(8, 4))

        tk.Label(self.main_frame, text="Traza de llamadas del Descenso Recursivo:", font=("Arial", 10, "bold")).pack(
            anchor="w"
        )
        txt_traza = scrolledtext.ScrolledText(self.main_frame, height=18, font=("Consolas", 10))
        txt_traza.pack(fill="both", expand=True, pady=5)

        def generar_afn_desde_er():
            expr = entry_er.get().strip()
            id_afn = entry_id.get().strip()
            if not id_afn:
                messagebox.showerror("Error", "Ingresa un ID para guardar el AFN.")
                return

            if not afns_en_memoria:
                reiniciar_contador_estados()

            try:
                parser = DescRecER_AFN(expr)
                afn_generado = parser.analizar()
                afns_en_memoria[id_afn] = afn_generado

                lbl_info.config(
                    text=(
                        f"AFN '{id_afn}' construido | Estado inicial: q{afn_generado.EdoIni.IdEdo} | "
                        f"Total estados: {len(afn_generado.EdosAFN)} | Alfabeto: {sorted(afn_generado.Alfabeto)}"
                    )
                )
                txt_traza.delete("1.0", tk.END)
                for idx, paso in enumerate(parser.traza, start=1):
                    txt_traza.insert(tk.END, f"{idx:>3}. {paso}\n")

                messagebox.showinfo(
                    "AFN Generado",
                    f"La e.r. se convirtió exitosamente en el AFN '{id_afn}' y se guardó en memoria.",
                )
            except Exception as e:
                messagebox.showerror("Error en Descenso Recursivo", str(e))

        def ver_diagrama_directo():
            id_afn = entry_id.get().strip()
            if id_afn not in afns_en_memoria:
                generar_afn_desde_er()
            if id_afn in afns_en_memoria:
                try:
                    afns_en_memoria[id_afn].generar_diagrama(nombre_archivo=f"Diagrama_{id_afn}")
                except Exception as e:
                    messagebox.showerror("Error Graphviz", str(e))

        frm_btns = tk.Frame(frm_in)
        frm_btns.grid(row=0, column=2, rowspan=2, padx=10)
        tk.Button(frm_btns, text="Construir AFN", command=generar_afn_desde_er, width=18).pack(pady=3)
        tk.Button(frm_btns, text="Ver Diagrama AFN", command=ver_diagrama_directo, width=18).pack(pady=3)

    # ----------------------------------------------------------
    #  4. VER AFN (GRAPHVIZ)
    # ----------------------------------------------------------
    def mostrar_vista_ver_afn(self):
        self.limpiar_frame()
        tk.Label(self.main_frame, text="VISUALIZAR AFN (GRAPHVIZ)", font=("Arial", 12, "bold")).grid(
            row=0, column=0, columnspan=2, pady=(0, 20), sticky="w"
        )

        opciones_afn = list(afns_en_memoria.keys())
        tk.Label(self.main_frame, text="Seleccionar AFN:").grid(row=1, column=0, pady=10, sticky="e")
        combo_afn = ttk.Combobox(self.main_frame, values=opciones_afn, state="readonly", width=22)
        combo_afn.grid(row=1, column=1, padx=10, pady=10)

        def accion_visualizar():
            id_sel = combo_afn.get()
            if not id_sel:
                messagebox.showerror("Error", "Selecciona un AFN de la lista.")
                return
            try:
                afns_en_memoria[id_sel].generar_diagrama(nombre_archivo=f"Diagrama_{id_sel}")
            except Exception as e:
                messagebox.showerror("Error de Visualización", str(e))

        tk.Button(self.main_frame, text="Generar y Ver Diagrama", command=accion_visualizar, width=22).grid(
            row=2, column=0, columnspan=2, pady=20
        )

    # ----------------------------------------------------------
    #  5. UNIÓN PARA ANALIZADOR LÉXICO
    # ----------------------------------------------------------
    def mostrar_vista_union_lexico(self):
        self.limpiar_frame()
        tk.Label(self.main_frame, text="UNIÓN PARA ANALIZADOR LÉXICO", font=("Arial", 12, "bold")).pack(
            anchor="w", pady=(0, 10)
        )

        tk.Label(
            self.main_frame,
            text="Nota: Asigna Token 20001 a espacios/tabuladores si deseas omitirlos en el escaneo léxico.",
            fg="#b00020",
            font=("Arial", 9, "bold"),
        ).pack(anchor="w", pady=(0, 10))

        if not afns_en_memoria:
            tk.Label(self.main_frame, text="No hay AFNs en memoria. Crea primero los patrones léxicos.").pack(anchor="w")
            return

        frm_lista = tk.Frame(self.main_frame)
        frm_lista.pack(fill="x", pady=5)

        tk.Label(frm_lista, text="Incluir", font=("Arial", 9, "bold")).grid(row=0, column=0, padx=10)
        tk.Label(frm_lista, text="ID AFN", font=("Arial", 9, "bold")).grid(row=0, column=1, padx=10)
        tk.Label(frm_lista, text="Token", font=("Arial", 9, "bold")).grid(row=0, column=2, padx=10)

        controles = []
        for idx, id_afn in enumerate(afns_en_memoria.keys(), start=1):
            var_chk = tk.BooleanVar(value=True)
            chk = tk.Checkbutton(frm_lista, variable=var_chk)
            chk.grid(row=idx, column=0, padx=10, pady=3)

            tk.Label(frm_lista, text=id_afn).grid(row=idx, column=1, padx=10, pady=3, sticky="w")

            ent_tok = tk.Entry(frm_lista, width=12)
            ent_tok.insert(0, str(idx * 10))
            ent_tok.grid(row=idx, column=2, padx=10, pady=3)
            controles.append((id_afn, var_chk, ent_tok))

        frm_dest = tk.Frame(self.main_frame)
        frm_dest.pack(fill="x", pady=15)
        tk.Label(frm_dest, text="ID AFN Léxico Global:").pack(side="left")
        entry_global = tk.Entry(frm_dest, width=20)
        entry_global.insert(0, "AFN_LEXICO")
        entry_global.pack(side="left", padx=10)

        def aplicar_union_lexica():
            id_global = entry_global.get().strip()
            if not id_global:
                messagebox.showerror("Error", "Ingresa un ID para el AFN global.")
                return

            seleccionados = []
            for id_afn, var_chk, ent_tok in controles:
                if var_chk.get():
                    try:
                        tok_val = int(ent_tok.get().strip())
                    except ValueError:
                        messagebox.showerror("Error", f"Token inválido para '{id_afn}'. Debe ser entero.")
                        return
                    seleccionados.append((id_afn, tok_val))

            if not seleccionados:
                messagebox.showerror("Error", "Selecciona al menos un AFN.")
                return

            afn_lexico = AFN()
            edo_ini_global = Estado()
            afn_lexico.EdoIni = edo_ini_global
            afn_lexico.EdosAFN.add(edo_ini_global)

            for id_afn, tok_val in seleccionados:
                sub_afn = afns_en_memoria[id_afn]
                for edo in sub_afn.EdosAcept:
                    edo.EdoAcept = True
                    edo.Token = tok_val
                edo_ini_global.Transiciones.add(Transicion(EPSILON, sub_afn.EdoIni))
                afn_lexico.EdosAFN.update(sub_afn.EdosAFN)
                afn_lexico.EdosAcept.update(sub_afn.EdosAcept)
                afn_lexico.Alfabeto.update(sub_afn.Alfabeto)

            afns_en_memoria[id_global] = afn_lexico
            messagebox.showinfo(
                "Unión Léxica Lista",
                f"Se creó '{id_global}' uniendo {len(seleccionados)} autómatas.",
            )

        tk.Button(self.main_frame, text="Generar Unión Léxica", command=aplicar_union_lexica, width=22).pack(
            anchor="w", pady=10
        )

    # ----------------------------------------------------------
    #  6. CONVERTIR AFN A AFD (TABLA Y EXPORTACIÓN .TXT)
    # ----------------------------------------------------------
    def mostrar_vista_convertir_afd(self):
        self.limpiar_frame()
        tk.Label(self.main_frame, text="CONVERTIR AFN A AFD", font=("Arial", 12, "bold")).pack(
            anchor="w", pady=(0, 12)
        )

        frm_top = tk.Frame(self.main_frame)
        frm_top.pack(fill="x", pady=5)

        tk.Label(frm_top, text="AFN origen:").pack(side="left")
        combo_afn = ttk.Combobox(frm_top, values=list(afns_en_memoria.keys()), state="readonly", width=18)
        combo_afn.pack(side="left", padx=8)

        tk.Label(frm_top, text="ID AFD:").pack(side="left")
        entry_afd = tk.Entry(frm_top, width=16)
        entry_afd.insert(0, f"AFD_{len(afds_en_memoria) + 1}")
        entry_afd.pack(side="left", padx=8)

        estado_local = {"afd": None, "id": ""}

        frm_tabla = tk.Frame(self.main_frame)
        frm_tabla.pack(fill="both", expand=True, pady=10)

        def convertir():
            id_afn = combo_afn.get()
            id_afd = entry_afd.get().strip()
            if not id_afn or not id_afd:
                messagebox.showerror("Error", "Selecciona un AFN e indica el ID del AFD.")
                return

            afd_obj = afns_en_memoria[id_afn].Convertir_a_AFD()
            afds_en_memoria[id_afd] = afd_obj
            estado_local["afd"] = afd_obj
            estado_local["id"] = id_afd
            btn_guardar.config(state="normal")

            for w in frm_tabla.winfo_children():
                w.destroy()

            alfabeto_ord = sorted(list(afd_obj.Alfabeto))
            cols = ["Estado"] + [repr(c) if c in (" ", "\t") else c for c in alfabeto_ord] + ["Token"]

            tree = ttk.Treeview(frm_tabla, columns=cols, show="headings", height=16)
            sb_y = ttk.Scrollbar(frm_tabla, orient="vertical", command=tree.yview)
            sb_x = ttk.Scrollbar(frm_tabla, orient="horizontal", command=tree.xview)
            tree.configure(yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)

            for c in cols:
                tree.heading(c, text=c)
                tree.column(c, width=65, anchor="center")

            for edo in afd_obj.EdosAFD:
                fila = [f"S{edo.IdAFD}"]
                for sim in alfabeto_ord:
                    dest = edo.TransEdo[ord(sim)]
                    fila.append(str(dest) if dest != -1 else "-")
                tok = edo.TransEdo[256]
                fila.append(str(tok) if tok != -1 else "-1")
                tree.insert("", "end", values=fila)

            sb_y.pack(side="right", fill="y")
            sb_x.pack(side="bottom", fill="x")
            tree.pack(fill="both", expand=True)

        def guardar_txt():
            afd_obj = estado_local["afd"]
            if afd_obj is None:
                return
            ruta = filedialog.asksaveasfilename(
                defaultextension=".txt",
                initialfile=f"{estado_local['id']}.txt",
                filetypes=[("Archivo de texto", "*.txt")],
            )
            if ruta:
                try:
                    afd_obj.guardarArchivo(ruta, id_afd=estado_local["id"])
                    messagebox.showinfo("Guardado", f"Tabla AFD exportada en:\n{ruta}")
                except Exception as e:
                    messagebox.showerror("Error al guardar", str(e))

        tk.Button(frm_top, text="Convertir a AFD", command=convertir, width=16).pack(side="left", padx=6)
        btn_guardar = tk.Button(frm_top, text="Guardar en .txt", command=guardar_txt, width=16, state="disabled")
        btn_guardar.pack(side="left", padx=6)

    # ----------------------------------------------------------
    #  7. PROBAR ANALIZADOR LÉXICO (CADENA σ)
    # ----------------------------------------------------------
    def mostrar_vista_probar_lexico(self):
        self.limpiar_frame()
        tk.Label(self.main_frame, text="PROBAR ANALIZADOR LÉXICO (yylex)", font=("Arial", 12, "bold")).pack(
            anchor="w", pady=(0, 12)
        )

        frm_top = tk.Frame(self.main_frame)
        frm_top.pack(fill="x", pady=5)

        tk.Label(frm_top, text="AFD Léxico:").grid(row=0, column=0, sticky="e", pady=5)
        combo_afd = ttk.Combobox(frm_top, values=list(afds_en_memoria.keys()), state="readonly", width=20)
        combo_afd.grid(row=0, column=1, padx=8, pady=5, sticky="w")

        tk.Label(frm_top, text="Cadena σ:").grid(row=1, column=0, sticky="e", pady=5)
        entry_sigma = tk.Entry(frm_top, width=45, font=("Consolas", 11))
        entry_sigma.grid(row=1, column=1, padx=8, pady=5, sticky="w")

        cols = ("Paso", "Lexema (yytext)", "Token", "Estado")
        tree = ttk.Treeview(self.main_frame, columns=cols, show="headings", height=16)
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=180, anchor="center")
        tree.pack(fill="both", expand=True, pady=10)

        def escanear():
            id_afd = combo_afd.get()
            if not id_afd:
                messagebox.showerror("Error", "Selecciona un AFD de la lista.")
                return
            for item in tree.get_children():
                tree.delete(item)

            lexer = AnalizadorLexico(afd_lexico=afds_en_memoria[id_afd], cadena_sigma=entry_sigma.get())
            paso = 1
            while True:
                tok = lexer.yylex()
                if tok == 0:
                    tree.insert("", "end", values=(paso, "$ (EOF)", "0", "FIN DE CADENA"))
                    break
                elif tok == 20001:
                    tree.insert("", "end", values=(paso, repr(lexer.yytext), "20001", "OMITIDO (ESPACIO)"))
                elif tok == -1:
                    tree.insert("", "end", values=(paso, repr(lexer.yytext), "-1", "ERROR LÉXICO"))
                else:
                    tree.insert("", "end", values=(paso, repr(lexer.yytext), str(tok), "RECONOCIDO"))
                paso += 1

        tk.Button(frm_top, text="Analizar Cadena σ", command=escanear, width=18).grid(
            row=0, column=2, rowspan=2, padx=12
        )

    # ----------------------------------------------------------
    #  8. CALCULADORA POR DESCENSO RECURSIVO (AnSint / CalculadoraAS)
    # ----------------------------------------------------------
    def mostrar_vista_calculadora(self):
        self.limpiar_frame()
        tk.Label(
            self.main_frame,
            text="CALCULADORA SINTÁCTICA POR DESCENSO RECURSIVO (AnSint / CalculadoraAS)",
            font=("Arial", 12, "bold"),
        ).pack(anchor="w", pady=(0, 10))

        tk.Label(
            self.main_frame,
            text="Tokens esperados: + (10), - (20), * (30), / (40), ( (50), ) (60), número (70), espacio (20001).",
            fg="#333333",
        ).pack(anchor="w", pady=(0, 10))

        frm = tk.Frame(self.main_frame)
        frm.pack(fill="x", pady=5)

        tk.Label(frm, text="Expresión aritmética:").pack(side="left")
        entry_exp = tk.Entry(frm, width=35, font=("Consolas", 11))
        entry_exp.insert(0, "3 + 4 * (2 + 1)")
        entry_exp.pack(side="left", padx=8)

        lbl_res = tk.Label(self.main_frame, text="", font=("Arial", 11, "bold"), fg="#0b5394")
        lbl_res.pack(anchor="w", pady=15)

        def evaluar():
            patrones_calc = [
                ("+", 10),
                ("-", 20),
                ("*", 30),
                ("/", 40),
                ("'('", 50),
                ("')'", 60),
                ("[0-9]+&(.&[0-9]+)?", 70),
                ("' '", 20001),
            ]
            _, afd_calc = construir_automatas_desde_patrones(patrones_calc)

            lexer = AnalizadorLexico(afd_lexico=afd_calc, cadena_sigma=entry_exp.get())
            orig_yylex = lexer.yylex

            def yylex_sin_espacios():
                t = orig_yylex()
                while t == 20001:
                    t = orig_yylex()
                return t

            lexer.yylex = yylex_sin_espacios
            lexer.deshacerToken = lexer.UndoToken

            try:
                calc = AccSemCalc(lexer)
                exito, valor, postfija = calc.IniSintact()
                if exito:
                    lbl_res.config(text=f"VÁLIDA  |  Resultado: {valor}  |  Postfija: {postfija}", fg="#137333")
                else:
                    lbl_res.config(text="ERROR SINTÁCTICO en la expresión aritmética.", fg="#b00020")
            except Exception as e:
                lbl_res.config(text=f"Error: {e}", fg="#b00020")

        tk.Button(frm, text="Evaluar", command=evaluar, width=15).pack(side="left", padx=8)

    # ----------------------------------------------------------
    #  9. ANALIZADOR LL(1): TABLA LL(1) Y ANÁLISIS DE CADENA σ
    # ----------------------------------------------------------
    def mostrar_vista_ll1(self, mostrar_resultado: bool = False):
        self.limpiar_frame()

        frm_header = tk.Frame(self.main_frame)
        frm_header.pack(fill="x", pady=(0, 8))
        tk.Label(
            frm_header,
            text="ANALIZADOR SINTÁCTICO LL(1) — TABLA Y ANÁLISIS DE CADENA σ",
            font=("Arial", 12, "bold"),
        ).pack(side="left")

        estado_ll1 = {"gram": None, "analizador": None}

        # Panel superior: Entrada de Gramática + Cadena σ y Mapeo Léxico
        frm_config = tk.Frame(self.main_frame)
        frm_config.pack(fill="x", pady=4)

        frm_gram = tk.LabelFrame(frm_config, text="1. Reglas de la Gramática LL(1)", padx=8, pady=6)
        frm_gram.pack(side="left", fill="both", expand=True, padx=(0, 6))

        txt_gram = scrolledtext.ScrolledText(frm_gram, width=42, height=8, font=("Consolas", 10))
        txt_gram.pack(fill="both", expand=True)

        frm_sigma = tk.LabelFrame(frm_config, text="2. Cadena σ y Mapeo Léxico (Token -> Terminal)", padx=8, pady=6)
        frm_sigma.pack(side="left", fill="both", expand=True, padx=(6, 0))

        frm_s_row = tk.Frame(frm_sigma)
        frm_s_row.pack(fill="x", pady=(0, 4))
        tk.Label(frm_s_row, text="Cadena σ:").pack(side="left")
        entry_sigma = tk.Entry(frm_s_row, width=32, font=("Consolas", 10))
        entry_sigma.pack(side="left", padx=6, fill="x", expand=True)

        modo_var = tk.StringVar(value="directo")
        frm_modo = tk.Frame(frm_sigma)
        frm_modo.pack(fill="x", pady=2)
        tk.Radiobutton(
            frm_modo,
            text="Terminales separados por espacio",
            variable=modo_var,
            value="directo",
        ).pack(side="left")
        tk.Radiobutton(
            frm_modo,
            text="Escanear σ con AFD Léxico",
            variable=modo_var,
            value="lexico",
        ).pack(side="left", padx=8)

        frm_afd_sel = tk.Frame(frm_sigma)
        frm_afd_sel.pack(fill="x", pady=2)
        tk.Label(frm_afd_sel, text="AFD:").pack(side="left")
        combo_afd = ttk.Combobox(frm_afd_sel, values=list(afds_en_memoria.keys()), state="readonly", width=18)
        combo_afd.pack(side="left", padx=6)

        txt_mapa = scrolledtext.ScrolledText(frm_sigma, width=34, height=4, font=("Consolas", 9))
        txt_mapa.pack(fill="both", expand=True, pady=(4, 0))

        # Pestañas de salida: Tabla LL(1) | FIRST y FOLLOW | Análisis de Cadena σ
        notebook = ttk.Notebook(self.main_frame)
        notebook.pack(fill="both", expand=True, pady=8)

        tab_tabla = tk.Frame(notebook)
        tab_ff = tk.Frame(notebook)
        tab_traza = tk.Frame(notebook)

        notebook.add(tab_tabla, text="Tabla LL(1)")
        notebook.add(tab_ff, text="Conjuntos FIRST y FOLLOW")
        notebook.add(tab_traza, text="Análisis de Cadena σ (Pila)")

        lbl_estado_ll1 = tk.Label(self.main_frame, text="", font=("Arial", 10, "bold"))
        lbl_estado_ll1.pack(anchor="w")

        def construir_tabla_ll1():
            try:
                g = construir_gramatica_desde_texto(txt_gram.get("1.0", tk.END))
                analizador = AnalizadorLL1(g)
                estado_ll1["gram"] = g
                estado_ll1["analizador"] = analizador
            except Exception as e:
                messagebox.showerror("Error en Gramática LL(1)", str(e))
                return

            for w in tab_tabla.winfo_children():
                w.destroy()

            cols = ["Símbolo"] + analizador.columnas
            tree_t = ttk.Treeview(tab_tabla, columns=cols, show="headings", height=12)
            sb_y = ttk.Scrollbar(tab_tabla, orient="vertical", command=tree_t.yview)
            sb_x = ttk.Scrollbar(tab_tabla, orient="horizontal", command=tree_t.xview)
            tree_t.configure(yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)

            for c in cols:
                tree_t.heading(c, text=c)
                tree_t.column(c, width=85, anchor="center")

            for fila in analizador.filas:
                valores = [fila] + [analizador.tabla[fila][col] for col in analizador.columnas]
                tree_t.insert("", "end", values=valores)

            sb_y.pack(side="right", fill="y")
            sb_x.pack(side="bottom", fill="x")
            tree_t.pack(fill="both", expand=True)

            for w in tab_ff.winfo_children():
                w.destroy()

            txt_ff = scrolledtext.ScrolledText(tab_ff, font=("Consolas", 10))
            txt_ff.pack(fill="both", expand=True)
            txt_ff.insert(tk.END, "=== REGLAS NUMERADAS ===\n")
            for idx, (izq, der) in enumerate(g.reglas, start=1):
                txt_ff.insert(tk.END, f"  ({idx:>2}) {izq:<5} -> {' '.join(der)}\n")

            txt_ff.insert(tk.END, "\n=== CONJUNTOS FIRST Y FOLLOW ===\n")
            follow_dict = g.follow
            for nt in g.no_terminales:
                f_set = sorted(g.first_secuencia([nt]))
                fl_set = sorted(follow_dict.get(nt, set()))
                txt_ff.insert(tk.END, f"  {nt:<5} | FIRST: {f_set} | FOLLOW: {fl_set}\n")

            if analizador.conflictos:
                lbl_estado_ll1.config(
                    text=f"Tabla LL(1) construida con {len(analizador.conflictos)} conflicto(s).",
                    fg="#b00020",
                )
            else:
                lbl_estado_ll1.config(text="Tabla LL(1) construida sin conflictos.", fg="#137333")
            notebook.select(tab_tabla)

        def analizar_sigma_ll1():
            if estado_ll1["analizador"] is None:
                construir_tabla_ll1()
            analizador = estado_ll1["analizador"]
            g = estado_ll1["gram"]
            if analizador is None or g is None:
                return

            sigma = entry_sigma.get().strip()
            if not sigma:
                messagebox.showerror("Error", "Ingresa la cadena σ a analizar.")
                return

            try:
                if modo_var.get() == "lexico":
                    id_afd = combo_afd.get()
                    if not id_afd or id_afd not in afds_en_memoria:
                        messagebox.showerror("Error", "Selecciona un AFD léxico válido.")
                        return
                    mapa = parsear_mapa_tokens(txt_mapa.get("1.0", tk.END))
                    lexer = AnalizadorLexico(afd_lexico=afds_en_memoria[id_afd], cadena_sigma=sigma)
                    tokens_entrada = []
                    while True:
                        tok = lexer.yylex()
                        if tok == 0:
                            break
                        if tok == 20001:
                            continue
                        if tok == -1 or tok not in mapa:
                            messagebox.showerror(
                                "Error Léxico",
                                f"Token no reconocido o no mapeado: {tok} ('{lexer.yytext}')",
                            )
                            return
                        tokens_entrada.append(mapa[tok])
                else:
                    tokens_entrada = sigma.split()

                aceptada, pasos = ejecutar_analisis_ll1(analizador, g, tokens_entrada)
            except Exception as e:
                messagebox.showerror("Error en Análisis LL(1)", str(e))
                return

            for w in tab_traza.winfo_children():
                w.destroy()

            cols = ("Paso", "Pila", "Entrada σ", "Acción")
            tree_p = ttk.Treeview(tab_traza, columns=cols, show="headings", height=12)
            sb_y = ttk.Scrollbar(tab_traza, orient="vertical", command=tree_p.yview)
            tree_p.configure(yscrollcommand=sb_y.set)

            tree_p.heading("Paso", text="Paso")
            tree_p.heading("Pila", text="Pila")
            tree_p.heading("Entrada σ", text="Entrada σ")
            tree_p.heading("Acción", text="Acción")

            tree_p.column("Paso", width=60, anchor="center")
            tree_p.column("Pila", width=260, anchor="w")
            tree_p.column("Entrada σ", width=260, anchor="w")
            tree_p.column("Acción", width=320, anchor="w")

            for fila in pasos:
                tree_p.insert("", "end", values=fila)

            sb_y.pack(side="right", fill="y")
            tree_p.pack(fill="both", expand=True)

            notebook.select(tab_traza)
            if aceptada:
                lbl_estado_ll1.config(text=f"RESULTADO LL(1): Cadena '{sigma}' ACEPTADA.", fg="#137333")
            else:
                lbl_estado_ll1.config(text=f"RESULTADO LL(1): Cadena '{sigma}' RECHAZADA.", fg="#b00020")

        frm_btns = tk.Frame(self.main_frame)
        frm_btns.pack(fill="x", pady=4)
        tk.Button(frm_btns, text="1. Construir Tabla LL(1)", command=construir_tabla_ll1, width=22).pack(
            side="left", padx=(0, 8)
        )
        tk.Button(frm_btns, text="2. Analizar Cadena σ", command=analizar_sigma_ll1, width=22).pack(
            side="left", padx=8
        )

        if mostrar_resultado:
            txt_gram.delete("1.0", tk.END)
            txt_gram.insert("1.0", CONFIG_ER_LL1["gramatica"])
            entry_sigma.delete(0, tk.END)
            entry_sigma.insert(0, CONFIG_ER_LL1["sigma"])
            txt_mapa.delete("1.0", tk.END)
            txt_mapa.insert("1.0", CONFIG_ER_LL1["mapa_tokens"])

            afn_bool, afd_bool = construir_automatas_desde_patrones(CONFIG_ER_LL1["patrones"])
            afns_en_memoria["AFN_Booleanas"] = afn_bool
            afds_en_memoria["AFD_Booleanas"] = afd_bool
            combo_afd["values"] = list(afds_en_memoria.keys())
            combo_afd.set("AFD_Booleanas")
            modo_var.set("lexico")

            construir_tabla_ll1()
            analizar_sigma_ll1()
        else:
            txt_gram.insert("1.0", "E -> T E'\nE' -> + T E' | EPSILON\nT -> F T'\nT' -> * F T' | EPSILON\nF -> ( E ) | id")
            entry_sigma.insert(0, "id + id * id")

    # ----------------------------------------------------------
    #  10. ANALIZADOR LR(0): CREACIÓN DE TABLA Y ANÁLISIS DE σ
    # ----------------------------------------------------------
    def mostrar_vista_lr0(self, mostrar_resultado: bool = False):
        self.limpiar_frame()

        frm_header = tk.Frame(self.main_frame)
        frm_header.pack(fill="x", pady=(0, 8))
        tk.Label(
            frm_header,
            text="ANALIZADOR SINTÁCTICO LR(0) — CREACIÓN DE TABLA Y ANÁLISIS DE CADENA σ",
            font=("Arial", 12, "bold"),
        ).pack(side="left")

        estado_lr0 = {"gram": None, "lr0": None}

        # Panel superior: Reglas LR(0) + Cadena σ y Mapeo Léxico
        frm_config = tk.Frame(self.main_frame)
        frm_config.pack(fill="x", pady=4)

        frm_gram = tk.LabelFrame(frm_config, text="1. Reglas de la Gramática LR(0) (se aumenta automáticamente)", padx=8, pady=6)
        frm_gram.pack(side="left", fill="both", expand=True, padx=(0, 6))

        txt_gram = scrolledtext.ScrolledText(frm_gram, width=42, height=7, font=("Consolas", 10))
        txt_gram.pack(fill="both", expand=True)

        frm_sigma = tk.LabelFrame(frm_config, text="2. Cadena σ y Mapeo Léxico (Token -> Terminal)", padx=8, pady=6)
        frm_sigma.pack(side="left", fill="both", expand=True, padx=(6, 0))

        frm_s_row = tk.Frame(frm_sigma)
        frm_s_row.pack(fill="x", pady=(0, 4))
        tk.Label(frm_s_row, text="Cadena σ:").pack(side="left")
        entry_sigma = tk.Entry(frm_s_row, width=32, font=("Consolas", 10))
        entry_sigma.pack(side="left", padx=6, fill="x", expand=True)

        modo_var = tk.StringVar(value="directo")
        frm_modo = tk.Frame(frm_sigma)
        frm_modo.pack(fill="x", pady=2)
        tk.Radiobutton(
            frm_modo,
            text="Terminales separados por espacio",
            variable=modo_var,
            value="directo",
        ).pack(side="left")
        tk.Radiobutton(
            frm_modo,
            text="Escanear σ con AFD Léxico",
            variable=modo_var,
            value="lexico",
        ).pack(side="left", padx=8)

        frm_afd_sel = tk.Frame(frm_sigma)
        frm_afd_sel.pack(fill="x", pady=2)
        tk.Label(frm_afd_sel, text="AFD:").pack(side="left")
        combo_afd = ttk.Combobox(frm_afd_sel, values=list(afds_en_memoria.keys()), state="readonly", width=18)
        combo_afd.pack(side="left", padx=6)

        txt_mapa = scrolledtext.ScrolledText(frm_sigma, width=34, height=4, font=("Consolas", 9))
        txt_mapa.pack(fill="both", expand=True, pady=(4, 0))

        # Pestañas de salida: Reglas + Tabla LR(0) | Estados Canónicos Sj | Análisis de Cadena σ
        notebook = ttk.Notebook(self.main_frame)
        notebook.pack(fill="both", expand=True, pady=8)

        tab_tabla = tk.Frame(notebook)
        tab_estados = tk.Frame(notebook)
        tab_traza = tk.Frame(notebook)

        notebook.add(tab_tabla, text="Reglas y Tabla LR(0)")
        notebook.add(tab_estados, text="Colección de Estados Sj")
        notebook.add(tab_traza, text="Análisis de Cadena σ (Pila)")

        lbl_estado_lr0 = tk.Label(self.main_frame, text="", font=("Arial", 10, "bold"))
        lbl_estado_lr0.pack(anchor="w")

        def crear_tabla_lr0():
            try:
                g = construir_gramatica_desde_texto(txt_gram.get("1.0", tk.END))
                lr0 = AnalizadorLR0(g)
                estado_lr0["gram"] = g
                estado_lr0["lr0"] = lr0
            except Exception as e:
                messagebox.showerror("Error en Gramática LR(0)", str(e))
                return

            for w in tab_tabla.winfo_children():
                w.destroy()

            frm_reglas_num = tk.LabelFrame(tab_tabla, text="Reglas Numeradas (Gramática Aumentada)", padx=6, pady=4)
            frm_reglas_num.pack(fill="x", padx=4, pady=(4, 6))

            reglas_str = "   |   ".join(
                f"r{idx}: {izq} -> {' '.join(der)}" for idx, (izq, der) in enumerate(lr0.reglas)
            )
            tk.Label(frm_reglas_num, text=reglas_str, font=("Consolas", 9), justify="left", wraplength=1020).pack(
                anchor="w"
            )

            frm_grid = tk.Frame(tab_tabla)
            frm_grid.pack(fill="both", expand=True, padx=4, pady=2)

            cols = ["Estado"] + lr0.columnas_accion + lr0.columnas_ira
            tree_lr = ttk.Treeview(frm_grid, columns=cols, show="headings", height=11)
            sb_y = ttk.Scrollbar(frm_grid, orient="vertical", command=tree_lr.yview)
            sb_x = ttk.Scrollbar(frm_grid, orient="horizontal", command=tree_lr.xview)
            tree_lr.configure(yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)

            for c in cols:
                tree_lr.heading(c, text=c)
                tree_lr.column(c, width=75, anchor="center")

            for id_edo in range(len(lr0.estados)):
                fila = [f"S{id_edo}"] + [lr0.tabla[id_edo].get(c, "") for c in (lr0.columnas_accion + lr0.columnas_ira)]
                tree_lr.insert("", "end", values=fila)

            sb_y.pack(side="right", fill="y")
            sb_x.pack(side="bottom", fill="x")
            tree_lr.pack(fill="both", expand=True)

            for w in tab_estados.winfo_children():
                w.destroy()

            txt_edos = scrolledtext.ScrolledText(tab_estados, font=("Consolas", 10))
            txt_edos.pack(fill="both", expand=True)
            for id_edo, conj_items in enumerate(lr0.estados):
                items_legibles = []
                for idx_r, pos_p in sorted(conj_items):
                    izq, der = lr0.reglas[idx_r]
                    if der == [EPSILON]:
                        cuerpo = "·"
                    else:
                        cuerpo = " ".join(der[:pos_p] + ["·"] + der[pos_p:])
                    items_legibles.append(f"[{izq} -> {cuerpo}]")
                txt_edos.insert(tk.END, f"S{id_edo:<2}: {', '.join(items_legibles)}\n")

            if lr0.conflictos:
                lbl_estado_lr0.config(
                    text=f"Tabla LR(0) creada ({len(lr0.estados)} estados) con {len(lr0.conflictos)} conflicto(s).",
                    fg="#b00020",
                )
            else:
                lbl_estado_lr0.config(
                    text=f"Tabla LR(0) creada correctamente ({len(lr0.estados)} estados canónicos).",
                    fg="#137333",
                )
            notebook.select(tab_tabla)

        def analizar_sigma_lr0():
            if estado_lr0["lr0"] is None:
                crear_tabla_lr0()
            lr0 = estado_lr0["lr0"]
            if lr0 is None:
                return

            sigma = entry_sigma.get().strip()
            if not sigma:
                messagebox.showerror("Error", "Ingresa la cadena σ a analizar.")
                return

            try:
                if modo_var.get() == "lexico":
                    id_afd = combo_afd.get()
                    if not id_afd or id_afd not in afds_en_memoria:
                        messagebox.showerror("Error", "Selecciona un AFD léxico válido.")
                        return
                    mapa = parsear_mapa_tokens(txt_mapa.get("1.0", tk.END))
                    lexer = AnalizadorLexico(afd_lexico=afds_en_memoria[id_afd], cadena_sigma=sigma)
                    orig_yylex = lexer.yylex

                    def yylex_sin_espacios():
                        t = orig_yylex()
                        while t == 20001:
                            t = orig_yylex()
                        return t

                    lexer.yylex = yylex_sin_espacios
                    exito, historial = lr0.analizar_con_lexer(lexer, sigma, mapa)
                else:
                    exito, historial = lr0.analizar_cadena(sigma)
            except Exception as e:
                messagebox.showerror("Error en Análisis LR(0)", str(e))
                return

            for w in tab_traza.winfo_children():
                w.destroy()

            cols = ("Paso", "PILA", "Cadena σ", "Acción")
            tree_p = ttk.Treeview(tab_traza, columns=cols, show="headings", height=12)
            sb_y = ttk.Scrollbar(tab_traza, orient="vertical", command=tree_p.yview)
            tree_p.configure(yscrollcommand=sb_y.set)

            tree_p.heading("Paso", text="Paso")
            tree_p.heading("PILA", text="PILA")
            tree_p.heading("Cadena σ", text="Cadena σ")
            tree_p.heading("Acción", text="Acción")

            tree_p.column("Paso", width=60, anchor="center")
            tree_p.column("PILA", width=310, anchor="w")
            tree_p.column("Cadena σ", width=260, anchor="w")
            tree_p.column("Acción", width=310, anchor="w")

            for idx, (pila_s, ent_s, acc_s) in enumerate(historial, start=1):
                tree_p.insert("", "end", values=(idx, pila_s, ent_s, acc_s))

            sb_y.pack(side="right", fill="y")
            tree_p.pack(fill="both", expand=True)

            notebook.select(tab_traza)
            if exito:
                lbl_estado_lr0.config(text=f"RESULTADO LR(0): Cadena '{sigma}' ACEPTADA.", fg="#137333")
            else:
                lbl_estado_lr0.config(text=f"RESULTADO LR(0): Cadena '{sigma}' RECHAZADA.", fg="#b00020")

        frm_btns = tk.Frame(self.main_frame)
        frm_btns.pack(fill="x", pady=4)
        tk.Button(frm_btns, text="1. Crear Tabla LR(0)", command=crear_tabla_lr0, width=22).pack(
            side="left", padx=(0, 8)
        )
        tk.Button(frm_btns, text="2. Analizar Cadena σ", command=analizar_sigma_lr0, width=22).pack(
            side="left", padx=8
        )

        if mostrar_resultado:
            txt_gram.delete("1.0", tk.END)
            txt_gram.insert("1.0", CONFIG_LR0["gramatica"])
            entry_sigma.delete(0, tk.END)
            entry_sigma.insert(0, CONFIG_LR0["sigma"])
            txt_mapa.delete("1.0", tk.END)
            txt_mapa.insert("1.0", CONFIG_LR0["mapa_tokens"])

            afn_bloques, afd_bloques = construir_automatas_desde_patrones(CONFIG_LR0["patrones"])
            afns_en_memoria["AFN_Bloques"] = afn_bloques
            afds_en_memoria["AFD_Bloques"] = afd_bloques
            combo_afd["values"] = list(afds_en_memoria.keys())
            combo_afd.set("AFD_Bloques")
            modo_var.set("lexico")

            crear_tabla_lr0()
            analizar_sigma_lr0()
        else:
            txt_gram.insert("1.0", "E -> E + n | n")
            entry_sigma.insert(0, "n + n + n")


if __name__ == "__main__":
    root = tk.Tk()
    app = InterfazCompilador(root)
    root.mainloop()