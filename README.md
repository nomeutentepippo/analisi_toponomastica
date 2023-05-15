# Analisi Toponomastica
Ho analizzato le denominazioni di vie e piazze italiane con l'idea di estrapolarne informazioni statistiche globali e tendenze regionali.
Al di là delle classifiche delle vie più usate può essere interessante aggregare per tipologie di vie. Poichè non è possibile classificare automaticamente il nome di una via all'iterno di una data tipologia il lavoro è stato condotto per le 350 denominazioni più esate che ricoprono all'incirca un quarto delle totalità dele circa 1 milione e 800 mila vie (piazze, corsi, ...) presenti sull territorio italiano.
![Dataframe Header](output/analisi_globale_per_tipologia_delle_denominazioni_più_diffuse.png)
Tra le personalità il podio spetta a Marconi, Garibialdi e Dante mentre tra gli Eventi Storici il Quattro Maggio è il più celebrato. La scelta delle categorie delle vie è stata arbitraria e non sembra nettamente definita: il Piave ad esempio è stato inserito negli Eventi Storici anzichè negli Elementi Geografici. San Francesco, San Rocco e San Martino sono i santi più popolari mentre tra le città Roma è di gran lunga quelle che riceve più dediche. 
![Dataframe Header](output/personalità.png)
![Dataframe Header](output/eventi_storici.png)
![Dataframe Header](output/santi.png)
![Dataframe Header](output/città.png)

La classifica delle Città ha ispirato una ricerca tra la correlazione tra le regioni. Ho misurato quanto un comune presente in una regione è predisposto a dedicare una sua via a una città presente nella propria regione piuttosto che in un altra. Si definisce quindi una metrica di correlazione che misura la percentuale di vie di una regione dedicate a città (comuni con più di 10 mila abitanti) di altre regioni (o della regione stessa).
Clusterizzando le regioni risulta che Val d'Aosta e Sardegna sono le più "isolate" rispetto alle altre regioni. Come ci si poteva aspettare ogni regione è più propoensa a dedicare vie alla proprie città ma tra tutte la Sicilia è la più autoreferenziale. Il Lazio e il Veneto sono le regioni che ricevono più dediche.
![Dataframe Header](output/correlazione_regioni.png)

