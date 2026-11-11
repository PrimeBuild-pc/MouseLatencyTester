# Verifica del front-end ottico BPV10 / OPA380 / TLV3501

Verifica documentale: 8 novembre 2026. Nessun montaggio, simulazione o collaudo eseguito. Documento esaminato tramite connettore GitHub: [optical_front_end.md](https://github.com/PrimeBuild-pc/MouseLatencyTester/blob/main/docs/optical_front_end.md), blob `f87307ba82cdc1d8058b42bd20731c27583896eb`. La pagina dichiara esplicitamente che il circuito non è costruito/verificato e non è ancora supportato dal firmware.

## Esito

Non emergono errori nel pinout, nel collegamento SHDN o nella polarità del fotodiodo dello schema attuale. Questi tre aspetti sono coerenti. Le prestazioni dell'intero rilevatore restano da dimostrare; i tempi dei singoli componenti non equivalgono all'accuratezza di un LDAT completo.

## Pinout verificato, vista dall'alto

| Pin SOIC-8 | OPA380AID | TLV3501AID |
|---|---|---|
| 1 | NC | NC |
| 2 | −IN | −IN |
| 3 | +IN | +IN |
| 4 | V− / GND | V− / GND |
| 5 | NC | NC |
| 6 | OUT | OUT |
| 7 | V+ | V+ |
| 8 | NC | SHDN |

Fonti: [OPA380, pagina 2](https://www.ti.com/lit/ds/symlink/opa380.pdf#page=2) e [TLV3501, pagina 3](https://www.ti.com/lit/ds/symlink/tlv3501.pdf#page=3). Per TLV3501, SHDN basso abilita il dispositivo; alto lo spegne e pone OUT ad alta impedenza. Il collegamento a GND previsto è corretto; non lasciarlo flottante. [TI, §7.4.1](https://www.ti.com/lit/ds/symlink/tlv3501.pdf#page=11).

## Polarità e margini del TIA

OPA380 ammette alimentazione 2,7–5,5 V e modo comune fino a V+−1,8 V. A 5 V il bias di 2,5 V rientra nel limite di 3,2 V. La stessa divisione a metà alimentazione **non è valida a 3,3 V**: 1,65 V supera 1,5 V. Il bias positivo del fotodiodo è una topologia esplicitamente prevista da TI. [OPA380, pagine 3, 9 e 11](https://www.ti.com/lit/ds/symlink/opa380.pdf).

Deduzione circuitale: con anodo BPV10 a GND e catodo al nodo invertente, il diodo è polarizzato inversamente di circa 2,5 V. La fotocorrente esce dal nodo attraverso il diodo; l'uscita deve fornire quella corrente attraverso Rf. Pertanto `VOUT ≈ VBIAS + Iphoto × 10 kΩ`: più luce fa salire VOUT. Collegando VOUT al −IN del comparatore, il passaggio al bianco genera correttamente un fronte FALLING.

Il limite di uscita garantito OPA380 è circa V+−0,6 V con il carico specificato. Stima prudente a 5 V: margine 4,4−2,5=1,9 V, pari a circa 190 µA con Rf=10 kΩ. Non è un limite di fotocorrente misurato sul montaggio. [OPA380, pagina 10](https://www.ti.com/lit/ds/symlink/opa380.pdf#page=10).

## Guadagno: correzione dell'11 novembre 2026

La verifica qui sopra controllava il margine verso la saturazione, non l'ampiezza del segnale. Dal datasheet BPV10: 70 µA tipici (38 minimi) a 1 mW/cm² e 950 nm, sensibilità relativa circa 0,45 a 550 nm, semiangolo ±20°. Un display bianco a 250 cd/m² appoggiato al sensore dà una radianza di circa 0,9 W/(m²·sr); sull'angolo utile del BPV10 (circa 0,5 sr) equivale a 0,05 mW/cm², cioè circa **1 µA**. Con Rf = 10 kΩ sono circa 10 mV, sotto l'isteresi del comparatore calcolata più avanti (18,5 mV). Il PCB A1b monta quindi **Rf = 1 MΩ**: circa 1 V a 250 cd/m², saturazione oltre circa 1,9 µA. Con Cf = 15 pF il polo scende a 10,6 kHz (τ = 15 µs): alla soglia il ritardo è di pochi microsecondi. È una stima, da confermare su TP2. I calcoli di banda del paragrafo seguente restano riferiti al valore originale di 10 kΩ.

## Banda, soglia e fotodiodo

- Calcolo sul solo feedback: 10 kΩ × 15 pF = 150 ns, polo circa 1,06 MHz. Non garantisce il ritardo reale: capacità del diodo, parassiti e stabilità vanno verificati. La scelta è plausibile; TI mostra anche un esempio 10 kΩ / 16 pF per limitare la banda vicino a 1 MHz. [OPA380, pagina 12](https://www.ti.com/lit/ds/symlink/opa380.pdf#page=12).
- TLV3501 ha già circa 6 mV di isteresi interna. La resistenza da 1 MΩ aggiunge isteresi positiva: con trimmer da 10 kΩ a metà corsa, la resistenza equivalente è 2,5 kΩ e il contributo ideale è circa `5 V × 2,5 kΩ/(1 MΩ+2,5 kΩ) = 12,5 mV`; totale approssimativo 18,5 mV. È una deduzione, dipendente dalla posizione del trimmer e dall'escursione reale dell'uscita. Segnali ottici piccoli potrebbero non consentire commutazione e riarmo affidabili. [TLV3501, §8.1.1](https://www.ti.com/lit/ds/symlink/tlv3501.pdf#page=12).
- BPV10 vede il visibile e vicino infrarosso: banda 380–1100 nm, picco 920 nm. Vishay specifica tempi tipici 80 ns salita e 60 ns discesa a **10 V inversi, 50 Ω e 830 nm**; non sono una garanzia alle condizioni del circuito. Capacità tipica 11 pF a 0 V, 3,8 pF a 5 V. Occorre schermare la luce ambiente e misurare contrasto bianco/nero sul display reale. [BPV10, pagine 1–3](https://www.vishay.com/docs/81502/bpv10.pdf).

## Montaggio a mano

I codici acquistati con suffisso **D** sono SOIC-8; **DR** cambia la confezione, non il package. Evitare di confonderli con OPA380AIDGK o TLV3501AIDBVR. [Scheda OPA380AID](https://www.ti.com/product/OPA380/part-details/OPA380AID), [scheda TLV3501AID](https://www.ti.com/product/TLV3501/part-details/TLV3501AID).

Il package D ha passo 1,27 mm e piedini accessibili: giudizio pratico, è saldabile a mano con flussante e ingrandimento su PCB/adattatore appropriato. Un adattatore SOIC→DIP aiuta su millefori da 2,54 mm, ma non rende automaticamente valido il layout veloce. [Disegno ufficiale D0008A](https://www.ti.com/lit/pdf/MSOI002K).

TI richiede bypass vicino ai pin, percorsi corti e buon ritorno di massa per il comparatore. Per una PCB dedicata mettere direttamente i SOIC sulla scheda, senza adattatori; tenere fotodiodo e Rf/Cf vicini all'OPA380 e separare il percorso dell'uscita digitale dal nodo invertente. Sono indicazioni di implementazione, non collaudo. [TLV3501, §10](https://www.ti.com/lit/ds/symlink/tlv3501.pdf#page=15).

## Correzioni documentali e prove necessarie

La frase secondo cui il diodo non deve mai caricare capacità è una semplificazione: restano capacità di giunzione e parassiti. Anche l'affermazione che il condensatore sul +IN debba sostenere direttamente i gradini di fotocorrente è imprecisa: la corrente principale passa nel nodo invertente e nel feedback. Non compromettono la topologia, ma non giustificano da sole le prestazioni.

Prima di affidarsi alle misure: controllare alimentazione reale e livelli logici, bias al buio, incremento bianco/nero, assenza di saturazione, transitori/oscillazioni e fronti multipli con oscilloscopio; verificare poi ISR, timer e latenza software. La PCB deve consentire di misurare VBIAS, TIA OUT e comparator OUT. Non è stata verificata qui la parte Teensy/firmware.
