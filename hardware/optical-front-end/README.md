# Front-end ottico — prima bozza elettrica

Questo progetto contiene lo schema del solo front-end BPV10 / OPA380AIDR / TLV3501AID. Non è ancora la scheda completa con Teensy, pulsanti e OLED; nessun file qui presente è un Gerber da ordinare.

La topologia e i valori iniziali provengono da [MouseLatencyTester](https://github.com/PrimeBuild-pc/MouseLatencyTester/blob/main/docs/optical_front_end.md), verificati documentalmente sui datasheet [OPA380](https://www.ti.com/lit/ds/symlink/opa380.pdf), [TLV3501](https://www.ti.com/lit/ds/symlink/tlv3501.pdf) e [BPV10](https://www.vishay.com/docs/81502/bpv10.pdf). Sono un punto di partenza da collaudare, non prestazioni garantite.

I simboli passivi, power e connettori derivano dalle librerie ufficiali archiviate [KiCad](https://github.com/KiCad/kicad-symbols), con la [relativa licenza](https://github.com/KiCad/kicad-symbols/blob/master/LICENSE.md). I due simboli IC locali sono ricavati dai pinout TI; tutti gli otto pin sono rappresentati, inclusi NC e SHDN.

Il file nativo `optical_front_end.kicad_sch` è il sorgente da modificare. `build_draft.py` e `make_native.py` sono costruttori iniziali e rifiutano di sovrascriverlo. KiCad CLI non ha convertito direttamente lo schematico legacy, quindi `make_native.py` ha composto il primo file nativo usando il parser S-expression di text-to-cad e i simboli convertiti dal comando ufficiale KiCad. `mlt.lib` e `.sch` sono intermedi storici; `mlt.kicad_sym` e `sym-lib-table` rendono il progetto autosufficiente. Gli intermedi non vanno rigenerati dopo modifiche al file nativo. `tidy_native.py` documenta la sistemazione dei campi dopo il primo controllo visivo e verifica che non cambi nome, tipo o rete di alcun pin.

Verifica della revisione presente: `cad kicad_sch erc optical_front_end.kicad_sch --json` passa con zero errori e zero warning; restano tre controlli di librerie footprint non effettuati, dichiarati in `erc.json`. `cad run verify_circuit.py` passa: 46 connessioni pin/rete confrontate con la specifica indipendente, cinque NC e numerazione completa di entrambi gli IC. `preview.png` è stato generato dallo schematico finale e ispezionato dopo la sistemazione dei testi. Non è stata eseguita una simulazione elettrica o una prova fisica. Il runtime usato è cad-server 0.11.1 con KiCad headless 10.99: il formato della libreria è della versione di sviluppo e non è stata verificata l'apertura in una versione stabile di KiCad.

Alimentazione nominale 5 V dal Teensy 2.0, mai oltre i limiti dei componenti. Il partitore VBIAS a metà alimentazione non è valido a 3,3 V per il modo comune OPA380. J1.4 è destinato al pad D3, Arduino digital 8; J1.3 è destinato a F0/A0. Il KY-018 non deve pilotare contemporaneamente lo stesso ingresso analogico.

Ancora da completare: formato dei due 10 µF e degli altri passivi; posizionamento del bypass con collegamenti corti; footprint del trimmer reale; pinout/geometria di Teensy e OLED; dimensioni del case e accesso alle regolazioni. I footprint mancanti non sono da inventare durante l'esportazione: vanno fissati prima del layout.

Il firmware esistente v1.5 usa KY-018 e ADC: occorre implementare il timestamp sul fronte del comparatore. Né il firmware né il circuito sono stati collaudati su questo nuovo hardware. Il PCB completo e il case rimangono lavoro aperto.
