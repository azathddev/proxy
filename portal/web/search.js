const form = document.getElementById("search-form");
const query = document.getElementById("query");
const type = document.getElementById("type");
const results = document.getElementById("results");
const health = document.getElementById("health");

function renderResult(item) {
  const details = Object.entries(item)
    .filter(([k]) => !["type"].includes(k))
    .map(([k, v]) => `<div><strong>${k}:</strong> ${String(v)}</div>`)
    .join("");
  return `
    <article class="card">
      <span class="type">${item.type}</span>
      ${details}
    </article>
  `;
}

async function loadHealth() {
  const res = await fetch("/api/health");
  const payload = await res.json();
  health.textContent = JSON.stringify(payload.status, null, 2);
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  results.innerHTML = "<p>Loading...</p>";

  const url = `/api/search?q=${encodeURIComponent(query.value)}&type=${encodeURIComponent(type.value)}`;
  const res = await fetch(url);
  const payload = await res.json();

  if (!Array.isArray(payload.results) || payload.results.length === 0) {
    results.innerHTML = "<p>No matches found.</p>";
    return;
  }

  results.innerHTML = payload.results.map(renderResult).join("");
});

loadHealth().catch((err) => {
  health.textContent = `Health check failed: ${err.message}`;
});

