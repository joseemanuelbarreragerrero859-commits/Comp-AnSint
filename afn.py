from collections import deque
from base import Estado, Transicion, EPSILON
from afd import EdoAFD, AFD, Sj

#Clase AFN (incluye conversión a AFD)
class AFN:
    def __init__(self):
        self.Alfabeto = set()
        self.EdoIni = None
        self.EdosAcept = set()
        self.EdosAFN = set()

    def CrearBasico(self, simb1, simb2=None):
        f = AFN()
        e1 = Estado()
        e2 = Estado()

        if simb2 is None:
            t = Transicion(simb1, e2)
            f.Alfabeto.add(simb1)
        else:
            t = Transicion(simb1, simb2, e2)
            for val in range(ord(simb1), ord(simb2) + 1):
                f.Alfabeto.add(chr(val))

        e1.Transiciones.add(t)
        e2.EdoAcept = True

        f.EdoIni = e1
        f.EdosAcept.add(e2)
        f.EdosAFN.add(e1)
        f.EdosAFN.add(e2)
        return f

    def UnirAFN(self, f2):
        e1 = Estado()
        e2 = Estado()

        e1.Transiciones.add(Transicion(EPSILON, self.EdoIni))
        e1.Transiciones.add(Transicion(EPSILON, f2.EdoIni))

        for edo in self.EdosAcept:
            edo.Transiciones.add(Transicion(EPSILON, e2))
            edo.EdoAcept = False

        for edo in f2.EdosAcept:
            edo.Transiciones.add(Transicion(EPSILON, e2))
            edo.EdoAcept = False

        e2.EdoAcept = True

        self.EdosAFN.update(f2.EdosAFN)
        self.EdosAFN.add(e1)
        self.EdosAFN.add(e2)

        self.EdoIni = e1
        self.EdosAcept.clear()
        self.EdosAcept.add(e2)
        self.Alfabeto.update(f2.Alfabeto)
        return self

    def Concatenar(self, f2):
        for e in self.EdosAcept:
            for t in f2.EdoIni.Transiciones:
                e.Transiciones.add(t)
            e.EdoAcept = False

        self.EdosAFN.update(f2.EdosAFN)
        if f2.EdoIni in self.EdosAFN:
            self.EdosAFN.remove(f2.EdoIni)

        self.EdosAcept.clear()
        self.EdosAcept.update(f2.EdosAcept)
        self.Alfabeto.update(f2.Alfabeto)
        return self

    def cerraduraPos(self):
        e1 = Estado()
        e2 = Estado()

        e2.EdoAcept = True
        e1.Transiciones.add(Transicion(EPSILON, self.EdoIni))

        for e in self.EdosAcept:
            e.Transiciones.add(Transicion(EPSILON, e2))
            e.Transiciones.add(Transicion(EPSILON, self.EdoIni))
            e.EdoAcept = False

        self.EdosAFN.add(e1)
        self.EdosAFN.add(e2)
        self.EdoIni = e1
        self.EdosAcept.clear()
        self.EdosAcept.add(e2)
        return self

    def cerraduraKleen(self):
        self.cerraduraPos()
        for e in self.EdosAcept:
            self.EdoIni.Transiciones.add(Transicion(EPSILON, e))
        return self

    def Opcional(self):
        e1 = Estado()
        e2 = Estado()

        e2.EdoAcept = True
        e1.Transiciones.add(Transicion(EPSILON, self.EdoIni))

        for e in self.EdosAcept:
            e.Transiciones.add(Transicion(EPSILON, e2))
            e.EdoAcept = False

        e1.Transiciones.add(Transicion(EPSILON, e2))

        self.EdosAFN.add(e1)
        self.EdosAFN.add(e2)
        self.EdoIni = e1
        self.EdosAcept.clear()
        self.EdosAcept.add(e2)
        return self

    # Conversión AFN → AFD
    def CerraduraEpsilon(self, c_edos):
        R = set()
        S = []
        if isinstance(c_edos, Estado):
            S.append(c_edos)
        else:
            for e in c_edos:
                S.append(e)

        while len(S) != 0:
            EdoAux = S.pop()
            R.add(EdoAux)
            for t in EdoAux.Transiciones:
                if t.SimbInf == EPSILON and t.SimbSup == EPSILON:
                    if t.EdoDest not in R and t.EdoDest not in S:
                        S.append(t.EdoDest)
        return R

    def Mover(self, c_edos, simb):
        R = set()
        if isinstance(c_edos, Estado):
            edos = {c_edos}
        else:
            edos = c_edos

        for e in edos:
            for t in e.Transiciones:
                if t.SimbInf != EPSILON and t.SimbInf <= simb <= t.SimbSup:
                    R.add(t.EdoDest)
        return R

    def IrA(self, C, S_simb):
        return self.CerraduraEpsilon(self.Mover(C, S_simb))

    def Convertir_a_AFD(self):
        NumConjSj = 0
        ConjSjSinAnalizar = deque()
        ConjTodosSj = []
        QEdosAFD = deque()

        def BuscarSj(conj_sj, sj_temp):
            for sj in conj_sj:
                if sj.Edos == sj_temp.Edos:
                    return sj.Id
            return -1

        SjAux = Sj()
        SjAux.Edos = self.CerraduraEpsilon(self.EdoIni)
        SjAux.Id = NumConjSj
        NumConjSj += 1

        ConjSjSinAnalizar.append(SjAux)
        ConjTodosSj.append(SjAux)

        while len(ConjSjSinAnalizar) != 0:
            SjAux = ConjSjSinAnalizar.popleft()
            EdojAFD = EdoAFD()
            EdojAFD.IdAFD = SjAux.Id

            for sim in sorted(self.Alfabeto):
                SjTemp = Sj()
                SjTemp.Edos = self.IrA(SjAux.Edos, sim)

                if len(SjTemp.Edos) == 0:
                    continue

                IdEdo = BuscarSj(ConjTodosSj, SjTemp)

                if IdEdo == -1:
                    SjTemp.Id = NumConjSj
                    NumConjSj += 1
                    ConjTodosSj.append(SjTemp)
                    ConjSjSinAnalizar.append(SjTemp)
                    EdojAFD.TransEdo[ord(sim)] = SjTemp.Id
                    EdojAFD.PonerTransicion(sim, SjTemp.Id)
                else:
                    EdojAFD.TransEdo[ord(sim)] = IdEdo
                    EdojAFD.PonerTransicion(sim, IdEdo)

            QEdosAFD.append(EdojAFD)

        ConvAFD = AFD()
        ConvAFD.NumEdos = NumConjSj
        ConvAFD.EdosAFD = [EdoAFD() for _ in range(NumConjSj)]
        ConvAFD.Alfabeto.update(self.Alfabeto)

        for i in range(NumConjSj):
            ConvAFD.EdosAFD[i].IdAFD = i

        while len(QEdosAFD) != 0:
            EdoAFDTemp = QEdosAFD.popleft()

            for j in range(257):
                ConvAFD.EdosAFD[EdoAFDTemp.IdAFD].TransEdo[j] = EdoAFDTemp.TransEdo[j]

            edos_sj_actual = set()
            for sj in ConjTodosSj:
                if sj.Id == EdoAFDTemp.IdAFD:
                    edos_sj_actual = sj.Edos
                    break

            EdoAceptAFD = list(self.EdosAcept.intersection(edos_sj_actual))

            if len(EdoAceptAFD) == 0:
                continue

            ConvAFD.EdosAFD[EdoAFDTemp.IdAFD].EdoAcept = True
            ConvAFD.EdosAFD[EdoAFDTemp.IdAFD].TransEdo[256] = EdoAceptAFD[0].Token

            if len(EdoAceptAFD) >= 2:
                print(f"Advertencia: ambigüedad en AFD estado {EdoAFDTemp.IdAFD}, "
                      f"tokens candidatos: {[e.Token for e in EdoAceptAFD]}")

        return ConvAFD
    
    def generar_diagrama(self, nombre_archivo="diagrama_afn"):
        """
        Recorre el AFN actual y genera su diagrama de estados utilizando Graphviz.
        Genera un archivo PNG y lo abre automáticamente en el visor del sistema.
        """
        try:
            from graphviz import Digraph
            
            dot = Digraph(name=nombre_archivo, format="png")
            dot.attr(rankdir='LR')
            
            dot.node('start', shape='point')
            if self.EdoIni:
                dot.edge('start', str(self.EdoIni.IdEdo))
                
            for edo in self.EdosAFN:
                forma = 'doublecircle' if edo in self.EdosAcept else 'circle'
                dot.node(str(edo.IdEdo), label=f"q{edo.IdEdo}", shape=forma)
                
                for t in edo.Transiciones:
                    if t.SimbInf == t.SimbSup:
                        etiqueta = "EPSILON" if t.SimbInf == EPSILON else str(t.SimbInf)
                    else:
                        etiqueta = f"[{t.SimbInf}-{t.SimbSup}]"
                        
                    dot.edge(str(edo.IdEdo), str(t.EdoDest.IdEdo), label=etiqueta)
                    
            dot.render(nombre_archivo, view=True, cleanup=True)
            return True
            
        except ImportError:
            raise Exception("El módulo 'graphviz' no está instalado en Python.")
        except Exception as e:
            raise Exception(f"Error al generar el diagrama: {e}")