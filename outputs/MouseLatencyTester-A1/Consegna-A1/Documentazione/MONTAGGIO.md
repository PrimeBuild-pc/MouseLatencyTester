# Montaggio A1b

Usare lo schema e le anteprime inclusi. Le viste del retro sono specchiate rispetto al fronte. Le coordinate qui sono viste dall'alto, origine nell'angolo alto sinistro del PCB, X verso destra e Y verso il basso.

## Popolamento

| Riferimenti | Componente | Lato / indicazioni |
|---|---|---|
| U1 | OPA380AIDR, SOIC-8 passo 1,27 mm | Fronte; pin 1 come footprint, non orientare dalla scritta dell'inserzione |
| U2 | TLV3501AID/AIDR, SOIC-8 passo 1,27 mm | Fronte; non intercambiare U1/U2 |
| U3 | Teensy 2.0 | Fronte; USB Mini-B verso bordo sinistro |
| D1 | BPV10 | **Retro** (serigrafia `LATO MONITOR`), corpo rivolto al monitor; pad 1 quadrato con `K` = catodo, pad 2 = anodo. Fori Ø1,0 mm per i reofori 0,63 × 0,5 mm |
| C3 | 15 pF NP0/C0G 0805 | **Retro**, sotto U1; nessuna polarità |
| R1 | 10 kΩ 1% | Fronte, orizzontale, passo 7,62 mm |
| R2 | 10 kΩ 1% | Fronte, **verticale**, passo 2,54 mm |
| R3 | **1 MΩ 1%** (guadagno del TIA) | Fronte, verticale. **Corpo sul pad col cerchio serigrafato** (nodo SUM, verso R1); il reoforo ripiegato va sul pad verso U1 |
| R4 | 1 MΩ 1% | Fronte, verticale |
| R5 | 100 Ω 1% | Fronte, verticale |
| C1, C4, C5 | 100 nF ceramici radiali, fori a passo 2,5 mm | Fronte; terminali corti, specialmente C4/C5 vicino agli IC. Se i tuoi hanno passo 5 mm piega i reofori verso l'interno e tieni il corpo a ridosso della scheda |
| C2, C6 | 10 µF 16 V radiali, Ø4 mm, passo 1,5 mm | Fronte, polarizzati: pad 1 quadrato = positivo, pad 2 = negativo/GND |
| RV1 | 3296W 10 kΩ | Fronte; vite accessibile dal case |
| SW1, SW2 | Pulsanti 6 × 6 mm THT a 4 gambe, altezza riferimento 4,3 mm | Fronte; verificare orientamento e interassi prima di saldare |
| J1 | Header 1 × 4, passo 2,54 mm | Fronte; verso OLED con cavetto. Serigrafia `5V GND SCL SDA` |
| J2 | Header 1 × 2, passo 2,54 mm | Fronte; verso sonda esterna. Serigrafia `PROBE` sul pin 1 |

La fascia chiara degli elettrolitici indica normalmente il **negativo**: non allinearla al simbolo +. Nel disegno Vishay il catodo del BPV10 è il reoforo più corto (1,5 mm di differenza). Confermalo col tester in prova diodi prima di saldare: quando indica circa 0,5–0,7 V il puntale nero è sul catodo, che va nel pad quadrato `K`. Un BPV10 montato al contrario non si rompe ma porta TP2 a saturare verso massa.

I due SOIC si saldano direttamente: gli adattatori SOP→DIP acquistati non servono su questa scheda. Iniziare da C3 e dai SOIC, poi resistenze/ceramici, fotodiodo, elettrolitici, trimmer e connettori. Tenere accessibile il retro fino al termine della saldatura. Pulire bene il flussante attorno a U1, R3 e C3.

Il Teensy può essere rimovibile con due file da 12 contatti passo 2,54 mm, distanza fra le file 15,24 mm; una soluzione a pin saldati direttamente riduce l'altezza. I pin supplementari interni/di estremità non devono creare supporti disallineati: le due file esterne includono alimentazione, massa e tutti i segnali usati da A1. La numerazione dei pad del modulo nel CAD non coincide con la numerazione Arduino.

## Collegamenti

**OLED J1 — ordine specifico del modulo fotografato EstarDyn 1.30 IIC V2.0:**

| Pin J1 | Rete | Pin OLED |
|---|---|---|
| 1, quadrato | +5 V | VDD |
| 2 | GND | GND |
| 3 | I2C_SCL | SCK/SCL |
| 4 | I2C_SDA | SDA |

