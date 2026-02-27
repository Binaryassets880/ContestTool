// Grand Arena Contest Tool - Frontend

let upcomingTable = null;
let analysisTable = null;
let schemesTable = null;
let classChangesTable = null;
let selectedTokenId = null;
let selectedSchemeTokenId = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    loadUpcomingData();
    initInfoOverlay();
});

// Initialize info overlay toggle
function initInfoOverlay() {
    const infoBtn = document.getElementById('ms-info-btn');
    const overlay = document.getElementById('ms-info-overlay');

    if (infoBtn && overlay) {
        infoBtn.addEventListener('click', () => {
            overlay.classList.add('show');
        });

        // Close when clicking outside the content
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                overlay.classList.remove('show');
            }
        });
    }
}

// Tab switching
function initTabs() {
    const tabs = document.querySelectorAll('.tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            if (tab.disabled) return;

            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            const tabId = tab.dataset.tab;
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            document.getElementById(tabId).classList.add('active');

            // Load analysis data when tab is clicked
            if (tabId === 'analysis' && !analysisTable) {
                loadAnalysisData();
            }

            // Load schemes data when tab is clicked
            if (tabId === 'schemes' && !schemesTable) {
                loadSchemesData();
            }

            // Load class changes data when tab is clicked
            if (tabId === 'class-changes' && !classChangesTable) {
                loadClassChangesData();
            }
        });
    });
}

// Load upcoming matchups data
async function loadUpcomingData() {
    const container = document.getElementById('upcoming-table');
    container.innerHTML = '<div class="loading">Loading matchup data...</div>';

    try {
        const response = await fetch('/api/upcoming');
        const data = await response.json();
        initUpcomingTable(data);
    } catch (error) {
        container.innerHTML = `<div class="loading">Error loading data: ${error.message}</div>`;
    }
}

// Initialize the upcoming matchups table
function initUpcomingTable(data) {
    upcomingTable = new Tabulator("#upcoming-table", {
        data: data,
        layout: "fitColumns",
        responsiveLayout: "collapse",
        rowHeight: 40,
        selectable: 1,

        columns: [
            {
                title: "Champion",
                field: "name",
                minWidth: 150,
                headerTooltip: "Champion name - click row to see matchup details"
            },
            {
                title: "Class",
                field: "class",
                width: 100,
                headerTooltip: "Champion's role/class",
                formatter: function(cell) {
                    const cls = cell.getValue();
                    return `<span class="class-badge class-${cls}">${cls}</span>`;
                }
            },
            {
                title: "Base WR%",
                field: "base_win_rate",
                width: 100,
                hozAlign: "center",
                headerTooltip: "Historical win rate from all past matches",
                formatter: function(cell) {
                    return cell.getValue().toFixed(1) + '%';
                }
            },
            {
                title: "Games",
                field: "games",
                width: 70,
                hozAlign: "center",
                headerTooltip: "Number of scheduled upcoming games"
            },
            {
                title: "Exp Wins",
                field: "expected_wins",
                width: 90,
                hozAlign: "center",
                headerTooltip: "Expected wins based on matchup scores. Sum of (score/100) for each game.",
                formatter: function(cell) {
                    const val = cell.getValue();
                    const games = cell.getRow().getData().games;
                    const ratio = val / games;
                    let cls = 'score-medium';
                    if (ratio >= 0.6) cls = 'score-high';
                    else if (ratio < 0.5) cls = 'score-low';
                    return `<span class="${cls}">${val.toFixed(1)}</span>`;
                },
                sorter: "number"
            },
            {
                title: "Avg Score",
                field: "avg_score",
                width: 90,
                hozAlign: "center",
                headerTooltip: "Average matchup score across all upcoming games (0-100). Higher = better matchups.",
                formatter: function(cell) {
                    const val = cell.getValue();
                    let cls = 'score-medium';
                    if (val >= 60) cls = 'score-high';
                    else if (val < 40) cls = 'score-low';
                    return `<span class="${cls}">${val.toFixed(1)}</span>`;
                }
            },
            {
                title: "Favorable",
                field: "favorable",
                width: 100,
                hozAlign: "center",
                headerTooltip: "Games with matchup score >= 60 (good odds to win)",
                formatter: function(cell) {
                    const val = cell.getValue();
                    const total = cell.getRow().getData().games;
                    const cls = val >= total * 0.6 ? 'favorable-high' : '';
                    return `<span class="${cls}">${val}</span>`;
                },
                sorter: "number"
            },
            {
                title: "Unfavorable",
                field: "unfavorable",
                width: 100,
                hozAlign: "center",
                headerTooltip: "Games with matchup score < 40 (tough matchups)",
                formatter: function(cell) {
                    const val = cell.getValue();
                    const cls = val > 5 ? 'unfavorable-high' : '';
                    return `<span class="${cls}">${val}</span>`;
                },
                sorter: "number"
            }
        ],

        initialSort: [
            { column: "expected_wins", dir: "desc" }
        ],

        rowFormatter: function(row) {
            row.getElement().style.cursor = 'pointer';
        }
    });

    // Handle row click
    upcomingTable.on("rowClick", function(e, row) {
        const tokenId = row.getData().token_id;
        const rowElement = row.getElement();

        if (selectedTokenId === tokenId) {
            hideDetailPanel();
            selectedTokenId = null;
            upcomingTable.deselectRow();
        } else {
            selectedTokenId = tokenId;
            showMatchupDetail(tokenId, rowElement);
        }
    });

    // Search filter
    document.getElementById('search').addEventListener('input', function() {
        const val = this.value.toLowerCase();
        upcomingTable.setFilter(function(data) {
            return data.name.toLowerCase().includes(val);
        });
    });

    // Class filter
    document.getElementById('class-filter').addEventListener('change', function() {
        const val = this.value;
        if (val) {
            upcomingTable.setFilter("class", "=", val);
        } else {
            upcomingTable.clearFilter();
        }
        const searchVal = document.getElementById('search').value;
        if (searchVal) {
            upcomingTable.addFilter(function(data) {
                return data.name.toLowerCase().includes(searchVal.toLowerCase());
            });
        }
    });
}

