"use strict";

const state = {
    settings: null,
    optionsMeta: null,
    results: {},
    profiles: [],
    profileFields: [],
    activeProfileId: null,
    sourceMode: "current",
    initialized: false,
    requestToken: 0,
};

const $ = (id) => document.getElementById(id);

function setStatus(text) {
    $("statusBadge").textContent = text;
}

function showError(message) {
    const box = $("errorBox");
    if (!message) {
        box.textContent = "";
        box.classList.add("hidden");
        return;
    }
    box.textContent = String(message);
    box.classList.remove("hidden");
}

async function api(url, options = {}) {
    const response = await fetch(url, {
        headers: {"Content-Type": "application/json"},
        ...options,
    });
    const payload = await response.json();
    if (!response.ok || !payload.ok) {
        throw new Error(payload.error || `请求失败：HTTP ${response.status}`);
    }
    return payload.data;
}

function pad2(n) {
    return String(n).padStart(2, "0");
}

function localDateTimeString(date = new Date()) {
    return [
        date.getFullYear(), "-", pad2(date.getMonth() + 1), "-", pad2(date.getDate()),
        "T", pad2(date.getHours()), ":", pad2(date.getMinutes()), ":", pad2(date.getSeconds()),
    ].join("");
}

function timezoneOffsetString(date = new Date()) {
    const totalMinutes = -date.getTimezoneOffset();
    const sign = totalMinutes >= 0 ? "+" : "-";
    const abs = Math.abs(totalMinutes);
    return `${sign}${pad2(Math.floor(abs / 60))}:${pad2(abs % 60)}`;
}

// ---------- 勾选组：主行星 / 小行星 / 恒星 共用同一套交互 ----------
// 每一项都是独立的复选框：点一下勾上，再点一下取消，互不影响；
// 每组都有「全选 / 全不选」和「已选 n/m」。恒星组另有「添加」输入框。

const PLANET_NAMES = {
    Su: "太阳", Mo: "月亮", Me: "水星", Ve: "金星", Ma: "火星", Ju: "木星", Sa: "土星",
    Ur: "天王星", Ne: "海王星", Pl: "冥王星", Ra: "罗睺", Ke: "计都",
    Ch: "凯龙", Ph: "福斯", Ce: "谷神", Pa: "智神", Jn: "婚神", Vs: "灶神",
};

function planetLabel(code) {
    return PLANET_NAMES[code] ? `${code} ${PLANET_NAMES[code]}` : code;
}

function starLabel(value) {
    const [name, designation] = String(value).split(",").map((s) => s.trim());
    return designation ? `${name} · ${designation}` : name;
}

function checkGroupBoxes(rootId) {
    return Array.from($(rootId).querySelectorAll(".check-grid input[type='checkbox']"));
}

function updateCheckCount(rootId) {
    const boxes = checkGroupBoxes(rootId);
    const checked = boxes.filter((b) => b.checked).length;
    $(rootId).querySelector(".check-count").textContent = `已选 ${checked}/${boxes.length}`;
}

function addCheckItem(rootId, value, label, checked, title = "") {
    const item = document.createElement("label");
    item.className = "check-item";
    if (title) item.title = title;

    const box = document.createElement("input");
    box.type = "checkbox";
    box.value = value;
    box.checked = checked;
    box.addEventListener("change", () => updateCheckCount(rootId));

    const text = document.createElement("span");
    text.textContent = label;

    item.append(box, text);
    $(rootId).querySelector(".check-grid").appendChild(item);
}

function getChecked(rootId) {
    return checkGroupBoxes(rootId).filter((b) => b.checked).map((b) => b.value);
}

function setChecked(rootId, values) {
    const wanted = new Set(values || []);
    checkGroupBoxes(rootId).forEach((b) => { b.checked = wanted.has(b.value); });
    updateCheckCount(rootId);
}

