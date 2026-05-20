# 🏫 Gestione Orario Scolastico e Supplenze

Un'applicazione web *stand-alone* (funziona interamente nel browser senza bisogno di server o database esterni) progettata per gestire in modo avanzato l'orario scolastico, le cattedre, le compresenze e le supplenze di un intero Istituto Comprensivo (Infanzia, Primaria e Secondaria).

## 🚀 Come iniziare
L'applicazione non richiede installazione. 
1. Scarica il file `app-orario.html`.
2. Fai doppio clic sul file per aprirlo nel tuo browser preferito (Chrome, Edge, Safari, Firefox).
3. I dati inseriti vengono **salvati in automatico** all'interno della memoria del browser (*localStorage*).

> ⚠️ **IMPORTANTE:** Poiché i dati risiedono nel browser, ricordati di utilizzare spesso la funzione **"Esporta Backup (.json)"** (nella scheda "Dati & Excel") per creare copie di sicurezza sul tuo PC!

---

## 🛠️ Guida alle Funzionalità (Schede)

L'applicazione è divisa in 6 comode schede (Tab) per seguire un flusso di lavoro logico:

### 1. Dati Base
È il punto di partenza per configurare l'istituto.
* **Materia / Attività:** Inserisci le materie di insegnamento o attività speciali (es. *Matematica, Sorveglianza Mensa, TSP*).
* **Classi:** Crea le classi specificando a quale ordine di scuola appartengono (Infanzia, Primaria, Secondaria).
* **Generatore Automatico:** Permette di creare in un solo clic la griglia oraria di un'intera settimana per un ordine di scuola (es. 8 ore da 60 minuti a partire dalle 08:00).
* **Editor Interattivo Fasce:** Permette di personalizzare le fasce orarie create, modificare gli orari al minuto, inserire le "Ricreazioni" o il "Pranzo" eliminando le lezioni da quegli specifici slot.

### 2. Assegnazioni (Cattedre)
Qui definisci il corpo docenti e dove insegnano.
* **Crea Docente:** Inserisci nome, giorno libero e monte ore settimanale.
* **Assegna alle Classi:** Selezionando un docente dall'elenco (rigorosamente in ordine alfabetico), vedrai tutte le classi dell'istituto. Metti una spunta sulla classe desiderata e scegli la materia che il docente insegna in quella classe. *Premi "Salva Assegnazioni".*

### 3. Componi Orario
La "scacchiera" in cui si posizionano i docenti nel tabellone.
* Seleziona una classe: apparirà la griglia della settimana.
* Clicca sulla tendina di una cella per aggiungere un docente. L'app ti proporrà solo i docenti precedentemente assegnati a quella classe.
* **Compresenze illimitate:** Puoi inserire più di un docente nella stessa casella (es. Titolare + Sostegno).
* **Prevenzione Errori:** Se provi a inserire un docente nel suo giorno libero, o in un'ora in cui sta già insegnando in un'altra classe, l'app ti bloccherà avvisandoti dell'errore.

### 4. Assenze & Supplenze (Sistema Intelligente)
Il cuore dinamico dell'applicazione per le emergenze giornaliere.
* Scegli un docente assente e la **Data esatta** dell'assenza tramite il calendario.
* L'app ti mostrerà solo le ore in cui quel docente doveva insegnare.
* Per ogni ora scoperta, potrai assegnare un Sostituto. L'app **filtra automaticamente i docenti liberi** escludendo chi è già impegnato, chi ha il giorno libero o chi sta già facendo un'altra supplenza in quell'ora.

**⚙️ Regole di Supplenza Avanzate:**
L'app possiede un filtro intelligente attivabile tramite interruttori:
* **Regola Ristretta (Primaria/Secondaria):** Se attivata, l'app propone come supplenti SOLO i docenti che *già insegnano in quella specifica classe*.
* **Gestione Pomeriggi:** Puoi spuntare in quali giorni il pomeriggio è "Curricolare" (es. Martedì e Giovedì). In questi giorni la regola ristretta varrà anche dopo le 13:30. Nei pomeriggi "Extra" (es. Lunedì, Mercoledì, Venerdì), la regola ristretta si spegne automaticamente dopo le 13:30, permettendoti di usare come supplente qualsiasi docente del plesso.

### 5. Monitor & Stampa
La plancia di comando per visualizzare l'orario finito e fare modifiche "al volo".
* **Vista per Ordine:** Mostra tutto il tabellone di una scuola (es. tutta la Secondaria) affiancando le classi.
* **Vista per Classe o Docente:** Mostra l'orario specifico di una sezione o di un professore.
* **Visualizzazione per Data:** Mostra solo le lezioni e le supplenze attive per il giorno selezionato nel calendario.
* **Modifica al volo:** Cliccando su qualsiasi cella del tabellone, si aprirà una finestra per assegnare rapidamente una supplenza senza dover passare dalla scheda 4. Anche qui, l'elenco dei docenti sarà in ordine alfabetico e indicherà tra parentesi il plesso di appartenenza `[es. Primaria, Secondaria]`.
* **Stampa PDF:** Premi "Stampa questa vista" per ottenere una versione ottimizzata A4 Orizzontale, perfetta per il registro o la bacheca.

### 6. Dati & Excel
Strumenti essenziali per la sicurezza e l'esportazione dei dati.
* **Esporta/Importa Backup JSON:** Salva l'intero database sul tuo PC o ripristinalo. *(Usalo come salvataggio a fine giornata!)*
* **Esporta in Excel:** Esporta tabelle `.xlsx` eleganti e leggibili dell'intero Tabellone, della singola classe o del singolo docente.
* **Importa da Excel:** Scarica il template, compilalo e caricalo per popolare l'app massivamente senza digitare a mano materie, classi e docenti.

---

## 💡 Tips & Tricks
* **Ordini di Scuola Sincronizzati:** Se un docente insegna sia alla Primaria che alla Secondaria, ti basta assegnargli classi di entrambi i livelli nella Tab 2. L'app controllerà automaticamente le concomitanze impedendo accavallamenti tra i due plessi!
* **Stampa Riepilogo Supplenze:** Nella Tab 4 (Assenze) c'è un comodo tasto per stampare o salvare in PDF un foglio giornaliero firmabile con l'elenco esatto delle supplenze del giorno (ora, classe, assente e sostituto).
* **Nomi automatici:** Quando esporti un PDF o un Excel, l'app assegna automaticamente un nome file intelligente (es. `Orario_Classe_1A_Sec.pdf` o `Supplenze_2026-05-11`).