// Hide the detail panel
function hideDetailPanel() {
    const panel = document.getElementById('detail-panel');
    panel.classList.add('hidden');
    panel.innerHTML = '';
}

// Show matchup detail for a champion - positioned after clicked row
async function showMatchupDetail(tokenId, rowElement) {
    const panel = document.getElementById('detail-panel');
    panel.classList.remove('hidden');
    panel.innerHTML = '<div class="loading">Loading matchup details...</div>';

    // Move panel to appear right after the clicked row
    rowElement.insertAdjacentElement('afterend', panel);

    try {
        const response = await fetch(`/api/champions/${tokenId}/matchups`);
        const data = await response.json();
        renderMatchupDetail(panel, data);
    } catch (error) {
        panel.innerHTML = `<div class="loading">Error loading details: ${error.message}</div>`;
    }
}

// Format supporter info with name, class, and stats
function formatSupporter(s) {
    // Handle undefined/null supporters
    if (!s) return '';

    // Extract ID from name if it's "Moki #1234" format, otherwise use token_id
    let displayName = s.name || `#${s.token_id || '?'}`;
    if (s.name && s.name.startsWith('Moki #')) {
        displayName = s.name;  // Already has ID
    } else if (s.token_id) {
        displayName = `#${s.token_id}`;
    }

    const careerElims = s.career_elims ?? 0;
    const careerDeps = s.career_deps ?? 0;
    const careerWart = s.career_wart ?? 0;
    const suppClass = s.class || 'Unknown';

    const elimClass = careerElims >= 2.0 ? 'high-elims' : (careerElims < 1.0 ? 'low-elims' : '');

    return `
        <div class="supporter-card">
            <span class="supp-name">${displayName}</span>
            <span class="class-badge class-${suppClass}">${suppClass}</span>
            <span class="supp-stats">
                <span class="${elimClass}" title="Career Avg Eliminations">${careerElims.toFixed(1)}e</span>
                <span title="Career Avg Gacha Deposits">${careerDeps.toFixed(1)}g</span>
                <span title="Career Avg Wart Distance">${careerWart.toFixed(0)}w</span>
            </span>
        </div>
    `;
}