function mountCheckGroup(rootId, title, items, checkedValues, options = {}) {
    const root = $(rootId);
    root.className = "check-group";
    root.innerHTML = `
        <div class="check-group-head">
            <span class="check-group-title">${escapeHtml(title)} <span class="check-count muted"></span></span>
            <span class="check-group-actions">
                <button type="button" data-act="all">全选</button>
                <button type="button" data-act="none">全不选</button>
            </span>
        </div>
        <div class="check-grid"></div>
        ${options.addable ? `
        <div class="check-add">
            <input type="text" placeholder="${escapeHtml(options.addPlaceholder || "")}">
            <button type="button" data-act="add">添加</button>
        </div>` : ""}
    `;

    const wanted = new Set(checkedValues || []);
    for (const item of items) {
        addCheckItem(rootId, item.value, item.label, wanted.has(item.value), item.title || "");
    }
    updateCheckCount(rootId);

    root.querySelector("[data-act='all']").addEventListener("click", () => {
        checkGroupBoxes(rootId).forEach((b) => { b.checked = true; });
        updateCheckCount(rootId);
    });
    root.querySelector("[data-act='none']").addEventListener("click", () => {
        checkGroupBoxes(rootId).forEach((b) => { b.checked = false; });
        updateCheckCount(rootId);
    });

    if (options.addable) {
        const input = root.querySelector(".check-add input");
        const commit = () => {
            const value = input.value.split(",").map((s) => s.trim()).filter(Boolean).join(",");
            if (!value) return;
            const existing = checkGroupBoxes(rootId).find(
                (b) => b.value.toLowerCase() === value.toLowerCase()
            );
            if (existing) existing.checked = true;
            else addCheckItem(rootId, value, starLabel(value), true, value);
            input.value = "";
            updateCheckCount(rootId);
        };
        input.addEventListener("keydown", (event) => {
            if (event.key === "Enter") {
                event.preventDefault();
                commit();
            }
        });
        root.querySelector("[data-act='add']").addEventListener("click", commit);
    }
}

function mountSelectionGroups() {
    const calc = state.settings.calculation_defaults;
    const meta = state.optionsMeta;

    mountCheckGroup(
        "selectedPlanets", "主行星",
        meta.main_planets.map((code) => ({value: code, label: planetLabel(code)})),
        calc.selected_planets
    );
    mountCheckGroup(
        "selectedMinorPlanets", "小行星",
        meta.minor_planets.map((code) => ({value: code, label: planetLabel(code)})),
        calc.selected_minor_planets
    );

    const stars = Array.from(new Set(calc.selected_stars || []));
    mountCheckGroup(
        "selectedStars", "恒星",
        stars.map((value) => ({value, label: starLabel(value), title: value})),
        stars,
        {addable: true, addPlaceholder: "添加恒星，如 Betelgeuse,alOri"}
    );
}

// values 里的每一项既可以是字符串，也可以是 {value, label}。
function fillSelect(selectElement, values) {
    selectElement.innerHTML = "";
    for (const entry of values) {
        const isObject = entry !== null && typeof entry === "object";
        const option = document.createElement("option");
        option.value = isObject ? entry.value : entry;
        option.textContent = isObject ? (entry.label ?? entry.value) : entry;
        selectElement.appendChild(option);
    }
}

// 设置下拉菜单的值；如果 settings.json 里写的值不在选项里（例如手改过），
// 临时补一个选项，避免下拉菜单悄悄变成空白、又悄悄用另一个值去计算。
function setSelectValue(selectElement, value) {
    const text = String(value ?? "");
    const exists = Array.from(selectElement.options).some((o) => o.value === text);
    if (!exists && text !== "") {
        const option = document.createElement("option");
        option.value = text;
        option.textContent = `${text}（不在预设列表中）`;
        selectElement.appendChild(option);
    }
    selectElement.value = text;
}

function setFormFromDefaults() {
    const birth = state.settings.birth_defaults;
    const calc = state.settings.calculation_defaults;

    $("elevation").value = birth.elevation;
    $("atpress").value = birth.atpress;
    $("attemp").value = birth.attemp;
    $("calendar").value = birth.calendar;

    $("eclipticMode").value = calc.ecliptic_mode;
    setSelectValue($("ayanamshaMode"), calc.ayanamsha_mode);
    $("nodeMode").value = calc.node_mode;
    $("houseSystem").value = calc.house_system;
    $("heliocentric").checked = Boolean(calc.heliocentric);
    $("strictEphe").checked = Boolean(calc.strict_ephe);
    $("horaryActive").checked = Boolean(calc.KP_HORARY?.is_active);
    $("horaryMode").value = calc.KP_HORARY?.mode || "KS-N";
    $("horaryNumber").value = calc.KP_HORARY?.number ?? 78;
    $("dashaDaysInYear").value = calc.dasha_days_in_year ?? 365.25;
}

