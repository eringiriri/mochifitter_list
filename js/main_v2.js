// グローバル変数
let allProfiles = [];
let allAvatars = {};
let filteredProfiles = [];
let currentLanguage = localStorage.getItem('selectedLang') || 'ja';
let lastUpdatedText = '';

const TRANSLATIONS = {
    ja: {
        pageTitle: 'もちふぃった～プロファイル一覧 V2',
        prototypeBanner: 'プロファイル中心の表示スタイルに調整中',
        siteTitle: 'もちふぃった～プロファイル一覧',
        siteSubtitle: 'プロファイル単位で表示する新仕様のプロトタイプ',
        experimental: 'Experimental',
        lastUpdated: '最終更新',
        loading: '読み込み中...',
        searchPlaceholder: 'プロファイル作者、アバター名、Booth末尾番号で検索...',
        filterAll: '全て',
        filterOfficial: '公式',
        filterUnofficial: '非公式',
        filterForward: '順方向',
        filterReverse: '逆方向',
        filterFree: '無料',
        filterPaid: '有料',
        filterIncluded: 'アバター同梱',
        profileList: 'プロファイル一覧',
        empty: '該当するプロファイルが見つかりませんでした',
        loadError: 'データの読み込みに失敗しました',
        notesLabel: '備考',
        profileOf: '{author} のプロファイル',
        updated: '更新',
        by: 'by',
        count: '{filtered} / {total} 件',
        official: 'OFFICIAL',
        pricingFree: '無料',
        pricingPaid: '有料',
        pricingIncluded: 'アバター同梱'
    },
    en: {
        pageTitle: 'MochiFitter Profile List V2',
        siteTitle: 'MochiFitter Profile List',
        siteSubtitle: 'Prototype of the new profile-based listing',
        experimental: 'Experimental',
        lastUpdated: 'Last updated',
        loading: 'Loading...',
        searchPlaceholder: 'Search by profile author, avatar name, or Booth item number...',
        filterAll: 'All',
        filterOfficial: 'Official',
        filterUnofficial: 'Unofficial',
        filterForward: 'Forward',
        filterReverse: 'Reverse',
        filterFree: 'Free',
        filterPaid: 'Paid',
        filterIncluded: 'Avatar included',
        profileList: 'Profile List',
        empty: 'No matching profiles found',
        loadError: 'Failed to load data',
        notesLabel: 'Notes',
        profileOf: "{author}'s profile",
        updated: 'Updated',
        by: 'by',
        count: '{filtered} / {total} items',
        official: 'OFFICIAL',
        pricingFree: 'Free',
        pricingPaid: 'Paid',
        pricingIncluded: 'Avatar included'
    },
    ko: {
        pageTitle: '모치피터 프로필 목록 V2',
        siteTitle: '모치피터 프로필 목록',
        siteSubtitle: '프로필 단위로 표시하는 새 사양의 프로토타입',
        experimental: 'Experimental',
        lastUpdated: '마지막 업데이트',
        loading: '불러오는 중...',
        searchPlaceholder: '프로필 제작자, 아바타 이름, Booth 상품 번호로 검색...',
        filterAll: '전체',
        filterOfficial: '공식',
        filterUnofficial: '비공식',
        filterForward: '정방향',
        filterReverse: '역방향',
        filterFree: '무료',
        filterPaid: '유료',
        filterIncluded: '아바타 포함',
        profileList: '프로필 목록',
        empty: '일치하는 프로필을 찾을 수 없습니다',
        loadError: '데이터를 불러오지 못했습니다',
        notesLabel: '비고',
        profileOf: '{author}의 프로필',
        updated: '업데이트',
        by: '제작',
        count: '{filtered} / {total}건',
        official: '공식',
        pricingFree: '무료',
        pricingPaid: '유료',
        pricingIncluded: '아바타 포함'
    },
    zh: {
        pageTitle: 'MochiFitter 资料列表 V2',
        siteTitle: 'MochiFitter 资料列表',
        siteSubtitle: '按资料显示的新规格原型',
        experimental: 'Experimental',
        lastUpdated: '最后更新',
        loading: '正在加载...',
        searchPlaceholder: '按资料作者、头像名称或 Booth 商品编号搜索...',
        filterAll: '全部',
        filterOfficial: '官方',
        filterUnofficial: '非官方',
        filterForward: '正向',
        filterReverse: '反向',
        filterFree: '免费',
        filterPaid: '付费',
        filterIncluded: '包含头像',
        profileList: '资料列表',
        empty: '未找到匹配的资料',
        loadError: '数据加载失败',
        notesLabel: '备注',
        profileOf: '{author} 的资料',
        updated: '更新',
        by: '作者',
        count: '{filtered} / {total} 条',
        official: '官方',
        pricingFree: '免费',
        pricingPaid: '付费',
        pricingIncluded: '包含头像'
    }
};

