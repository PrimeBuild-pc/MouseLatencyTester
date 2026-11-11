# MouseLatencyTester: decisione su PCB e case

Ricerca e progettazione del 2026-11-08. Aggiornamento: completato il PCB compatto Prototype A1 / BPV10, 56 × 48 mm, due layer. Schema/PCB, Gerber, forature, distinta e istruzioni sono nel pacchetto `outputs/MouseLatencyTester-A1/MouseLatencyTester-A1-Progetto.zip`. ERC e DRC puliti; collaudo fisico e firmware ottico ancora da svolgere.

## Raccomandazione

Conservare MouseLatencyTester e la dashboard, senza archiviare o cancellare la repo. Per costruire con i componenti già acquistati, è ragionevole mantenere il Teensy 2.0 nella prima revisione e sviluppare il nuovo front-end ottico con misurazione locale di entrambi i fronti. La conferma dipende dall'inventario reale dei componenti e dalla verifica del timer/interrupt del firmware. Non vi è evidenza che una migrazione a Teensy 4.1, da sola, migliori l'accuratezza del sistema.

La finalità è un dispositivo ispirato al formato LDAT, non una replica con equivalenza di precisione dimostrata. La fotografia fornita è un riferimento estetico; non permette di ricavare quote affidabili.

## Progetti confrontati

| Progetto | Materiale verificato | Conseguenza pratica |
|---|---|---|
| [MouseLatencyTester](https://github.com/PrimeBuild-pc/MouseLatencyTester) | Teensy 2.0, SH1106, KY-018, due pulsanti, dashboard; progetto BPV10/OPA380/TLV3501 dichiarato non costruito e senza firmware dedicato; nessun KiCad/Gerber nel tree esaminato | Riutilizzare applicazione e percorso esistente; il front-end nuovo richiede progetto e collaudo |
| [Open-Source-LDAT di S4N-T0S](https://github.com/S4N-T0S/Open-Source-LDAT) | Teensy 4.1, SSD1306, TEMT6000, firmware e immagine di cablaggio; nessun PCB/Gerber/case nel tree | Riferimento per modalità e utilizzo; nessun PCB pronto per i componenti di Lorenzo |
| [MiSTer Laggy](https://github.com/MiSTer-devel/MiSTerLaggy_MiSTer/blob/main/Readme.md) | Core MiSTer DE-10, sensore sul User Port, KiCad e case STEP/STL | Misura il percorso video/display a partire dal segnale generato da MiSTer, non mouse/PC/gioco |
| [OpenLDAT di Federico Dossena](https://github.com/adolfintel/OpenLDAT) | App, firmware, hardware Fritzing e Gerber in Device/Hardware, case STL in Device/Case | Riferimento concreto per evitare lavoro duplicato; elettronica, sensore e protocollo non sono intercambiabili con la soluzione proposta |

Il sito del negozio UltimateMiSTer ha restituito 403, e la pagina TechPowerUp non è risultata accessibile tramite il browser di ricerca. Il confronto funzionale di MiSTer Laggy deriva dal progetto originale, quello di LDAT dalla [pagina ufficiale NVIDIA](https://developer.nvidia.com/nvidia-latency-display-analysis-tool). Nessun acquisto consigliato sulla base di pagine non lette.

## Misure da distinguere

- Probe-to-PC: contatto della sonda fino alla risposta software; dipende anche dal percorso Windows/USB e dalla calibrazione. Non comprende il display.
- Probe-to-Photon: contatto della sonda fino alla luce rilevata. Nel progetto attuale usa KY-018 e ADC; il nuovo circuito deve timestampare il comparatore localmente. Il dashboard non deve definire l'istante finale della misura ottica.
- Click USB generato dal dispositivo: non misura la latenza del mouse fisico che non viene utilizzato.
- Display lag con un generatore video: non equivale al percorso completo mouse/PC/gioco/display.

La sonda esterna non rileva direttamente il contatto elettrico dello switch del mouse. L'allineamento meccanico rimane una fonte di errore anche con un sensore ottico più veloce. Risoluzione numerica, frequenza USB, velocità del sensore e accuratezza complessiva sono grandezze diverse.

## Due forme da valutare, una sola prima produzione

1. **Compatta, proposta principale:** PCB e Teensy nello stesso case da fissare al monitor; BPV10 e analogica vicini alla finestra ottica; pulsanti/connettori accessibili; eventuale OLED verso l'esterno o opzionale. Quote da definire sui componenti reali, non sulla foto. La posizione deve escludere luce ambientale e luce di eventuali LED/OLED dal percorso del sensore.
2. **Base e testa ottica separate:** testa piccola con BPV10, TIA e comparatore; base con Teensy, OLED e controlli. Portare fuori dalla testa il segnale digitale e, se utile, un'uscita analogica condizionata; evitare un lungo filo fra fotodiodo e ingresso TIA. Maggiori connettori e ingombro complessivo, ma meno peso sul monitor e regolazioni più comode.

È stata realizzata la prima opzione come PCB A1. La testa separata resta una possibilità successiva al collaudo, senza un secondo pacchetto di produzione. I SOIC acquistati vengono saldati direttamente. Il case 3D non è ancora realizzato: DXF con contorno e fori incluso; altezze dell'assieme da misurare.

## Condizioni per tracciare ed esportare

Lorenzo ha confermato il Teensy 2.0. Le foto documentano BPV10, BPW34 aggiuntivo, 3296W 10k, 15 pF NP0 0805, 100 nF radiali, resistenze senza valori leggibili, OPA380AIDR e TLV3501AID/AIDR SOIC-8, adattatori e millefori. L'OLED è SH1106 I²C 1,3 pollici, VDD/GND/SCK/SDA; viene collegato con cavetto per non inventare interassi. I 10 µF non risultano acquistati e Lorenzo autorizza a recuperarli: selezionati due ECEA1CKS100, 10 µF 16 V radiali Ø4 mm, altezza 5 mm, passo 1,5 mm. Vedere [inventario](purchased-components.md).

Completati schema, layout con punti di test e accesso al trimmer, controlli ERC/DRC, confronto schema-PCB e verifica dei Gerber/forature dalla stessa revisione. Da svolgere: costruzione e prove di stabilità/soglia, firmware per il comparatore, verifica temporale e case. Le istruzioni di montaggio e la revisione nel pacchetto distinguono questi limiti dai controlli superati.

Regole confrontate con le [capacità ufficiali PCBWay](https://www.pcbway.com/capabilities.html): due layer FR-4, 1,6 mm, 1 oz, piste/distanze minime 0,2 mm, bordo rame 0,5 mm, vias 0,7/0,3 mm. Non sono stati preparati preventivi o effettuati ordini.

## Ruolo di text-to-cad

La [skill PCB pubblica](https://github.com/earthtojake/text-to-cad/blob/main/skills/pcb/SKILL.md) è stata usata concretamente per schemi/PCB KiCad, ERC/DRC ed esportazioni. La copia di lavoro completa è `hardware/compact/`; `hardware/optical-front-end/` conserva la prima bozza storica del solo front-end. Il pacchetto finale include una copia compatibile con KiCad 9, librerie locali e licenze. La conversione non ha segnalato perdite e passa i controlli. Lo strumento aiuta il progetto ma non sostituisce il collaudo fisico.
