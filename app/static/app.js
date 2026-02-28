// Grand Arena Contest Tool - Frontend

let upcomingTable = null;
let analysisTable = null;
let schemesTable = null;
let classChangesTable = null;
let teamCompsTable = null;
let selectedTokenId = null;
let selectedSchemeTokenId = null;
let upcomingFiltersInitialized = false;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    loadUpcomingData();
    initInfoOverlay();
    initUpcomingFilters();
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

            // Clean up any open detail panels before switching
            cleanupDetailPanels();

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

            // Load team comps data when tab is clicked
            if (tabId === 'team-comps' && !teamCompsTable) {
                loadTeamCompsData();
            }
        });
    });
}

// Clean up all detail panels and reset selection state
function cleanupDetailPanels() {
    // Reset upcoming tab state - always clean up fully
    selectedTokenId = null;
    if (upcomingTable) {
        upcomingTable.deselectRow();
    }
    const upcomingPanel = document.getElementById('detail-panel');
    if (upcomingPanel) {
        upcomingPanel.classList.add('hidden');
        upcomingPanel.innerHTML = '';
        // Move panel back to container to avoid DOM issues
        const container = document.getElementById('table-wrapper');
        if (container && upcomingPanel.parentNode !== container) {
            container.appendChild(upcomingPanel);
        }
    }

    // Reset analysis tab state
    if (typeof selectedAnalysisMatchId !== 'undefined') {
        selectedAnalysisMatchId = null;
    }
    if (analysisTable) {
        analysisTable.deselectRow();
    }
    const analysisPanel = document.getElementById('analysis-detail-panel');
    if (analysisPanel) {
        analysisPanel.classList.add('hidden');
        analysisPanel.innerHTML = '';
    }

    // Reset schemes tab state
    if (typeof selectedSchemeTokenId !== 'undefined') {
        selectedSchemeTokenId = null;
    }
    if (schemesTable) {
        schemesTable.deselectRow();
    }
    const schemePanel = document.getElementById('scheme-detail-panel');
    if (schemePanel) {
        schemePanel.classList.add('hidden');
        schemePanel.innerHTML = '';
    }
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
                title: "Avg Grade",
                field: "avg_grade",
                width: 80,
                hozAlign: "center",
                headerTooltip: "Average grade across all upcoming games. A=must-play, B=good, C=coinflip, D=avoid, F=bad",
                formatter: function(cell) {
                    const val = cell.getValue();
                    let cls = 'grade-c';
                    if (val === 'A') cls = 'grade-a';
                    else if (val === 'B') cls = 'grade-b';
                    else if (val === 'D') cls = 'grade-d';
                    else if (val === 'F') cls = 'grade-f';
                    return `<span class="${cls}">${val}</span>`;
                }
            },
            {
                title: "A/B",
                field: "good_games",
                width: 60,
                hozAlign: "center",
                headerTooltip: "Number of Grade A or B games (favorable matchups)",
                formatter: function(cell) {
                    const val = cell.getValue();
                    const total = cell.getRow().getData().games;
                    const cls = val >= total * 0.5 ? 'favorable-high' : '';
                    return `<span class="${cls}">${val}</span>`;
                },
                sorter: "number"
            },
            {
                title: "D/F",
                field: "bad_games",
                width: 60,
                hozAlign: "center",
                headerTooltip: "Number of Grade D or F games (tough matchups)",
                formatter: function(cell) {
                    const val = cell.getValue();
                    const cls = val > 5 ? 'unfavorable-high' : '';
                    return `<span class="${cls}">${val}</span>`;
                },
                sorter: "number"
            },
            {
                title: "Avg FP",
                field: "avg_proj_fp",
                width: 80,
                hozAlign: "center",
                headerTooltip: "Average projected fantasy points per game (Elims×80 + Deps×50 + Wart×0.5625 + WinProb×300)",
                formatter: function(cell) {
                    const val = cell.getValue();
                    let cls = 'fp-average';
                    if (val >= 400) cls = 'fp-high';
                    else if (val < 300) cls = 'fp-low';
                    return `<span class="${cls}">${val.toFixed(1)}</span>`;
                },
                sorter: "number"
            },
            {
                title: "Total FP",
                field: "total_proj_fp",
                width: 85,
                hozAlign: "center",
                headerTooltip: "Total projected fantasy points across all upcoming games",
                formatter: function(cell) {
                    const val = cell.getValue();
                    return `<span class="fp-total">${val.toFixed(1)}</span>`;
                },
                sorter: "number"
            },
            {
                title: "Pattern",
                field: "team_pattern",
                width: 80,
                hozAlign: "center",
                headerTooltip: "Most common team composition pattern: 2G=2 gacha, 2E=2 elim, LONE=lone gacha, MIX=mixed",
                formatter: function(cell) {
                    const val = cell.getValue() || "BAL";
                    return formatPatternBadge(val);
                }
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
}

