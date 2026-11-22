EPSILON = 'EPSILON'

class Estado:
    ContEdos = 0

    def __init__(self):
        self.IdEdo = Estado.ContEdos
        Estado.ContEdos += 1
        self.EdoAcept = False
        self.Token = -1
        self.Transiciones = set()

def reiniciar_contador_estados():
    """Reinicia el contador estático de estados a 0."""
    Estado.ContEdos = 0


class Transicion:
    def __init__(self, *args):
        if len(args) == 2:
            self.SimbInf = args[0]
            self.SimbSup = args[0]
            self.EdoDest = args[1]
        elif len(args) == 3:
            self.SimbInf = args[0]
            self.SimbSup = args[1]
            self.EdoDest = args[2]