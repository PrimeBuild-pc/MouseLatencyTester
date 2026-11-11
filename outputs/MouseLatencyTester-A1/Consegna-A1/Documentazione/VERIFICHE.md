# Revisione del prototipo A1b

Ambito: `mouse_latency_tester`, revisione Prototype A1b / BPV10 dell'11 novembre 2026. PCBWay, PCB nudi FR-4 a due layer, 1,6 mm, rame esterno 1 oz, finitura HASL senza piombo. Saldatura a mano di Lorenzo. Nessun servizio di approvvigionamento o assemblaggio esaminato.

## Revisione indipendente dell'11 novembre: cosa è cambiato

Schema, piedinature, footprint, alimentazione e layout sono stati riletti sui datasheet Vishay BPV10 (rev. 2.1), TI OPA380 (SBOS291G) e TLV3501 (SBOS321E), sul pinout e sulle quote PJRC del Teensy 2.0 e sulla geometria salvata nel PCB.

| Punto | Evidenza | Esito | Modifica |
|---|---|---|---|
| Guadagno del TIA, R3 | BPV10: 70 µA tipici a 1 mW/cm² e 950 nm, sensibilità relativa 0,45 a 550 nm, semiangolo ±20°. Stima per il bianco di un display a 250 cd/m² appoggiato al sensore: circa 1 µA. Con 10 kΩ sono circa 10 mV, meno dell'isteresi del comparatore (6 mV interni + 12,5 mV da R4) | **Errore funzionale**: il comparatore non avrebbe commutato o non si sarebbe riarmato | R3 da 10 kΩ a **1 MΩ**: circa 1 V a 250 cd/m². C3 resta 15 pF: banda 10,6 kHz, τ = 15 µs, stabile (Cf minimo ≈ 0,15 pF) |
| Fori di D1 | Reofori 0,63 × 0,5 mm, diagonale 0,80 mm nominale e fino a 1,05 mm a tolleranza; foro 0,9 mm | A rischio di non entrare | Foro **1,0 mm**, piazzola 1,8 mm invariata, in libreria e sul PCB |
| Serigrafia | J1 senza nomi dei pin, punti di test e J2 anonimi, nessuna revisione sulla scheda | Rischio di cablare l'OLED al contrario | Aggiunti `5V GND SCL SDA`, `PROBE`, `VBIAS TIA CMP GND`, `MLT A1b 2026-11`; sul retro `K` e `LATO MONITOR` |
| Piedinatura U1, U2 | SO-8: 1 NC, 2 −IN, 3 +IN, 4 V−, 5 NC, 6 OUT, 7 V+, 8 NC (OPA380) / SHDN (TLV3501, basso = attivo) | Corretta | Nessuna |
| Polarità D1 e bias | Catodo su −IN, anodo a GND, +IN a 2,5 V: inversa 2,5 V; modo comune ammesso fino a V+ − 1,8 V = 3,2 V | Corretta, solo a 5 V | Nessuna |
| Teensy 2.0 | File a 15,24 mm, passo 2,54 mm, 12 + 12 + 5 + 2 fori; PD0/PD1 = SCL/SDA, PD2/PD3 = INT2/INT3, PF0 = ADC0; USB verso il bordo sinistro, sporge 0,3 mm dalla scheda | Corretta | Nessuna |
| Footprint dei componenti acquistati | SOIC-8 3,9 × 4,9 passo 1,27; 3296W tre pin in linea passo 2,54; 0805; pulsanti 6,5 × 4,5 mm; ECEA1CKS100 passo 1,5 mm, foro 0,6 | Coerenti con i codici | 100 nF: i fori sono a passo 2,5 mm, il passo dei pezzi reali non è noto (vedi montaggio) |
| Alimentazione | Solo USB dal Teensy; consumo stimato sotto 100 mA; TLV3501 massimo assoluto 5,5 V | Accettabile | Aggiunto il controllo della tensione alla prima accensione |
| Ingombri | Distanze fra corpi calcolate dalle coordinate: minimo 0,6 mm (C4–U1, C5–U2, C1–R3) | Stretto ma montabile | Nessuna |

Lasciati come sono, da tenere presenti: la soglia THRESH deriva dal +5 V non filtrato, quindi il rumore dell'USB entra nella soglia (con 1 MΩ il segnale lo sovrasta); TIA_OUT arriva a PF0 senza resistenza in serie, quindi il firmware non deve mai impostare A0 come uscita né leggere l'ADC nella finestra di misura; PROBE entra in PD2 senza protezione ESD, come nel montaggio attuale; il trigger ottico è su INT3 e non su un ingresso di cattura (PC7/ICP3 è libero).