Verificare la serigrafia del pezzo reale prima di alimentare: molti OLED di altre marche hanno VCC/GND invertiti. Usare un cavetto corto, non forzare il modulo sui fori del carrier.

**Sonda J2:** pin 1 quadrato = PROBE, pin 2 = GND. Predisposto per un contatto passivo normalmente aperto che chiude verso massa. Il pull-up va abilitato dal firmware. Nessuna tensione esterna va applicata alla sonda.

| Funzione | Porta ATmega32U4 / Teensy 2.0 | Uso previsto |
|---|---|---|
| BTN1, BTN2 | PB0, PB1 / Arduino 0, 1 | INPUT_PULLUP, pressione = basso |
| OLED SCL, SDA | PD0, PD1 / Arduino 5, 6 | I²C SH1106 |
| PROBE | PD2 / Arduino 7 | Inizio misura, fronte verso basso |
| OPT_TRIGGER | PD3 / Arduino 8 | Fine ottica, fronte FALLING |
| TIA_OUT | PF0 / A0 | Diagnostica analogica; non termine temporale della misura |

Il firmware attuale della versione KY-018 non viene trasformato automaticamente in firmware per il comparatore da questi file. Serve implementare e verificare timestamp locali dei due eventi, gestione timeout/riarmo e compatibilità con dashboard/OLED. Evitare aggiornamenti OLED/I²C durante la finestra di misura.

## Prima accensione e collaudo

1. Senza alimentazione verificare saldature, polarità e assenza di corto fra +5 V e GND; misurare i valori dei resistori prima di montarli. Controllare continuità dei contatti della sonda e dei pulsanti.
2. Alimentare dalla USB Mini-B del Teensy. La scheda è progettata per circa 5 V, non per la modifica Teensy a 3,3 V. Per la prima prova è preferibile un'alimentazione USB con corrente sorvegliata. Non unire una seconda alimentazione esterna al rail USB.
3. Con riferimento TP4 GND, verificare +5 V sui condensatori di bypass: deve stare fra 4,5 e 5,25 V. Sopra 5,5 V il TLV3501 è fuori dal massimo assoluto: cambiare porta o alimentatore. Attendere almeno un secondo e misurare TP1 VBIAS: circa metà alimentazione, nominalmente 2,5 V.
4. Leggere TP2 TIA_OUT con diodo oscurato e poi illuminato dal bianco del display. La tensione deve aumentare con la luce. Con R3 = 1 MΩ il guadagno è 1 V per µA: stima da datasheet 0,3–1,5 V di salto fra nero e bianco a 100–300 cd/m², non misurata. Oltre circa 4,4 V l'uscita satura: per il solo trigger non è un problema; se vuoi la telemetria A0 lineare su schermi molto luminosi scendi a 330–470 kΩ. Se il salto è sotto 100 mV controlla allineamento e polarità di D1 prima di toccare i valori. C3 = 15 pF con 1 MΩ dà una banda di circa 10 kHz, costante di tempo 15 µs.
5. Con oscilloscopio controllare che TP2 non oscilli e che il passaggio nero/bianco sia distinguibile. Regolare RV1 perché la soglia cada fra i due livelli, 0,1–0,2 V sopra il valore al buio (la soglia THRESH si misura sul piedino centrale di RV1); controllare TP3 CMP_RAW: il passaggio al bianco deve portare l'uscita verso basso. L'isteresi non deve impedire il riarmo al nero.
6. Verificare al Teensy che i fronti arrivino una sola volta, quindi collaudare il firmware ottico e il percorso completo. Solo dopo quantificare ripetibilità e errore, confrontando un riferimento temporale indipendente.

Non caricare il nodo SUM con puntali lunghi o con la capacità di una sonda ordinaria: effettuare le misure di routine sui punti di test predisposti. L'allineamento fra sonda meccanica e click del mouse resta parte dell'incertezza di misura.

## Quote per il futuro case

PCB 56 × 48 × 1,6 mm, smussi planari 2 mm. Fori Ø2,2 mm ai centri (3;3), (53;3), (3;45), (53;45). Queste sono quote del progetto, non tolleranze aggiuntive richieste al fabbricante. Usare il DXF incluso per il contorno e lasciare gioco per le tolleranze di produzione.

Prevedere sul lato monitor una cavità per D1 e i terminali saldati, una finestra ottica schermata e spazio per C3. Il fronte richiede spazio per Teensy, resistenze verticali, connettori e vite RV1. L'altezza complessiva dipende da zoccoli e header effettivi; misurarla prima di chiudere il case. Fissare e scaricare meccanicamente il cavo USB e quello della sonda.
