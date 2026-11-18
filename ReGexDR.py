# Descenso Recursivo para Expresiones Regulares
from AnLex import AnalizadorLexico
import afn


class ReGexDR:
    # --- Constantes de tipos de token ---
    TOK_OR       = 10   # '|'
    TOK_CONCAT   = 20   # '·'
    TOK_POS      = 30   # '+'
    TOK_KLEENE   = 40   # '*'
    TOK_OPC      = 50   # '?'
    TOK_BASICO   = 60   # símbolo literal
    TOK_PAREN_A  = 70   # '('
    TOK_RANGO    = 80   # '-'
    TOK_PAREN_C  = 90   # ')'

    def __init__(self, lexer: AnalizadorLexico):
        self.lexic = lexer

    def _asignar_afn(self, destino: afn.AFN, origen: afn.AFN):
        """Copia los atributos del AFN recién creado hacia el objeto pasado por referencia."""
        destino.Alfabeto = origen.Alfabeto
        destino.EdoIni = origen.EdoIni
        destino.EdosAcept = origen.EdosAcept
        destino.EdosAFN = origen.EdosAFN

    def _obtener_simbolo(self):
        """Extrae el carácter literal manejando secuencias de escape con '\\'."""
        if len(self.lexic.yytext) > 1 and self.lexic.yytext[0] == '\\':
            return self.lexic.yytext[1]
        return self.lexic.yytext[0]

    def IniSintact(self, f: afn.AFN):
        """Punto de entrada que valida la expresión regular completa hasta el EOF."""
        if self.E(f):
            token = self.lexic.yylex()
            if token == 0:
                return True
        return False

    def E(self, f: afn.AFN):
        if self.T(f):
            if self.Ep(f):
                return True
        return False

    def Ep(self, f: afn.AFN):
        token = self.lexic.yylex()
        if token == self.TOK_OR:
            f2 = afn.AFN()
            if self.T(f2):
                f.UnirAFN(f2)
                if self.Ep(f):
                    return True
            return False
        self.lexic.UndoToken()   # Transición Epsilon (vacía)
        return True

    def T(self, f: afn.AFN):
        if self.C(f):
            if self.Tp(f):
                return True
        return False

    def Tp(self, f: afn.AFN):
        token = self.lexic.yylex()
        if token == self.TOK_CONCAT:
            f2 = afn.AFN()
            if self.C(f2):
                f.Concatenar(f2)
                if self.Tp(f):
                    return True
            return False
        self.lexic.UndoToken()   # Transición Epsilon (vacía)
        return True

    def C(self, f: afn.AFN):
        if self.F(f):
            if self.Cp(f):
                return True
        return False

    def Cp(self, f: afn.AFN):
        token = self.lexic.yylex()
        if token == self.TOK_POS:
            f.cerraduraPos()
            return self.Cp(f)
        elif token == self.TOK_KLEENE:
            f.cerraduraKleen()
            return self.Cp(f)
        elif token == self.TOK_OPC:
            f.Opcional()
            return self.Cp(f)
        self.lexic.UndoToken()   # Transición Epsilon (vacía)
        return True

    def F(self, f: afn.AFN):
        token = self.lexic.yylex()

        if token == self.TOK_BASICO:
            simb1 = self._obtener_simbolo()
            nuevo_afn = f.CrearBasico(simb1)
            self._asignar_afn(f, nuevo_afn)
            return True

        elif token == self.TOK_PAREN_A:
            if self.E(f):
                token = self.lexic.yylex()
                if token == self.TOK_PAREN_C:
                    # Agrupación estándar: (E)
                    return True
                elif token == self.TOK_RANGO and len(f.EdosAFN) == 2:
                    # Rango de caracteres: (simb1-simb2)
                    trans_inicial = next(iter(f.EdoIni.Transiciones))
                    simb1 = trans_inicial.SimbInf
                    token = self.lexic.yylex()
                    if token != self.TOK_BASICO:
                        return False
                    simb2 = self._obtener_simbolo()
                    token = self.lexic.yylex()
                    if token == self.TOK_PAREN_C:
                        nuevo_afn = f.CrearBasico(simb1, simb2)
                        self._asignar_afn(f, nuevo_afn)
                        return True

        return False