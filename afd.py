#  Clases auxiliares del AFD
class EdoAFD:
    def __init__(self):
        self.TransEdo = [-1] * 257
        self.IdAFD = 0
        self.EdoAcept = False
        self.Transiciones = dict()

    def PonerTransicion(self, sim, edo_dest):
        self.Transiciones[sim] = edo_dest


class AFD:
    def __init__(self):
        self.Alfabeto = set()
        self.EdosAFD = []
        self.EdoIni = None
        self.EdosAcept = set()
        self.NumEdos = 0
        
    def guardarArchivo(self, ruta_archivo, id_afd=None):
        """
        Serializa la tabla de transiciones del AFD en un archivo de texto plano.
        """
        try:
            with open(ruta_archivo, 'w', encoding='utf-8') as f:
                f.write(f"ID_AFD:{id_afd if id_afd else 'Sin_ID'}\n")
                f.write(f"NUM_EDOS:{self.NumEdos}\n")
                
                alfabeto_ordenado = sorted(list(self.Alfabeto))
                f.write(f"ALFABETO:{','.join(alfabeto_ordenado)}\n")
                f.write("TRANSICIONES\n")
                
                for edo in self.EdosAFD:
                    fila = [str(edo.IdAFD)]
                    for sim in alfabeto_ordenado:
                        idx = ord(sim)
                        dest = edo.TransEdo[idx]
                        fila.append(str(dest))
                    
                    token = edo.TransEdo[256]
                    fila.append(str(token))
                    f.write('\t'.join(fila) + '\n')
                    
            print(f"El AFD se ha guardado correctamente en: {ruta_archivo}")
            return True
            
        except Exception as e:
            print(f"Error al guardar el AFD en el archivo: {e}")
            raise Exception(f"No se pudo guardar el archivo: {e}")

#auxiliar para subconjuntos
class Sj:  
    def __init__(self):
        self.Id = -1
        self.Edos = set()