// KS-N 上限 249，CIL-N 上限 2193（对应 kp.py 的 get_horary_ascendant）。
function updateHoraryRange() {
    const mode = $("horaryMode").value;
    const max = mode === "CIL-N" ? 2193 : 249;
    const input = $("horaryNumber");
    input.max = String(max);
    input.placeholder = `1-${max}`;

    const current = Number(input.value);
    if (!current || current < 1) input.value = "1";
    else if (current > max) input.value = String(max);
}

function formComplete() {
    return Boolean(
        $("localTime").value &&
        $("timezone").value.trim() &&
        $("latitude").value !== "" &&
        $("longitude").value !== ""
    );
}

function collectPayload() {
    return {
        birth: {
            local_time_str: $("localTime").value.replace("T", " "),
            timezone_str: $("timezone").value.trim(),
            latitude: Number($("latitude").value),
            longitude: Number($("longitude").value),
            elevation: Number($("elevation").value || 0),
            atpress: Number($("atpress").value || 1013.25),
            attemp: Number($("attemp").value || 20),
            calendar: $("calendar").value,
        },
        options: {
            ecliptic_mode: $("eclipticMode").value,
            ayanamsha_mode: $("ayanamshaMode").value,
            node_mode: $("nodeMode").value,
            house_system: $("houseSystem").value,
            heliocentric: $("heliocentric").checked,
            strict_ephe: $("strictEphe").checked,
            selected_planets: getChecked("selectedPlanets"),
            selected_minor_planets: getChecked("selectedMinorPlanets"),
            selected_stars: getChecked("selectedStars"),
            KP_HORARY: {
                is_active: $("horaryActive").checked,
                mode: $("horaryMode").value,
                number: Number($("horaryNumber").value || 1),
            },
            sunrise_rsmi: state.settings.calculation_defaults.sunrise_rsmi,
            dasha_days_in_year: Number($("dashaDaysInYear").value || 365.25),
        },
    };
}

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function formatValue(value) {
    if (value === null || value === undefined) return "";

    // 全是简单值的数组（如 KP 的 [1, 5, 9]、["Ju", "Sa"]）显示为「1, 5, 9」，不带方括号；
    // 空数组显示「—」。数据本身仍是原样的列表，只改显示。
    if (
        Array.isArray(value) &&
        value.every((v) => v === null || ["string", "number", "boolean"].includes(typeof v))
    ) {
        return value.length ? escapeHtml(value.join(", ")) : "—";
    }

    if (typeof value === "object") {
        return `<pre>${escapeHtml(JSON.stringify(value, null, 2))}</pre>`;
    }
    return escapeHtml(String(value));
}

function renderKeyValue(target, obj) {
    const container = $(target);
    if (!obj || Object.keys(obj).length === 0) {
        container.innerHTML = "<p class='muted'>无数据</p>";
        return;
    }

    let html = "<div class='table-wrap'><table><tbody>";
    for (const [key, value] of Object.entries(obj)) {
        html += `<tr><th>${escapeHtml(key)}</th><td>${formatValue(value)}</td></tr>`;
    }
    html += "</tbody></table></div>";
    container.innerHTML = html;
}

// 表格里这几列固定排在最前面、按这个顺序；其余的列（如 KP 的 sign_lord、A/B/C/D）排在后面，彼此保持原有顺序。
const COLUMN_ORDER = ["dms", "lon", "lat", "ra", "dec", "speed"];

function orderColumns(columns) {
    const rank = (name) => {
        const index = COLUMN_ORDER.indexOf(name);
        return index === -1 ? COLUMN_ORDER.length : index;
    };
    return [...columns].sort((a, b) => rank(a) - rank(b));
}

