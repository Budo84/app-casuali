const fs = require('fs');
const fetch = require('node-fetch');
const path = require('path');

const API_KEY = process.env.GEMINI_API_KEY;

// Percorsi relativi
const INPUT_DIR = path.join(__dirname, '../input');
const OUTPUT_FILE = path.join(__dirname, '../output/offerte.json');

async function main() {
    // Controllo di sicurezza: API Key presente?
    if (!API_KEY) {
        console.error("❌ ERRORE: Manca la GEMINI_API_KEY nei Secrets di GitHub!");
        process.exit(1);
    }

    // Assicura che le cartelle esistano
    if (!fs.existsSync(INPUT_DIR)) fs.mkdirSync(INPUT_DIR, { recursive: true });
    
    // Cerca PDF
    const files = fs.readdirSync(INPUT_DIR).filter(f => f.toLowerCase().endsWith('.pdf'));

    if (files.length === 0) {
        console.log("⚠️ Nessun PDF trovato in: " + INPUT_DIR);
        return;
    }

    const pdfPath = path.join(INPUT_DIR, files[0]);
    console.log(`📄 Elaborazione file: ${files[0]}`);

    // Prepara PDF per Gemini
    const pdfBuffer = fs.readFileSync(pdfPath);
    const base64Data = pdfBuffer.toString('base64');

    // Chiamata AI
    console.log("🤖 Analisi con Gemini AI...");
    
    // Prompt per l'AI
    const prompt = `Analizza questo volantino supermercato (file PDF).
    Estrai un array JSON con: prodotto, prezzo, unita (es. kg/pz).
    Regole:
    - Ignora indirizzi, orari e numeri di telefono.
    - Correggi nomi (es. "SANTAGATA ACQUA" -> "Acqua Santagata").
    - Prezzo usa il punto come separatore (es. 1.99).
    - Rispondi SOLO ed ESCLUSIVAMENTE con il JSON valido: [{"prodotto": "...", "prezzo": 0.00}]`;

    // 🔴 MODIFICA QUI: Usiamo 'gemini-1.5-flash-latest' per maggiore compatibilità
    const model = 'gemini-1.5-flash-latest'; 
    const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${API_KEY}`;

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                contents: [{
                    parts: [
                        { text: prompt },
                        { inline_data: { mime_type: "application/pdf", data: base64Data } }
                    ]
                }]
            })
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Errore API (${response.status}): ${errorText}`);
        }

        const data = await response.json();

        if (!data.candidates || data.candidates.length === 0) {
            console.error("❌ Nessun dato trovato nella risposta AI.");
            console.log(JSON.stringify(data, null, 2));
            process.exit(1);
        }

        // Pulizia del JSON (rimozione markdown ```json ... ```)
        let jsonString = data.candidates[0].content.parts[0].text
            .replace(/```json/g, '')
            .replace(/```/g, '')
            .trim();

        // Salva output
        const outputDir = path.dirname(OUTPUT_FILE);
        if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir, { recursive: true });

        fs.writeFileSync(OUTPUT_FILE, jsonString);
        console.log("✅ Fatto! JSON salvato in output/offerte.json");

    } catch (error) {
        console.error("❌ ERRORE CRITICO DURANTE L'ANALISI:", error.message);
        process.exit(1);
    }
}

main();
