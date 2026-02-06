
/**
 * 星盘全局配置 (Registry & Style)
 * 路径: D:\github\项目经验\Python_金融占星\html\astro_style_config.js
 */
window.ASTRO_STYLE = {
    // ----------------------------------
    // 1. 行星注册表 (Registry) - 定义符号和可见性
    // ----------------------------------
    planetsRegistry: {
        'Su': { symbol: '☉', color: '#FF8A80', visible: true },
        'Mo': { symbol: '☽', color: '#90CAF9', visible: true },
        'Me': { symbol: '☿', color: '#A5D6A7', visible: true },
        'Ve': { symbol: '♀', color: '#FFE082', visible: true },
        'Ma': { symbol: '♂', color: '#FF8A80', visible: true },
        'Ju': { symbol: '♃', color: '#FF8A80', visible: true },
        'Sa': { symbol: '♄', color: '#FFE082', visible: true },
        'Ur': { symbol: '♅', color: '#A5D6A7', visible: true },
        'Ne': { symbol: '♆', color: '#90CAF9', visible: true },
        'Pl': { symbol: '♇', color: '#90CAF9', visible: true },
        'Ra': { symbol: '☊', color: '#90CAF9', visible: true },
        'Ke': { symbol: '☋', color: '#90CAF9', visible: true },
        // 预留虚星点
        'Lilith': { symbol: '⚸', color: '#fa5252', visible: true }
    },

    // ----------------------------------
    // 2. 您的定制配置 (融合版)
    // ----------------------------------
    colors: {
        background: '#0d1117', // 画布全局背景(最底层)
        line: '#30363d',       // 线条颜色
        highlight: '#e6edf3',  // 宫位数字色 (已更新)
        textMain: '#e6edf3',   // 主文字
        textDim: '#e6edf3',    // 次文字
        retro: '#FF8A80',      // 逆行色

        // 区域背景色
        zones: {
            outerRing: '#161b22',
            planetRing: '#0d1117',
            innerDisk: '#21262d',
            centerCore: '#0d1117'
        },

        // 四元素
        elements: {
            fire: '#FF8A80', earth: '#FFE082', air: '#A5D6A7', water: '#90CAF9'
        },

        // 行星色
        planets: {
            'Su': '#ffd43b', 'Mo': '#f8f9fa', 'Me': '#a5d8ff', 'Ve': '#fcc2d7',
            'Ma': '#ff8787', 'Ju': '#ff922b', 'Sa': '#ced4da', 'Ur': '#66d9e8',
            'Ne': '#5c7cfa', 'Pl': '#862e9c', 'Ra': '#96f2d7', 'Ke': '#96f2d7'
        }
    },

    fonts: {
        base: 'bold 20px Menlo, Consolas, monospace', // 已更新
        symbol: '32px "Segoe UI Symbol", sans-serif',
        sign: '26px "Segoe UI Symbol", sans-serif',   // 已更新
        planet: '32px "Segoe UI Symbol", sans-serif', // 已更新
        houseNum: 'bold 20px sans-serif'
    },

    radii: {
        r1: 450, // 外边框
        r2: 420, // 宫头数据带
        r3: 390, // 黄道内界

        // 行星数据带 (垂直堆叠层) - 已更新您的数值
        r4: 355,
        r5: 315,
        r6: 270,
        r7: 230,
        r8: 200,

        // 宫位内盘 - 已更新您的数值
        r9: 175,
        r10: 150,
        r11: 125
    },

    settings: {
        collisionMinDist: 7.5, // 已更新
        arcSpread: 0.09
    }
};

// ============================================================
// [新增] 核心渲染逻辑 (Render Logic)
// 既然您希望逻辑分离，我们将渲染函数放在这里
// ============================================================

/**
 * 渲染所有数据表格 (KP, Info, Sigs, Ruling)
 * @param {Object} chartData - 从 Python 注入的全局数据
 */
