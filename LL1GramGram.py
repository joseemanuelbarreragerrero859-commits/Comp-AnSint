from AnLex import AnalizadorLexico
from base import EPSILON
from GramLL1 import SimbGram, ElemArrGram, Gramatica


class TokensGram_Gram:
    PC = 10       # ';'
    FLECHA = 20   # '->'
    SIMBOLO = 30  # Identificador de símbolo terminal o no terminal
    OR = 40       # '|'


class DescRecGram_Gram:
    def __init__(self, sigma: str = "", afd_lexico=None, lexer_instancia: AnalizadorLexico = None):
        self.Gramatica = sigma
        if lexer_instancia is not None:
            self.Lexic = lexer_instancia
        else:
            self.Lexic = AnalizadorLexico(afd_lexico, sigma)

        self.GramLL1 = Gramatica()
        self.ArrReglas = []
        self.NumReglas = 0

        self.Vn = set()
        self.Vt = set()
        self.ConjNoTerm = set()
        self.ConjTerm = set()
        self.ArrVt = []

    def SetGramatica(self, sigma: str) -> bool:
        self.Gramatica = sigma
        self.Lexic.AnaliLexic(sigma)
        self.GramLL1 = Gramatica()
        self.ArrReglas = []
        self.NumReglas = 0
        self.Vn.clear()
        self.Vt.clear()
        self.ConjNoTerm.clear()
        self.ConjTerm.clear()
        return True

    def AnalizarGramatica(self) -> bool:
        if self.G():
            token = self.Lexic.yylex()
            if token == 0:
                self._ClasificarSimbolos()
                self.GramLL1.ArrReglas = self.ArrReglas
                self.GramLL1.NumReglas = self.NumReglas
                return True
        return False

    def _ClasificarSimbolos(self):
        for i in range(self.NumReglas):
            for nodo in self.ArrReglas[i].l:
                if nodo.Simbolo == EPSILON:
                    nodo.EsTerminal = True
                elif nodo.Simbolo in self.Vn:
                    nodo.EsTerminal = False
                else:
                    nodo.EsTerminal = True
                    self.Vt.add(nodo.Simbolo)
                    self.ConjTerm.add(nodo)

        self.ConjTerm.add(SimbGram("$", 0, True))
        self.ArrVt = list(self.ConjTerm)

    def G(self) -> bool:
        if self.Reglas():
            return True
        return False

    def Reglas(self) -> bool:
        if self.Regla():
            Token = self.Lexic.yylex()
            if Token == TokensGram_Gram.PC:
                if self.ReglasP():
                    return True
        return False

    def ReglasP(self) -> bool:
        Token = self.Lexic.yylex()
        if Token == TokensGram_Gram.PC:
            if self.Reglas():
                if self.ReglasP():
                    return True
            return False
        self.Lexic.UndoToken()
        return True

    def Regla(self) -> bool:
        exito, NombLadoIzq = self.LadoIzq()
        if exito:
            s = SimbGram(NombLadoIzq, 0, False)
            self.ConjNoTerm.add(s)
            self.Vn.add(NombLadoIzq)
            Token = self.Lexic.yylex()
            if Token == TokensGram_Gram.FLECHA:
                if self.LadosDerechos(NombLadoIzq):
                    return True
        return False

    def LadoIzq(self):
        Token = self.Lexic.yylex()
        if Token == TokensGram_Gram.SIMBOLO:
            NombSimb = self.Lexic.yytext
            return True, NombSimb
        return False, ""

    def LadosDerechos(self, NombLadoIzq: str) -> bool:
        if self.LadoDerecho(NombLadoIzq):
            if self.LadosDerechosP(NombLadoIzq):
                return True
        return False

    def LadosDerechosP(self, NombLadoIzq: str) -> bool:
        Token = self.Lexic.yylex()
        if Token == TokensGram_Gram.OR:
            if self.LadoDerecho(NombLadoIzq):
                if self.LadosDerechosP(NombLadoIzq):
                    return True
            return False
        self.Lexic.UndoToken()
        return True

    def LadoDerecho(self, NombLadoIzq: str) -> bool:
        l = []
        s = SimbGram(NombLadoIzq, 0, False)
        if self.SecSimbolos(l):
            elem = ElemArrGram(s, l)
            self.ArrReglas.append(elem)
            self.NumReglas += 1
            return True
        return False

    def SecSimbolos(self, l: list) -> bool:
        Token = self.Lexic.yylex()
        if Token == TokensGram_Gram.SIMBOLO:
            Nodo = SimbGram(self.Lexic.yytext, 0, False)
            if self.SecSimbolosP(l):
                l.insert(0, Nodo)
                return True
        return False

    def SecSimbolosP(self, l: list) -> bool:
        Token = self.Lexic.yylex()
        if Token == TokensGram_Gram.SIMBOLO:
            Nodo = SimbGram(self.Lexic.yytext, 0, False)
            if self.SecSimbolosP(l):
                l.insert(0, Nodo)
                return True
            return False
        self.Lexic.UndoToken()
        return True