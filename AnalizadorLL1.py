from GramLL1 import Gramatica


class AnalizadorLL1:
    def __init__(self, gramatica: Gramatica):
        self.g = gramatica
        self.columnas = self.g.terminales + [Gramatica.FIN]
        self.filas = self.g.no_terminales + self.g.terminales + [Gramatica.FIN]
        self.tabla = {fila: {col: "" for col in self.columnas} for fila in self.filas}
        self.conflictos = []
        self._construir_tabla()

    def _construir_tabla(self):
        # 1. Reglas para No Terminales (numeradas desde 1 como en los apuntes)
        for num_regla, (izq, der) in enumerate(self.g.reglas, start=1):
            first_der = self.g.first_secuencia(der)

            for term in (first_der - {Gramatica.EPSILON}):
                self._asignar_celda(izq, term, str(num_regla))

            if Gramatica.EPSILON in first_der:
                for term in self.g.follow[izq]:
                    self._asignar_celda(izq, term, str(num_regla))

        # 2. Acciones POP para Terminales y Aceptar para '$'
        for term in self.g.terminales:
            self.tabla[term][term] = "POP"
        self.tabla[Gramatica.FIN][Gramatica.FIN] = "Aceptar"

    def _asignar_celda(self, fila, col, valor):
        if self.tabla[fila][col] != "" and self.tabla[fila][col] != valor:
            self.conflictos.append(
                f"Conflicto en ({fila}, {col}): ya tenía '{self.tabla[fila][col]}', se intentó poner '{valor}'"
            )
            self.tabla[fila][col] += f"/{valor}"
        else:
            self.tabla[fila][col] = valor