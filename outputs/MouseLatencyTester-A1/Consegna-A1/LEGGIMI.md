# MouseLatencyTester — prototipo A1b, BPV10

Scheda compatta per i componenti acquistati da Lorenzo: Teensy 2.0, BPV10, OPA380AIDR, TLV3501AID, trimmer 3296W e OLED SH1106 I²C. Progetto del 2026-11-08, revisionato l'11 (A1b: guadagno del TIA, foro del BPV10, serigrafie; dettagli in `Documentazione/VERIFICHE.md`). Destinato a una prima costruzione e al collaudo. **I Gerber A1 precedenti non vanno più usati.**

**Il PCB è sbrogliato e passa i controlli documentati. Il circuito non è stato costruito o misurato. Il firmware per il nuovo ingresso del comparatore deve ancora essere implementato e verificato.** Non è dimostrata equivalenza di accuratezza con NVIDIA LDAT.

## File da usare

- `KiCad/mouse_latency_tester.kicad_pro`: aprire questo progetto con KiCad 9 o successivo. Schema, PCB e librerie locali sono inclusi. La conversione dalla copia di lavoro 10.99 non ha segnalato perdite; controlli ripetuti sulla copia 9.
- `PCBWay/`: sette Gerber, due Excellon separati PTH/NPTH e Gerber job. Lo ZIP PCBWay separato contiene solo questi file.
- `Documentazione/mouse_latency_tester-bom.csv`: distinta esportata dallo schema. TP1–TP4 sono piazzole già sul PCB, non componenti da comprare.
- `Documentazione/MONTAGGIO.md`: popolamento, piedinatura e prima accensione.
- `Documentazione/VERIFICHE.md` e `Controlli/`: risultati, limiti e confronto con PCBWay.
- `Meccanica/mouse_latency_tester-outline.dxf`: contorno e fori, in millimetri. Non è il modello completo dell'assieme.
- `Anteprime/`: render da Gerber, schema e disegno di assemblaggio. Il verde del render è illustrativo; il colore si sceglie nell'ordine.

## Ordine PCBWay

Caricare **MouseLatencyTester-A1-PCBWay.zip**, controllando l'anteprima CAM con i due file di foratura. Non caricare lo ZIP completo del progetto come pacchetto Gerber.

| Opzione | Scelta per A1 |
|---|---|
| Servizio | PCB nudi, saldatura manuale |
| Numero disegni | 1 |
| Dimensioni nominali | 56 × 48 mm |
| Layer | 2 |
| Materiale / spessore | FR-4 / 1,6 mm |
| Rame esterno | 1 oz |
| Finitura | HASL senza piombo; ENIG possibile |
| Solder mask / legenda | Verde / bianco; altri colori a scelta |
| Fori di fissaggio | 4 × Ø2,2 mm non metallizzati |
| Impedenza controllata / vias cieche / castellation | Nessuna |
| Stencil / assemblaggio | Non necessari |

I file non sono stati caricati o ordinati presso PCBWay. Il controllo CAM del produttore resta distinto dai controlli del progetto. Ordinare inizialmente un lotto da prototipo, prima di produrre varianti.

## Componenti da completare

Recuperare **2 × 10 µF 16 V**, elettrolitici radiali Ø4 mm, altezza 5 mm, passo 1,5 mm: riferimento Panasonic **ECEA1CKS100**. Un equivalente deve rispettare anche ingombro, passo e polarità. I condensatori già fotografati sono 15 pF 0805 e 100 nF radiali: non sostituiscono i 10 µF.

Controllare con il tester i valori delle resistenze già possedute: **2 × 10 kΩ, 2 × 1 MΩ, 1 × 100 Ω**, 1%, corpi assiali fino a circa 6,3 × 2,5 mm. Le foto non consentono di leggerli. Servono inoltre connettori/cavetti per OLED e sonda; eventuali zoccoli per il Teensy; due pulsanti THT 6 × 6 mm compatibili col footprint. Questi accessori non erano identificati completamente negli ordini.

## Case e varianti

Questa è la variante compatta A1: fotodiodo rivolto al monitor sul retro, Teensy/controlli sul fronte, OLED collegato con quattro fili. Il PCB ha quattro fori per viti M2, interasse 50 × 42 mm. Il case LDAT resta da disegnare sulle altezze del montaggio reale: non è incluso uno STL pronto da stampare.

Il modulo OLED dichiarato dal venditore misura 35,5 × 33,5 × 4,3 mm; sporgenza connettore e interassi dei suoi fori non sono stati accertati. Non sono state inventate quote per un montaggio rigido. Il connettore del Teensy 2.0 è **USB Mini-B**. La finestra del BPV10 deve escludere luce ambiente e luce dell'OLED.

Una testa ottica separata o una versione BPW34 si possono valutare dopo il collaudo di A1. BPW34 non va sostituito al BPV10 con soli cavetti: cambiano geometria e capacità del diodo, quindi compensazione e stabilità da verificare. Non sono inclusi altri Gerber da produrre contemporaneamente.

## Repo e alternative

Consiglio di mantenere MouseLatencyTester: la dashboard e il lavoro esistente sono riutilizzabili. S4N-T0S/Open-Source-LDAT usa hardware differente e non forniva un PCB/case nel tree esaminato. MiSTer Laggy misura il display con un sistema MiSTer; non sostituisce questo percorso mouse/PC. adolfintel/OpenLDAT include hardware e case, ma impiega elettronica/protocollo diversi. Il confronto dettagliato è allegato in `Ricerca/`.

text-to-cad è stato utile concretamente per creare, controllare ed esportare i file nativi KiCad; resta necessario il collaudo dell'elettronica. Nessuna modifica è stata pubblicata sulla repo GitHub.

## Fonti dei componenti

- [Teensy 2.0 / PJRC](https://www.pjrc.com/store/teensy.html), [pinout](https://www.pjrc.com/teensy/card2a_rev5_web.pdf), [dimensioni](https://www.pjrc.com/teensy/dimensions_teensy20.png).
- [OPA380 / TI](https://www.ti.com/lit/ds/symlink/opa380.pdf), [TLV3501 / TI](https://www.ti.com/lit/ds/symlink/tlv3501.pdf), [BPV10 / Vishay](https://www.vishay.com/docs/81502/bpv10.pdf).
- [Panasonic ECEA1CKS100](https://industrial.panasonic.com/ww/products/pt/aluminum-cap-lead/models/ECEA1CKS100).
- [Capacità PCBWay](https://www.pcbway.com/capabilities.html), consultate il 2026-11-08.
