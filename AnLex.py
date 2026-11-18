# analizador léxico
from afd import AFD


class SimbolosEspeciales:
    EPSILON = chr(5)
    FIN = 0
    ERROR = 20000
    OMITIR = 20001


class EstadoAnalizadorLexico:
    """Clase Memento para guardar y restaurar el estado del analizador léxico."""
    def __init__(self):
        self.caracter_actual = ''
        self.edo_actual = 0
        self.edo_transicion = -1
        self.fin_lexema = -1
        self.indice_caracter_actual = 0
        self.ini_lexema = 0
        self.lexema = ""
        self.paso_por_edo_acept = False
        self.token = -1
        self.pila = []


class AnalizadorLexico:
    def __init__(self, afd_lexico=None, cadena_sigma="", ruta_archivo_afd=None, id_afd=None):
        self.yytext = ""
        self.sigma = cadena_sigma
        self.PasoPorEdoAcept = False
        self.IndCaracActual = 0
        self.IndIniLexema = 0
        self.IndFinLexema = -1
        self.EdoActual = 0
        self.EdosTransicion = -1
        self.CaracterActual = ''
        self.token = -1
        self.pila = []

        if afd_lexico is not None:
            self.AFD_Lexico = afd_lexico
        elif ruta_archivo_afd is not None:
            self.AFD_Lexico = AFD()
            self.AFD_Lexico.leerArchivo(ruta_archivo_afd, id_afd)
        else:
            self.AFD_Lexico = None

    def SetSigma(self, cadena_sigma):
        self.sigma = cadena_sigma
        self.PasoPorEdoAcept = False
        self.IndCaracActual = 0
        self.IndIniLexema = 0
        self.IndFinLexema = -1
        self.token = -1
        self.pila.clear()

    def CadenaXAnalizar(self):
        return self.sigma[self.IndCaracActual:]

    def GetEdoAnalizLexico(self):
        estado = EstadoAnalizadorLexico()
        estado.caracter_actual = self.CaracterActual
        estado.edo_actual = self.EdoActual
        estado.edo_transicion = self.EdosTransicion
        estado.fin_lexema = self.IndFinLexema
        estado.indice_caracter_actual = self.IndCaracActual
        estado.ini_lexema = self.IndIniLexema
        estado.lexema = self.yytext
        estado.paso_por_edo_acept = self.PasoPorEdoAcept
        estado.token = self.token
        estado.pila = self.pila.copy()
        return estado

    def SetEdoAnalizLexico(self, estado: EstadoAnalizadorLexico):
        self.CaracterActual = estado.caracter_actual
        self.EdoActual = estado.edo_actual
        self.EdosTransicion = estado.edo_transicion
        self.IndFinLexema = estado.fin_lexema
        self.IndCaracActual = estado.indice_caracter_actual
        self.IndIniLexema = estado.ini_lexema
        self.yytext = estado.lexema
        self.PasoPorEdoAcept = estado.paso_por_edo_acept
        self.token = estado.token
        self.pila = estado.pila.copy()
        return True

    def yylex(self):
        self.pila.append(self.IndCaracActual)

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
            if token == 20001:  return self.yylex()
            return token
        else:
            self.yytext = self.sigma[self.IndIniLexema : self.IndIniLexema + 1]
            self.IndCaracActual = self.IndIniLexema + 1
            return -1

    def UndoToken(self):
        if len(self.pila) == 0:
            return False
        self.IndCaracActual = self.pila.pop()
        return True