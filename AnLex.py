# analizador léxico
class AnalizadorLexico:
    def __init__(self, afd_lexico=None, cadena_sigma=""):
        self.yytext = ""
        self.AFD_Lexico = afd_lexico
        self.sigma = cadena_sigma
        self.PasoPorEdoAcept = False
        self.IndCaracActual = 0
        self.IndIniLexema = 0
        self.IndFinLexema = -1

    def AnaliLexic(self, cadena_sigma):
        self.sigma = cadena_sigma
        self.PasoPorEdoAcept = False
        self.IndCaracActual = 0
        self.IndIniLexema = 0
        self.IndFinLexema = -1

    def yylex(self):
        self.PasoPorEdoAcept = False
        self.IndIniLexema = self.IndCaracActual
        EdoActual = 0
        token = -1

        if self.IndCaracActual >= len(self.sigma):
            return 0

        while self.IndCaracActual < len(self.sigma):
            caracter = self.sigma[self.IndCaracActual]
            idx = ord(caracter)

            if idx >= 257:
                break

            EdoActual = self.AFD_Lexico.EdosAFD[EdoActual].TransEdo[idx]

            if EdoActual != -1:
                if self.AFD_Lexico.EdosAFD[EdoActual].TransEdo[256] != -1:
                    self.IndFinLexema = self.IndCaracActual
                    self.PasoPorEdoAcept = True
                    token = self.AFD_Lexico.EdosAFD[EdoActual].TransEdo[256]

                self.IndCaracActual += 1
                continue
            else:
                break

        if self.PasoPorEdoAcept:
            self.yytext = self.sigma[self.IndIniLexema : self.IndFinLexema + 1]
            self.IndCaracActual = self.IndFinLexema + 1
            return token
        else:
            self.yytext = self.sigma[self.IndIniLexema : self.IndIniLexema + 1]
            self.IndCaracActual = self.IndIniLexema + 1
            return -1

    def UndoToken(self):
        self.IndCaracActual = self.IndIniLexema