/* Previsioni meteo per una tappa (coordinate di arrivo), tramite Open-Meteo:
   gratuita, senza chiave, nessun limite di utilizzo per uso non commerciale. */

const METEO = {
  ENDPOINT: 'https://api.open-meteo.com/v1/forecast',

  async previsioni(lat, lon) {
    const url = `${this.ENDPOINT}?latitude=${lat}&longitude=${lon}&daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=auto&forecast_days=5`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Il servizio meteo ha risposto con errore ${res.status}.`);
    const data = await res.json();
    const giorni = data.daily.time.map((data_, i) => ({
      data: data_,
      tempMax: Math.round(data.daily.temperature_2m_max[i]),
      tempMin: Math.round(data.daily.temperature_2m_min[i]),
      precipitazione: data.daily.precipitation_probability_max[i],
      codice: data.daily.weathercode[i]
    }));
    return giorni;
  },

  // Traduce il weathercode WMO in un'emoji e una breve descrizione in italiano
  descrizione(codice) {
    const mappa = {
      0: ['☀️', 'Sereno'], 1: ['🌤️', 'Poco nuvoloso'], 2: ['⛅', 'Parz. nuvoloso'], 3: ['☁️', 'Coperto'],
      45: ['🌫️', 'Nebbia'], 48: ['🌫️', 'Nebbia'],
      51: ['🌦️', 'Pioviggine'], 53: ['🌦️', 'Pioviggine'], 55: ['🌧️', 'Pioviggine'],
      61: ['🌧️', 'Pioggia debole'], 63: ['🌧️', 'Pioggia'], 65: ['🌧️', 'Pioggia forte'],
      71: ['🌨️', 'Neve debole'], 73: ['🌨️', 'Neve'], 75: ['❄️', 'Neve forte'],
      80: ['🌦️', 'Rovesci'], 81: ['🌧️', 'Rovesci'], 82: ['⛈️', 'Rovesci forti'],
      95: ['⛈️', 'Temporale'], 96: ['⛈️', 'Temporale'], 99: ['⛈️', 'Temporale forte']
    };
    return mappa[codice] || ['🌡️', 'N/D'];
  }
};
