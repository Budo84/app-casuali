const fs = require('fs');
const path = require('path');
const { GoogleGenerativeAI } = require("@google/generative-ai");

// CONFIGURAZIONE
const API_KEY = process.env.GEMINI_API_KEY;
const INPUT_DIR = path.join(__dirname, '../input');
const OUTPUT_FILE = path.join(__dirname, '../output/offerte.json');

async function main() {
    // 1. Controllo Sicurezza
    if (!API_KEY) {
        console.error("❌ ERRORE: Manca la GEMINI_API_KEY nei Secrets di GitHub!");
        process.exit(1);
    }

    // 2. Cerca PDF
    if (!fs.existsSync(INPUT_DIR)) fs.mkdirSync(INPUT_DIR, { recursive: true });
    const files = fs.readdirSync(INPUT_DIR).filter(f => f.toLowerCase().endsWith('.pdf'));

    if (files.length === 0) {
        console.log("⚠️ Nessun PDF trovato da elaborare.");
        return;
    }

    const pdfPath = path.join(INPUT_DIR, files[0]);
    console.log(`📄 Trovato file: ${files[0]}`);

    // 3. Prepara il file per l'SDK di Google
    const pdfBuffer = fs.readFileSync(pdfPath);
    // Converte il buffer in formato base64 accettato da Gemini
    const pdfBase64 = pdfBuffer.toString('base64');
    
    const filePart = {
        inlineData: {
            data: pdfBase64,
            mimeType: "application/pdf",
        },
    };

    // 4. Inizializza l'AI (Usa la libreria ufficiale)
    console.log("🤖 Connessione a Gemini...");
    const genAI = new GoogleGenerativeAI(API_KEY);
    
    // Usa il modello più stabile
    const model = genAI.getGenerativeModel({ model: "gemini-1.5-flash" });

    const prompt = `Analizza questo volantino (file PDF).
    Estrai un array JSON contenente le offerte.
    Ogni oggetto deve avere: "prodotto", "prezzo" (numero con punto), "unita" (kg/pz/lt).
    Regole:
    - Ignora indirizzi, orari, telefoni e testo generico.
    - Correggi i nomi dei prodotti se sono spezzati.
    - Rispondi SOLO con il codice JSON, niente markdown.`;

    try {
        const result = await model.generateContent([prompt, filePart]);
        const response = await result.response;
        const text = response.text();

        // 5. Pulisci il risultato
        let jsonString = text.replace(/```json/g, '').replace(/```/g, '').trim();

        // Verifica che sia JSON valido
        JSON.parse(jsonString); 

        // 6. Salva
        const outputDir = path.dirname(OUTPUT_FILE);
        if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir, { recursive: true });
        
        fs.writeFileSync(OUTPUT_FILE, jsonString);
        console.log("✅ Successo! JSON salvato in output/offerte.json");

    } catch (error) {
        console.error("❌ Errore durante l'analisi AI:");
        console.error(error.message);
        // Se l'errore è 500 o block, spesso riprovare funziona, ma qui usciamo.
        process.exit(1);
    }
}

main();