window.renderKpTables = function (chartData) {
    if (!chartData) return;

    // --- 通用：动态创建表格函数 ---
    const createDynamicTable = (headers, rows, isKeyVal = false) => {
        let html = '<table class="astro-table"><thead><tr>';
        headers.forEach(h => html += `<th>${h}</th>`);
        html += '</tr></thead><tbody>';

        rows.forEach(row => {
            html += '<tr>';
            if (Array.isArray(row)) {
                // 处理数组型行数据
                row.forEach(cell => {
                    // 如果是数组(比如宫位列表)，转字符串
                    let content = Array.isArray(cell) ? cell.join(', ') : cell;
                    if (content === '') content = '-';
                    html += `<td>${content}</td>`;
                });
            } else {
                // 处理对象型行数据 (KP表用)
                html += `<td>${row.name}</td>
                         <td>${row.sign}</td>
                         <td>${row.pos_str}</td>
                         <td>${row.star}</td>
                         <td>${row.rl}</td>
                         <td>${row.nl}</td>
                         <td>${row.sl}</td>
                         <td>${row.ssl}</td>
                         <td>${row.paada}</td>`;
            }
            html += '</tr>';
        });
        html += '</tbody></table>';
        return html;
    };

    // 1. 渲染配置信息表 (Info Table) - 递归平铺字典
    if (chartData.chart_info) {
        const infoRows = [];
        // 递归函数：把嵌套字典拍平成 Key-Value (修改版：不带父级前缀)
        const flattenDict = (obj) => {
            Object.keys(obj).forEach(key => {
                const val = obj[key];

                // 如果是字典，继续往里挖 (注意：这里不再传递 prefix 参数了)
                if (typeof val === 'object' && val !== null && !Array.isArray(val)) {
                    flattenDict(val);
                }
                // 如果是具体的值，直接保存
                else {
                    // 注意：这里只保存 [key, val]，不再加 prefix
                    infoRows.push([key, val]);
                }
            });
        };
        flattenDict(chartData.chart_info);

        const el = document.getElementById('infoTable');
        if (el) el.innerHTML = createDynamicTable(['Parameter', 'Value'], infoRows);
    }

    // 2. 渲染主宰星表 (Ruling Planets)
    if (chartData.kp_ruling) {
        const rData = chartData.kp_ruling;
        // 动态获取所有 Key
        const rows = Object.keys(rData).map(k => [k.replace(/_/g, ' '), rData[k]]);
        const el = document.getElementById('rulingTable');
        if (el) el.innerHTML = createDynamicTable(['Lord Type', 'Planet'], rows);
    }

    // 3. 渲染原有的 KP 表 (Planets & Houses)
    // 这里的逻辑复用原来的，但适配了上面的通用生成器
    if (chartData.kp_data) {
        const kpHeaders = ['Name', 'Sign', 'Position', 'Star', 'RL', 'NL', 'SL', 'SSL', 'Paada'];

        if (chartData.kp_data.planets && chartData.kp_data.planets.length > 0) {
            // 注意：这里传的是对象数组，createDynamicTable 会走进 else 分支
            document.getElementById('kpPlanetTable').innerHTML = createDynamicTable(kpHeaders, chartData.kp_data.planets);
        }
        if (chartData.kp_data.houses && chartData.kp_data.houses.length > 0) {
            document.getElementById('kpHouseTable').innerHTML = createDynamicTable(kpHeaders, chartData.kp_data.houses);
        }
    }

    // 4. 渲染行星象征星 (Planet Significators)
    // 数据结构: Su: {'A': [4], 'B': [4], 'C': [2, 7], 'D': [11]}
    if (chartData.kp_sigs && chartData.kp_sigs.planets) {
        const pSigs = chartData.kp_sigs.planets;
        const pKeys = Object.keys(pSigs); // 动态获取行星列表
        if (pKeys.length > 0) {
            // 动态获取列名 (A, B, C, D)
            const firstVal = pSigs[pKeys[0]];
            const levels = Object.keys(firstVal).sort(); // ['A', 'B', 'C', 'D']

            const headers = ['Planet', ...levels];
            const rows = pKeys.map(planet => {
                const rowData = [planet];
                levels.forEach(lvl => rowData.push(pSigs[planet][lvl]));
                return rowData;
            });

            const el = document.getElementById('sigPlanetTable');
            if (el) el.innerHTML = createDynamicTable(headers, rows);
        }
    }

    // 5. 渲染宫位象征星 (House Significators)
    // 数据结构: 1: {'Level-1': [], 'Level-2': [], ...}
    if (chartData.kp_sigs && chartData.kp_sigs.houses) {
        const hSigs = chartData.kp_sigs.houses;
        // 宫位Key可能是数字或字符串，做个排序
        const hKeys = Object.keys(hSigs).sort((a, b) => parseInt(a) - parseInt(b));

        if (hKeys.length > 0) {
            const firstVal = hSigs[hKeys[0]];
            const levels = Object.keys(firstVal).sort(); // ['Level-1', 'Level-2', ...]

            const headers = ['House', ...levels];
            const rows = hKeys.map(h => {
                const rowData = [h];
                levels.forEach(lvl => rowData.push(hSigs[h][lvl]));
                return rowData;
            });

            const el = document.getElementById('sigHouseTable');
            if (el) el.innerHTML = createDynamicTable(headers, rows);
        }
    }
};