function renderObjectMap(target, obj) {
    const container = $(target);
    if (!obj || Object.keys(obj).length === 0) {
        container.innerHTML = "<p class='muted'>无数据</p>";
        return;
    }

    const first = Object.values(obj)[0];
    if (typeof first !== "object" || first === null || Array.isArray(first)) {
        renderKeyValue(target, obj);
        return;
    }

    const columns = new Set();
    Object.values(obj).forEach((row) => {
        Object.keys(row || {}).forEach((key) => columns.add(key));
    });

    const cols = orderColumns(Array.from(columns));
    let html = "<div class='table-wrap'><table><thead><tr><th>项目</th>";
    html += cols.map((c) => `<th>${escapeHtml(c)}</th>`).join("");
    html += "</tr></thead><tbody>";

    for (const [name, row] of Object.entries(obj)) {
        html += `<tr><th>${escapeHtml(name)}</th>`;
        for (const col of cols) {
            html += `<td>${formatValue(row?.[col])}</td>`;
        }
        html += "</tr>";
    }

    html += "</tbody></table></div>";
    container.innerHTML = html;
}

function renderAllResults() {
    renderKeyValue("contextResult", state.results.context || {});
    renderObjectMap("planetResult", state.results.planet_pos || {});
    renderObjectMap("minorPlanetResult", state.results.minor_planet_pos || {});
    renderObjectMap("fixedStarResult", state.results.fixed_star_pos || {});

    const house = state.results.house_result || {};
    $("houseResult").innerHTML = `
        <h3>十二宫宫头</h3><div id="houseCuspsInner"></div>
        <h3>四轴</h3><div id="houseAxesInner"></div>
        <h3>辅助轴点</h3><div id="houseAuxInner"></div>
    `;
    renderObjectMap("houseCuspsInner", house.houses || {});
    renderObjectMap("houseAxesInner", house.axes || {});
    renderObjectMap("houseAuxInner", house.auxiliary_points || {});

    $("kpResult").innerHTML = `
        <h3>KP 行星星主</h3><div id="kp1"></div>
        <h3>KP 宫位星主</h3><div id="kp2"></div>
        <h3>行星象征宫位 ABCD</h3><div id="kp3"></div>
        <h3>宫位象征星 1234</h3><div id="kp4"></div>
        <h3>主宰星</h3><div id="kp5"></div>
    `;
    renderObjectMap("kp1", state.results.kp_planet_results || {});
    renderObjectMap("kp2", state.results.kp_house_results || {});
    renderObjectMap("kp3", state.results.kp_planet_sigs || {});
    renderObjectMap("kp4", state.results.kp_house_sigs || {});
    renderKeyValue("kp5", state.results.kp_ruling_planets || {});

    $("sunResult").innerHTML = `
        <h3>日出日落</h3><div id="sun1"></div>
        <h3>值日星</h3><div id="sun2"></div>
        <h3>行星时</h3><div id="sun3"></div>
    `;
    renderKeyValue("sun1", state.results.sun_events || {});
    renderKeyValue("sun2", state.results.day_lord_result || {});
    renderKeyValue("sun3", state.results.planetary_hour_data || {});

    renderDashaRoot();
}

// 标记「当前所在大运」的符号；想换成别的符号，只改这一处。
const DASHA_NOW_MARK = "●";

function findNowIndex(items, now) {
    for (let i = 0; i < items.length; i++) {
        const start = new Date(items[i].start);
        const end = new Date(items[i].end);
        if (now >= start && now < end) return i;
    }
    return -1;
}

function fetchDashaChildren(item) {
    return api("/api/dasha/expand", {
        method: "POST",
        body: JSON.stringify({
            planet: item.planet,
            start: item.start,
            duration_seconds: item.duration_seconds,
        }),
    });
}

