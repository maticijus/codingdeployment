/* VC Pulse — Dashboard JS */

const API = '';
let heatmapChart = null;
const sparklineCharts = {};

// --- Helpers ---

function formatUSD(amount) {
    if (amount == null) return '—';
    if (amount >= 1e9) return '$' + (amount / 1e9).toFixed(1) + 'B';
    if (amount >= 1e6) return '$' + (amount / 1e6).toFixed(1) + 'M';
    if (amount >= 1e3) return '$' + (amount / 1e3).toFixed(0) + 'K';
    return '$' + amount.toFixed(0);
}

function formatDate(dateStr) {
    if (!dateStr) return '—';
    const d = new Date(dateStr);
    if (isNaN(d)) return '—';
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function relativeTime(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    if (isNaN(d)) return '';
    const diff = Date.now() - d.getTime();
    const hours = Math.floor(diff / 3600000);
    if (hours < 1) return 'just now';
    if (hours < 24) return hours + 'h ago';
    const days = Math.floor(hours / 24);
    if (days < 7) return days + 'd ago';
    return formatDate(dateStr);
}

function escapeHtml(str) {
    if (!str) return '';
    const el = document.createElement('span');
    el.textContent = str;
    return el.innerHTML;
}

async function fetchJSON(url) {
    const resp = await fetch(API + url);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return resp.json();
}

// --- Loaders ---

async function loadStats() {
    try {
        const data = await fetchJSON('/api/stats?days=30');
        document.getElementById('stat-deals').textContent = data.total_deals.toLocaleString();
        document.getElementById('stat-median').textContent = formatUSD(data.median_round_size);
        document.getElementById('stat-sector').textContent = data.hottest_sector || '—';
        document.getElementById('stat-sector-count').textContent =
            data.hottest_sector ? data.hottest_sector_count + ' deals' : '';
        document.getElementById('stat-largest').textContent = formatUSD(data.largest_round);
        document.getElementById('stat-largest-company').textContent = data.largest_round_company || '';
    } catch (e) {
        console.error('Failed to load stats:', e);
    }
}

async function loadHeatmap() {
    try {
        const data = await fetchJSON('/api/sectors/heatmap?days=30');
        if (!data.length) {
            document.getElementById('heatmap-chart').parentElement.innerHTML =
                '<div class="empty-state">No sector data available yet. Run ingestion first.</div>';
            return;
        }

        const labels = data.map(d => d.sector);
        const dealCounts = data.map(d => d.deal_count);
        const avgRounds = data.map(d => d.avg_round_size || 0);
        const maxCount = Math.max(...dealCounts);

        const colors = data.map(d => {
            const intensity = 0.3 + (d.deal_count / maxCount) * 0.7;
            return `rgba(59, 130, 246, ${intensity})`;
        });

        const ctx = document.getElementById('heatmap-chart').getContext('2d');
        if (heatmapChart) heatmapChart.destroy();

        heatmapChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels,
                datasets: [{
                    label: 'Avg Round Size',
                    data: avgRounds,
                    backgroundColor: colors,
                    borderColor: 'rgba(59, 130, 246, 0.8)',
                    borderWidth: 1,
                    borderRadius: 4,
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => {
                                const i = ctx.dataIndex;
                                return [
                                    'Avg Round: ' + formatUSD(avgRounds[i]),
                                    'Deals: ' + dealCounts[i]
                                ];
                            }
                        },
                        backgroundColor: '#1a2540',
                        borderColor: '#2a3556',
                        borderWidth: 1,
                        titleColor: '#f5f7fa',
                        bodyColor: '#b0b8c8',
                    }
                },
                scales: {
                    x: {
                        ticks: {
                            color: '#7d8a9d',
                            callback: v => formatUSD(v),
                        },
                        grid: { color: 'rgba(42, 53, 86, 0.5)' },
                    },
                    y: {
                        ticks: { color: '#b0b8c8', font: { size: 12 } },
                        grid: { display: false },
                    }
                }
            }
        });
    } catch (e) {
        console.error('Failed to load heatmap:', e);
    }
}

