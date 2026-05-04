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

// NUOVE VARIABILI GLOBALI PER LA PLAYLIST
let playlistAttuale = [];
let indiceBranoCorrente = -1;

// Aggiungiamo un "ascoltatore" al player audio: quando finisce un brano, passa al prossimo!
document.getElementById('audio-player').addEventListener('ended', playNext);

async function recuperaBrani() {
    try {
        const response = await fetch('./database.json');
        // Salviamo la lista nella nostra variabile globale
        playlistAttuale = await response.json(); 
        mostraPlaylist(playlistAttuale);
    } catch (error) {
        console.error('Errore nel caricamento del database:', error);
        alert("Impossibile caricare la lista delle canzoni dal JSON.");
    }
}

function mostraPlaylist(canzoni) {
    const playlist = document.getElementById('playlist');
    playlist.innerHTML = ''; 
    
    // NOTA: Ora usiamo anche 'index' per sapere la posizione del brano nella lista
    canzoni.forEach((brano, index) => {
        const li = document.createElement('li');
        li.className = 'song-card';
        
        const imgId = `cover-${brano.id}`;
        li.innerHTML = `
            <img id="${imgId}" src="https://via.placeholder.com/150/282828/FFFFFF?text=🎵" class="song-cover" alt="Copertina">
            <p class="song-title">${brano.titolo}</p>
            <p class="song-artist">${brano.artista}</p>
        `;
        
        // Quando clicchi, passi l'INDICE (0, 1, 2...) invece di tutto il brano
        li.onclick = () => riproduciBrano(index);
        playlist.appendChild(li);

        if (brano.coverDriveId) {
            caricaCopertina(brano.coverDriveId, imgId);
        }
    });
}



// NUOVA FUNZIONE: Brano precedente
function playPrevious() {
    if (indiceBranoCorrente > 0) {
        // Se non siamo al primo brano, vai a quello prima
        riproduciBrano(indiceBranoCorrente - 1);
    } else {
        // Se siamo al primo, vai all'ultimo della lista
        riproduciBrano(playlistAttuale.length - 1);
    }
}

// NUOVA FUNZIONE: Scarica l'immagine in modo sicuro e l'assegna alla card
async function caricaCopertina(fileId, imgId) {
    try {
        const coverUrl = `https://www.googleapis.com/drive/v3/files/${fileId}?alt=media`;
        
        // Scarichiamo l'immagine passando l'autorizzazione in modo sicuro
        const response = await fetch(coverUrl, { 
            headers: { 'Authorization': `Bearer ${accessToken}` } 
        });
        
        if (response.ok) {
            const blob = await response.blob();
            // Troviamo l'immagine nella griglia e sostituiamo il segnaposto con la copertina vera
            document.getElementById(imgId).src = URL.createObjectURL(blob);
        }
    } catch (error) {
        console.error('Errore nel caricamento della copertina:', error);
    }
}

// Funzione aggiornata per ricevere l'indice invece del brano
async function riproduciBrano(indice) {
    indiceBranoCorrente = indice; // Aggiorniamo la memoria su quale brano stiamo ascoltando
    const brano = playlistAttuale[indice]; // Peschiamo il brano dalla lista globale

    const playerContainer = document.getElementById('player-container');
    const audioPlayer = document.getElementById('audio-player');
    const nowPlaying = document.getElementById('now-playing');
    const albumCover = document.getElementById('album-cover');

    playerContainer.style.display = 'block';
    nowPlaying.textContent = `⏳ Caricamento: ${brano.titolo}...`;

    try {
        if (brano.coverDriveId) {
            const coverUrl = `https://www.googleapis.com/drive/v3/files/${brano.coverDriveId}?alt=media`;
            const coverResponse = await fetch(coverUrl, { headers: { 'Authorization': `Bearer ${accessToken}` } });
            const coverBlob = await coverResponse.blob();
            albumCover.src = URL.createObjectURL(coverBlob);
            albumCover.style.display = 'block';
        } else {
            albumCover.style.display = 'none';
        }

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

// NUOVA FUNZIONE: Brano successivo
function playNext() {
    if (indiceBranoCorrente < playlistAttuale.length - 1) {
        // Se non siamo all'ultimo brano, vai al prossimo
        riproduciBrano(indiceBranoCorrente + 1);
    } else {
        // Se siamo all'ultimo, ricomincia dal primo!
        riproduciBrano(0);
    }
}
