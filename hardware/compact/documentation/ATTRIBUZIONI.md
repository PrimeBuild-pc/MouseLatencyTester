# Fonti e librerie

Progetto di circuito e PCB A1 preparato per Lorenzo / PrimeBuild-pc, a partire dai requisiti e dalla topologia descritta in [MouseLatencyTester/docs/optical_front_end.md](https://github.com/PrimeBuild-pc/MouseLatencyTester/blob/main/docs/optical_front_end.md). Firmware e dashboard della repo non sono copiati né modificati nel pacchetto.

La libreria locale `mlt.kicad_sym` e `mlt.pretty` raccoglie solamente i simboli e footprint necessari, inclusi nel progetto per renderlo portabile.

- Simbolo Teensy da [XenGi/teensy_library](https://github.com/XenGi/teensy_library), licenza MIT. Campo nome visualizzato abbreviato mantenendo numeri e tipi dei pin.
- Footprint Teensy da [XenGi/teensy.pretty](https://github.com/XenGi/teensy.pretty), licenza MIT. Aggiunti courtyard e modifiche a serigrafia/Fab; connessione diretta al piano per il pad GND 1.
- Altri simboli da [KiCad/kicad-symbols](https://github.com/KiCad/kicad-symbols) e footprint da [KiCad/kicad-footprints](https://github.com/KiCad/kicad-footprints), copyright contributori KiCad, CC-BY-SA 4.0 con eccezione per i progetti elettronici. Le copie locali sono rinominate nella libreria mlt; riferimenti e posizioni possono essere adattati nel progetto. Il simbolo del condensatore polarizzato è una rappresentazione locale con pin 1 positivo / 2 negativo.

Le licenze upstream sono incluse in questa cartella. Queste attribuzioni descrivono i materiali riutilizzati e non modificano le licenze degli altri progetti citati nella ricerca.