async function loadTopDeals() {
    const tbody = document.getElementById('deals-tbody');
    try {
        const data = await fetchJSON('/api/deals/top?days=30&limit=15');
        if (!data.length) {
            tbody.innerHTML = '<tr><td colspan="6" class="empty-state">No deals yet. Run ingestion first.</td></tr>';
            return;
        }

        tbody.innerHTML = data.map(d => `
            <tr onclick="${d.source_url ? `window.open('${escapeHtml(d.source_url)}', '_blank')` : ''}">
                <td style="color: var(--text-primary); font-weight: 500;">${escapeHtml(d.company)}</td>
                <td>${d.round_type ? `<span class="round-badge">${escapeHtml(d.round_type)}</span>` : '—'}</td>
                <td class="amount">${formatUSD(d.amount_usd)}</td>
                <td>${d.sector ? `<span class="sector-badge">${escapeHtml(d.sector)}</span>` : '—'}</td>
                <td>${escapeHtml(d.lead_investors) || '—'}</td>
                <td style="white-space: nowrap;">${formatDate(d.published_at)}</td>
            </tr>
        `).join('');
    } catch (e) {
        console.error('Failed to load deals:', e);
        tbody.innerHTML = '<tr><td colspan="6" class="empty-state">Failed to load deals.</td></tr>';
    }
}

async function loadSparklines() {
    const container = document.getElementById('sparklines-container');
    try {
        const data = await fetchJSON('/api/trends/weekly');
        if (!data.length) {
            container.innerHTML = '<div class="empty-state">No trend data available yet.</div>';
            return;
        }

        container.innerHTML = '';
        const topSectors = data.slice(0, 6);

        topSectors.forEach((sector, i) => {
            const card = document.createElement('div');
            card.className = 'sparkline-card';

            const mentions = sector.weeks.map(w => w.mentions);
            const last = mentions[mentions.length - 1] || 0;
            const prev = mentions[mentions.length - 2] || 0;
            const change = prev > 0 ? ((last - prev) / prev * 100).toFixed(0) : 0;
            const changeClass = change > 0 ? 'up' : change < 0 ? 'down' : 'flat';
            const changePrefix = change > 0 ? '+' : '';

            card.innerHTML = `
                <div class="sparkline-header">
                    <span class="sparkline-sector">${escapeHtml(sector.sector)}</span>
                    <span class="sparkline-change ${changeClass}">${changePrefix}${change}%</span>
                </div>
                <div class="sparkline-canvas">
                    <canvas id="spark-${i}" height="40"></canvas>
                </div>
            `;
            container.appendChild(card);

            const ctx = document.getElementById(`spark-${i}`).getContext('2d');
            if (sparklineCharts[i]) sparklineCharts[i].destroy();

            sparklineCharts[i] = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: sector.weeks.map(w => w.week),
                    datasets: [{
                        data: mentions,
                        borderColor: changeClass === 'up' ? '#14b8a6' : changeClass === 'down' ? '#ef4444' : '#7d8a9d',
                        borderWidth: 2,
                        fill: true,
                        backgroundColor: changeClass === 'up'
                            ? 'rgba(20, 184, 166, 0.1)'
                            : changeClass === 'down'
                            ? 'rgba(239, 68, 68, 0.1)'
                            : 'rgba(125, 138, 157, 0.1)',
                        tension: 0.4,
                        pointRadius: 0,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false }, tooltip: { enabled: false } },
                    scales: {
                        x: { display: false },
                        y: { display: false, beginAtZero: true }
                    }
                }
            });
        });
    } catch (e) {
        console.error('Failed to load sparklines:', e);
    }
}

async function loadFeed() {
    const container = document.getElementById('feed-container');
    try {
        const data = await fetchJSON('/api/articles?days=30&limit=30');
        if (!data.length) {
            container.innerHTML = '<div class="empty-state">No articles yet. Run ingestion first.</div>';
            return;
        }

        container.innerHTML = data.map(d => `
            <a class="feed-card" href="${escapeHtml(d.source_url) || '#'}" target="_blank" rel="noopener">
                <div class="feed-card-header">
                    <span class="source-badge ${escapeHtml(d.source || '')}">${escapeHtml(d.source || 'unknown')}</span>
                    <span class="feed-date">${relativeTime(d.published_at)}</span>
                </div>
                <div class="feed-title">${escapeHtml(d.title)}</div>
                ${d.summary ? `<div class="feed-summary">${escapeHtml(d.summary)}</div>` : ''}
            </a>
        `).join('');
    } catch (e) {
        console.error('Failed to load feed:', e);
        container.innerHTML = '<div class="empty-state">Failed to load articles.</div>';
    }
}

// --- Init ---

async function refreshAll() {
    document.getElementById('last-updated').textContent = 'Refreshing...';
    await Promise.all([
        loadStats(),
        loadHeatmap(),
        loadTopDeals(),
        loadSparklines(),
        loadFeed(),
    ]);
    document.getElementById('last-updated').textContent =
        'Updated ' + new Date().toLocaleTimeString();
}

refreshAll();
