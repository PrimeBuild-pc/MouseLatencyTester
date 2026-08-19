# Latency Tester Dashboard v2.0

Compatibile con il firmware `latency_tester_oled_ldr_v1_3.ino`.

## Dipendenze

```powershell
pip install pyserial pynput matplotlib
```

## Avvio

1. Chiudi Arduino Serial Monitor, il vecchio companion e le vecchie dashboard.
2. Avvia:

```powershell
python LatencyTester_Dashboard_v2.py
```

## Workflow consigliato

1. **DISPOSITIVI** → crea il profilo del mouse.
2. **LIVE TEST** → imposta nome run, polling rate, wired/wireless, firmware del mouse e note.
3. Premi **Calibra**.
4. Scegli il target (es. 50 campioni) e premi **ENTRA IN TEST MODE**.
5. Premi soltanto quando la schermata è verde.
6. A target completato premi `ESC`.
7. Premi **Salva sessione**.
8. Cambia polling rate/configurazione, premi **Nuova run** e ripeti.
9. **SESSIONI** contiene lo storico permanente.
10. **CONFRONTA** permette di selezionare più run e visualizzare:
   - Campioni grezzi
   - Box plot
   - ECDF
   - Istogramma

## Statistiche

La dashboard calcola:
- Media
- Mediana
- Min / Max
- Deviazione standard
- P95 / P99
- IQR
- Jitter = P95 - P5

## Archivio

I profili, le sessioni e i singoli campioni vengono salvati automaticamente in un database SQLite:

`Documenti/LatencyTester/latency_tester.db`

Ogni run conserva anche:
- calibrazione Teensy
- polling rate
- modalità wired/wireless
- firmware del mouse
- note
- luce iniziale/finale
- timestamp di ogni campione

Puoi inoltre esportare ogni run in CSV.
