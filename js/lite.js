// グローバル変数
let allProfiles = [];
let currentSort = { column: null, direction: 'asc' };

// DOMContentLoaded
document.addEventListener('DOMContentLoaded', async () => {
    await loadProfiles();
    setupEventListeners();
    renderTable();
});

// プロファイルデータの読み込み
async function loadProfiles() {
    try {
        const response = await fetch('data/profiles.json');
        const data = await response.json();
        allProfiles = data.profiles || [];

        // 最終更新日時を表示
        if (data.lastUpdated) {
            document.getElementById('updateTime').textContent = data.lastUpdated;
        }
    } catch (error) {
        console.error('データの読み込みに失敗しました:', error);
        document.getElementById('updateTime').textContent = '読み込み失敗';
    }
}

// イベントリスナーのセットアップ
function setupEventListeners() {
    // 検索
    document.getElementById('searchInput').addEventListener('input', renderTable);

    // フィルター
    document.getElementById('filterOfficial').addEventListener('change', renderTable);
    document.getElementById('filterUnofficial').addEventListener('change', renderTable);
    document.getElementById('filterForward').addEventListener('change', renderTable);
    document.getElementById('filterReverse').addEventListener('change', renderTable);

    // ソート
    document.querySelectorAll('th[data-sort]').forEach(th => {
        th.addEventListener('click', () => {
            const column = th.dataset.sort;
            if (currentSort.column === column) {
                currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
            } else {
                currentSort.column = column;
                currentSort.direction = 'asc';
            }
            renderTable();
        });
    });
}

// テーブルのレンダリング
function renderTable() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const showOfficial = document.getElementById('filterOfficial').checked;
    const showUnofficial = document.getElementById('filterUnofficial').checked;
    const showForward = document.getElementById('filterForward').checked;
    const showReverse = document.getElementById('filterReverse').checked;

    // フィルタリング
    let filtered = allProfiles.filter(profile => {
        // 公式/非公式フィルター
        if (profile.official && !showOfficial) return false;
        if (!profile.official && !showUnofficial) return false;

        // 順方向/逆方向フィルター
        if (!profile.forwardSupport && !profile.reverseSupport) return true;
        if (profile.forwardSupport && !showForward && (!profile.reverseSupport || !showReverse)) return false;
        if (profile.reverseSupport && !showReverse && (!profile.forwardSupport || !showForward)) return false;

        // 検索
        if (searchTerm) {
            const searchableText = [
                profile.id,
                profile.avatarName,
                profile.avatarAuthor,
                profile.profileAuthor,
                profile.downloadMethod,
                profile.notes || ''
            ].join(' ').toLowerCase();

            if (!searchableText.includes(searchTerm)) return false;
        }

        return true;
    });

    // ソート
    if (currentSort.column) {
        filtered.sort((a, b) => {
            let aVal = a[currentSort.column];
            let bVal = b[currentSort.column];

            // 数値または日付の場合
            if (currentSort.column === 'id') {
                aVal = parseInt(aVal) || 0;
                bVal = parseInt(bVal) || 0;
            }

            // 真偽値の場合
            if (typeof aVal === 'boolean') {
                aVal = aVal ? 1 : 0;
                bVal = bVal ? 1 : 0;
            }

            // 文字列の場合
            if (typeof aVal === 'string') {
                aVal = aVal.toLowerCase();
                bVal = bVal.toLowerCase();
            }

            if (aVal < bVal) return currentSort.direction === 'asc' ? -1 : 1;
            if (aVal > bVal) return currentSort.direction === 'asc' ? 1 : -1;
            return 0;
        });
    }

    // ソートインジケーターの更新
    document.querySelectorAll('th[data-sort]').forEach(th => {
        th.classList.remove('sorted-asc', 'sorted-desc');
        if (th.dataset.sort === currentSort.column) {
            th.classList.add(`sorted-${currentSort.direction}`);
        }
    });

    // テーブルボディの更新
    const tbody = document.getElementById('tableBody');
    tbody.innerHTML = filtered.map(profile => `
        <tr>
            <td>${escapeHtml(profile.id)}</td>
            <td>${escapeHtml(profile.registeredDate)}</td>
            <td>${escapeHtml(profile.updatedDate)}</td>
            <td>
                ${profile.boothUrl ?
                    `<a href="${escapeHtml(profile.boothUrl)}" target="_blank" rel="noopener noreferrer">${escapeHtml(profile.avatarName)}</a>` :
                    escapeHtml(profile.avatarName)
                }
            </td>
            <td>${escapeHtml(profile.profileVersion)}</td>
            <td>${escapeHtml(profile.avatarAuthor)}</td>
            <td>${escapeHtml(profile.profileAuthor)}</td>
            <td>
                <span class="badge ${profile.official ? 'badge-official' : 'badge-unofficial'}">
                    ${profile.official ? '公式' : '非公式'}
                </span>
            </td>
            <td>${escapeHtml(profile.downloadMethod)}</td>
            <td>
                ${profile.downloadLocation ?
                    `<a href="${escapeHtml(profile.downloadLocation)}" target="_blank" rel="noopener noreferrer">DL</a>` :
                    '-'
                }
            </td>
            <td>
                <span class="badge ${profile.forwardSupport ? 'badge-yes' : 'badge-no'}">
                    ${profile.forwardSupport ? '○' : '×'}
                </span>
            </td>
            <td>
                <span class="badge ${profile.reverseSupport ? 'badge-yes' : 'badge-no'}">
                    ${profile.reverseSupport ? '○' : '×'}
                </span>
            </td>
            <td>${profile.notes ? escapeHtml(profile.notes) : '-'}</td>
        </tr>
    `).join('');

    // 件数表示の更新
    document.getElementById('profileCount').textContent = filtered.length;
}

// HTMLエスケープ
function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