// 排盘后只显示第一层大运（已由后端算好）；当前所在的一支会高亮并加符号标出，但不自动展开。
// 需要看下一层时，点击某个区间才向后端请求并展开（见 buildDashaLevel），再点一次收起。
function renderDashaRoot() {
    const root = $("dashaResult");
    root.innerHTML = "";
    const data = state.results.dasha_level1 || [];
    if (!data.length) {
        root.innerHTML = "<p class='muted'>没有大运数据。请确认主行星选择中包含 Mo。</p>";
        return;
    }

    root.appendChild(buildDashaLevel(data, 1, findNowIndex(data, new Date())));
}

function buildDashaLevel(items, level, nowIndex) {
    const wrapper = document.createElement("div");
    wrapper.className = "dasha-level";
    wrapper.dataset.level = String(level);

    items.forEach((item, index) => {
        const holder = document.createElement("div");
        const row = document.createElement("div");
        row.className = "dasha-row" + (index === nowIndex ? " current-dasha" : "");
        row.innerHTML = `
            <div class="dasha-level-tag">L${level}</div>
            <div class="dasha-planet">${escapeHtml(item.planet)}${
                index === nowIndex ? `<span class="dasha-now-mark">${DASHA_NOW_MARK}</span>` : ""
            }</div>
            <div>${escapeHtml(item.start)}</div>
            <div>${escapeHtml(item.end)}</div>
        `;

        row.addEventListener("click", async (event) => {
            event.stopPropagation();

            const existing = holder.querySelector(":scope > .dasha-level");
            if (existing) {
                existing.remove();
                return;
            }

            try {
                const children = await fetchDashaChildren(item);
                holder.appendChild(buildDashaLevel(children, level + 1, findNowIndex(children, new Date())));
            } catch (error) {
                showError(error.message);
            }
        });

        holder.appendChild(row);
        wrapper.appendChild(holder);
    });

    return wrapper;
}

async function calculateFull() {
    if (!formComplete()) {
        showError("请先填写完整的本地时间、时区、纬度、经度。");
        setStatus("参数不完整");
        return;
    }

    const token = ++state.requestToken;
    showError("");
    setStatus("计算中");

    try {
        const result = await api("/api/chart/full", {
            method: "POST",
            body: JSON.stringify(collectPayload()),
        });

        if (token !== state.requestToken) return;

        state.results = result;
        renderAllResults();
        setStatus("已更新");
    } catch (error) {
        if (token !== state.requestToken) return;
        showError(error.message);
        setStatus("计算失败");
    }
}

async function calculatePartial(changedFields) {
    if (!formComplete()) return;

    if (!Object.keys(state.results).length) {
        await calculateFull();
        return;
    }

    const token = ++state.requestToken;
    showError("");
    setStatus("局部更新中");

    try {
        const payload = collectPayload();
        payload.changed_fields = Array.from(changedFields);
        payload.current_results = state.results;

        const updates = await api("/api/chart/partial", {
            method: "POST",
            body: JSON.stringify(payload),
        });

        if (token !== state.requestToken) return;

        Object.assign(state.results, updates);
        renderAllResults();
        setStatus("已更新");
    } catch (error) {
        if (token !== state.requestToken) return;
        showError(error.message);
        setStatus("计算失败");
    }
}

// 不再逐字段自动排盘：当前时间/位置、手动输入这两种模式下，
// 改完参数需要点这个按钮才会重新计算；calculatePartial() 保留在上面，
// 只是暂时没有自动触发它的地方了，以后想恢复自动增量计算随时能接回来。
function bindCalcButton() {
    $("calcBtn").addEventListener("click", () => {
        calculateFull();
    });
}

function updateModeUI() {
    $("profilePanel").classList.toggle("hidden", state.sourceMode !== "profile");
    document.querySelectorAll("input[name='sourceMode']").forEach((radio) => {
        radio.checked = radio.value === state.sourceMode;
    });
}