## Risultati riproducibili

Verifica aggiuntiva dell'11 novembre 2026 con **KiCad 9.0.8 ufficiale installato su Windows**, invocato direttamente senza passare dal runtime 10.99. Il primo controllo ha rilevato tre fili non suddivisi alle giunzioni esistenti, nella rete VBIAS e nel feedback di U1: KiCad 9 ricostruiva alcune reti in modo diverso. I fili sono stati segmentati alle giunzioni in entrambe le copie dello schema, conservando circuito previsto, valori, simboli e geometria del disegno. Nessuna modifica al PCB o ai Gerber. La verifica conclusiva con KiCad 9.0.8 passa ERC, DRC e parità; anche la netlist esportata dal motore 9 coincide con tutte le 88 associazioni pin/rete del PCB. Il confronto SHA-256 conferma che lo ZIP PCBWay è identico a quello A1b precedente a questa correzione dello schema.

| Verifica | Esito / evidenza |
|---|---|
| KiCad 9.0.8 installato: ERC, DRC e parità | PASS, zero violazioni, collegamenti mancanti o differenze; `kicad9-native-erc.json`, `kicad9-native-drc.json` |
| Netlist del motore 9 contro PCB | PASS, 88 associazioni uniche coincidenti; `kicad9-native-summary.json` |
| ERC schema | PASS, zero errori e warning; `final-erc.json` |
| DRC con zone riempite | PASS, zero errori e zero warning, zero collegamenti mancanti, zero errori di parità; `final-drc.json` |
| Schema contro PCB | PASS, 88 associazioni uniche riferimento/pin/rete; `independent-checks.json` |
| Pin critici contro specifica datasheet | PASS, 38 associazioni esplicite per IC, Teensy, diodo, connettori e polarità; stesso report |
| Geometria piste | PASS, nessun segmento fuori da multipli di 45°, larghezza minima 0,2 mm |
| C4 e C5 rispetto ai pin 7 di U1/U2 | 2,825 mm fra centri dei pad; ciascuno sullo stesso lato, ritorno GND tramite pad THT vicino |
| Fori di fissaggio | PASS, quattro Ø2,2 mm NPTH ai centri previsti; preservati come oggetti board-only |
| Gerber ed Excellon esportati | PASS, sette layer non vuoti, 80 fori metallizzati e quattro NPTH; tutti gli 84 fori coincidono per posizione e diametro con piazzole e vias del PCB; contorno 56 × 48 mm; `fabrication-files.json`, `drill-report.txt` |
| Conversione KiCad 9 | PASS, nessuna perdita/approssimazione segnalata; `kicad9-export.json` |
| Copia KiCad 9 contro originale | PASS, 92 record pad, 122 record piste e 90 record pin dello schema uguali; `portable-comparison.json` |
| DRC/parità ed ERC copia KiCad 9 | PASS, zero violazioni, collegamenti mancanti, problemi di parità o ERC; `portable-drc.json`, `portable-erc.json`. Eseguiti con il motore KiCad 10.99 sui file in formato 9, non con un KiCad 9 installato |
| Aspetto schema, montaggio e Gerber | Esaminati su render; orientamento retro, polarità, accesso a USB/connettori e assenza di evidenti sovrapposizioni |

Le differenze fra i conteggi riguardano pin di alimentazione virtuali, pad duplicati dei pulsanti e quattro fori meccanici. Non indicano collegamenti mancanti.

Il DRC include errori e warning. Il report elenca cinque controlli ignorati nella configurazione di partenza del runtime: courtyard mancante, centraggio delle piste sulle vias, profili di tuning, filtri footprint e corrispondenza del tipo di footprint. Non sono stati disattivati controlli per nascondere violazioni. Courtyard/ingombri e piedinatura sono stati esaminati separatamente; il report non equivale a una verifica di ogni proprietà possibile di KiCad.

## Regole e fabbricazione

