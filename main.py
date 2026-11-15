from base import Estado, Transicion, EPSILON
from afn import AFN

# ==============================================================
#  PRUEBAS INDEPENDIENTES
# ==============================================================
if __name__ == "__main__":
    Estado.ContEdos = 0

    afn_letras = AFN().CrearBasico('a', 'z').cerraduraPos()
    for edo in afn_letras.EdosAcept:
        edo.Token = 10

    afn_numeros = AFN().CrearBasico('0', '9').cerraduraPos()
    for edo in afn_numeros.EdosAcept:
        edo.Token = 20

    afn_lexico = AFN()
    estado_inicial_global = Estado()

    estado_inicial_global.Transiciones.add(Transicion(EPSILON, afn_letras.EdoIni))
    estado_inicial_global.Transiciones.add(Transicion(EPSILON, afn_numeros.EdoIni))

    afn_lexico.EdoIni = estado_inicial_global
    afn_lexico.EdosAFN.add(estado_inicial_global)
    afn_lexico.EdosAFN.update(afn_letras.EdosAFN)
    afn_lexico.EdosAFN.update(afn_numeros.EdosAFN)
    afn_lexico.EdosAcept.update(afn_letras.EdosAcept)
    afn_lexico.EdosAcept.update(afn_numeros.EdosAcept)
    afn_lexico.Alfabeto.update(afn_letras.Alfabeto)
    afn_lexico.Alfabeto.update(afn_numeros.Alfabeto)

    afd_final = afn_lexico.Convertir_a_AFD()
    print(f"=== AFD construido: {afd_final.NumEdos} estados ===")