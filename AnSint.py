# Clase y constructores genrales para un alanizador sintactico con descenso recursivo
from AnLex import AnalizadorLexico

class AnalizadorSintactico:
    # Recibe la instancia del analizador léxico ya inicializado
    # Pasar como parámetro la instancia del analizador léxico ya inicializado a lexer
    def __init__(self, lexer: AnalizadorLexico):
        self.lexic = lexer

    def E(self):
        if self.T():
            if self.Ep():
                return True
        return False

    def Ep(self):
        token = self.lexic.yylex()
        if token == 10 or token == 20: #tokens para suma (+) y resta (-)
            if self.T():
                if self.Ep():
                    return True
            return False
        self.lexic.UndoToken() # Transición Epsilon (vacía)
        return True

    def T(self):
        if self.F():
            if self.Tp():
                return True
        return False

    def Tp(self):
        token = self.lexic.yylex()
        if token == 30 or token == 40: #tokens para multiplicación (*) y división (/)
            if self.F():
                if self.Tp():
                    return True
            return False
        self.lexic.UndoToken()
        return True

    def F(self):
        token = self.lexic.yylex()
# Se reemplaza el Switch por if/elif
        if token == 50: # Token 50: paréntesis izquierdo '('
            if self.E():
                token = self.lexic.yylex()
                if token == 60: # Token 60: paréntesis derecho ')'
                    return True
        elif token == 70: # Token 70: num
            return True    
        return False

    def IniSintact(self):
        if self.E():
            token = self.lexic.yylex()
            if token == 0: # Token 0: fin de cadena
                return True
        return False