Confronto con [capacità PCBWay](https://www.pcbway.com/capabilities.html), consultate il 2026-11-08, per due layer e rame 1 oz. I limiti sono condizioni pubblicate, non un preventivo o accettazione CAM.

| Voce | Progetto | Limite pubblicato / esito |
|---|---|---|
| Pista / distanza rame | Minimi configurati 0,20 / 0,20 mm, DRC pulito | 0,10 / 0,10 mm: PASS |
| Rame dal bordo fresato | Minimo configurato 0,50 mm, DRC pulito | 0,25 mm: PASS |
| Foratura più piccola | Vias Ø0,30 mm; componenti 0,6 / 0,8 / 1,0 / 1,1 mm | Sotto Ø0,20 mm è indicato sovrapprezzo: PASS |
| Corona anulare | Vias Ø0,70 / foro Ø0,30: 0,20 mm; regola minima 0,15 mm | Minimo 0,15 mm: PASS |
| Serigrafia visibile | Altezza 0,8–1,2 mm, tratto 0,15 mm | Minimi 0,8 / 0,15 mm: PASS, al limite per le scritte da 0,8 mm |
| Fori / slot speciali | Nessun foro cieco, interrato, asola o bordo metallizzato | Nessun processo speciale previsto |

I Gerber sono stati riletti con un parser diverso da KiCad e renderizzati su entrambe le facce insieme ai file Excellon. Il parser segnala la posizione del comando G90 dopo la chiusura dell'header Excellon; riconosce correttamente unità, coordinate, utensili e tutti gli 84 fori. Nessun errore di parsing. Nessuna pasta saldante esportata: montaggio manuale, stencil non richiesto.

## Copertura elettrica e prove ancora necessarie

- U1/U2: alimentazioni, pin NC, SHDN a GND, feedback, polarità BPV10 e uscita verso il Teensy verificati sullo schema e sul PCB. Bypass locali presenti. Il nodo invertente ha percorsi corti e svuotamento del piano circostante; il comparatore è separato dal fotodiodo.
- C2 e C6 sono elettrolitici polarizzati scelti al posto dei 10 µF ceramici citati nella proposta iniziale; C1/C4/C5 ceramici rimangono per il bypass. Valore, tensione, passo e polarità sono espliciti nella distinta.
- Il consumo effettivo dell'assieme e la corrente disponibile dalla porta USB non sono misurati. Non è dichiarata una portata termica validata delle piste. Non vi sono carichi di potenza previsti, ma un bilancio completo richiede anche OLED e Teensy reali.
- Il valore di R3 viene da una stima sui dati del datasheet, non da una misura: la fotocorrente reale dipende da display, luminosità e allineamento.
- Non sono verificati con simulazione o banco: stabilità del TIA, ringing del comparatore, immunità alla luce ambiente, tolleranze, rumore, saturazione, falsi fronti e riarmo. Il layout e i valori sono una prima implementazione della topologia della repo.
- Non sono svolti test EMC/ESD, robustezza dei cavi o protezione delle porte esterne. La sonda prevista è un contatto passivo.
- Nessun timestamp del firmware ottico è stato implementato o collaudato in questo pacchetto. Risoluzione del timer e tempi nominali dei componenti non dimostrano accuratezza di sistema.
- Nessun assemblaggio fisico provato. I package sono ricavati dai codici e dai datasheet; autenticità e quote dei pezzi ricevuti non sono stabilite dalle inserzioni. Le resistenze vanno misurate; OLED, pulsanti, zoccoli e cavi vanno confrontati con i componenti reali.
- Non è fornito un STEP completo dell'assieme: mancano modelli 3D verificati per tutti i componenti. Il DXF riporta contorno e fori; ingombri verticali e case sono ancora da definire.

La revisione supporta la fabbricazione di un **prototipo** con i file allegati; non costituisce collaudo funzionale né promessa di equivalenza con LDAT. Non sono stati effettuati upload, pagamenti, ordini o pubblicazioni GitHub.

## Comandi principali

Eseguiti nella copia di lavoro con text-to-cad / KiCad headless 10.99:

```text
cad kicad_sch erc mouse_latency_tester.kicad_sch --json
python apply_review_a1b.py
cad run kicad-cli pcb drc --refill-zones --save-board --schematic-parity --severity-all --format json -o checks/final-drc.json mouse_latency_tester.kicad_pcb
cad run verify_final.py
cad run kicad-cli pcb export gerbers --layers F.Cu,B.Cu,F.Mask,B.Mask,F.SilkS,B.SilkS,Edge.Cuts -o fab mouse_latency_tester.kicad_pcb
cad run kicad-cli pcb export drill --format excellon --excellon-units mm --excellon-separate-th --generate-report --report-path checks/drill-report.txt -o fab mouse_latency_tester.kicad_pcb
uv run --no-project --with gerbonara --with resvg-py audit_fabrication.py
cad run kicad-cli project downgrade --target 9.0 --output <cartella-nuova> --report-json checks/kicad9-export.json mouse_latency_tester.kicad_pro
```

Gli script di verifica sono inclusi in `Controlli/script/`. La sorgente da modificare per l'utilizzatore è il progetto nativo in `KiCad/`; gli script non sono un generatore integrale del progetto. Il manifesto SHA-256 identifica i file esatti consegnati.