async function initializeCurrentMode() {
    state.sourceMode = "current";
    updateModeUI();

    $("localTime").value = localDateTimeString();
    $("timezone").value = timezoneOffsetString();

    const defaultLocation = state.settings.default_location;
    $("latitude").value = defaultLocation.latitude;
    $("longitude").value = defaultLocation.longitude;

    let permissionText = "权限状态未知";
    try {
        if (navigator.permissions?.query) {
            const status = await navigator.permissions.query({name: "geolocation"});
            permissionText = `权限：${status.state}`;
        }
    } catch (_) {}

    if (!navigator.geolocation) {
        $("locationInfo").textContent =
            `浏览器不支持 Geolocation API，已使用默认地点：${defaultLocation.label}。` +
            `点击右上角「排盘」计算。`;
        return;
    }

    $("locationInfo").textContent =
        `正在通过浏览器 Geolocation API 请求位置。${permissionText}。` +
        `网页无法判断底层实际来自 GPS、Wi‑Fi、基站还是系统融合定位。`;

    await new Promise((resolve) => {
        navigator.geolocation.getCurrentPosition(
            (position) => {
                $("latitude").value = position.coords.latitude.toFixed(6);
                $("longitude").value = position.coords.longitude.toFixed(6);

                const accuracy = Number.isFinite(position.coords.accuracy)
                    ? `${Math.round(position.coords.accuracy)} 米`
                    : "未知";

                $("locationInfo").textContent =
                    `定位方式：浏览器 Geolocation API；底层定位提供方不会暴露给网页。` +
                    `报告精度：${accuracy}；${permissionText}。点击右上角「排盘」计算。`;
                resolve();
            },
            (error) => {
                $("locationInfo").textContent =
                    `定位未获得，已使用默认地点：${defaultLocation.label}。` +
                    `原因：${error.message || "用户拒绝、系统定位不可用或定位超时"}。` +
                    `点击右上角「排盘」计算。`;
                resolve();
            },
            {
                enableHighAccuracy: true,
                timeout: 8000,
                maximumAge: 0,
            }
        );
    });
}

function switchToManualMode() {
    state.sourceMode = "manual";
    updateModeUI();
    $("locationInfo").textContent =
        "手动输入模式：填好时间、时区、经纬度后，点击右上角「排盘」计算。";
}

function renderProfiles() {
    const select = $("profileSelect");
    select.innerHTML = "";

    const empty = document.createElement("option");
    empty.value = "";
    empty.textContent = "（未选择档案）";
    select.appendChild(empty);

    for (const profile of state.profiles) {
        const option = document.createElement("option");
        option.value = String(profile.id);
        option.textContent = profile.display_name;
        select.appendChild(option);
    }

    if (state.activeProfileId) {
        select.value = String(state.activeProfileId);
    }
}

async function refreshProfiles() {
    state.profiles = await api("/api/profiles");
    renderProfiles();
}

// ---------- 自定义字段：表单里的输入框 ----------

// preserved：{字段id: 值}，用于重画输入框时保留已填内容。
function renderProfileCustomFields(preserved = null) {
    const box = $("profileCustomFields");
    box.innerHTML = "";

    for (const field of state.profileFields) {
        const label = document.createElement("label");
        label.textContent = field.label;

        const input = document.createElement(field.multiline ? "textarea" : "input");
        if (field.multiline) input.rows = 3;
        else input.type = "text";
        input.dataset.fieldId = String(field.id);
        input.value = preserved?.[field.id] ?? "";

        label.appendChild(input);
        box.appendChild(label);
    }
}

function collectProfileFields() {
    const values = {};
    $("profileCustomFields").querySelectorAll("[data-field-id]").forEach((el) => {
        values[el.dataset.fieldId] = el.value;
    });
    return values;
}

function loadProfileIntoForm(profile) {
    $("profileName").value = profile.display_name || "";
    renderProfileCustomFields(profile.fields || {});
    $("localTime").value = String(profile.birth_time || "").replace(" ", "T");
    $("timezone").value = profile.timezone_offset || "";
    $("latitude").value = profile.latitude ?? "";
    $("longitude").value = profile.longitude ?? "";
}

async function selectProfile(profileId) {
    if (!profileId) return;
    const profile = await api(`/api/profiles/${profileId}`);
    state.activeProfileId = profile.id;
    loadProfileIntoForm(profile);
    await calculateFull();
}

function profilePayload() {
    return {
        display_name: $("profileName").value.trim(),
        birth_time: $("localTime").value.replace("T", " "),
        timezone_offset: $("timezone").value.trim(),
        latitude: Number($("latitude").value),
        longitude: Number($("longitude").value),
        fields: collectProfileFields(),
    };
}

