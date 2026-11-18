#Calculadora con descenso recursivo y evaluador de expresiones aritméticas. Aplica AnLex y AnSint
from AnLex import AnalizadorLexico, SimbolosEspeciales


class EvaluadorExpr:
    def __init__(self, afd_lexico=None, cadena_sigma="", ruta_archivo_afd=None, id_afd=None, lexer_instancia=None):
        self.expresion = cadena_sigma
        self.result = 0.0
        self.expr_post = ""

        if lexer_instancia is not None:
            self.lexic = lexer_instancia
        else:
            self.lexic = AnalizadorLexico(
                afd_lexico=afd_lexico,
                cadena_sigma=cadena_sigma,
                ruta_archivo_afd=ruta_archivo_afd,
                id_afd=id_afd
            )

    def SetExpresion(self, sigma):
        self.expresion = sigma
        self.result = 0.0
        self.expr_post = ""
        self.lexic.SetSigma(sigma)

    def IniEval(self):
        exito, v, postfijo = self._E()
        if exito:
            token = self.lexic.yylex()
            if token == SimbolosEspeciales.FIN:
                self.result = v
                self.expr_post = postfijo.strip()
                return True
        return False

    def _E(self):
        exito, v, post = self._T()
        if exito:
            exito_ep, v, post = self._Ep(v, post)
            if exito_ep:
                return True, v, post
        return False, 0.0, ""

    def _Ep(self, v, post):
        token = self.lexic.yylex()
        if token == 10 or token == 20:  # + o -
            exito, v2, post2 = self._T()
            if exito:
                v = v + (v2 if token == 10 else -v2)
                op_str = "+" if token == 10 else "-"
                post = f"{post} {post2} {op_str}"
                return self._Ep(v, post)
            return False, 0.0, ""

        self.lexic.UndoToken()
        return True, v, post

    def _T(self):
        exito, v, post = self._F()
        if exito:
            exito_tp, v, post = self._Tp(v, post)
            if exito_tp:
                return True, v, post
        return False, 0.0, ""

    def _Tp(self, v, post):
        token = self.lexic.yylex()
        if token == 30 or token == 40:  # * o /
            exito, v2, post2 = self._F()
            if exito:
                if token == 40 and v2 == 0:
                    raise ZeroDivisionError("Error Semántico: División entre cero")
                v = v * (v2 if token == 30 else (1.0 / v2))
                op_str = "*" if token == 30 else "/"
                post = f"{post} {post2} {op_str}"
                return self._Tp(v, post)
            return False, 0.0, ""

        self.lexic.UndoToken()
        return True, v, post

    def _F(self):
        token = self.lexic.yylex()
        if token == 50:  # '('
            exito, v, post = self._E()
            if exito:
                token_cierre = self.lexic.yylex()
                if token_cierre == 60:  # ')'
                    return True, v, post
        elif token == 70:  # NUM
            v = float(self.lexic.yytext)
            post = str(self.lexic.yytext)
            return True, v, post

        return False, 0.0, ""