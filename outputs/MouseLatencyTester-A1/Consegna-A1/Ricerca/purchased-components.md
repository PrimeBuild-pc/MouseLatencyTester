# Componenti indicati negli screenshot degli ordini

8 novembre 2026. Lorenzo conferma di mantenere Teensy 2.0 e di avere acquistato i componenti della versione ottica futura. Le immagini degli ordini documentano le voci seguenti; non dimostrano identità del produttore, quote dei pezzi effettivamente ricevuti o prestazioni.

| Componente | Dato leggibile | Implicazione per il PCB |
|---|---|---|
| BPV10 | Variante selezionata BPV10, inserzione da 10 pezzi | Sensore del progetto attuale; package ottico cilindrico, da confermare fisicamente |
| BPW34 | Variante selezionata BPW34, inserzione da 5 pezzi | Alternativa piatta già acquistata; non confondere con una variante SMD dedotta dal titolo generico |
| Trimmer | 3296W 10K | Predisporre accesso alla vite nel case; verificare ingombro del pezzo reale |
| Condensatore feedback | 0805, 15 pF, NP0, 50 V | Conferma il formato SMD del condensatore; piazzole per saldatura manuale |
| Condensatori bypass | 100 nF, marcatura 104, ceramici radiali | Footprint e lunghezza collegamenti richiedono attenzione vicino agli IC veloci |
| Resistenze | Tre immagini di resistenze assiali; valori non leggibili | Non dedurre 10k/1M/100R dallo screenshot; valori necessari dalla distinta della repo da confermare |
| Adattatori | Kit SOP/SMD verso DIP | Utili per esperimenti; evitabili se gli IC vengono saldati direttamente sul PCB finale |
| Millefori | 5 × 7 cm | Materiale per prototipazione, non necessario alla scheda da produrre |

Le immagini successive confermano **OPA380AIDR SOIC-8** e **TLV3501AID/AIDR SOIC-8**. Le resistenze restano senza valori leggibili. L'OLED fotografato è **EstarDyn 1.30 IIC V2.0, SH1106 128×64**, piedinatura **1 VDD, 2 GND, 3 SCK/SCL, 4 SDA**; ingombro dichiarato 35,5 × 33,5 × 4,3 mm, header e fori reali da verificare. Collegamento A1 tramite cavetto. Teensy confermato **2.0**, USB **Mini-B**.

I **10 µF non risultano nelle foto**, come chiarito da Lorenzo, che può recuperarli da un amico. Selezionati **2 × Panasonic ECEA1CKS100**, elettrolitici radiali **10 µF 16 V, Ø4 mm, altezza 5 mm, passo 1,5 mm**, per C2 e C6. Sono polarizzati, pad 1 positivo, pad 2 GND; un equivalente deve rispettare anche il footprint e l'ingombro. I 100 nF ceramici locali sono mantenuti. La foto generica NP0 non mostra un condensatore da 10 µF.

La distinta A1b richiede **2 × 10 kΩ, 2 × 1 MΩ, 1 × 100 Ω, 1%** (R3 è passata da 10 kΩ a 1 MΩ nella revisione dell'11 novembre). Verificare i pezzi già disponibili con il tester. R1 orizzontale; R2–R5 verticali per ridurre l'ingombro. Pulsanti scelti sul PCB: THT 6 × 6 mm, 4 terminali, altezza di riferimento 4,3 mm; confrontarli con i pezzi disponibili. Header/cavetti ed eventuali zoccoli del Teensy non erano documentati completamente nelle foto.

## BPV10 o BPW34

Fonti primarie: [Vishay BPV10](https://www.vishay.com/docs/81502/bpv10.pdf), [Vishay BPW34](https://www.vishay.com/docs/81521/bpw34.pdf).

BPV10 è un sensore cilindrico da 5 mm con angolo di metà sensibilità ±20°. BPW34 è piatto, 5,4 × 4,3 × 3,2 mm, angolo ±65°. Il secondo offre un'opzione meccanica interessante per un sensore rivolto al monitor in un case piatto, ma questa è una valutazione progettuale, non una superiorità di accuratezza dimostrata.

La capacità tipica a zero bias differisce: 11 pF per BPV10, 70 pF per BPW34. La scelta del fotodiodo richiede quindi nuova verifica della compensazione del TIA, banda e stabilità; non basta cambiare footprint lasciando senza verifica Rf/Cf. Non collegare entrambi i sensori in parallelo per renderli selezionabili. Se si prevedono due popolamenti o due piccole teste ottiche, quello non montato deve restare elettricamente escluso e il nodo invertente deve mantenere percorsi molto corti.

Proposta: mantenere BPV10 come riferimento iniziale coerente con la distinta della repo, valutando BPW34 per il formato compatto dopo il confronto del segnale sul display e della stabilità del TIA. Non ordinare due elettroniche diverse solo per usare tutti i pezzi acquistati.
