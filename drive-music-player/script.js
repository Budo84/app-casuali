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

// Funzione per leggere il tuo file JSON locale invece di cercare su Drive
async function recuperaBrani() {
    try {
        // Scarica il file database.json dalla tua stessa repository GitHub
        const response = await fetch('./database.json');
        const canzoni = await response.json();
        
        mostraPlaylist(canzoni);
    } catch (error) {
        console.error('Errore nel caricamento del database:', error);
        alert("Impossibile caricare la lista delle canzoni dal JSON.");
    }
}

// Funzione aggiornata per mostrare Artista e Titolo dal JSON
function mostraPlaylist(canzoni) {
    const playlist = document.getElementById('playlist');
    playlist.innerHTML = ''; 
    
    canzoni.forEach(brano => {
        const li = document.createElement('li');
        // Ora possiamo mostrare i dati formattati bene!
        li.innerHTML = `<strong>${brano.titolo}</strong> <br> <small>${brano.artista} - ${brano.album}</small>`;
        
        // Passiamo tutto l'oggetto brano alla funzione di riproduzione
        li.onclick = () => riproduciBrano(brano);
        
        playlist.appendChild(li);
    });
}

// Funzione aggiornata per riprodurre audio E mostrare la copertina
async function riproduciBrano(brano) {
    const playerContainer = document.getElementById('player-container');
    const audioPlayer = document.getElementById('audio-player');
    const nowPlaying = document.getElementById('now-playing');
    const albumCover = document.getElementById('album-cover');

    playerContainer.style.display = 'block';
    nowPlaying.textContent = `⏳ Caricamento: ${brano.titolo}...`;

    try {
        // 1. CARICA LA COPERTINA (se esiste l'ID)
        if (brano.coverDriveId) {
            // Per le immagini possiamo usare un link diretto senza token se il file su Drive 
            // è impostato su "Chiunque abbia il link", altrimenti usiamo il metodo sicuro:
            const coverUrl = `https://www.googleapis.com/drive/v3/files/${brano.coverDriveId}?alt=media`;
            const coverResponse = await fetch(coverUrl, { headers: { 'Authorization': `Bearer ${accessToken}` } });
            const coverBlob = await coverResponse.blob();
            albumCover.src = URL.createObjectURL(coverBlob);
            albumCover.style.display = 'block';
        } else {
            albumCover.style.display = 'none'; // Nascondi se non c'è copertina
        }

        // 2. CARICA L'AUDIO
        const audioUrl = `https://www.googleapis.com/drive/v3/files/${brano.audioDriveId}?alt=media`;
        const audioResponse = await fetch(audioUrl, { headers: { 'Authorization': `Bearer ${accessToken}` } });
        
        if (!audioResponse.ok) throw new Error("Impossibile accedere all'audio.");
        
        const audioBlob = await audioResponse.blob();
        audioPlayer.src = URL.createObjectURL(audioBlob);
        
        nowPlaying.textContent = `▶ ${brano.artista} - ${brano.titolo}`;
        audioPlayer.play();

    } catch (error) {
        console.error('Errore durante la riproduzione:', error);
        nowPlaying.textContent = `❌ Errore di riproduzione.`;
    }
}