// Render the matchup detail table
function renderMatchupDetail(container, data) {
    const champion = data.champion;
    const matchups = data.matchups;

    container.innerHTML = `
        <h3>
            <span>${champion.name}'s Upcoming Schedule (${matchups.length} games)</span>
            <div class="score-legend">
                <span class="legend-item"><span class="score-high">Green</span> = Favorable (60+)</span>
                <span class="legend-item"><span class="score-medium">Yellow</span> = Even (40-60)</span>
                <span class="legend-item"><span class="score-low">Red</span> = Tough (&lt;40)</span>
            </div>
            <button class="close-btn" onclick="hideDetailPanel(); selectedTokenId = null; upcomingTable.deselectRow();">Close</button>
        </h3>
        <div id="detail-table"></div>
    `;

    // Create detail Tabulator
    new Tabulator("#detail-table", {
        data: matchups,
        layout: "fitColumns",
        height: Math.min(500, matchups.length * 55 + 60),

        columns: [
            {
                title: "Date",
                field: "date",
                width: 95,
                headerTooltip: "Match date"
            },
            {
                title: "Opponent",
                field: "opponent",
                minWidth: 110,
                headerTooltip: "Opponent champion name"
            },
            {
                title: "Class",
                field: "opponent_class",
                width: 90,
                headerTooltip: "Opponent champion class",
                formatter: function(cell) {
                    const cls = cell.getValue();
                    return `<span class="class-badge class-${cls}">${cls}</span>`;
                }
            },
            {
                title: "My Supporters",
                field: "my_supporters",
                minWidth: 280,
                headerTooltip: "Your supporting mokis: ID, Class, then stats (e=elims, g=gacha deposits, w=wart distance)",
                formatter: function(cell) {
                    const supps = cell.getValue();
                    return supps.map(s => formatSupporter(s)).join('');
                }
            },
            {
                title: "Opp Supporters",
                field: "opp_supporters",
                minWidth: 280,
                headerTooltip: "Opponent's supporting mokis: ID, Class, then stats (e=elims, g=gacha deposits, w=wart distance)",
                formatter: function(cell) {
                    const supps = cell.getValue();
                    return supps.map(s => formatSupporter(s)).join('');
                }
            },
            {
                title: "Score",
                field: "score",
                width: 70,
                hozAlign: "center",
                headerTooltip: "Matchup score (0-100): Based on your base WR, class advantage, supporter elims vs opponent elims",
                formatter: function(cell) {
                    const val = cell.getValue();
                    let cls = 'score-medium';
                    if (val >= 60) cls = 'score-high';
                    else if (val < 40) cls = 'score-low';
                    return `<span class="${cls}">${val.toFixed(1)}</span>`;
                }
            },
            {
                title: "Edge",
                field: "edge",
                width: 90,
                hozAlign: "center",
                headerTooltip: "Favorable (60+), Even (40-60), or Tough (<40)",
                formatter: function(cell) {
                    const val = cell.getValue();
                    let cls = 'edge-even';
                    if (val === 'Favorable') cls = 'edge-favorable';
                    else if (val === 'Tough') cls = 'edge-tough';
                    return `<span class="${cls}">${val}</span>`;
                }
            }
        ],

        initialSort: [
            { column: "score", dir: "desc" }
        ]
    });
}

// ========== ANALYSIS TAB ==========

// Load historical analysis data
async function loadAnalysisData() {
    const container = document.getElementById('analysis-table');
    container.innerHTML = '<div class="loading">Loading historical data...</div>';

    try {
        const response = await fetch('/api/analysis?limit=2000');
        const data = await response.json();
        renderBucketStats(data.bucket_stats);
        initAnalysisTable(data.games);
    } catch (error) {
        container.innerHTML = `<div class="loading">Error loading data: ${error.message}</div>`;
    }
}

// Render the win rate by MS bucket summary
function renderBucketStats(stats) {
    const container = document.getElementById('bucket-stats');

    let html = '<div class="bucket-cards">';
    stats.forEach(bucket => {
        let colorClass = 'bucket-neutral';
        if (bucket.win_rate >= 60) colorClass = 'bucket-good';
        else if (bucket.win_rate < 50) colorClass = 'bucket-bad';

        html += `
            <div class="bucket-card ${colorClass}">
                <div class="bucket-range">MS ${bucket.range}</div>
                <div class="bucket-winrate">${bucket.win_rate}%</div>
                <div class="bucket-sample">${bucket.wins}/${bucket.games} wins</div>
            </div>
        `;
    });
    html += '</div>';

    container.innerHTML = html;
}

