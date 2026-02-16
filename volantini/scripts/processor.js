const fs = require('fs');
const fetch = require('node-fetch');
const path = require('path');

const API_KEY = process.env.GEMINI_API_KEY;

// Percorsi relativi alla posizione di QUESTO script (dentro /scripts)
const INPUT_DIR = path.join(__dirname, '../input');
const OUTPUT_FILE = path.join(__dirname, '../output/offerte.json');

async function main() {
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
    const prompt = `Analizza questo volantino supermercato.
    Estrai un array JSON con: prodotto, prezzo, unita (es. kg/pz).
    Regole:
    - Ignora indirizzi e orari.
    - Correggi nomi (es. "SANTAGATA ACQUA" -> "Acqua Santagata").
    - Rispondi SOLO JSON valido: [{"prodotto": "...", "prezzo": 0.00}]`;

    const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${API_KEY}`, {
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

    const data = await response.json();

    if (!data.candidates) {
        console.error("❌ Errore API:", JSON.stringify(data));
        process.exit(1);
    }

    const jsonString = data.candidates[0].content.parts[0].text
        .replace(/```json|```/g, '')
        .trim();

    // Salva output
    const outputDir = path.dirname(OUTPUT_FILE);
    if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir, { recursive: true });

    fs.writeFileSync(OUTPUT_FILE, jsonString);
    console.log("✅ Fatto! JSON salvato in output/offerte.json");
}

main();