// DOMContentLoaded時の初期化
document.addEventListener('DOMContentLoaded', () => {
    loadData();
    setupEventListeners();
    initLanguageSelector();
});

function t(key, replacements = {}) {
    const dictionary = TRANSLATIONS[currentLanguage] || TRANSLATIONS.ja;
    let text = dictionary[key] || TRANSLATIONS.ja[key] || key;
    Object.entries(replacements).forEach(([name, value]) => {
        text = text.replace(`{${name}}`, value);
    });
    return text;
}

function applyTranslations() {
    document.documentElement.lang = currentLanguage;
    document.title = t('pageTitle');

    document.querySelectorAll('[data-i18n]').forEach(element => {
        element.textContent = t(element.dataset.i18n);
    });

    document.querySelectorAll('[data-i18n-placeholder]').forEach(element => {
        element.placeholder = t(element.dataset.i18nPlaceholder);
    });

    const updateTimeElement = document.getElementById('updateTime');
    if (updateTimeElement) {
        updateTimeElement.textContent = lastUpdatedText || t('loading');
    }

    updateCount();
}

// 言語セレクターの初期化
function initLanguageSelector() {
    const langSelect = document.getElementById('langSelect');
    if (!TRANSLATIONS[currentLanguage]) currentLanguage = 'ja';

    if (langSelect) {
        langSelect.value = currentLanguage;
        langSelect.addEventListener('change', (e) => {
            currentLanguage = e.target.value;
            localStorage.setItem('selectedLang', currentLanguage);
            applyTranslations();
            renderProfiles();
            updateCount();
        });
    }

    applyTranslations();
}

// プロファイルとアバターデータの読み込み
async function loadData() {
    try {
        const [profilesRes, avatarsRes] = await Promise.all([
            fetch('data/profiles_new.json'),
            fetch('data/avatars_new.json')
        ]);

        if (!profilesRes.ok || !avatarsRes.ok) {
            throw new Error(t('loadError'));
        }

        const profilesData = await profilesRes.json();
        const avatarsData = await avatarsRes.json();

        allProfiles = profilesData.profiles;
        
        // ID逆順でソート（最新のプロファイルを先頭に）
        allProfiles.sort(compareProfileIdDesc);
        
        // アバターデータをIDをキーにしたオブジェクトに変換
        avatarsData.avatars.forEach(avatar => {
            allAvatars[avatar.id] = avatar;
        });

        filteredProfiles = [...allProfiles];

        if (profilesData.lastUpdated) {
            lastUpdatedText = profilesData.lastUpdated;
            const updateTimeElement = document.getElementById('updateTime');
            if (updateTimeElement) {
                updateTimeElement.textContent = lastUpdatedText;
            }
        }

        renderProfiles();
        updateCount();
    } catch (error) {
        console.error('Error loading data:', error);
        showError(t('loadError'));
    }
}

// イベントリスナーの設定
function setupEventListeners() {
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(applyFilters, 300));
    }

    const filterCheckboxes = [
        'filterOfficial', 'filterUnofficial',
        'filterForward', 'filterReverse',
        'filterFree', 'filterPaid', 'filterIncluded'
    ];

    const filterAll = document.getElementById('filterAll');
    if (filterAll) {
        filterAll.addEventListener('change', () => applyFilters());
    }

    filterCheckboxes.forEach(id => {
        const checkbox = document.getElementById(id);
        if (checkbox) {
            checkbox.addEventListener('change', () => {
                if (checkbox.checked && filterAll) filterAll.checked = false;
                applyFilters();
            });
        }
    });
}

