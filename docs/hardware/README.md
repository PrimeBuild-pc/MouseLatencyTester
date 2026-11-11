# PCB compatto A1b / BPV10

Questo percorso raccoglie la ricerca e la documentazione del PCB compatto. Firmware, dashboard e hardware sono ora nella stessa cartella di progetto.

## File principali

| Contenuto | Percorso |
|---|---|
| Pacchetto per PCBWay, Gerber e forature | [MouseLatencyTester-A1-PCBWay.zip](../../outputs/MouseLatencyTester-A1/MouseLatencyTester-A1-PCBWay.zip) |
| Pacchetto completo | [MouseLatencyTester-A1-Progetto.zip](../../outputs/MouseLatencyTester-A1/MouseLatencyTester-A1-Progetto.zip) |
| Istruzioni di consegna | [LEGGIMI](../../outputs/MouseLatencyTester-A1/Consegna-A1/LEGGIMI.md) |
| Progetto portabile KiCad 9 | [mouse_latency_tester.kicad_pro](../../outputs/MouseLatencyTester-A1/Consegna-A1/KiCad/mouse_latency_tester.kicad_pro) |
| Montaggio e collegamenti | [MONTAGGIO](../../outputs/MouseLatencyTester-A1/Consegna-A1/Documentazione/MONTAGGIO.md) |
| Verifiche e limiti | [VERIFICHE](../../outputs/MouseLatencyTester-A1/Consegna-A1/Documentazione/VERIFICHE.md) |
| Sorgenti di lavoro KiCad 10.99 e script | [hardware/compact](../../hardware/compact/) |
| Prima bozza del solo front-end | [hardware/optical-front-end](../../hardware/optical-front-end/) |
| Librerie e licenze originali | [hardware/sources](../../hardware/sources/) |

La copia di lavoro e l'esportazione per KiCad 9 hanno formati diversi e ruoli distinti. La copia portabile mantenuta è quella in `Consegna-A1/KiCad`; non occorrono altre cartelle `KiCad9` o `KiCad9-Final`.

## Ricerca e componenti

- [Decisioni progettuali e alternative](recommendation.md).
- [Componenti acquistati e integrazioni](purchased-components.md).
- [Verifica dei datasheet ottici](optical-datasheet-audit.md).
- [Confronto OpenLDAT](open-ldat-comparison.md).
- [Quote Teensy 2.0](teensy20-dimensions.png) e [pinout](teensy20-pinout.png).

**Stato:** PCB 56 × 48 mm, due layer, revisione A1b dell'11 novembre 2026 (R3 = 1 MΩ, foro di D1 da 1,0 mm, serigrafie; motivi in [VERIFICHE](../../outputs/MouseLatencyTester-A1/Consegna-A1/Documentazione/VERIFICHE.md)). ERC/DRC e confronto schema-PCB superati. Il circuito non è stato costruito o collaudato. Restano firmware per il comparatore, verifica temporale e case. Gli script storici che creano la prima bozza non vanno usati per rigenerare il progetto esistente.

Per il produttore usare esclusivamente lo ZIP PCBWay. Il pacchetto completo comprende documentazione, sorgenti e rapporti, quindi non è lo ZIP da caricare come Gerber.