function clearProfileForm() {
    state.activeProfileId = null;
    $("profileSelect").value = "";
    $("profileName").value = "";
    renderProfileCustomFields(null);
}

// 「新建」：把当前表单里的内容存成一份全新的档案，并切换到这份新档案。
async function createProfileFromForm() {
    if (!formComplete()) {
        showError("请先填写完整的本地时间、时区、纬度、经度。");
        return;
    }
    const payload = profilePayload();
    if (!payload.display_name) {
        showError("人物名称不能为空。");
        return;
    }

    const sameName = state.profiles.some(
        (p) => String(p.display_name).trim().toLowerCase() === payload.display_name.toLowerCase()
    );
    if (sameName && !confirm(`已经有一份叫「${payload.display_name}」的档案了，仍要再新建一份吗？`)) {
        return;
    }

    try {
        showError("");
        const saved = await api("/api/profiles", {
            method: "POST",
            body: JSON.stringify(payload),
        });
        state.activeProfileId = saved.id;
        await refreshProfiles();
        $("profileSelect").value = String(saved.id);
        setStatus(`已新建档案「${saved.display_name}」`);
    } catch (error) {
        showError(error.message);
    }
}

// 「保存」：用当前表单内容直接覆盖当前选中的那份档案。
async function saveActiveProfile() {
    if (!state.activeProfileId) {
        showError("当前没有选中的档案，无法覆盖保存。请先在上方选择一份档案，或点击「新建」把当前内容存成新档案。");
        return;
    }
    if (!formComplete()) {
        showError("请先填写完整的本地时间、时区、纬度、经度。");
        return;
    }

    try {
        showError("");
        const saved = await api(`/api/profiles/${state.activeProfileId}`, {
            method: "PUT",
            body: JSON.stringify(profilePayload()),
        });
        await refreshProfiles();
        $("profileSelect").value = String(saved.id);
        setStatus(`已覆盖保存「${saved.display_name}」`);
    } catch (error) {
        showError(error.message);
    }
}

function bindProfileActions() {
    $("profileSelect").addEventListener("change", async () => {
        const id = Number($("profileSelect").value);
        if (!id) {
            // 选回"未选择"：只取消选中，表单里的内容保留，方便改一改再「新建」。
            state.activeProfileId = null;
            return;
        }
        try {
            await selectProfile(id);
        } catch (error) {
            showError(error.message);
        }
    });

    $("newProfileBtn").addEventListener("click", createProfileFromForm);
    $("saveProfileBtn").addEventListener("click", saveActiveProfile);
    $("clearProfileBtn").addEventListener("click", clearProfileForm);

    $("deleteProfileBtn").addEventListener("click", async () => {
        if (!state.activeProfileId) return;
        if (!confirm("确定删除当前人物档案？")) return;

        try {
            await api(`/api/profiles/${state.activeProfileId}`, {
                method: "DELETE",
            });
            clearProfileForm();
            await refreshProfiles();
            setStatus("档案已删除");
        } catch (error) {
            showError(error.message);
        }
    });

    bindFieldManager();
}

// ---------- 自定义字段：管理（增 / 改名 / 删） ----------

async function reloadProfileFields() {
    const preserved = collectProfileFields();   // 保住已经敲进去、还没保存的内容
    state.profileFields = await api("/api/profile-fields");
    renderProfileCustomFields(preserved);
    renderFieldManager();
}

