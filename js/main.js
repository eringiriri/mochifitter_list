// グローバル変数
let allProfiles = [];
let filteredProfiles = [];

// DOMContentLoaded時の初期化
document.addEventListener('DOMContentLoaded', () => {
    loadProfiles();
    setupEventListeners();
});

// 最終更新日時の表示
function updateLastUpdatedDisplay(lastUpdated) {
    const updateTimeElement = document.getElementById('updateTime');
    if (updateTimeElement && lastUpdated) {
        updateTimeElement.textContent = lastUpdated;
        updateTimeElement.setAttribute('datetime', lastUpdated);
    }
}

// プロファイルデータの読み込み
async function loadProfiles() {
    try {
        const response = await fetch('data/profiles.json');
        if (!response.ok) {
            throw new Error('データの読み込みに失敗しました');
        }
        const data = await response.json();
        // IDでソート(逆順)
        allProfiles = data.profiles.sort((a, b) => b.id.localeCompare(a.id));
        filteredProfiles = [...allProfiles];

        // 最終更新日時を表示
        if (data.lastUpdated) {
            updateLastUpdatedDisplay(data.lastUpdated);
        }

        // 初期表示
        renderProfiles();
        updateCount();
    } catch (error) {
        console.error('Error loading profiles:', error);
        showError('プロファイルデータの読み込みに失敗しました');
    }
}

// イベントリスナーの設定
function setupEventListeners() {
    // 検索入力
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(applyFilters, 300));
    }

    // フィルターチェックボックス
    const filterCheckboxes = [
        'filterOfficial',
        'filterUnofficial',
        'filterForward',
        'filterReverse',
        'filterBidirectional',
        'filterFree',
        'filterPaid',
        'filterBundled'
    ];

    // 「全て」チェックボックス
    const filterAll = document.getElementById('filterAll');
    if (filterAll) {
        filterAll.addEventListener('change', () => {
            applyFilters();
        });
    }

    // 各フィルターチェックボックス
    filterCheckboxes.forEach(id => {
        const checkbox = document.getElementById(id);
        if (checkbox) {
            checkbox.addEventListener('change', () => {
                // 「全て」以外がONになったら「全て」をOFFにする
                if (checkbox.checked && filterAll) {
                    filterAll.checked = false;
                }
                applyFilters();
            });
        }
    });

    // 備考バッジのツールチップ（イベントデリゲーション）
    const profilesContainer = document.getElementById('profilesContainer');
    if (profilesContainer) {
        profilesContainer.addEventListener('mouseover', (event) => {
            if (event.target.classList.contains('notes-badge')) {
                showNotesTooltip(event.target);
            }
        });

        profilesContainer.addEventListener('mouseout', (event) => {
            if (event.target.classList.contains('notes-badge')) {
                hideNotesTooltip();
            }
        });
    }
}

// ツールチップを表示
function showNotesTooltip(badgeElement) {
    const notes = badgeElement.dataset.notes;
    if (!notes) return;

    // 既存のツールチップを削除
    hideNotesTooltip();

    // ツールチップ要素を作成
    const tooltip = document.createElement('div');
    tooltip.className = 'notes-tooltip';
    tooltip.textContent = notes;
    tooltip.id = 'notesTooltip';

    // 位置を計算
    const rect = badgeElement.getBoundingClientRect();
    tooltip.style.position = 'fixed';
    tooltip.style.left = `${rect.left}px`;
    tooltip.style.top = `${rect.bottom + 5}px`;

    document.body.appendChild(tooltip);
}

// ツールチップを非表示
function hideNotesTooltip() {
    const tooltip = document.getElementById('notesTooltip');
    if (tooltip) {
        tooltip.remove();
    }
}

// フィルタリング処理
function applyFilters() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const showAll = document.getElementById('filterAll').checked;
    const showOfficial = document.getElementById('filterOfficial').checked;
    const showUnofficial = document.getElementById('filterUnofficial').checked;
    const showForward = document.getElementById('filterForward').checked;
    const showReverse = document.getElementById('filterReverse').checked;
    const showBidirectional = document.getElementById('filterBidirectional').checked;
    const showFree = document.getElementById('filterFree').checked;
    const showPaid = document.getElementById('filterPaid').checked;
    const showBundled = document.getElementById('filterBundled').checked;

    filteredProfiles = allProfiles.filter(profile => {
        // テキスト検索
        const matchesSearch = !searchTerm ||
            profile.avatarName.toLowerCase().includes(searchTerm) ||
            profile.avatarAuthor.toLowerCase().includes(searchTerm) ||
            profile.profileAuthor.toLowerCase().includes(searchTerm);

        // 「全て」がONの場合は全て表示
        if (showAll) {
            return matchesSearch;
        }

        // ORフィルター：いずれかのフィルターに合致すれば表示
        const matchesOfficial = showOfficial && profile.official;
        const matchesUnofficial = showUnofficial && !profile.official;
        const matchesForward = showForward && profile.forwardSupport;
        const matchesReverse = showReverse && profile.reverseSupport;
        const matchesBidirectional = showBidirectional && profile.forwardSupport && profile.reverseSupport;
        const matchesFree = showFree && profile.pricing === '無料';
        const matchesPaid = showPaid && profile.pricing === '単体有料';
        const matchesBundled = showBundled && profile.pricing === 'アバター同梱';

        const matchesAnyFilter = matchesOfficial || matchesUnofficial ||
                                 matchesForward || matchesReverse || matchesBidirectional ||
                                 matchesFree || matchesPaid || matchesBundled;

        // フィルターが何も選択されていない場合は全て表示
        const noFiltersSelected = !showOfficial && !showUnofficial &&
                                  !showForward && !showReverse && !showBidirectional &&
                                  !showFree && !showPaid && !showBundled;

        return matchesSearch && (matchesAnyFilter || noFiltersSelected);
    });

    renderProfiles();
    updateCount();
}