// ============================================================
// [新增] 主绘图逻辑 (Main Chart Rendering)
// 移植自 Python chart.py，现在作为独立模块存在
// ============================================================
window.renderAstroChart = function (CHART_DATA) {
    // 1. 读取配置
    let STYLE = window.ASTRO_STYLE;
    if (!STYLE) {
        console.error("❌ 无法加载配置文件 window.ASTRO_STYLE");
        return;
    }

    // 2. 提取配置项
    const REGISTRY = STYLE.planetsRegistry;
    const COLORS = STYLE.colors;
    const RADII = STYLE.radii;
    const FONTS = STYLE.fonts;
    const SETTINGS = STYLE.settings || { collisionMinDist: 7.5, arcSpread: 0.09 };

    // 3. 初始化画布
    document.body.style.backgroundColor = COLORS.background;
    const canvas = document.getElementById('astroCanvas');
    if (!canvas) {
        console.error("❌ 找不到 ID 为 'astroCanvas' 的画布元素");
        return;
    }
    const ctx = canvas.getContext('2d', { alpha: false });

    // ============================================================
    // 渲染引擎内部函数
    // ============================================================

    // 辅助：获取星座颜色
    function getSignColor(signIdx) {
        const rem = signIdx % 4;
        if (rem === 0) return COLORS.elements.fire;
        if (rem === 1) return COLORS.elements.earth;
        if (rem === 2) return COLORS.elements.air;
        return COLORS.elements.water;
    }

    // 辅助：角度转换
    function deg2rad(deg) { return deg * (Math.PI / 180); }

    // 辅助：获取屏幕绘制角度 (以升宫为 180度/9点钟方向 为基准)
    function getScreenAngle(objLon) {
        const ascLon = CHART_DATA.asc_lon;
        // 修正逻辑：升宫 ASC 在左侧 (π)，逆时针排列
        return Math.PI + deg2rad(ascLon - objLon);
    }

    // 辅助：查表获取行星样式
    function getPlanetStyle(name) {
        const style = REGISTRY[name];
        if (style) return style;
        return { symbol: name[0], color: '#8b949e', visible: true };
    }

    // 核心：防碰撞算法 (V7 环形拓扑版)
    function solvePlanetCollisions(planets) {
        let active = planets.filter(p => getPlanetStyle(p.name).visible !== false);
        if (active.length === 0) return [];

        let pList = active.map(p => ({ ...p, render_lon: p.abs_lon })).sort((a, b) => a.render_lon - b.render_lon);
        const MIN_DIST = SETTINGS.collisionMinDist;
        let clusters = [];

        if (pList.length > 0) {
            let current = [pList[0]];
            clusters.push(current);
            for (let i = 1; i < pList.length; i++) {
                let prev = pList[i - 1];
                let curr = pList[i];
                if ((curr.render_lon - prev.render_lon) < MIN_DIST) {
                    current.push(curr);
                } else {
                    current = [curr];
                    clusters.push(current);
                }
            }
        }

        // 环形边界检测
        if (clusters.length > 1) {
            let firstC = clusters[0];
            let lastC = clusters[clusters.length - 1];
            let gap = (firstC[0].render_lon + 360) - lastC[lastC.length - 1].render_lon;
            if (gap < MIN_DIST) {
                firstC.forEach(p => p.render_lon += 360);
                let combined = lastC.concat(firstC);
                spreadCluster(combined, MIN_DIST);
                combined.forEach(p => p.render_lon %= 360);
                clusters.shift();
            }
        }

        clusters.forEach(c => spreadCluster(c, MIN_DIST));
        return pList;
    }

    function spreadCluster(cluster, minDist) {
        if (cluster.length <= 1) return;
        let sumLon = 0;
        cluster.forEach(p => sumLon += p.render_lon);
        let avgLon = sumLon / cluster.length;
        let totalSpan = (cluster.length - 1) * minDist;
        let startLon = avgLon - (totalSpan / 2);
        cluster.forEach((p, idx) => p.render_lon = startLon + (idx * minDist));
    }

    // 核心：绘图函数
    function draw() {
        // 重置矩阵并清空背景
        ctx.save();
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.fillStyle = COLORS.background;
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.restore();

        const ZONES = COLORS.zones || {};

        // 1. 绘制同心圆轨道
        drawCircle(RADII.r1, ZONES.outerRing);
        drawCircle(RADII.r3, ZONES.planetRing);
        drawCircle(RADII.r9, ZONES.innerDisk);
        drawCircle(RADII.r11, ZONES.centerCore);

        // 2. 绘制宫位分割线
        ctx.strokeStyle = COLORS.line;
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        CHART_DATA.houses.forEach(h => {
            const theta = getScreenAngle(h.abs_lon);
            ctx.moveTo(Math.cos(theta) * RADII.r3, Math.sin(theta) * RADII.r3);
            ctx.lineTo(Math.cos(theta) * RADII.r11, Math.sin(theta) * RADII.r11);
        });
        ctx.stroke();

        // 3. 绘制圆环边界线
        ctx.strokeStyle = COLORS.textMain;
        ctx.lineWidth = 2.0;
        [RADII.r1, RADII.r3, RADII.r9, RADII.r11].forEach(r => {
            ctx.beginPath();
            ctx.arc(0, 0, r, 0, Math.PI * 2);
            ctx.stroke();
        });

        // 4. 绘制宫头文字 (星座符号、度数)
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        const arcSpread = SETTINGS.arcSpread;

        CHART_DATA.houses.forEach(h => {
            const centerAngle = getScreenAngle(h.abs_lon);
            const z = h.zodiac;
            const eleColor = getSignColor(z.sign_idx);

            drawText(z.sign_sym, centerAngle, RADII.r2, FONTS.sign, eleColor);
            drawText(z.min + "′", centerAngle + arcSpread, RADII.r2, FONTS.base, COLORS.textDim);
            drawText(z.deg + '°', centerAngle - arcSpread, RADII.r2, FONTS.base, COLORS.textMain);
        });

        // 5. 绘制行星
        const renderPlanets = solvePlanetCollisions(CHART_DATA.planets);
        renderPlanets.forEach(p => {
            const angle = getScreenAngle(p.render_lon);
            const z = p.zodiac;
            const signColor = getSignColor(z.sign_idx);
            const style = getPlanetStyle(p.name);

            drawText(style.symbol, angle, RADII.r4, FONTS.planet, style.color);
            drawText(z.deg + '°', angle, RADII.r5, FONTS.base, COLORS.textMain);
            drawText(z.sign_sym, angle, RADII.r6, FONTS.sign, signColor);
            drawText(z.min + "′", angle, RADII.r7, FONTS.base, COLORS.textDim);
            if (p.is_retro) {
                drawText('R', angle, RADII.r8, 'bold 16px sans-serif', COLORS.retro);
            }
        });

        // 6. 绘制宫位编号 (中点)
        if (CHART_DATA.house_mids) {
            CHART_DATA.house_mids.forEach(hm => {
                drawText(hm.id, getScreenAngle(hm.lon), RADII.r10, FONTS.houseNum, COLORS.highlight);
            });
        }
    }

    // 基础绘图辅助：画圆
    function drawCircle(r, color) {
        ctx.beginPath();
        ctx.arc(0, 0, r, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();
    }

    // 基础绘图辅助：旋转文字
    function drawText(text, angle, radius, font, color) {
        ctx.save();
        ctx.font = font;
        ctx.fillStyle = color;
        ctx.rotate(angle);
        ctx.translate(radius, 0);
        ctx.rotate(-angle);
        ctx.fillText(text, 0, 0);
        ctx.restore();
    }

    // 响应式调整
    function resize() {
        const dpr = window.devicePixelRatio || 1;
        // 计算合适的大小 (取宽高的较小值，留 5% 边距)
        const size = Math.min(window.innerWidth, window.innerHeight * 0.95);

        canvas.width = size * dpr;
        canvas.height = size * dpr;
        canvas.style.width = size + 'px';
        canvas.style.height = size + 'px';

        // 坐标系归一化
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.translate(canvas.width / 2, canvas.height / 2);

        // 计算缩放比例 (基于 r1 外半径)
        const scaleFactor = (size * dpr / 2) / (RADII.r1 + 30);
        ctx.scale(scaleFactor, scaleFactor);

        draw();
    }

    // 绑定事件并初始调用
    window.addEventListener('resize', resize);
    resize();
};



/* ... (window.renderAstroChart 结束的大括号之后) ... */

// ============================================================
// [修改后] 渲染南印度方盘 (South Indian Chart)
// ============================================================
window.renderSouthIndianChart = function (chartData) {
    const container = document.getElementById('southIndianChart');
    if (!container) return;

    // 1. 准备容器
    let signsData = Array.from({ length: 12 }, () => []);

    // 辅助函数：将绝对经度转为 度°分′秒″ 格式
    function formatDMS(absLon) {
        // 计算在该星座内的相对度数 (0-30)
        let relativeDeg = absLon % 30;

        let d = Math.floor(relativeDeg);
        let mFloat = (relativeDeg - d) * 60;
        let m = Math.floor(mFloat);
        let s = Math.round((mFloat - m) * 60);

        // 处理进位 (例如 59.99秒 变成 60秒 -> 00秒, 分+1)
        if (s === 60) { s = 0; m += 1; }
        if (m === 60) { m = 0; d += 1; }

        // 补零
        const dd = d < 10 ? '0' + d : d;
        const mm = m < 10 ? '0' + m : m;
        const ss = s < 10 ? '0' + s : s;

        return `${dd}°${mm}′${ss}″`;
    }

    // 2. 填充行星 (记录 abs_lon 用于计算秒)
    chartData.planets.forEach(p => {
        signsData[p.zodiac.sign_idx].push({
            type: 'planet',
            name: p.name,
            abs_lon: p.zodiac.abs_lon // 必须要有这个字段
        });
    });

    // 3. 填充宫位
    const roman = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"];
    chartData.houses.forEach(h => {
        signsData[h.zodiac.sign_idx].push({
            type: 'house',
            name: roman[h.id - 1],
            abs_lon: h.zodiac.abs_lon
        });
    });

    // 4. 排序：按绝对度数取余30（即星座内度数）从大到小
    signsData.forEach(bucket => {
        bucket.sort((a, b) => (b.abs_lon % 30) - (a.abs_lon % 30));
    });

    // 5. 布局坐标 (固定不变)
    const layoutMap = [
        { idx: 11, r: 1, c: 1 }, { idx: 0, r: 1, c: 2 }, { idx: 1, r: 1, c: 3 }, { idx: 2, r: 1, c: 4 },
        { idx: 10, r: 2, c: 1 }, { idx: 3, r: 2, c: 4 },
        { idx: 9, r: 3, c: 1 }, { idx: 4, r: 3, c: 4 },
        { idx: 8, r: 4, c: 1 }, { idx: 7, r: 4, c: 2 }, { idx: 6, r: 4, c: 3 }, { idx: 5, r: 4, c: 4 }
    ];

    // 6. 生成 HTML
    let html = '';

    // [修改点] 中间留空，删除文字
    html += `<div class="si-center"></div>`;

    layoutMap.forEach(pos => {
        const signIndex = pos.idx;
        const items = signsData[signIndex];
        const styleStr = `grid-row: ${pos.r}; grid-column: ${pos.c};`;

        let contentHtml = '';
        items.forEach(item => {
            // [修改点] 调用新函数生成 秒 级精度
            const dmsStr = formatDMS(item.abs_lon);

            contentHtml += `
                <div class="si-item ${item.type}">
                    <span>${item.name}</span>
                    <span>${dmsStr}</span>
                </div>`;
        });

        // [修改点] 删除了 si-sign-name div
        html += `
        <div class="si-cell" style="${styleStr}">
            ${contentHtml}
        </div>`;
    });

    container.innerHTML = html;
};





// ============================================================
// [新增] 渲染相位表 (Aspect Tables - 下三角矩阵)
// ============================================================
window.renderAspectTables = function (chartData) {
    const container = document.getElementById('aspectsContainer');
    if (!container || !chartData.aspects) return;

    // 1. 获取基础配置列表 (从 Python 传来的 settings)
    // 如果 Python 没传，就用默认兜底
    const rawPlanets = chartData.settings?.selected_planets ||
        ['Su', 'Mo', 'Ma', 'Me', 'Ju', 'Ve', 'Sa', 'Ra', 'Ke'];
    const activeHouses = chartData.settings?.active_houses || [];

    // 辅助：获取显示符号
    const getSymbol = (name) => {
        // 如果是 house 1, house 10 这种格式
        if (name.startsWith('house')) {
            return name.replace('house ', ''); // 返回数字
        }
        // 如果是行星，查表
        if (window.ASTRO_STYLE.planetsRegistry[name]) {
            return window.ASTRO_STYLE.planetsRegistry[name].symbol;
        }
        return name; // 兜底
    };

    // 辅助：构建查找键 (p1, p2) -> "Su-Mo" (字母排序以保证唯一性)
    const makeKey = (p1, p2) => {
        return [p1, p2].sort().join('-');
    };

    // -------------------------------------------------------
    // 核心渲染器：根据模式数据和骨架列表生成 DOM
    // -------------------------------------------------------
    const buildMatrixHTML = (modeName, aspectList, axisItems) => {
        // 1. 建立数据索引表 Map<"Su-Mo", aspectObj>
        const dataMap = {};
        aspectList.forEach(item => {
            const k = makeKey(item.p1, item.p2);
            dataMap[k] = item;
        });

        let html = `<div class="aspect-mode-block">
            <div class="aspect-mode-title">✨ ${modeName}</div>`;

        // 2. 遍历生成行 (下三角逻辑)
        // 规则：
        // axisItems[i] 是当前行的“主角”。
        // 第一行 (i=0): [空] [主角0] (对角线)
        // 第二行 (i=1): [主角1] [数据0-1] [主角1] (对角线)
        // 第 N 行: [主角i] + (i个数据格) + [主角i]

        for (let i = 0; i < axisItems.length; i++) {
            const currentItem = axisItems[i]; // 当前行的行星
            const currentSym = getSymbol(currentItem);

            html += `<div class="aspect-row">`;

            // A. 左侧标签
            if (i === 0) {
                // 第一行左侧是空的 (First row first column is empty)
                html += `<div class="aspect-label empty-start"></div>`;
            } else {
                html += `<div class="aspect-label">${currentSym}</div>`;
            }

            // B. 中间数据单元格 (遍历之前的行星)
            // j 必须小于 i，形成下三角
            for (let j = 0; j < i; j++) {
                const targetItem = axisItems[j];
                const key = makeKey(currentItem, targetItem);
                const data = dataMap[key];

                if (data) {
                    // 有相位数据
                    let content = `<div class="aspect-symbol">${data.type}</div>`;

                    // 如果是容许度模式，且有度数信息
                    if (data.orb !== undefined) {
                        // 格式化度数 (不含秒)
                        // data.orb 是误差度数? 不，通常显示实际度数还是误差? 
                        // 需求说: "填上相位符号，如果是容许度模式，还要填上“度数”和“A/S”标志"
                        // 建议显示: error orb (误差) 或者 actual distance? 
                        // 通常相位表显示的是 "允许度内的误差" (Orb) 比如 6°06'

                        let degVal = Math.abs(data.orb);
                        let d = Math.floor(degVal);
                        let m = Math.floor((degVal - d) * 60);
                        let timeStr = `${d}°${m < 10 ? '0' + m : m}'`;

                        content += `<div class="aspect-deg">${timeStr} ${data.state || ''}</div>`;
                    }

                    html += `<div class="aspect-cell aspect-data-cell">${content}</div>`;
                } else {
                    // 无相位 (空子)
                    html += `<div class="aspect-cell aspect-data-cell" style="background:#0d1117"></div>`;
                }
            }

            // C. 右侧对角线标签 (每一行最后都有)
            html += `<div class="aspect-label">${currentSym}</div>`;

            html += `</div>`; // End row
        }

        html += `</div>`; // End block
        return html;
    };

    // -------------------------------------------------------
    // 根据数据动态调用
    // -------------------------------------------------------

    // 1. Orb Mode (容许度模式)
    if (chartData.aspects.orb) {
        // 骨架 = 行星列表 + 激活的宫位
        // 注意：activeHouses 是数字数组 [1, 5, 10]，需要转成 "house 1" 格式以匹配 data
        const houseKeys = activeHouses.map(h => `house ${h}`);
        const skeleton = [...rawPlanets, ...houseKeys];

        container.innerHTML += buildMatrixHTML("Orb Mode (容许度)", chartData.aspects.orb, skeleton);
    }

    // 2. Whole Sign Mode (整宫制)
    if (chartData.aspects.whole_sign) {
        // 骨架 = 仅行星
        container.innerHTML += buildMatrixHTML("Whole Sign (整宫制)", chartData.aspects.whole_sign, rawPlanets);
    }

    // 3. Vedic Mode (印度模式)
    if (chartData.aspects.vedic) {
        // 骨架 = 仅行星
        container.innerHTML += buildMatrixHTML("Vedic (印度模式)", chartData.aspects.vedic, rawPlanets);
    }
};