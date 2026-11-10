document.addEventListener("DOMContentLoaded", () => {

    if (typeof L === "undefined") {
        alert("Leaflet could not load.");
        return;
    }

    // --------------------------------------------------
    // 1. Map
    // --------------------------------------------------

    const map = L.map("map").setView([25, 10], 2);

    L.tileLayer(
        "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        {
            maxZoom: 19,
            attribution: "&copy; OpenStreetMap contributors"
        }
    ).addTo(map);

    const markers = new Map();

    let cities = [];
    let unit = "C";
    let activeCity = null;
    let activeMarker = null;
    let currentWeather = null;
    let currentForecast = null;
    let activeTab = "current";

    const searchInput = document.getElementById("citySearch");
    const unitInput = document.getElementById("temperatureUnit");
    const countLabel = document.getElementById("cityCount");
    const loading = document.getElementById("loading");

    // --------------------------------------------------
    // 2. Helpers
    // --------------------------------------------------

    function escapeHtml(value) {
        return String(value ?? "").replace(
            /[&<>"']/g,
            char => ({
                "&": "&amp;",
                "<": "&lt;",
                ">": "&gt;",
                '"': "&quot;",
                "'": "&#39;"
            }[char])
        );
    }

    function temperature(value) {
        if (value === null || value === undefined) {
            return "N/A";
        }

        const c = Number(value);

        if (!Number.isFinite(c)) {
            return "N/A";
        }

        const result = unit === "F"
            ? (c * 9 / 5) + 32
            : c;

        return `${result.toFixed(1)}°${unit}`;
    }

    function numberValue(value, suffix = "") {
        if (value === null || value === undefined) {
            return "N/A";
        }

        const number = Number(value);

        return Number.isFinite(number)
            ? `${number}${suffix}`
            : "N/A";
    }

    function showLoading(isLoading) {
        loading.classList.toggle("active", isLoading);
    }

    async function fetchJSON(url) {
        const response = await fetch(url);
        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
            throw new Error(
                data.error || `HTTP ${response.status}`
            );
        }

        return data;
    }

    function tabs() {
        return `
            <div class="weather-tabs">
                <button
                    type="button"
                    class="weather-tab ${activeTab === "current" ? "active" : ""}"
                    data-weather-tab="current"
                >
                    Current
                </button>

                <button
                    type="button"
                    class="weather-tab ${activeTab === "forecast" ? "active" : ""}"
                    data-weather-tab="forecast"
                >
                    Forecast
                </button>
            </div>
        `;
    }

    // --------------------------------------------------
    // 3. Current weather
    // --------------------------------------------------

    function renderCurrent(data) {
        if (!data) {
            return `<div class="error-message">
                Current weather is not available.
            </div>`;
        }

        return `
            <div class="weather-description">
                ${escapeHtml(data.description || "Unknown conditions")}
            </div>

            <div class="weather-info">
                <div class="weather-item">
                    <strong>Temperature</strong>
                    <span>${temperature(data.temperature)}</span>
                </div>

                <div class="weather-item">
                    <strong>Feels like</strong>
                    <span>${temperature(data.feels_like)}</span>
                </div>

                <div class="weather-item">
                    <strong>Humidity</strong>
                    <span>${numberValue(data.humidity, "%")}</span>
                </div>

                <div class="weather-item">
                    <strong>Wind speed</strong>
                    <span>${numberValue(data.wind_speed, " m/s")}</span>
                </div>

                <div class="weather-item">
                    <strong>Pressure</strong>
                    <span>${numberValue(data.pressure, " hPa")}</span>
                </div>
            </div>
        `;
    }

    // --------------------------------------------------
    // 4. Forecast
    // --------------------------------------------------

    function renderForecast(data) {
        if (!data || !Array.isArray(data.forecast)) {
            return `<div class="error-message">
                Forecast is not available.
            </div>`;
        }

        return `
            <div class="forecast-list">
                ${data.forecast.map(day => `
                    <div class="forecast-day">
                        <strong>${escapeHtml(day.date)}</strong>

                        <p>
                            ${escapeHtml(day.description || "No description")}
                        </p>

                        <div class="forecast-temperature">
                            Low: ${temperature(day.min_temp)}
                            <br>
                            High: ${temperature(day.max_temp)}
                        </div>

                        <small>
                            Humidity: ${numberValue(day.humidity, "%")}
                        </small>
                    </div>
                `).join("")}
            </div>
        `;
    }

    // --------------------------------------------------
    // 5. Popup rendering
    // --------------------------------------------------

    function updatePopup() {
        if (!activeMarker || !activeCity) {
            return;
        }

        const content = activeTab === "current"
            ? renderCurrent(currentWeather)
            : renderForecast(currentForecast);

        const html = `
            <div class="weather-popup">
                <h3>
                    ${escapeHtml(activeCity.name)},
                    ${escapeHtml(activeCity.country)}
                </h3>

                ${tabs()}

                ${content}

                <p style="font-size:11px;color:#64748b;margin-top:10px">
                    Weather data provided by XWeather
                </p>
            </div>
        `;

        activeMarker.bindPopup(
            html,
            { maxWidth: 340 }
        ).openPopup();
    }

    function showError(message) {
        if (!activeMarker || !activeCity) {
            return;
        }

        activeMarker.bindPopup(`
            <div class="weather-popup">
                <h3>${escapeHtml(activeCity.name)}</h3>
                <div class="error-message">
                    ${escapeHtml(message)}
                </div>
            </div>
        `).openPopup();
    }

    // --------------------------------------------------
    // 6. Open a city
    // --------------------------------------------------

    async function openCity(city, marker) {
        activeCity = city;
        activeMarker = marker;
        activeTab = "current";

        currentWeather = null;
        currentForecast = null;

        showLoading(true);

        try {
            const weather = await fetchJSON(
                `/api/weather/${city.id}/`
            );

            // Ignore a response if another city was selected.
            if (activeCity.id !== city.id) {
                return;
            }

            currentWeather = weather;
            updatePopup();

        } catch (error) {
            if (activeCity.id === city.id) {
                showError(error.message);
            }

        } finally {
            if (activeCity.id === city.id) {
                showLoading(false);
            }
        }
    }

    // --------------------------------------------------
    // 7. Open the forecast tab
    // --------------------------------------------------

    async function loadForecast() {
        if (!activeCity) {
            return;
        }

        const cityId = activeCity.id;

        activeTab = "forecast";
        updatePopup();

        if (currentForecast) {
            return;
        }

        showLoading(true);

        try {
            const data = await fetchJSON(
                `/api/forecast/${cityId}/`
            );

            if (activeCity.id !== cityId) {
                return;
            }

            currentForecast = data;
            updatePopup();

        } catch (error) {
            if (activeCity.id === cityId && activeMarker) {
                activeMarker.setPopupContent(`
                    <div class="weather-popup">
                        <h3>${escapeHtml(activeCity.name)}</h3>
                        ${tabs()}
                        <div class="error-message">
                            ${escapeHtml(error.message)}
                        </div>
                    </div>
                `);
                activeMarker.openPopup();
            }

        } finally {
            if (activeCity.id === cityId) {
                showLoading(false);
            }
        }
    }

    // The popup buttons are created dynamically.
    document.addEventListener("click", event => {
        const button = event.target.closest(
            "[data-weather-tab]"
        );

        if (!button) {
            return;
        }

        const selectedTab = button.dataset.weatherTab;

        if (selectedTab === "current") {
            activeTab = "current";
            updatePopup();
        }

        if (selectedTab === "forecast") {
            loadForecast();
        }
    });

    // --------------------------------------------------
    // 8. Load cities
    // --------------------------------------------------

    function addCityMarker(city) {
        const marker = L.circleMarker(
            [city.latitude, city.longitude],
            {
                radius: 8,
                color: "#ffffff",
                weight: 2,
                fillColor: "#2563eb",
                fillOpacity: 0.95
            }
        ).addTo(map);

        marker.bindTooltip(
            `${city.name}, ${city.country}`
        );

        marker.on("click", () => {
            openCity(city, marker);
        });

        markers.set(city.id, marker);
    }

    async function loadCities() {
        try {
            cities = await fetchJSON("/api/cities/");

            cities.forEach(addCityMarker);

            countLabel.textContent =
                `${cities.length} cities available`;

        } catch (error) {
            countLabel.textContent =
                "Could not load cities";

            console.error(error);
        }
    }

    // --------------------------------------------------
    // 9. Search
    // --------------------------------------------------

    searchInput.addEventListener("input", () => {
        const query = searchInput.value
            .trim()
            .toLowerCase();

        if (!query) {
            countLabel.textContent =
                `${cities.length} cities available`;
            return;
        }

        const matches = cities.filter(city =>
            city.name.toLowerCase().includes(query) ||
            city.country.toLowerCase().includes(query)
        );

        countLabel.textContent =
            `${matches.length} matching cities`;

        if (matches.length > 0) {
            const city = matches[0];

            map.setView(
                [city.latitude, city.longitude],
                6
            );

            const marker = markers.get(city.id);

            if (marker) {
                marker.openTooltip();
            }
        }
    });

    // --------------------------------------------------
    // 10. Celsius / Fahrenheit
    // --------------------------------------------------

    unitInput.addEventListener("change", event => {
        unit = event.target.value;
        updatePopup();
    });

    // --------------------------------------------------
    // 11. Reset
    // --------------------------------------------------

    document.getElementById("resetMap").addEventListener(
        "click",
        () => {
            searchInput.value = "";

            map.setView([25, 10], 2);
            map.closePopup();

            countLabel.textContent =
                `${cities.length} cities available`;
        }
    );

    loadCities();
});