const fs = require('fs');
const fetch = require('node-fetch');
const path = require('path');

const API_KEY = process.env.GEMINI_API_KEY;
const INPUT_DIR = './volantini/input';
const OUTPUT_FILE = './volantini/output/offerte.json';

async function main() {
    // 1. Cerca il file PDF
    if (!fs.existsSync(INPUT_DIR)) fs.mkdirSync(INPUT_DIR, { recursive: true });
    const files = fs.readdirSync(INPUT_DIR).filter(f => f.toLowerCase().endsWith('.pdf'));

    if (files.length === 0) {
        console.log("⚠️ Nessun PDF trovato nella cartella input.");
        return;
    }

    const pdfPath = path.join(INPUT_DIR, files[0]);
    console.log(`📄 Trovato file: ${files[0]}`);

    // 2. Prepara il file per Gemini (Base64)
    const pdfBuffer = fs.readFileSync(pdfPath);
    const base64Data = pdfBuffer.toString('base64');

    // 3. Chiedi all'AI di estrarre i dati
    console.log("🤖 Invio a Gemini AI per l'analisi...");
    
    const prompt = `Sei un estrattore dati esperto. Analizza questo volantino supermercato.
    Estrai un elenco JSON di tutti i prodotti con il loro prezzo.
    Regole:
    - Ignora indirizzi, orari, numeri di telefono.
    - Se il prodotto è "SANTAGATA ACQUA", scrivi "Acqua Santagata".
    - Formato JSON obbligatorio: [{"prodotto": "Nome", "prezzo": 0.00, "unita": "pz/kg/lt"}]
    - Rispondi SOLO con il JSON grezzo, senza markdown.`;

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

    if (!data.candidates || !data.candidates[0]) {
        console.error("❌ Errore nella risposta AI:", JSON.stringify(data));
        process.exit(1);
    }

    // 4. Pulisci e salva il JSON
    let jsonString = data.candidates[0].content.parts[0].text
        .replace(/```json/g, '')
        .replace(/```/g, '')
        .trim();

    // Assicura che la cartella output esista
    const outputDir = path.dirname(OUTPUT_FILE);
    if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir, { recursive: true });

    fs.writeFileSync(OUTPUT_FILE, jsonString);
    console.log("✅ File offerte.json generato con successo!");
}

main();
