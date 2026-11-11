# Open-Source-LDAT: cosa riutilizzare per MouseLatencyTester

Verifica: 8 novembre 2026. Repository Open-Source-LDAT esaminato al commit `8e0173e42369316ef7b38d9b7735b61706cdbbb2`, tramite albero ricorsivo e sorgenti effettivi.

**Conclusione:** utile come riferimento per automazione e interfaccia, ma non offre una PCB o un contenitore già pronti da adattare. Per mantenere Teensy 2.0, SH1106 e la futura catena BPV10–OPA380–TLV3501, il trapianto del firmware richiederebbe cambiamenti sostanziali.

## Materiale effettivamente pubblicato

L'albero completo contiene `src/main.cpp`, `include/config.h`, configurazione PlatformIO, patch USB, immagini di cablaggio e strumenti Windows. Non risultano schemi CAD elettronici, layout PCB, Gerber, distinta di produzione, STL, STEP o CAD del case. La fotografia di cablaggio non sostituisce quei file. Anche l'elenco delle release è vuoto. Quindi il progetto non evita il lavoro di progettazione meccanica o della scheda. [Albero completo](https://api.github.com/repos/S4N-T0S/Open-Source-LDAT/git/trees/8e0173e42369316ef7b38d9b7735b61706cdbbb2?recursive=1), [release](https://api.github.com/repos/S4N-T0S/Open-Source-LDAT/releases).

## Misura e modalità

Il progetto documenta Teensy 4.1, sensore analogico TEMT6000, OLED SSD1306 128×64, pulsante e, per pilotare un mouse reale, BC547A con resistenza da 220 Ω. Le modalità **Automatic/Auto UE4** comandano elettricamente il microswitch di un mouse cablato: includono la sua elettronica successiva al comando, non la corsa meccanica del pulsante. **Direct Auto/Direct UE4** generano invece un evento HID dal Teensy: misurano sistema e display attraverso quel dispositivo, escludendo il mouse da confrontare. UE4 usa il software Black to White di Aperture Grille; Automatic può usare marker o variazioni luminose nel gioco. [README](https://github.com/S4N-T0S/Open-Source-LDAT/blob/8e0173e42369316ef7b38d9b7735b61706cdbbb2/README.md).

Il sorgente configura due ADC a **8 bit, velocità molto alta** e legge ripetutamente `adc->analogRead()`: non cattura un fronte di comparatore. `elapsedMicros` parte prima del comando click. In Automatic il valore finale viene letto dopo il rilascio del click, includendo anche quel percorso software. In Auto UE4 il click fisico viene tenuto per il tempo configurato prima di interrogare il sensore. Sono differenze concrete rispetto a due timestamp su interrupt della sonda e del comparatore. [ADC e inizializzazione](https://github.com/S4N-T0S/Open-Source-LDAT/blob/8e0173e42369316ef7b38d9b7735b61706cdbbb2/src/main.cpp#L223-L235), [Automatic](https://github.com/S4N-T0S/Open-Source-LDAT/blob/8e0173e42369316ef7b38d9b7735b61706cdbbb2/src/main.cpp#L903-L949), [UE4](https://github.com/S4N-T0S/Open-Source-LDAT/blob/8e0173e42369316ef7b38d9b7735b61706cdbbb2/src/main.cpp#L689-L713).

## Compatibilità pratica

| Punto | Open-Source-LDAT | Implicazione per il dispositivo di Lorenzo |
|---|---|---|
| MCU | Teensy 4.1, Cortex-M7, 600 MHz | Teensy 2.0 è AVR ATmega32U4, 16 MHz: build e codice specifico non sono intercambiabili |
| Segnali | I/O e ADC 0–3,3 V; non tollera 5 V | La catena a 5 V del progetto Teensy 2.0 non si collega direttamente a un 4.1 |
| OLED | SSD1306; SDA 18/SCL 19 | SH1106 richiede driver e mappatura appropriati |
| Pin firmware | Pulsante 4, click 5, presenza mouse 21, luce 23 | Da rimappare: non sono nomi di pad AVR |
| USB Direct | Patch del core `teensy4`, intervallo HID 125 µs | Non è una patch portabile al core AVR/USB Full Speed del Teensy 2.0 |

Fonti: [configurazione hardware](https://github.com/S4N-T0S/Open-Source-LDAT/blob/8e0173e42369316ef7b38d9b7735b61706cdbbb2/include/config.h), [build](https://github.com/S4N-T0S/Open-Source-LDAT/blob/8e0173e42369316ef7b38d9b7735b61706cdbbb2/platformio.ini), [patch USB](https://github.com/S4N-T0S/Open-Source-LDAT/blob/8e0173e42369316ef7b38d9b7735b61706cdbbb2/scripts/8kHz_polling.py), [specifiche PJRC](https://www.pjrc.com/teensy/techspecs.html), [livelli Teensy 4.1](https://www.pjrc.com/store/teensy41.html), [USB ATmega32U4](https://www.pjrc.com/teensy/atmega32u4.pdf).

## Precisione: evidenza e limiti

Il README dichiara alta precisione e propone una verifica del polling con HamsterWheel; questo verifica il comportamento HID, non calibra la catena ottica. Nell'albero esaminato non compaiono misure contro oscilloscopio/LDAT, tempi caratterizzati del sensore o bilancio d'incertezza. Le soglie sono valori configurabili, tarati dall'autore su un OLED. Non è quindi dimostrata un'accuratezza assoluta equivalente a LDAT. [README e indicazioni di regolazione](https://github.com/S4N-T0S/Open-Source-LDAT/blob/8e0173e42369316ef7b38d9b7735b61706cdbbb2/README.md).

Inferenza dal codice: le quattro cifre decimali visualizzate in millisecondi non dimostrano risoluzione di 0,1 µs, poiché il risultato passa attraverso un conteggio intero di microsecondi. Sensore, conversione ADC, soglia e chiamate software restano parte della misura. [Conversione statistica](https://github.com/S4N-T0S/Open-Source-LDAT/blob/8e0173e42369316ef7b38d9b7735b61706cdbbb2/src/main.cpp#L1134-L1148), [formato display](https://github.com/S4N-T0S/Open-Source-LDAT/blob/8e0173e42369316ef7b38d9b7735b61706cdbbb2/src/main.cpp#L1559-L1574).

## Riutilizzo consigliato

Riprendere le idee di sessioni automatiche, warm-up, timeout, intervallo casuale tra prove, statistiche e salvataggio CSV. Per la PCB e il case partire invece dalle dimensioni reali dei moduli, dopo aver validato il front-end di MouseLatencyTester. La documentazione del suo front-end fotodiodo propone già una strada diversa: sonda come `t0`, comparatore su D3/digital 8 come `t1`, A0 per telemetria; quella pagina si dichiara ancora non verificata. Il firmware `photon_v1_5` esistente usa ancora il KY-018 con lettura ADC, non questo comparatore. [Front-end MouseLatencyTester](https://github.com/PrimeBuild-pc/MouseLatencyTester/blob/5dbc38db602ff642d39eb9fda592c3cf0161cec4/docs/optical_front_end.md).

Per copiare codice considerare anche le licenze: Open-Source-LDAT indica GPL v3 o successiva negli header; MouseLatencyTester pubblica MIT. Registrare provenienza e licenza del materiale effettivamente incorporato prima di distribuirlo. [Header Open-Source-LDAT](https://github.com/S4N-T0S/Open-Source-LDAT/blob/8e0173e42369316ef7b38d9b7735b61706cdbbb2/src/main.cpp#L1-L17), [MIT MouseLatencyTester](https://github.com/PrimeBuild-pc/MouseLatencyTester/blob/5dbc38db602ff642d39eb9fda592c3cf0161cec4/LICENSE).
