// --- INSERISCI I TUOI DATI QUI SOTTO ---
const CLIENT_ID = '1046271355606-9gfr0obafnan3rn4i8suj23i1v11m5lt.apps.googleusercontent.com';
const FOLDER_ID = '1NbNmlW5lUlcAhPWbIiPZiJ_fMTjqPlNP';
// ---------------------------------------

let tokenClient;
let accessToken = null;

// Questa funzione parte in automatico appena la pagina si carica
window.onload = function () {
    // Inizializza il sistema di login di Google
    tokenClient = google.accounts.oauth2.initTokenClient({
        client_id: CLIENT_ID,
        scope: 'https://www.googleapis.com/auth/drive.readonly',
        callback: (tokenResponse) => {
            if (tokenResponse && tokenResponse.access_token) {
                accessToken = tokenResponse.access_token;
                document.getElementById('login-btn').style.display = 'none'; // Nascondi il bottone
                recuperaBrani(); // Vai a prendere i brani
            }
        },
    });
};

// Funzione chiamata quando clicchi il bottone "Accedi con Google"
function handleAuthClick() {
    tokenClient.requestAccessToken();
}

// Funzione per scaricare la lista dei file MP3 dalla tua cartella
async function recuperaBrani() {
    // URL delle API di Google Drive per cercare file mp3 in una cartella specifica
    const url = `https://www.googleapis.com/drive/v3/files?q='${FOLDER_ID}'+in+parents+and+mimeType='audio/mpeg'&fields=files(id,name)`;

    try {
        const response = await fetch(url, {
            headers: {
                'Authorization': `Bearer ${accessToken}`
            }
        });
        
        const data = await response.json();
        mostraPlaylist(data.files);
    } catch (error) {
        console.error('Errore nel recupero dei file:', error);
        alert("C'è stato un errore nel caricamento dei file.");
    }
}

// Funzione per creare la lista cliccabile sullo schermo
function mostraPlaylist(files) {
    const playlist = document.getElementById('playlist');
    playlist.innerHTML = ''; // Svuota la lista
    
    if (!files || files.length === 0) {
        playlist.innerHTML = '<li>Nessun file MP3 trovato in questa cartella.</li>';
        return;
    }

    files.forEach(file => {
        const li = document.createElement('li');
        li.textContent = file.name.replace('.mp3', ''); // Rimuove .mp3 dal nome visibile
        
        // Quando clicchi su un brano, fallo partire
        li.onclick = () => riproduciBrano(file.id, file.name);
        
        playlist.appendChild(li);
    });
}

// Funzione AGGIORNATA per caricare il brano in modo sicuro
async function riproduciBrano(fileId, fileName) {
    const playerContainer = document.getElementById('player-container');
    const audioPlayer = document.getElementById('audio-player');
    const nowPlaying = document.getElementById('now-playing');

    // Mostra il player e un messaggio di caricamento
    playerContainer.style.display = 'block';
    nowPlaying.textContent = `⏳ Caricamento: ${fileName.replace('.mp3', '')}...`;

    // URL per scaricare il file
    const url = `https://www.googleapis.com/drive/v3/files/${fileId}?alt=media`;

    try {
        // Usiamo fetch per scaricare il file passando il token nell'intestazione (il modo più sicuro)
        const response = await fetch(url, {
            headers: {
                'Authorization': `Bearer ${accessToken}`
            }
        });

        if (!response.ok) {
            throw new Error("Impossibile accedere al file audio.");
        }

        // Trasformiamo la risposta in un "Blob" (Binary Large Object)
        const blob = await response.blob();
        
        // Creiamo un URL temporaneo locale per il nostro file
        const objectUrl = URL.createObjectURL(blob);

        // Assegna l'URL temporaneo al player e fai play
        audioPlayer.src = objectUrl;
        nowPlaying.textContent = `▶ In riproduzione: ${fileName.replace('.mp3', '')}`;
        audioPlayer.play();

    } catch (error) {
        console.error('Errore durante la riproduzione:', error);
        nowPlaying.textContent = `❌ Errore: impossibile riprodurre il brano.`;
    }
}
