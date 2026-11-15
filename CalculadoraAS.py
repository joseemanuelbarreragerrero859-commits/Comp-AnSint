# Calculadora que implementa acciones semanticas analizando sintaciticamente una expresion aritmetica
# aplicando descenso recursivo y dando un resultado

class AccSemCalc:
    def __init__(self, lexer_instancia):
        self.lexic = lexer_instancia

    def IniSintact(self):
        """Punto de entrada principal para evaluar y validar hasta el fin de cadena."""
        exito, v, post = self.E()
        if exito:
            token = self.lexic.yylex()
            if token == 0:  # Token 0: Fin de archivo / cadena (EOF)
                return True, v, post
        return False, 0.0, ""

    def E(self):
        exito, v, post = self.T()
        if exito:
            exito_ep, v, post = self.Ep(v, post)
            if exito_ep:
                return True, v, post
        return False, 0.0, ""

    def Ep(self, v, post):
        token = self.lexic.yylex()
        if token == 10 or token == 20:  # Token 10: '+', Token 20: '-'
            exito, v2, post2 = self.T()
            if exito:
                # Operación aritmética
                v = v + (v2 if token == 10 else -v2)
                
                # Construcción de la notación postfija
                op_str = " +" if token == 10 else " -"
                post = f"{post} {post2}{op_str}"
                
                # Llamada recursiva a Ep
                return self.Ep(v, post)
            return False, 0.0, ""
        
        # Transición Epsilon (vacía)
        self.lexic.deshacerToken()
        return True, v, post

    def T(self):
        exito, v, post = self.F()
        if exito:
            exito_tp, v, post = self.Tp(v, post)
            if exito_tp:
                return True, v, post
        return False, 0.0, ""

    def Tp(self, v, post):
        token = self.lexic.yylex()
        if token == 30 or token == 40:  # Token 30: '*', Token 40: '/'
            exito, v2, post2 = self.F()
            if exito:
                # Validar división entre cero
                if token == 40 and v2 == 0:
                    raise ZeroDivisionError("Error Semántico: División entre cero")
                
                # Operación aritmética
                v = v * (v2 if token == 30 else (1.0 / v2))
                
                # Construcción de la notación postfija
                op_str = " *" if token == 30 else " /"
                post = f"{post} {post2}{op_str}"
                
                # Llamada recursiva a Tp (Corregido: en el pseudocódigo llamaba a Ep por error)
                return self.Tp(v, post)
            return False, 0.0, ""
        
        # Transición Epsilon (vacía)
        self.lexic.deshacerToken()
        return True, v, post

    def F(self):
        token = self.lexic.yylex()
        
        if token == 50:  # Token 50: '('
            exito, v, post = self.E()
            if exito:
                token_cierre = self.lexic.yylex()
                if token_cierre == 60:  # Token 60: ')'
                    return True, v, post
                    
        elif token == 70:  # Token 70: Número / Identificador
            v = float(self.lexic.yytext)
            post = str(self.lexic.yytext)  # Se asigna el valor al string postfijo
            return True, v, post

        return False, 0.0, ""