// Initialize filters for upcoming table (called once on page load)
function initUpcomingFilters() {
    if (upcomingFiltersInitialized) return;
    upcomingFiltersInitialized = true;

    // Search filter
    document.getElementById('search').addEventListener('input', function() {
        if (!upcomingTable) return;

        // Close any open detail panel before filtering
        if (selectedTokenId !== null) {
            hideDetailPanel();
            selectedTokenId = null;
            upcomingTable.deselectRow();
        }

        const val = this.value.toLowerCase();
        const classVal = document.getElementById('class-filter').value;

        // Clear and reapply all filters
        upcomingTable.clearFilter();
        if (val) {
            upcomingTable.addFilter(function(data) {
                return data.name.toLowerCase().includes(val);
            });
        }
        if (classVal) {
            upcomingTable.addFilter("class", "=", classVal);
        }
    });

    // Class filter
    document.getElementById('class-filter').addEventListener('change', function() {
        if (!upcomingTable) return;

        // Close any open detail panel before filtering
        if (selectedTokenId !== null) {
            hideDetailPanel();
            selectedTokenId = null;
            upcomingTable.deselectRow();
        }

        const val = this.value;
        const searchVal = document.getElementById('search').value.toLowerCase();

        // Clear and reapply all filters
        upcomingTable.clearFilter();
        if (val) {
            upcomingTable.addFilter("class", "=", val);
        }
        if (searchVal) {
            upcomingTable.addFilter(function(data) {
                return data.name.toLowerCase().includes(searchVal);
            });
        }
    });
}

// Hide the detail panel
function hideDetailPanel() {
    const panel = document.getElementById('detail-panel');
    panel.classList.add('hidden');
    panel.innerHTML = '';
    // Move panel back to its original container to avoid DOM issues
    const container = document.getElementById('table-wrapper');
    if (panel.parentNode !== container) {
        container.appendChild(panel);
    }
}

// Show matchup detail for a champion - inline under the clicked row
async function showMatchupDetail(tokenId, rowElement) {
    const panel = document.getElementById('detail-panel');
    panel.classList.remove('hidden');
    panel.innerHTML = '<div class="loading">Loading matchup details...</div>';

    // Insert the panel directly after the clicked row in the table
    // This makes it appear inline, expanding under the selected champion
    if (rowElement && rowElement.parentNode) {
        rowElement.parentNode.insertBefore(panel, rowElement.nextSibling);
    }

    try {
        const response = await fetch(`/api/champions/${tokenId}/matchups`);
        const data = await response.json();

        if (!response.ok) {
            panel.innerHTML = `<div class="loading">Error: ${data.detail || response.statusText}</div>`;
            return;
        }

        renderMatchupDetail(panel, data);
    } catch (error) {
        panel.innerHTML = `<div class="loading">Error loading details: ${error.message}</div>`;
    }
}

