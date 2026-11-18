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

    def leerArchivo(self, ruta_archivo, id_afd=None):
        """
        Carga la tabla de transiciones de un AFD previamente serializado con guardarArchivo.
        """
        try:
            with open(ruta_archivo, 'r', encoding='utf-8') as f:
                lineas = [linea.strip() for linea in f if linea.strip()]

            num_edos = int(lineas[1].split(':')[1])
            alfabeto_str = lineas[2].split(':', 1)[1]
            alfabeto = alfabeto_str.split(',') if alfabeto_str else []

            self.Alfabeto = set(alfabeto)
            self.NumEdos = num_edos
            self.EdosAFD = [EdoAFD() for _ in range(num_edos)]
            self.EdosAcept.clear()

            for i in range(num_edos):
                self.EdosAFD[i].IdAFD = i

            # Las filas de transiciones comienzan después de la cabecera "TRANSICIONES" (índice 4)
            for linea in lineas[4:]:
                partes = linea.split('\t')
                id_edo = int(partes[0])
                edo_obj = self.EdosAFD[id_edo]

                for idx_sim, sim in enumerate(alfabeto):
                    dest = int(partes[idx_sim + 1])
                    edo_obj.TransEdo[ord(sim)] = dest
                    if dest != -1:
                        edo_obj.PonerTransicion(sim, dest)

                token = int(partes[-1])
                edo_obj.TransEdo[256] = token
                if token != -1:
                    edo_obj.EdoAcept = True
                    self.EdosAcept.add(edo_obj)

            if self.EdosAFD:
                self.EdoIni = self.EdosAFD[0]
            return True

        except Exception as e:
            raise Exception(f"Error al leer el AFD desde el archivo: {e}")

#auxiliar para subconjuntos
class Sj:  
    def __init__(self):
        self.Id = -1
        self.Edos = set()