// プロファイルの描画
function renderProfiles() {
    const container = document.getElementById('profilesContainer');

    if (!container) return;

    // 空状態の確認
    if (filteredProfiles.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <h3>該当するプロファイルが見つかりませんでした</h3>
                <p>検索条件やフィルターを変更してみてください</p>
            </div>
        `;
        return;
    }

    // プロファイルカードの生成
    container.innerHTML = filteredProfiles.map(profile => createProfileCard(profile)).join('');
}

// 価格バッジのクラスを取得
function getPriceBadgeClass(pricing) {
    switch(pricing) {
        case '無料':
            return 'price-free';
        case '単体有料':
            return 'price-paid';
        case 'アバター同梱':
            return 'price-bundled';
        default:
            return '';
    }
}

// プロファイルカードの生成
function createProfileCard(profile) {
    const officialBadge = profile.official ?
        '<span class="badge official">公式</span>' :
        '<span class="badge unofficial">非公式</span>';

    const forwardBadge = profile.forwardSupport ?
        '<div class="support-badge supported">順方向: 対応</div>' :
        '<div class="support-badge not-supported">順方向: 未対応</div>';

    const reverseBadge = profile.reverseSupport ?
        '<div class="support-badge supported">逆方向: 対応</div>' :
        '<div class="support-badge not-supported">逆方向: 未対応</div>';

    // 備考バッジ（備考がある場合のみ表示）
    const notesBadge = profile.notes && profile.notes.trim() ?
        `<span class="badge notes-badge" data-notes="${escapeHtml(profile.notes)}">備考</span>` : '';

    // 画像のHTML（imageUrlがある場合のみ表示）
    const imageHtml = profile.imageUrl ?
        `<div class="profile-image">
            <img src="${escapeHtml(profile.imageUrl)}" alt="${escapeHtml(profile.avatarName)}" loading="lazy">
            ${notesBadge}
            ${officialBadge}
        </div>` :
        `<div class="profile-image-placeholder">${notesBadge}${officialBadge}</div>`;

    // リンク化ヘルパー関数
    const createLink = (text, url) => {
        if (url && url.trim()) {
            return `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer" class="info-link">${escapeHtml(text)}</a>`;
        }
        return escapeHtml(text);
    };

    return `
        <div class="profile-card" data-profile-id="${escapeHtml(profile.id)}">
            ${imageHtml}
            <div class="profile-header">
                <h3 class="profile-name">${createLink(profile.avatarName, profile.avatarNameUrl)}</h3>
            </div>

            <div class="profile-info">
                <div class="info-row">
                    <span class="info-label">アバター作者</span>
                    <span class="info-value">${createLink(profile.avatarAuthor, profile.avatarAuthorUrl)}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">プロファイル作者</span>
                    <span class="info-value">${createLink(profile.profileAuthor, profile.profileAuthorUrl)}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">DL方法</span>
                    <span class="info-value">${escapeHtml(profile.downloadMethod)}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">プロファイル価格</span>
                    <span class="info-value">
                        <span class="price-badge ${getPriceBadgeClass(profile.pricing)}">${escapeHtml(profile.pricing)}</span>
                        ${profile.price && profile.price !== '-' && profile.price !== '0' ? `<span class="price-amount">${escapeHtml(profile.price)}円</span>` : ''}
                    </span>
                </div>
                <div class="info-row">
                    <span class="info-label">アバター価格</span>
                    <span class="info-value">${profile.avatarPrice && profile.avatarPrice.trim() ? escapeHtml(profile.avatarPrice) + '円' : '未登録'}</span>
                </div>
            </div>

            <div class="support-badges">
                ${forwardBadge}
                ${reverseBadge}
            </div>

            <div class="profile-footer">
                <a href="${escapeHtml(profile.downloadLocation)}"
                   class="download-link"
                   target="_blank"
                   rel="noopener noreferrer">
                    ダウンロード
                </a>
                <div class="profile-dates">
                    <span>登録: ${formatDate(profile.registeredDate)}</span>
                    <span>更新: ${formatDate(profile.updatedDate)}</span>
                </div>
            </div>
        </div>
    `;
}

// カウント表示の更新
function updateCount() {
    const countElement = document.getElementById('profileCount');
    if (countElement) {
        countElement.textContent = `${filteredProfiles.length} / ${allProfiles.length} 件`;
    }
}

// エラー表示
function showError(message) {
    const container = document.getElementById('profilesContainer');
    if (container) {
        container.innerHTML = `
            <div class="empty-state">
                <h3>エラー</h3>
                <p>${escapeHtml(message)}</p>
            </div>
        `;
    }
}

// ユーティリティ関数: HTMLエスケープ
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ユーティリティ関数: 日付フォーマット
function formatDate(dateString) {
    const date = new Date(dateString);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}/${month}/${day}`;
}

// ユーティリティ関数: デバウンス
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Googleフォームリンクの設定
const GOOGLE_FORM_URL = 'https://docs.google.com/forms/d/e/1FAIpQLSdxX1ik7rtV8ofXRSED2-jsjJLCAAIkH-unuyGj_TtTVkvMjA/viewform';

// フォームリンクの設定
document.addEventListener('DOMContentLoaded', () => {
    const formLink = document.getElementById('requestFormLink');
    if (formLink && GOOGLE_FORM_URL) {
        formLink.href = GOOGLE_FORM_URL;
    }
});