// Initialize the analysis table
function initAnalysisTable(games) {
    analysisTable = new Tabulator("#analysis-table", {
        data: games,
        layout: "fitColumns",
        height: 500,
        pagination: true,
        paginationSize: 50,

        columns: [
            {
                title: "Date",
                field: "date",
                width: 100,
                headerTooltip: "Match date"
            },
            {
                title: "Champion",
                field: "champion",
                minWidth: 130,
                headerTooltip: "Your champion"
            },
            {
                title: "Class",
                field: "champion_class",
                width: 90,
                headerTooltip: "Champion class",
                formatter: function(cell) {
                    const cls = cell.getValue();
                    return `<span class="class-badge class-${cls}">${cls}</span>`;
                }
            },
            {
                title: "Opponent",
                field: "opponent",
                minWidth: 130,
                headerTooltip: "Opponent champion"
            },
            {
                title: "Opp Class",
                field: "opponent_class",
                width: 90,
                headerTooltip: "Opponent class",
                formatter: function(cell) {
                    const cls = cell.getValue();
                    return `<span class="class-badge class-${cls}">${cls}</span>`;
                }
            },
            {
                title: "MS",
                field: "matchup_score",
                width: 70,
                hozAlign: "center",
                headerTooltip: "Matchup Score (calculated before game)",
                formatter: function(cell) {
                    const val = cell.getValue();
                    let cls = 'score-medium';
                    if (val >= 70) cls = 'score-high';
                    else if (val < 50) cls = 'score-low';
                    return `<span class="${cls}">${val}</span>`;
                }
            },
            {
                title: "Result",
                field: "result",
                width: 70,
                hozAlign: "center",
                headerTooltip: "Game result",
                formatter: function(cell) {
                    const val = cell.getValue();
                    const cls = val === 'W' ? 'result-win' : 'result-loss';
                    return `<span class="${cls}">${val}</span>`;
                }
            },
            {
                title: "Win Type",
                field: "win_type",
                width: 100,
                headerTooltip: "How the game was won"
            }
        ],

        initialSort: [
            { column: "date", dir: "desc" }
        ]
    });

    // Set up filters
    document.getElementById('analysis-search').addEventListener('input', function() {
        applyAnalysisFilters();
    });

    document.getElementById('analysis-result-filter').addEventListener('change', function() {
        applyAnalysisFilters();
    });

    document.getElementById('analysis-ms-filter').addEventListener('change', function() {
        applyAnalysisFilters();
    });
}

// Apply all analysis filters
function applyAnalysisFilters() {
    const searchVal = document.getElementById('analysis-search').value.toLowerCase();
    const resultVal = document.getElementById('analysis-result-filter').value;
    const msVal = document.getElementById('analysis-ms-filter').value;

    analysisTable.setFilter(function(data) {
        // Search filter - only match champion column (to see matchups from their perspective)
        if (searchVal && !data.champion.toLowerCase().includes(searchVal)) {
            return false;
        }

        // Result filter
        if (resultVal && data.result !== resultVal) {
            return false;
        }

        // MS filter
        if (msVal && data.matchup_score < parseInt(msVal)) {
            return false;
        }

        return true;
    });
}

// ========== SCHEMES TAB ==========

// Load schemes data
async function loadSchemesData() {
    const container = document.getElementById('schemes-table');
    container.innerHTML = '<div class="loading">Loading schemes data...</div>';

    try {
        const response = await fetch('/api/schemes');
        const data = await response.json();
        initSchemesTable(data.champions);
    } catch (error) {
        container.innerHTML = `<div class="loading">Error loading data: ${error.message}</div>`;
    }
}

