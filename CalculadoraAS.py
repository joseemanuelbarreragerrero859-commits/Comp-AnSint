#Calculadora con descenso recursivo y evaluador de expresiones aritméticas. Aplica AnLex y AnSint
from AnLex import AnalizadorLexico, SimbolosEspeciales


class EvaluadorExpr:
# --- Constantes de tipos de token ---
    TOK_SUM     = 10   # '+'
    TOK_RES     = 20   # '-'
    TOK_PROD    = 30   # '*'
    TOK_DIV     = 40   # '/'
    TOK_PAR_I   = 50   # '('
    TOK_PAR_D   = 60   # ')'
    TOK_num     = 70   # [0-9]+(\.[0-9]+)?

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
        if token == self.TOK_SUM or token == self.TOK_RES:  # + o -
            exito, v2, post2 = self._T()
            if exito:
                v = v + (v2 if token == self.TOK_SUM else -v2)
                op_str = "+" if token == self.TOK_SUM else "-"
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
        if token == self.TOK_PROD or token == self.TOK_DIV:  # * o /
            exito, v2, post2 = self._F()
            if exito:
                if token == self.TOK_DIV and v2 == 0:
                    raise ZeroDivisionError("Error Semántico: División entre cero")
                v = v * (v2 if token == self.TOK_PROD else (1.0 / v2))
                op_str = "*" if token == self.TOK_PROD else "/"
                post = f"{post} {post2} {op_str}"
                return self._Tp(v, post)
            return False, 0.0, ""

        self.lexic.UndoToken()
        return True, v, post

    def _F(self):
        token = self.lexic.yylex()
        if token == self.TOK_PAR_I:  # '('
            exito, v, post = self._E()
            if exito:
                token_cierre = self.lexic.yylex()
                if token_cierre == self.TOK_PAR_D:  # ')'
                    return True, v, post
        elif token == self.TOK_num:  # NUM
            v = float(self.lexic.yytext)
            post = str(self.lexic.yytext)
            return True, v, post

        return False, 0.0, ""
