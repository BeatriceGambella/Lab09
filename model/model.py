from database.parco_DAO import ParcoDAO
from database.escursione_DAO import EscursioneDAO
from database.punto_interesse_DAO import PuntoInteresseDAO

class Model:
    def __init__(self):
        self.escursioni_map = {} # Mappa ID escursione -> oggetti Escursione
        self.punti_interesse_map = {} # Mappa ID punto di interesse -> oggetti PuntoInteresse

        self._pacchetto_ottimo = []
        self._valore_ottimo: int = -1
        self._costo = 0

        #inizializzo parametri che verranno scelti dall'utente e la lista che conterrà tutte le escursioni per il parco scelto
        self._budget = None
        self._giorni = None
        self._escursione_parco = []

        # Caricamento
        self.load_escursioni()
        self.load_punti_interesse()
        self.load_relazioni()

    @staticmethod
    def load_parchi():
        """ Restituisce tutti i parchi disponibili """
        return ParcoDAO.get_parchi()

    def load_escursioni(self):
        """ Carica tutte le escursioni in un dizionario [id, Escursione]"""
        self.escursioni_map = EscursioneDAO.get_escursioni()

    def load_punti_interesse(self):
        """ Carica tutti i punti di interesse in un dizionario [id, PuntoInteresse]"""
        self.punti_interesse_map = PuntoInteresseDAO.get_punti_interesse()

    def load_relazioni(self):
        """
            Interroga il database per ottenere tutte le relazioni fra escursioni e punti di interesse e salvarle nelle strutture dati
            Collega escursione <-> punti di interesse.
            --> Ogni Escursione ha un set di PuntoInteresse.
            --> Ogni PuntoInteresse ha un set di Escursioni.
        """
        relazioni = EscursioneDAO.get_escursioni_punti_interesse()   #tutte le escursioni
        #itero tutte le relazioni fra escursioni e punti di interesse
        for relazione in relazioni:
            #se il punto di interesse e l'escursione sono contenuti nelle mappe li aggiungo ai set delle escursioni e dei punti di interesse
            if relazione['id_escursione'] in self.escursioni_map and relazione['id_punto_interesse'] in self.punti_interesse_map:
                escursione = self.escursioni_map[relazione['id_escursione']]
                punto_interesse = self.punti_interesse_map[relazione['id_punto_interesse']]
                escursione.punti_interesse.add(punto_interesse)
                punto_interesse.escursioni.add(escursione)

    def genera_pacchetto(self, id_parco: str, max_giorni: int = None, max_budget: float = None):
        """
        Calcola il pacchetto di escursioni ottimale per un parco rispettando i vincoli di durata, budget e punti di interesse unici.
        :param id_parco: id del parco
        :param max_giorni: numero massimo di giorni (può essere None --> nessun limite)
        :param max_budget: costo massimo del pacchetto (può essere None --> nessun limite)

        :return: self._pacchetto_ottimo (una lista di oggetti Escursione)
        :return: self._costo (il costo del pacchetto)
        :return: self._valore_ottimo (il voto complessivo dei visitatori per il pacchetto)
        """
        self._pacchetto_ottimo = []
        self._costo = 0
        self._valore_ottimo = -1

        self._escursione_parco = []
        #assegno ai parametri inizializzati all'inizio i valori scelti dall'interfaccia
        self._budget = max_budget
        self._giorni = max_giorni

        #iterando tutte le escursioni, mi salvo nella lista inizializzata all'inizio tutte quelle svolte nel parco selezionato
        for escursione in self.escursioni_map.values():
            if escursione.id_parco == id_parco:
                self._escursione_parco.append(escursione)

        #inizio la ricorsione per esplorare tutti i possibili pacchetti
        self._ricorsione(0, [], 0, 0, 0, set())

        return self._pacchetto_ottimo, self._costo, self._valore_ottimo

    def _ricorsione(self, start_index: int, pacchetto_parziale: list, durata_corrente: int, costo_corrente: float, valore_corrente: int, punti_usati: set):
        """ Algoritmo di ricorsione che deve trovare il pacchetto che massimizza il voto complessivo dei visitatori"""

        #aggiornamento soluzione ottima
        if valore_corrente > self._valore_ottimo:
            self._valore_ottimo = valore_corrente
            self._pacchetto_ottimo = pacchetto_parziale.copy()
            self._costo = costo_corrente

        #controllo condizione di terminazione (se sono state fatte tutte le escursione per il parco, se si è superato il budget o i giorni a disposizione)
        if start_index == len(self._escursione_parco) or (self._giorni is not None and durata_corrente == self._giorni) or \
                (self._budget is not None and costo_corrente == self._budget):
            return

        #generazione di tutte le soluzioni possibili
        for i in range(start_index, len(self._escursione_parco)):
            escursione = self._escursione_parco[i]

            #controllo vincoli
            risultato = self._vincoli(escursione, punti_usati, durata_corrente, costo_corrente)

            #se supera i vincoli salvo la nuova durata e il nuovo costo dopo l'aggiunta dell'escursione esaminata
            if risultato is not None:
                durata, costo = risultato

                #aggiunta dell'escursione che rispetta i vincoli
                pacchetto_parziale.append(escursione)
                punti_usati.update(escursione.punti_interesse)
                voto = valore_corrente
                for punto in escursione.punti_interesse:
                    voto = voto + punto.voto_visitatori

                #richiamo la ricorsione per procedere con la soluzione
                self._ricorsione(i + 1, pacchetto_parziale, durata, costo, voto, punti_usati)

                #elimino l'ultima escursione e i punti di interesse usati nell'ultima escursione per esplorare tutte le possibilità
                pacchetto_parziale.pop()
                punti_usati.difference_update(escursione.punti_interesse)

    # funzione che controlla i vincoli
    def _vincoli(self, escursione, punti_usati, durata_corrente, costo_corrente):
        #grazie allo start index tutte le escursioni saranno necessariamente diverse
        #controlla se sono presenti punti di interesse duplicati
        if punti_usati.intersection(escursione.punti_interesse):
            return None

        #trovo la durata e il costo della soluzione parziale
        durata = durata_corrente + escursione.durata_giorni
        costo = costo_corrente + escursione.costo

        #controllo che non si sia superato il budget e i giorni massimi
        if self._giorni is not None and durata > self._giorni:
            return None
        if self._budget is not None and costo > self._budget:
            return None

        return durata, costo
