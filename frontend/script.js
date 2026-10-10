let currentFile = null;
let currentPlots = [];

// Upload
document.getElementById('uploadBtn').addEventListener('click', async () => {
    const fileInput = document.getElementById('fileInput');
    const status = document.getElementById('uploadStatus');
    if (!fileInput.files.length) {
        status.textContent = 'Please select a file.';
        return;
    }
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    status.textContent = 'Uploading...';
    try {
        const res = await fetch('/api/upload', { method: 'POST', body: formData });
        const data = await res.json();
        if (res.ok) {
            currentFile = data.filename;
            status.textContent = `✅ Uploaded: ${currentFile}`;
        } else {
            status.textContent = `❌ Error: ${data.error}`;
        }
    } catch (e) {
        status.textContent = '❌ Upload failed.';
    }
});

// Analyze
document.getElementById('analyzeBtn').addEventListener('click', async () => {
    if (!currentFile) {
        alert('Please upload a CSV file first.');
        return;
    }
    const minSupport = parseFloat(document.getElementById('minSupport').value) || 0.02;
    const minConfidence = parseFloat(document.getElementById('minConfidence').value) || 0.1;
    const minFreq = parseInt(document.getElementById('minFreq').value) || 20;

    document.getElementById('analyzeBtn').textContent = 'Running...';
    try {
        const res = await fetch('/api/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: currentFile, min_support: minSupport, min_confidence: minConfidence, min_freq: minFreq })
        });
        const data = await res.json();
        if (res.ok) {
            currentPlots = data.plots || [];
            displayStats(data.stats);
            displayPlots(currentPlots);
            await loadTopItems();
            await loadTopRules();
            document.getElementById('statsContainer').style.display = 'block';
            document.getElementById('plotsContainer').style.display = 'block';
            document.getElementById('tablesContainer').style.display = 'block';
            document.getElementById('recContainer').style.display = 'block';
        } else {
            alert('Error: ' + data.error);
        }
    } catch (e) {
        alert('Analysis failed.');
    }
    document.getElementById('analyzeBtn').textContent = '▶ Run Analysis';
});

// Display Stats
function displayStats(stats) {
    const grid = document.getElementById('statGrid');
    const items = [
        { label: 'Transactions', value: stats.total_transactions },
        { label: 'Products', value: stats.total_products },
        { label: 'Frequent Itemsets', value: stats.frequent_itemsets },
        { label: 'Total Rules', value: stats.total_rules },
        { label: 'Strong Rules (≥50% conf)', value: stats.strong_rules }
    ];
    grid.innerHTML = items.map(s => `
        <div class="stat-card">
            <div class="value">${s.value}</div>
            <div class="label">${s.label}</div>
        </div>
    `).join('');
}

// Display Plots
function displayPlots(plots) {
    const container = document.getElementById('plotGrid');
    container.innerHTML = plots.map(p => `
        <img src="/api/plots/${p}" alt="${p}" loading="lazy">
    `).join('');
}

// Load Top Items
async function loadTopItems() {
    const res = await fetch('/api/top-items');
    const data = await res.json();
    if (res.ok && data.length) {
        const html = `
            <table>
                <thead><tr><th>Item</th><th>Support</th></tr></thead>
                <tbody>${data.map(d => `<tr><td>${d.items}</td><td>${d.support.toFixed(4)}</td></tr>`).join('')}</tbody>
            </table>
        `;
        document.getElementById('itemsTable').innerHTML = html;
    }
}

// Load Top Rules
async function loadTopRules() {
    const res = await fetch('/api/top-rules');
    const data = await res.json();
    if (res.ok && data.length) {
        const html = `
            <table>
                <thead><tr><th>Antecedent</th><th>Consequent</th><th>Support</th><th>Confidence</th><th>Lift</th></tr></thead>
                <tbody>${data.map(d => `
                    <tr>
                        <td>${d.antecedents}</td>
                        <td>${d.consequents}</td>
                        <td>${d.support.toFixed(4)}</td>
                        <td>${d.confidence.toFixed(4)}</td>
                        <td>${d.lift.toFixed(2)}</td>
                    </tr>
                `).join('')}</tbody>
            </table>
        `;
        document.getElementById('rulesTable').innerHTML = html;
    }
}

// Recommendations
document.getElementById('recBtn').addEventListener('click', async () => {
    const product = document.getElementById('recProduct').value.trim();
    if (!product) { alert('Enter a product name.'); return; }
    try {
        const res = await fetch('/api/recommend', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ product })
        });
        const data = await res.json();
        if (res.ok && data.length) {
            const html = `
                <table>
                    <thead><tr><th>If Customer Buys</th><th>Recommend</th><th>Confidence (%)</th><th>Lift</th></tr></thead>
                    <tbody>${data.map(d => `
                        <tr><td>${d.antecedents}</td><td>${d.consequents}</td><td>${d.confidence}</td><td>${d.lift}</td></tr>
                    `).join('')}</tbody>
                </table>
            `;
            document.getElementById('recResults').innerHTML = html;
        } else {
            document.getElementById('recResults').innerHTML = '<p style="color:#94a3b8;">No strong recommendations found for this product.</p>';
        }
    } catch (e) {
        alert('Recommendation failed.');
    }
});

// Initial state
document.getElementById('statsContainer').style.display = 'none';
document.getElementById('plotsContainer').style.display = 'none';
document.getElementById('tablesContainer').style.display = 'none';
document.getElementById('recContainer').style.display = 'none';