// フィルタリング処理
function applyFilters() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const showAll = document.getElementById('filterAll').checked;
    
    const showOfficial = document.getElementById('filterOfficial').checked;
    const showUnofficial = document.getElementById('filterUnofficial').checked;
    const showForward = document.getElementById('filterForward').checked;
    const showReverse = document.getElementById('filterReverse').checked;
    const showFree = document.getElementById('filterFree').checked;
    const showPaid = document.getElementById('filterPaid').checked;
    const showIncluded = document.getElementById('filterIncluded').checked;

    filteredProfiles = allProfiles.filter(profile => {
        // テキスト検索（作者名、および紐付くアバター名）
        const linkedAvatars = (profile.avatarIds || []).map(id => allAvatars[id]).filter(Boolean);
        const avatarNames = linkedAvatars.map(a => a.name.toLowerCase()).join(' ');
        
        // 紐付くアバター全員のURLからアイテムIDを抽出して文字列化
        const avatarItemIds = linkedAvatars.map(a => {
            const match = (a.nameUrl || '').match(/items\/(\d+)/);
            return match ? match[1] : '';
        }).join(' ');

        // プロファイル自体のBooth URL末尾の数値（アイテムID）を抽出
        const itemIdMatch = (profile.downloadLocation || '').match(/items\/(\d+)/);
        const itemId = itemIdMatch ? itemIdMatch[1] : '';

        const matchesSearch = !searchTerm ||
            profile.profileAuthor.toLowerCase().includes(searchTerm) ||
            avatarNames.includes(searchTerm) ||
            avatarItemIds.includes(searchTerm) ||
            itemId.includes(searchTerm);

        if (showAll) return matchesSearch;

        // グループ別フィルタ
        const matchesOfficial = !(showOfficial || showUnofficial) ||
            (showOfficial && profile.official) ||
            (showUnofficial && !profile.official);

        const matchesDirection = !(showForward || showReverse) ||
            (showForward && profile.forwardSupport) ||
            (showReverse && profile.reverseSupport);

        const matchesPrice = !(showFree || showPaid || showIncluded) ||
            (showFree && profile.pricing === '無料') ||
            (showPaid && profile.pricing === '有料') ||
            (showIncluded && profile.pricing === 'アバター同梱');

        return matchesSearch && matchesOfficial && matchesDirection && matchesPrice;
    });

    renderProfiles();
    updateCount();
}

// プロファイルの描画
function renderProfiles() {
    const container = document.getElementById('profilesContainer');
    if (!container) return;

    if (filteredProfiles.length === 0) {
        container.innerHTML = `<div class="empty-state">${escapeHtml(t('empty'))}</div>`;
        return;
    }

    container.innerHTML = filteredProfiles.map(profile => createProfileCard(profile)).join('');
}

