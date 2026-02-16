const fs = require('fs');
const fetch = require('node-fetch');
const path = require('path');

const API_KEY = process.env.GEMINI_API_KEY;
const INPUT_DIR = path.join(__dirname, '../input');
const OUTPUT_FILE = path.join(__dirname, '../output/offerte.json');

// Lista di modelli da provare in ordine. Se il primo fallisce, prova il secondo.
const MODELS_TO_TRY = [
    'gemini-1.5-flash',
    'gemini-1.5-flash-001',
    'gemini-1.5-flash-002',
    'gemini-1.5-pro',
    'gemini-1.5-pro-001'
];

async function tryGenerate(model, base64Data) {
    console.log(`🔄 Tento con il modello: ${model}...`);
    
    const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${API_KEY}`;
    
    const prompt = `Analizza questo volantino supermercato (PDF).
    Estrai un array JSON con: prodotto, prezzo, unita (es. kg/pz).
    Regole:
    - Ignora indirizzi e orari.
    - Correggi nomi (es. "SANTAGATA ACQUA" -> "Acqua Santagata").
    - Rispondi SOLO JSON valido: [{"prodotto": "...", "prezzo": 0.00}]`;

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
        if (response.status === 404) return null; // Modello non trovato, provane un altro
        const text = await response.text();
        throw new Error(`Errore API ${response.status}: ${text}`);
    }

    return await response.json();
}

async function main() {
    if (!API_KEY) {
        console.error("❌ ERRORE: Manca la GEMINI_API_KEY nei Secrets di GitHub!");
        process.exit(1);
    }

    if (!fs.existsSync(INPUT_DIR)) fs.mkdirSync(INPUT_DIR, { recursive: true });
    
    const files = fs.readdirSync(INPUT_DIR).filter(f => f.toLowerCase().endsWith('.pdf'));
    if (files.length === 0) {
        console.log("⚠️ Nessun PDF trovato.");
        return;
    }

    const pdfPath = path.join(INPUT_DIR, files[0]);
    console.log(`📄 Trovato file: ${files[0]}`);
    
    const pdfBuffer = fs.readFileSync(pdfPath);
    const base64Data = pdfBuffer.toString('base64');

    let resultData = null;

    // 🔄 LOOP DI TENTATIVI SUI MODELLI
    for (const model of MODELS_TO_TRY) {
        try {
            resultData = await tryGenerate(model, base64Data);
            if (resultData) {
                console.log(`✅ Successo con il modello: ${model}`);
                break; // Usciamo dal ciclo se funziona
            }
        } catch (e) {
            console.error(`⚠️ Errore con ${model}: ${e.message}`);
        }
    }

    if (!resultData || !resultData.candidates) {
        console.error("❌ TUTTI I MODELLI HANNO FALLITO. Controlla la chiave API o il PDF.");
        process.exit(1);
    }

    const jsonString = resultData.candidates[0].content.parts[0].text
        .replace(/```json/g, '')
        .replace(/```/g, '')
        .trim();

    const outputDir = path.dirname(OUTPUT_FILE);
    if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir, { recursive: true });

    fs.writeFileSync(OUTPUT_FILE, jsonString);
    console.log("✅ Fatto! JSON salvato in output/offerte.json");
}

main();
