from base import EPSILON


class SimbGram:
    def __init__(self, simbolo: str = "", token: int = -1, es_terminal: bool = False):
        self.Simbolo = simbolo
        self.Token = token
        self.EsTerminal = es_terminal

    def __eq__(self, other):
        if isinstance(other, SimbGram):
            return self.Simbolo == other.Simbolo and self.EsTerminal == other.EsTerminal
        return False

    def __hash__(self):
        return hash((self.Simbolo, self.EsTerminal))


class ElemArrGram:
    def __init__(self, simb_izq: SimbGram = None, lista_der: list = None):
        self.SimbIzqGram = simb_izq
        self.l = lista_der if lista_der is not None else []


class Gramatica:
    def __init__(self):
        self.NumReglas = 0
        self.ArrReglas = []

    def ContieneEpsilon(self, R: set) -> bool:
        for s in R:
            if s.Simbolo == EPSILON:
                return True
        return False

    def QuitarEpsilon(self, R: set):
        a_eliminar = None
        for s in R:
            if s.Simbolo == EPSILON:
                a_eliminar = s
                break
        if a_eliminar is not None:
            R.remove(a_eliminar)

    def First(self, lista: list) -> set:
        R = set()
        R.clear()

        if len(lista) == 0:
            return R

        if lista[0].EsTerminal or lista[0].Simbolo == EPSILON:
            R.add(lista[0])
            return R

        for i in range(self.NumReglas):
            if lista[0].Simbolo == self.ArrReglas[i].SimbIzqGram.Simbolo:
                R.update(self.First(self.ArrReglas[i].l))

        if self.ContieneEpsilon(R):
            if len(lista) > 1:
                self.QuitarEpsilon(R)
                l2 = lista[1:]
                R.update(self.First(l2))

        return R

    def Follow(self, s: SimbGram, _visitados: set = None) -> set:
        if _visitados is None:
            _visitados = set()

        R = set()
        R.clear()

        if s.Simbolo in _visitados:
            return R
        _visitados.add(s.Simbolo)
        if self.NumReglas > 0 and s.Simbolo == self.ArrReglas[0].SimbIzqGram.Simbolo:
            R.add(SimbGram("$", 0, True))

        for i in range(self.NumReglas):
            regla_actual = self.ArrReglas[i]
            for j in range(len(regla_actual.l)):
                if regla_actual.l[j].Simbolo == s.Simbolo:
                    l2 = regla_actual.l[j + 1:]
                    if len(l2) > 0:
                        first_l2 = self.First(l2)
                        tiene_eps = self.ContieneEpsilon(first_l2)
                        if tiene_eps:
                            self.QuitarEpsilon(first_l2)
                        R.update(first_l2)

                        if tiene_eps and regla_actual.SimbIzqGram.Simbolo != s.Simbolo:
                            R.update(self.Follow(regla_actual.SimbIzqGram, _visitados.copy()))
                    else:
                        if regla_actual.SimbIzqGram.Simbolo != s.Simbolo:
                            R.update(self.Follow(regla_actual.SimbIzqGram, _visitados.copy()))

        return R

    # Metodos para implementar exitosamente la clase AnalizadorLL1
    FIN = "$"

    @property
    def reglas(self):
        return [
            (r.SimbIzqGram.Simbolo, [s.Simbolo for s in r.l])
            for r in self.ArrReglas[:self.NumReglas]
        ]

    def first_secuencia(self, secuencia: list) -> set:
        nodos = [SimbGram(sim, sim == self.EPSILON, sim != self.EPSILON) for sim in secuencia]
        return {s.Simbolo for s in self.First(nodos)}

    @property
    def follow(self) -> dict:
        no_nts = {r.SimbIzqGram.Simbolo for r in self.ArrReglas[:self.NumReglas]}
        return {
            nt: {s.Simbolo for s in self.Follow(SimbGram(nt, 0, False))}
            for nt in no_nts
        }

    # Metodo para dar soporte a la clase AnalizadorLR0
    @property
    def simbolo_inicial(self) -> str:
        if self.ArrReglas and self.NumReglas > 0:
            return self.ArrReglas[0].SimbIzqGram.Simbolo
        return ""


class TablaLL1:
    def __init__(self, gram_ll1: Gramatica = None, simb_term: list = None, simb_no_term: list = None):
        self.GramLL1 = gram_ll1 if gram_ll1 is not None else Gramatica()
        self.SimbTerm = simb_term if simb_term is not None else []
        self.SimbNoTerm = simb_no_term if simb_no_term is not None else []
        self.Tabla = []

    def ConstruirTabla(self):
        filas = len(self.SimbNoTerm)
        columnas = len(self.SimbTerm)
        self.Tabla = [[-1 for _ in range(columnas)] for _ in range(filas)]

        mapa_no_term = {s.Simbolo: idx for idx, s in enumerate(self.SimbNoTerm)}
        mapa_term = {s.Simbolo: idx for idx, s in enumerate(self.SimbTerm)}

        for i in range(self.GramLL1.NumReglas):
            regla = self.GramLL1.ArrReglas[i]
            fila = mapa_no_term.get(regla.SimbIzqGram.Simbolo, -1)
            if fila == -1:
                continue

            conj_first = self.GramLL1.First(regla.l)
            for term in conj_first:
                if term.Simbolo != EPSILON and term.Simbolo in mapa_term:
                    col = mapa_term[term.Simbolo]
                    self.Tabla[fila][col] = i

            if self.GramLL1.ContieneEpsilon(conj_first):
                conj_follow = self.GramLL1.Follow(regla.SimbIzqGram)
                for term_follow in conj_follow:
                    if term_follow.Simbolo in mapa_term:
                        col = mapa_term[term_follow.Simbolo]
                        self.Tabla[fila][col] = i