const fs = require('fs');
const path = require('path');
const fetch = require('node-fetch');

// CONFIGURAZIONE
const API_KEY = process.env.GEMINI_API_KEY;
const INPUT_DIR = path.join(__dirname, '../input');
const OUTPUT_FILE = path.join(__dirname, '../output/offerte.json');

// Lista di modelli da tentare (tutti su endpoint v1beta)
const MODELS = [
    'gemini-1.5-flash',
    'gemini-1.5-flash-latest',
    'gemini-1.5-pro',
    'gemini-1.5-pro-latest',
    'gemini-1.0-pro-vision-latest' // Fallback vecchio ma affidabile
];

async function callGemini(modelName, base64Image) {
    // NOTA: Forziamo qui v1beta
    const url = `https://generativelanguage.googleapis.com/v1beta/models/${modelName}:generateContent?key=${API_KEY}`;
    
    console.log(`📡 Tento connessione a: ${modelName}...`);

    const prompt = `Analizza questo volantino (PDF) come se fossi un estrattore dati OCR avanzato.
    Estrai un array JSON valido con le offerte.
    Struttura: [{"prodotto": "Nome Prodotto", "prezzo": 1.99, "unita": "pz"}]
    Regole:
    - Prezzi: usa il punto per i decimali (es. 1.50).
    - Ignora: indirizzi, orari, numeri telefono, slogan.
    - Se trovi scritte come "SANTAGATA" e "1.5L" vicine, uniscile in "Acqua Santagata 1.5L".
    - Rispondi SOLO con il JSON.`;

    const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            contents: [{
                parts: [
                    { text: prompt },
                    { 
                        inline_data: { 
                            mime_type: "application/pdf", 
                            data: base64Image 
                        } 
                    }
                ]
            }]
        })
    });

    if (!response.ok) {
        // Se è un errore 404, ritorna null per provare il prossimo modello
        if (response.status === 404) {
            console.log(`⚠️ Modello ${modelName} non trovato (404). Passo al prossimo.`);
            return null;
        }
        // Altri errori (es. chiave scaduta, 500)
        const errText = await response.text();
        throw new Error(`Errore HTTP ${response.status}: ${errText}`);
    }

    const data = await response.json();
    return data;
}

async function main() {
    if (!API_KEY) {
        console.error("❌ ERRORE: Manca la GEMINI_API_KEY nei Secrets!");
        process.exit(1);
    }

    if (!fs.existsSync(INPUT_DIR)) fs.mkdirSync(INPUT_DIR, { recursive: true });
    
    // Cerca PDF
    const files = fs.readdirSync(INPUT_DIR).filter(f => f.toLowerCase().endsWith('.pdf'));
    if (files.length === 0) {
        console.log("⚠️ Nessun PDF trovato.");
        return;
    }

    const pdfPath = path.join(INPUT_DIR, files[0]);
    console.log(`📄 Elaborazione file: ${files[0]}`);

    const pdfBuffer = fs.readFileSync(pdfPath);
    const base64Data = pdfBuffer.toString('base64');

    let finalJson = null;

    // 🔄 Loop tentativi modelli
    for (const model of MODELS) {
        try {
            const result = await callGemini(model, base64Data);
            if (result && result.candidates && result.candidates.length > 0) {
                finalJson = result.candidates[0].content.parts[0].text;
                console.log(`✅ Successo con il modello: ${model}`);
                break; // Uscita dal loop
            }
        } catch (err) {
            console.error(`❌ Errore con ${model}:`, err.message);
        }
    }

    if (!finalJson) {
        console.error("❌ TUTTI I TENTATIVI SONO FALLITI.");
        process.exit(1);
    }

    // Pulizia e Salvataggio
    try {
        const cleanJson = finalJson.replace(/```json/g, '').replace(/```/g, '').trim();
        // Test validità JSON
        JSON.parse(cleanJson);

        const outputDir = path.dirname(OUTPUT_FILE);
        if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir, { recursive: true });

        fs.writeFileSync(OUTPUT_FILE, cleanJson);
        console.log("💾 File offerte.json salvato correttamente!");

    } catch (e) {
        console.error("❌ L'AI ha risposto ma il JSON non è valido:", e.message);
        console.log("Raw output:", finalJson);
        process.exit(1);
    }
}

main();