// Format team composition pattern badge
function formatPatternBadge(pattern) {
    const patternInfo = {
        "2G_AA": { short: "2G-AA", color: "#00d4ff", title: "Double Gacha (A+A) - Two elite depositors" },
        "2G_AB": { short: "2G-AB", color: "#00aacc", title: "Double Gacha (A+B) - Elite + good depositor" },
        "2G_BB": { short: "2G-BB", color: "#008899", title: "Double Gacha (B+B) - Two decent depositors" },
        "2E_AA": { short: "2E-AA", color: "#ff4444", title: "Double Elim (A+A) - Two elite eliminators" },
        "2E_AB": { short: "2E-AB", color: "#cc3333", title: "Double Elim (A+B) - Elite + good eliminator" },
        "2E_BB": { short: "2E-BB", color: "#992222", title: "Double Elim (B+B) - Two decent eliminators" },
        "LONE_G": { short: "LONE", color: "#ff9900", title: "Lone Gacha - Single depositor racing alone (liability!)" },
        "MIXED": { short: "MIX", color: "#aa88ff", title: "Mixed - Gacha + Elim supporters" },
        "WART": { short: "WART", color: "#88aa88", title: "Wart Focus - High wart distance supporters" },
        "BALANCED": { short: "BAL", color: "#888888", title: "Balanced - No strong specialization" }
    };

    const info = patternInfo[pattern] || { short: pattern?.substring(0, 4) || "?", color: "#888888", title: pattern || "Unknown" };
    return `<span class="pattern-badge" style="background: ${info.color}; color: #fff; padding: 2px 6px; border-radius: 3px; font-size: 11px; font-weight: bold;" title="${info.title}">${info.short}</span>`;
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
    // Handle error responses or missing data
    if (!data || !data.champion) {
        container.innerHTML = `<div class="loading">Error: No champion data available. ${data?.detail || ''}</div>`;
        return;
    }

    const champion = data.champion;
    const matchups = data.matchups || [];

    // Calculate stat-based FP (without win bonus) for display
    const statFP = (champion.avg_elims * 80) + (champion.avg_deps * 50) + (champion.avg_wart * 0.5625);

    container.innerHTML = `
        <h3>
            <span>${champion.name}'s Upcoming Schedule (${matchups.length} games)</span>
            <div class="score-legend">
                <span class="legend-item"><span class="grade-a">A</span>=must-play</span>
                <span class="legend-item"><span class="grade-b">B</span>=good</span>
                <span class="legend-item"><span class="grade-c">C</span>=coinflip</span>
                <span class="legend-item"><span class="grade-d">D</span>=avoid</span>
                <span class="legend-item"><span class="grade-f">F</span>=bad</span>
            </div>
            <button class="close-btn" onclick="hideDetailPanel(); selectedTokenId = null; upcomingTable.deselectRow();">Close</button>
        </h3>
        <div class="fp-breakdown">
            <span class="fp-breakdown-title">FP Projection:</span>
            <span class="fp-stat">${champion.avg_elims.toFixed(1)} elims × 80 = ${(champion.avg_elims * 80).toFixed(0)}</span>
            <span class="fp-stat">${champion.avg_deps.toFixed(1)}g × 50 = ${(champion.avg_deps * 50).toFixed(0)}</span>
            <span class="fp-stat">${champion.avg_wart.toFixed(0)} wart × 0.56 = ${(champion.avg_wart * 0.5625).toFixed(0)}</span>
            <span class="fp-stat fp-stat-total">Stats: ${statFP.toFixed(0)} + Win Bonus</span>
        </div>
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
                width: 100,
                headerTooltip: "Opponent champion name"
            },
            {
                title: "Class",
                field: "opponent_class",
                width: 85,
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
                width: 55,
                hozAlign: "center",
                headerTooltip: "Matchup score (25-75): Win probability based on class, supporters, etc.",
                formatter: function(cell) {
                    const val = cell.getValue();
                    let cls = 'score-medium';
                    if (val >= 60) cls = 'score-high';
                    else if (val < 40) cls = 'score-low';
                    return `<span class="${cls}">${val.toFixed(0)}</span>`;
                }
            },
            {
                title: "Grade",
                field: "grade",
                width: 55,
                hozAlign: "center",
                headerTooltip: "V4 Grade: A=must-play (70+), B=good (60-69), C=coinflip (50-59), D=avoid (40-49), F=bad (<40)",
                formatter: function(cell) {
                    const val = cell.getValue();
                    let cls = 'grade-c';
                    if (val === 'A') cls = 'grade-a';
                    else if (val === 'B') cls = 'grade-b';
                    else if (val === 'D') cls = 'grade-d';
                    else if (val === 'F') cls = 'grade-f';
                    return `<span class="${cls}">${val}</span>`;
                }
            },
            {
                title: "Comp",
                field: "my_pattern",
                width: 70,
                hozAlign: "center",
                headerTooltip: "Your team composition pattern",
                formatter: function(cell) {
                    return formatPatternBadge(cell.getValue());
                }
            },
            {
                title: "Proj FP",
                field: "proj_fp",
                width: 75,
                hozAlign: "center",
                headerTooltip: "Projected fantasy points (Elims×80 + Deps×50 + Wart×0.5625 + WinProb×300)",
                formatter: function(cell) {
                    const val = cell.getValue();
                    let cls = 'fp-average';
                    if (val >= 400) cls = 'fp-high';
                    else if (val < 300) cls = 'fp-low';
                    return `<span class="${cls}">${val.toFixed(0)}</span>`;
                }
            }
        ],

        initialSort: [
            { column: "date", dir: "desc" }
        ]
    });
}

// ========== ANALYSIS TAB ==========

// Load historical analysis data
async function loadAnalysisData() {
    const container = document.getElementById('analysis-table');
    container.innerHTML = '<div class="loading">Loading historical data...</div>';

    try {
        const response = await fetch('/api/analysis');
        const data = await response.json();
        renderBucketStats(data.bucket_stats, data.bucket_stats_v4);
        initAnalysisTable(data.games);
    } catch (error) {
        container.innerHTML = `<div class="loading">Error loading data: ${error.message}</div>`;
    }
}

// Render the win rate by grade bucket summary
function renderBucketStats(statsV3, statsV4) {
    const container = document.getElementById('bucket-stats');

    // Grade descriptions for tooltips
    const gradeDescriptions = {
        'A': 'Must-play (70+)',
        'B': 'Good (60-69)',
        'C': 'Coin flip (50-59)',
        'D': 'Avoid (40-49)',
        'F': 'Bad (<40)'
    };

    let html = '<div class="bucket-cards">';
    statsV4.forEach(bucket => {
        let colorClass = 'bucket-neutral';
        if (bucket.grade === 'A') colorClass = 'bucket-grade-a';
        else if (bucket.grade === 'B') colorClass = 'bucket-grade-b';
        else if (bucket.grade === 'C') colorClass = 'bucket-grade-c';
        else if (bucket.grade === 'D') colorClass = 'bucket-grade-d';
        else if (bucket.grade === 'F') colorClass = 'bucket-grade-f';

        const desc = gradeDescriptions[bucket.grade] || '';

        html += `
            <div class="bucket-card ${colorClass}" title="${desc}">
                <div class="bucket-grade">Grade ${bucket.grade}</div>
                <div class="bucket-winrate">${bucket.win_rate}%</div>
                <div class="bucket-sample">${bucket.wins}/${bucket.games} wins</div>
            </div>
        `;
    });
    html += '</div>';

    container.innerHTML = html;
}

// Track selected analysis row
let selectedAnalysisMatchId = null;

// Initialize the analysis table
function initAnalysisTable(games) {
    analysisTable = new Tabulator("#analysis-table", {
        data: games,
        layout: "fitColumns",
        height: 500,
        pagination: true,
        paginationSize: 50,
        selectable: 1,

        columns: [
            {
                title: "Match ID",
                field: "match_id",
                width: 110,
                headerTooltip: "Click to view on Grand Arena",
                formatter: function(cell) {
                    const matchId = cell.getValue();
                    // Show last 8 chars for brevity
                    const shortId = matchId.slice(-8);
                    return `<a href="https://train.grandarena.gg/matches/${matchId}" target="_blank" class="match-link" onclick="event.stopPropagation();">${shortId}</a>`;
                }
            },
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
                headerTooltip: "Your champion - click row to see supporter details"
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
                title: "Grade",
                field: "grade_v4",
                width: 55,
                hozAlign: "center",
                headerTooltip: "Grade: A=must-play (70+), B=good (60-69), C=coinflip (50-59), D=avoid (40-49), F=bad (<40)",
                formatter: function(cell) {
                    const val = cell.getValue();
                    let cls = 'grade-c';
                    if (val === 'A') cls = 'grade-a';
                    else if (val === 'B') cls = 'grade-b';
                    else if (val === 'D') cls = 'grade-d';
                    else if (val === 'F') cls = 'grade-f';
                    return `<span class="${cls}">${val}</span>`;
                }
            },
            {
                title: "My Comp",
                field: "my_pattern",
                width: 75,
                hozAlign: "center",
                headerTooltip: "Your team composition pattern",
                formatter: function(cell) {
                    return formatPatternBadge(cell.getValue());
                }
            },
            {
                title: "Opp Comp",
                field: "opp_pattern",
                width: 75,
                hozAlign: "center",
                headerTooltip: "Opponent team composition pattern",
                formatter: function(cell) {
                    return formatPatternBadge(cell.getValue());
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
            },
            {
                title: "Proj FP",
                field: "proj_fp",
                width: 75,
                hozAlign: "center",
                headerTooltip: "Projected fantasy points (calculated before game)",
                formatter: function(cell) {
                    const val = cell.getValue();
                    let cls = 'fp-average';
                    if (val >= 400) cls = 'fp-high';
                    else if (val < 300) cls = 'fp-low';
                    return `<span class="${cls}">${val.toFixed(1)}</span>`;
                }
            },
            {
                title: "Actual FP",
                field: "actual_fp",
                width: 80,
                hozAlign: "center",
                headerTooltip: "Actual fantasy points scored",
                formatter: function(cell) {
                    const val = cell.getValue();
                    let cls = 'fp-average';
                    if (val >= 400) cls = 'fp-high';
                    else if (val < 300) cls = 'fp-low';
                    return `<span class="${cls}">${val.toFixed(1)}</span>`;
                }
            },
            {
                title: "+/-",
                field: "fp_diff",
                width: 60,
                hozAlign: "center",
                headerTooltip: "Fantasy point difference (Actual - Projected). Positive = overperformed.",
                formatter: function(cell) {
                    const val = cell.getValue();
                    let cls = val >= 0 ? 'fp-diff-pos' : 'fp-diff-neg';
                    let sign = val >= 0 ? '+' : '';
                    return `<span class="${cls}">${sign}${val.toFixed(0)}</span>`;
                }
            }
        ],

        initialSort: [
            { column: "date", dir: "desc" }
        ],

        rowFormatter: function(row) {
            row.getElement().style.cursor = 'pointer';
        }
    });

    // Handle row click to expand supporter details
    analysisTable.on("rowClick", function(e, row) {
        // Don't expand if clicking on a link
        if (e.target.tagName === 'A') return;

        const data = row.getData();
        const matchId = data.match_id;
        const rowElement = row.getElement();

        if (selectedAnalysisMatchId === matchId) {
            hideAnalysisDetailPanel();
            selectedAnalysisMatchId = null;
            analysisTable.deselectRow();
        } else {
            selectedAnalysisMatchId = matchId;
            showAnalysisDetail(data, rowElement);
        }
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
    const gradeVal = document.getElementById('analysis-ms-filter').value;

    // Grade order for filtering (A is best, F is worst)
    const gradeOrder = { 'A': 5, 'B': 4, 'C': 3, 'D': 2, 'F': 1 };

    analysisTable.setFilter(function(data) {
        // Search filter - only match champion column (to see matchups from their perspective)
        if (searchVal && !data.champion.toLowerCase().includes(searchVal)) {
            return false;
        }

        // Result filter
        if (resultVal && data.result !== resultVal) {
            return false;
        }

        // Grade filter - show grades at or better than selected
        if (gradeVal && gradeOrder[data.grade_v4] < gradeOrder[gradeVal]) {
            return false;
        }

        return true;
    });
}

// Hide the analysis detail panel
function hideAnalysisDetailPanel() {
    const panel = document.getElementById('analysis-detail-panel');
    if (panel) {
        panel.classList.add('hidden');
        panel.innerHTML = '';
    }
}

// Show analysis detail for a match - positioned below the table
function showAnalysisDetail(data, rowElement) {
    // Get or create the detail panel
    let panel = document.getElementById('analysis-detail-panel');
    if (!panel) {
        panel = document.createElement('div');
        panel.id = 'analysis-detail-panel';
        panel.className = 'detail-panel';
    }

    panel.classList.remove('hidden');

    // Keep panel in its original position (below the table) rather than inserting into Tabulator's DOM
    const analysisContainer = document.getElementById('analysis');
    if (panel.parentNode !== analysisContainer) {
        analysisContainer.appendChild(panel);
    }

    const result = data.result === 'W' ? 'Won' : 'Lost';
    const resultClass = data.result === 'W' ? 'result-win' : 'result-loss';

    panel.innerHTML = `
        <div class="analysis-detail-content">
            <div class="analysis-detail-header">
                <h4>
                    <span class="champion-name">${data.champion}</span>
                    <span class="vs">vs</span>
                    <span class="opponent-name">${data.opponent}</span>
                    <span class="${resultClass}">(${result})</span>
                </h4>
                <a href="https://train.grandarena.gg/matches/${data.match_id}" target="_blank" class="view-match-btn">View on Grand Arena</a>
                <button class="close-btn" onclick="hideAnalysisDetailPanel(); selectedAnalysisMatchId = null; analysisTable.deselectRow();">Close</button>
            </div>
            <div class="supporters-comparison">
                <div class="team-supporters my-team">
                    <h5>${data.champion}'s Supporters</h5>
                    <div class="supporter-list">
                        ${data.my_supporters.map(s => formatSupporter(s)).join('')}
                    </div>
                    <div class="team-avg">
                        Avg Elims: ${(data.my_supporters.reduce((sum, s) => sum + s.career_elims, 0) / Math.max(data.my_supporters.length, 1)).toFixed(2)}
                    </div>
                </div>
                <div class="team-supporters opp-team">
                    <h5>${data.opponent}'s Supporters</h5>
                    <div class="supporter-list">
                        ${data.opp_supporters.map(s => formatSupporter(s)).join('')}
                    </div>
                    <div class="team-avg">
                        Avg Elims: ${(data.opp_supporters.reduce((sum, s) => sum + s.career_elims, 0) / Math.max(data.opp_supporters.length, 1)).toFixed(2)}
                    </div>
                </div>
            </div>
        </div>
    `;
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

    // Keep panel in its original position (below the table) rather than inserting into Tabulator's DOM
    const schemesContainer = document.getElementById('schemes');
    if (panel.parentNode !== schemesContainer) {
        schemesContainer.appendChild(panel);
    }

    try {
        const response = await fetch(`/api/champions/${tokenId}/matchups`);
        const data = await response.json();

        if (!response.ok) {
            panel.innerHTML = `<div class="loading">Error: ${data.detail || response.statusText}</div>`;
            return;
        }

        renderSchemeMatchupDetail(panel, data);
    } catch (error) {
        panel.innerHTML = `<div class="loading">Error loading details: ${error.message}</div>`;
    }
}

// Render matchup detail in schemes tab
function renderSchemeMatchupDetail(container, data) {
    // Handle error responses or missing data
    if (!data || !data.champion) {
        container.innerHTML = `<div class="loading">Error: No champion data available. ${data?.detail || ''}</div>`;
        return;
    }

    const champion = data.champion;
    const matchups = data.matchups || [];

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
                width: 55,
                hozAlign: "center",
                formatter: function(cell) {
                    const val = cell.getValue();
                    let cls = 'score-medium';
                    if (val >= 60) cls = 'score-high';
                    else if (val < 40) cls = 'score-low';
                    return `<span class="${cls}">${val.toFixed(0)}</span>`;
                }
            },
            {
                title: "Grade",
                field: "grade",
                width: 55,
                hozAlign: "center",
                formatter: function(cell) {
                    const val = cell.getValue();
                    let cls = 'grade-c';
                    if (val === 'A') cls = 'grade-a';
                    else if (val === 'B') cls = 'grade-b';
                    else if (val === 'D') cls = 'grade-d';
                    else if (val === 'F') cls = 'grade-f';
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

// ========== TEAM COMPS TAB ==========

// Load team composition data
async function loadTeamCompsData() {
    const container = document.getElementById('team-comps-table');
    container.innerHTML = '<div class="loading">Loading team compositions...</div>';

    const minGames = document.getElementById('comp-min-games').value || 50;

    try {
        const response = await fetch(`/api/composition-table?min_games=${minGames}`);
        const data = await response.json();
        initTeamCompsTable(data);
    } catch (error) {
        container.innerHTML = `<div class="loading">Error loading data: ${error.message}</div>`;
    }
}

// Format supporter role badge
function formatRoleBadge(role) {
    const roleInfo = {
        "ELIM": { color: "#ff4444", title: "Eliminator - High eliminations" },
        "GACHA": { color: "#00d4ff", title: "Gacha/Depositor - High deposits" },
        "WART": { color: "#88aa88", title: "Wart Runner - High wart distance" },
        "BALANCED": { color: "#888888", title: "Balanced - No strong specialization" },
        "HYBRID": { color: "#aa88ff", title: "Hybrid - Mixed stats" }
    };

    const info = roleInfo[role] || { color: "#888888", title: role || "Unknown" };
    return `<span class="role-badge" style="background: ${info.color}; color: #fff; padding: 2px 6px; border-radius: 3px; font-size: 11px; font-weight: bold;" title="${info.title}">${role}</span>`;
}

// Format matchup info (best vs or worst vs)
function formatMatchupInfo(matchup, isBest) {
    if (!matchup) return '<span style="color:#666;">-</span>';

    const cls = matchup.class;
    const supp1 = matchup.supp1;
    const supp2 = matchup.supp2;
    const wr = matchup.win_rate;
    const games = matchup.games;

    // For best matchup, we have wins; for worst matchup, we calculate wins from losses
    const wins = isBest ? matchup.wins : (games - matchup.losses);
    const record = `${wins}/${games}`;

    // Color based on win rate
    let wrColor = '#ffcc00';
    if (wr >= 60) wrColor = '#00ff88';
    else if (wr < 40) wrColor = '#ff4444';

    // Extract base class for styling (e.g., "Sprinter (Wart)" -> "Sprinter")
    const baseClass = cls.split(' ')[0];

    return `
        <div class="matchup-info" title="${cls} + ${supp1} + ${supp2} (${record})">
            <span class="class-badge class-${baseClass}" style="font-size:10px;padding:1px 4px;">${cls}</span>
            <span style="font-size:10px;color:#888;">+${supp1}+${supp2}</span>
            <span style="color:${wrColor};font-weight:bold;font-size:11px;">${wr}%</span>
            <span style="color:#888;font-size:10px;">(${record})</span>
        </div>
    `;
}

// Initialize the team comps table
function initTeamCompsTable(data) {
    const container = document.getElementById('team-comps-table');

    if (data.length === 0) {
        container.innerHTML = '<div class="no-data">No team compositions found with enough games.</div>';
        return;
    }

    teamCompsTable = new Tabulator("#team-comps-table", {
        data: data,
        layout: "fitColumns",
        height: 500,

        columns: [
            {
                title: "Class",
                field: "champion_class",
                width: 140,
                headerTooltip: "Champion class (with subtype for Sprinters/Grinders)",
                formatter: function(cell) {
                    const cls = cell.getValue();
                    // Extract base class for styling (e.g., "Sprinter (Wart)" -> "Sprinter")
                    const baseClass = cls.split(' ')[0];
                    return `<span class="class-badge class-${baseClass}">${cls}</span>`;
                }
            },
            {
                title: "Supp 1",
                field: "supp1",
                width: 90,
                hozAlign: "center",
                headerTooltip: "First supporter role",
                formatter: function(cell) {
                    return formatRoleBadge(cell.getValue());
                }
            },
            {
                title: "Supp 2",
                field: "supp2",
                width: 90,
                hozAlign: "center",
                headerTooltip: "Second supporter role",
                formatter: function(cell) {
                    return formatRoleBadge(cell.getValue());
                }
            },
            {
                title: "Win Rate",
                field: "win_rate",
                width: 95,
                hozAlign: "center",
                headerTooltip: "Historical win percentage",
                formatter: function(cell) {
                    const val = cell.getValue();
                    let cls = 'score-medium';
                    if (val >= 55) cls = 'score-high';
                    else if (val < 45) cls = 'score-low';
                    return `<span class="${cls}">${val.toFixed(1)}%</span>`;
                },
                sorter: "number"
            },
            {
                title: "Record",
                field: "games",
                width: 100,
                hozAlign: "center",
                headerTooltip: "Wins / Total Games",
                formatter: function(cell) {
                    const data = cell.getRow().getData();
                    return `<span style="color:#aaa;">${data.wins}/${data.games}</span>`;
                }
            },
            {
                title: "Best vs",
                field: "best_matchup",
                minWidth: 180,
                headerTooltip: "Composition this team beats most often",
                formatter: function(cell) {
                    return formatMatchupInfo(cell.getValue(), true);
                }
            },
            {
                title: "Worst vs",
                field: "worst_matchup",
                minWidth: 180,
                headerTooltip: "Composition this team loses to most often",
                formatter: function(cell) {
                    return formatMatchupInfo(cell.getValue(), false);
                }
            }
        ],

        initialSort: [
            { column: "win_rate", dir: "desc" }
        ]
    });

    // Set up filters
    document.getElementById('comp-class-filter').addEventListener('change', applyTeamCompsFilters);
    document.getElementById('comp-min-games').addEventListener('change', function() {
        // Reload data with new min_games filter
        loadTeamCompsData();
    });
}

// Apply team comps filters
function applyTeamCompsFilters() {
    const classVal = document.getElementById('comp-class-filter').value;

    if (!teamCompsTable) return;

    teamCompsTable.setFilter(function(data) {
        // Class filter
        if (classVal && data.champion_class !== classVal) {
            return false;
        }
        return true;
    });
}