// Initialize the schemes table
function initSchemesTable(champions) {
    schemesTable = new Tabulator("#schemes-table", {
        data: champions,
        layout: "fitColumns",
        height: 500,
        selectable: 1,

        columns: [
            {
                title: "Champion",
                field: "name",
                minWidth: 140,
                headerTooltip: "Champion name - click to see upcoming matchups"
            },
            {
                title: "Class",
                field: "class",
                width: 100,
                headerTooltip: "Champion class",
                formatter: function(cell) {
                    const cls = cell.getValue();
                    return `<span class="class-badge class-${cls}">${cls}</span>`;
                }
            },
            {
                title: "Matching Schemes",
                field: "matching_schemes",
                minWidth: 250,
                headerTooltip: "Trait-based schemes this champion qualifies for",
                formatter: function(cell) {
                    const schemes = cell.getValue();
                    if (!schemes || schemes.length === 0) {
                        return '<span class="no-schemes">None</span>';
                    }
                    return schemes.map(s => `<span class="scheme-tag">${s}</span>`).join(' ');
                }
            },
            {
                title: "Games",
                field: "games",
                width: 70,
                hozAlign: "center",
                headerTooltip: "Number of upcoming games"
            },
            {
                title: "Avg MS",
                field: "avg_score",
                width: 85,
                hozAlign: "center",
                headerTooltip: "Average Matchup Score for upcoming games",
                formatter: function(cell) {
                    const val = cell.getValue();
                    if (val === 0) return '-';
                    let cls = 'score-medium';
                    if (val >= 70) cls = 'score-high';
                    else if (val < 50) cls = 'score-low';
                    return `<span class="${cls}">${val.toFixed(1)}</span>`;
                }
            },
            {
                title: "Exp Wins",
                field: "expected_wins",
                width: 85,
                hozAlign: "center",
                headerTooltip: "Expected wins based on matchup scores",
                formatter: function(cell) {
                    const val = cell.getValue();
                    if (val === 0) return '-';
                    const games = cell.getRow().getData().games;
                    const ratio = val / games;
                    let cls = 'score-medium';
                    if (ratio >= 0.6) cls = 'score-high';
                    else if (ratio < 0.5) cls = 'score-low';
                    return `<span class="${cls}">${val.toFixed(1)}</span>`;
                }
            }
        ],

        initialSort: [
            { column: "avg_score", dir: "desc" }
        ],

        rowFormatter: function(row) {
            const data = row.getData();
            row.getElement().style.cursor = data.has_upcoming ? 'pointer' : 'default';
            if (!data.has_upcoming) {
                row.getElement().style.opacity = '0.5';
            }
        }
    });

    // Handle row click to show matchup details
    schemesTable.on("rowClick", function(e, row) {
        const data = row.getData();
        if (!data.has_upcoming) return;

        const tokenId = data.token_id;
        const rowElement = row.getElement();

        if (selectedSchemeTokenId === tokenId) {
            hideSchemeDetailPanel();
            selectedSchemeTokenId = null;
            schemesTable.deselectRow();
        } else {
            selectedSchemeTokenId = tokenId;
            showSchemeMatchupDetail(tokenId, rowElement);
        }
    });

    // Set up filters
    document.getElementById('scheme-filter').addEventListener('change', applySchemesFilters);
    document.getElementById('scheme-search').addEventListener('input', applySchemesFilters);
    document.getElementById('scheme-upcoming-only').addEventListener('change', applySchemesFilters);

    // Apply initial filter (upcoming only)
    applySchemesFilters();
}

// Apply schemes filters
function applySchemesFilters() {
    const schemeVal = document.getElementById('scheme-filter').value;
    const searchVal = document.getElementById('scheme-search').value.toLowerCase();
    const upcomingOnly = document.getElementById('scheme-upcoming-only').checked;

    schemesTable.setFilter(function(data) {
        // Upcoming filter
        if (upcomingOnly && !data.has_upcoming) {
            return false;
        }

        // Search filter
        if (searchVal && !data.name.toLowerCase().includes(searchVal)) {
            return false;
        }

        // Scheme filter
        if (schemeVal) {
            if (!data.matching_schemes || !data.matching_schemes.includes(schemeVal)) {
                return false;
            }
        }

        return true;
    });
}

// Hide scheme detail panel
function hideSchemeDetailPanel() {
    const panel = document.getElementById('scheme-detail-panel');
    panel.classList.add('hidden');
    panel.innerHTML = '';
}

// Show matchup detail for a champion in schemes tab
async function showSchemeMatchupDetail(tokenId, rowElement) {
    const panel = document.getElementById('scheme-detail-panel');
    panel.classList.remove('hidden');
    panel.innerHTML = '<div class="loading">Loading matchup details...</div>';

    // Move panel to appear right after the clicked row
    rowElement.insertAdjacentElement('afterend', panel);

    try {
        const response = await fetch(`/api/champions/${tokenId}/matchups`);
        const data = await response.json();
        renderSchemeMatchupDetail(panel, data);
    } catch (error) {
        panel.innerHTML = `<div class="loading">Error loading details: ${error.message}</div>`;
    }
}