// プロファイルカードの生成
function createProfileCard(profile) {
    const linkedAvatars = (profile.avatarIds || []).map(id => allAvatars[id]).filter(Boolean);
    
    // ドメイン判定
    let domain = '';
    let domainLabel = '';
    try {
        const url = new URL(profile.downloadLocation);
        domain = url.hostname;
        domainLabel = domain.replace('www.', '');
    } catch (e) {
        domainLabel = 'Link';
    }

    // アバターをタグ形式で表示
    const avatarTagsHtml = linkedAvatars.length > 0 ? `
        <div class="avatar-tags">
            ${linkedAvatars.map(avatar => {
                // 言語設定に基づいた名前の取得とフォールバック
                const langKey = `name_${currentLanguage}`;
                const displayName = (currentLanguage !== 'ja' && avatar[langKey]) ? avatar[langKey] : avatar.name;
                // nameUrl があればリンク、なければ span
                if (avatar.nameUrl) {
                    return `<a href="${escapeHtml(avatar.nameUrl)}" target="_blank" rel="noopener" class="avatar-tag">${escapeHtml(displayName)}</a>`;
                }
                return `<span class="avatar-tag">${escapeHtml(displayName)}</span>`;
            }).join('')}
        </div>
    ` : '';

    const officialHtml = profile.official ? `<span class="official-badge">${escapeHtml(t('official'))}</span>` : '';
    const pricingBadgeHtml = profile.pricing ? `<span class="price-overlay">${escapeHtml(translatePricing(profile.pricing))}</span>` : '';
    const notes = (profile.notes || '').replace(/\s*\r?\n\s*/g, ' ').trim();
    const notesHtml = notes ? `<div class="profile-notes">${escapeHtml(t('notesLabel'))}: ${escapeHtml(notes)}</div>` : '';

    // タイトルの決定（profileNameがあればそれを使用）
    const displayTitle = profile.profileName || t('profileOf', { author: profile.profileAuthor || '' });

    // profile-thumbnail: downloadLocation があればリンク、なければ div
    const thumbTag = profile.downloadLocation ? 'a' : 'div';
    const thumbAttr = profile.downloadLocation
        ? ` href="${escapeHtml(profile.downloadLocation)}" target="_blank" rel="noopener"`
        : '';

    // footer-info-main: profileAuthorUrl があればリンク、なければ div
    const footerTag = profile.profileAuthorUrl ? 'a' : 'div';
    const footerAttr = profile.profileAuthorUrl
        ? ` href="${escapeHtml(profile.profileAuthorUrl)}" target="_blank" rel="noopener"`
        : '';

    return `
        <div class="profile-card">
            <div class="profile-content">
                <${thumbTag}  class="profile-title"${thumbAttr}>
                    ${escapeHtml(displayTitle)}
                </${thumbTag}>
                
                ${avatarTagsHtml}

                <div class="profile-card-footer">
                    ${notesHtml}
                    <div class="profile-card-footer-main">
                        <${footerTag} class="footer-info-main"${footerAttr}>
                            <div class="domain-info">
                                <img src="https://www.google.com/s2/favicons?domain=${domain}&sz=32" class="domain-icon" alt="icon">
                                <span>${escapeHtml(domainLabel)}</span>
                            </div>
                            <div class="shop-info">
                                ${escapeHtml(t('by'))} ${escapeHtml(profile.profileshopname || profile.profileAuthor)}
                            </div>
                        </${footerTag}>
                        <div style="flex-shrink: 0;">${escapeHtml(t('updated'))}: ${formatDate(profile.updatedDate)}</div>
                    </div>
                </div>
            </div>
            
            <${thumbTag} class="profile-thumbnail"${thumbAttr}>
                <img src="${escapeHtml(profile.imageUrl || 'icon/icon.ico')}" alt="thumbnail" loading="lazy">
                ${officialHtml}
                ${pricingBadgeHtml}
            </${thumbTag}>
        </div>
    `;
}

// ユーティリティ
function updateCount() {
    const countElement = document.getElementById('profileCount');
    if (countElement) {
        if (allProfiles.length === 0) {
            countElement.textContent = t('loading');
            return;
        }
        countElement.textContent = t('count', {
            filtered: filteredProfiles.length,
            total: allProfiles.length
        });
    }
}

function showError(message) {
    const container = document.getElementById('profilesContainer');
    if (container) container.innerHTML = `<div class="empty-state">${escapeHtml(message)}</div>`;
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    if (isNaN(date)) return dateString;
    return `${date.getFullYear()}/${String(date.getMonth() + 1).padStart(2, '0')}/${String(date.getDate()).padStart(2, '0')}`;
}

function translatePricing(pricing) {
    const pricingMap = {
        '無料': 'pricingFree',
        '有料': 'pricingPaid',
        'アバター同梱': 'pricingIncluded'
    };
    return pricingMap[pricing] ? t(pricingMap[pricing]) : pricing;
}

function compareProfileIdDesc(a, b) {
    return getProfileIdNumber(b.id) - getProfileIdNumber(a.id);
}

function getProfileIdNumber(id) {
    const match = String(id || '').match(/\d+/);
    return match ? Number(match[0]) : 0;
}

function debounce(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}