function renderFieldManager() {
    const box = $("fieldManagerList");
    box.innerHTML = "";

    if (!state.profileFields.length) {
        box.innerHTML = "<p class='muted'>还没有自定义字段。</p>";
        return;
    }

    for (const field of state.profileFields) {
        const row = document.createElement("div");
        row.className = "field-row";

        const name = document.createElement("input");
        name.type = "text";
        name.value = field.label;
        name.maxLength = 40;
        name.title = "改完按回车，或点一下别处即保存";
        name.addEventListener("change", async () => {
            try {
                showError("");
                await api(`/api/profile-fields/${field.id}`, {
                    method: "PUT",
                    body: JSON.stringify({label: name.value}),
                });
                await reloadProfileFields();
            } catch (error) {
                showError(error.message);
                name.value = field.label;
            }
        });

        const multiLabel = document.createElement("label");
        const multi = document.createElement("input");
        multi.type = "checkbox";
        multi.checked = field.multiline;
        multi.addEventListener("change", async () => {
            try {
                showError("");
                await api(`/api/profile-fields/${field.id}`, {
                    method: "PUT",
                    body: JSON.stringify({multiline: multi.checked}),
                });
                await reloadProfileFields();
            } catch (error) {
                showError(error.message);
                multi.checked = field.multiline;
            }
        });
        multiLabel.append(multi, " 多行");

        const del = document.createElement("button");
        del.type = "button";
        del.className = "danger";
        del.textContent = "删除";
        del.addEventListener("click", () => deleteField(field));

        row.append(name, multiLabel, del);
        box.appendChild(row);
    }
}

async function addField() {
    const input = $("newFieldLabel");
    const label = input.value.trim();
    if (!label) return;

    try {
        showError("");
        await api("/api/profile-fields", {
            method: "POST",
            body: JSON.stringify({label, multiline: $("newFieldMultiline").checked}),
        });
        input.value = "";
        $("newFieldMultiline").checked = false;
        await reloadProfileFields();
        setStatus(`已为所有档案添加字段「${label}」`);
    } catch (error) {
        showError(error.message);
    }
}

async function deleteField(field) {
    try {
        showError("");
        // 先取最新的"有多少份档案填了这一项"，让确认框里的数字是准的。
        const latest = (await api("/api/profile-fields")).find((f) => f.id === field.id);
        if (!latest) {
            await reloadProfileFields();
            return;
        }

        const message = latest.used_count > 0
            ? `确定删除字段「${latest.label}」吗？\n\n所有档案中的这一项都会被一并删除（目前有 ${latest.used_count} 份档案填了内容），且无法恢复。`
            : `确定删除字段「${latest.label}」吗？`;
        if (!confirm(message)) return;

        await api(`/api/profile-fields/${field.id}`, {method: "DELETE"});
        await reloadProfileFields();
        await refreshProfiles();
        setStatus(`已从所有档案中删除字段「${latest.label}」`);
    } catch (error) {
        showError(error.message);
    }
}

function bindFieldManager() {
    $("addFieldBtn").addEventListener("click", addField);
    $("newFieldLabel").addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            event.preventDefault();
            addField();
        }
    });
}

function bindModeSwitching() {
    document.querySelectorAll("input[name='sourceMode']").forEach((radio) => {
        radio.addEventListener("change", async () => {
            const mode = radio.value;
            if (mode === "current") {
                await initializeCurrentMode();
            } else if (mode === "manual") {
                switchToManualMode();
            } else if (mode === "profile") {
                state.sourceMode = "profile";
                updateModeUI();
                $("locationInfo").textContent =
                    "人物档案模式：选择档案后立即排盘；之后如果修改了数值，需要重新点击「排盘」才会用新数值计算。";
            }
        });
    });
}

async function init() {
    try {
        setStatus("初始化中");
        const bootstrap = await api("/api/bootstrap");

        state.settings = bootstrap.settings;
        state.optionsMeta = bootstrap.options;
        state.profiles = bootstrap.profiles;
        state.profileFields = bootstrap.profile_fields || [];

        fillSelect($("houseSystem"), state.optionsMeta.house_systems);
        fillSelect($("ayanamshaMode"), state.optionsMeta.ayanamsha_modes);
        mountSelectionGroups();

        setFormFromDefaults();
        updateHoraryRange();
        $("horaryMode").addEventListener("change", updateHoraryRange);
        renderProfiles();
        renderProfileCustomFields();
        renderFieldManager();

        bindCalcButton();
        bindModeSwitching();
        bindProfileActions();

        state.initialized = true;
        await initializeCurrentMode();
    } catch (error) {
        showError(error.message);
        setStatus("初始化失败");
    }
}

window.addEventListener("DOMContentLoaded", init);