// Render matchup detail in schemes tab
function renderSchemeMatchupDetail(container, data) {
    const champion = data.champion;
    const matchups = data.matchups;

    container.innerHTML = `
        <h3>
            <span>${champion.name}'s Upcoming Schedule (${matchups.length} games)</span>
            <button class="close-btn" onclick="hideSchemeDetailPanel(); selectedSchemeTokenId = null; schemesTable.deselectRow();">Close</button>
        </h3>
        <div id="scheme-detail-table"></div>
    `;

    // Create detail Tabulator
    new Tabulator("#scheme-detail-table", {
        data: matchups,
        layout: "fitColumns",
        height: Math.min(400, matchups.length * 55 + 60),

        columns: [
            { title: "Date", field: "date", width: 95 },
            { title: "Opponent", field: "opponent", minWidth: 120 },
            {
                title: "Class",
                field: "opponent_class",
                width: 90,
                formatter: function(cell) {
                    const cls = cell.getValue();
                    return `<span class="class-badge class-${cls}">${cls}</span>`;
                }
            },
            {
                title: "Score",
                field: "score",
                width: 70,
                hozAlign: "center",
                formatter: function(cell) {
                    const val = cell.getValue();
                    let cls = 'score-medium';
                    if (val >= 70) cls = 'score-high';
                    else if (val < 50) cls = 'score-low';
                    return `<span class="${cls}">${val.toFixed(1)}</span>`;
                }
            },
            {
                title: "Edge",
                field: "edge",
                width: 90,
                hozAlign: "center",
                formatter: function(cell) {
                    const val = cell.getValue();
                    let cls = 'edge-even';
                    if (val === 'Favorable') cls = 'edge-favorable';
                    else if (val === 'Tough') cls = 'edge-tough';
                    return `<span class="${cls}">${val}</span>`;
                }
            }
        ],

        initialSort: [{ column: "score", dir: "desc" }]
    });
}

// ========== CLASS CHANGES TAB ==========

// Load class changes data
async function loadClassChangesData() {
    const container = document.getElementById('class-changes-table');
    container.innerHTML = '<div class="loading">Loading class changes...</div>';

    try {
        const response = await fetch('/api/class-changes');
        const data = await response.json();
        renderClassChangesSummary(data);
        initClassChangesTable(data.changes);
    } catch (error) {
        container.innerHTML = `<div class="loading">Error loading data: ${error.message}</div>`;
    }
}

// Render the class changes summary
function renderClassChangesSummary(data) {
    const container = document.getElementById('class-changes-summary');
    const count = data.total_changes;

    if (count === 0) {
        container.innerHTML = `
            <div class="summary-card">
                <span class="summary-label">No class changes detected in recent match history.</span>
            </div>
        `;
    } else {
        container.innerHTML = `
            <div class="summary-card">
                <span class="summary-count">${count}</span>
                <span class="summary-label">class change${count !== 1 ? 's' : ''} detected</span>
            </div>
        `;
    }
}

// Initialize the class changes table
function initClassChangesTable(changes) {
    const container = document.getElementById('class-changes-table');

    if (changes.length === 0) {
        container.innerHTML = '<div class="no-data">No class changes found in recent match history.</div>';
        return;
    }

    classChangesTable = new Tabulator("#class-changes-table", {
        data: changes,
        layout: "fitColumns",
        height: 400,

        columns: [
            {
                title: "Champion",
                field: "name",
                minWidth: 140,
                headerTooltip: "Champion name"
            },
            {
                title: "Old Class",
                field: "old_class",
                width: 110,
                headerTooltip: "Previous class",
                formatter: function(cell) {
                    const cls = cell.getValue();
                    return `<span class="class-badge class-${cls}">${cls}</span>`;
                }
            },
            {
                title: "",
                field: "arrow",
                width: 40,
                hozAlign: "center",
                formatter: function() {
                    return '<span class="class-arrow">→</span>';
                }
            },
            {
                title: "New Class",
                field: "new_class",
                width: 110,
                headerTooltip: "Current class",
                formatter: function(cell) {
                    const cls = cell.getValue();
                    return `<span class="class-badge class-${cls}">${cls}</span>`;
                }
            },
            {
                title: "Change Date",
                field: "change_date",
                width: 120,
                headerTooltip: "First match with new class"
            },
            {
                title: "Last Old Class Match",
                field: "last_match_as_old",
                width: 150,
                headerTooltip: "Last match played with old class"
            }
        ],

        initialSort: [
            { column: "change_date", dir: "desc" }
        ]
    });
}
