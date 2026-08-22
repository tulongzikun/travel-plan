// Leaflet 地图引擎。纯函数（buildNavLink/buildMapAppLinks/buildAmapDayMarkersLinks/routeCoordinates/
// gcj02ToWgs84/wgs84ToGcj02/normalizeStays）可单元测试；
// initTravelMap 需浏览器 + Leaflet (L)。浏览器与 Node 双用。

// HTML 转义，防止 XSS
function escapeHTML(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// 生成跳转手机地图导航的链接。
// iOS 不识别 geo: scheme，用 Apple Maps 的 https 通用链接；其余平台用 geo:。
// ua 可选（浏览器里传 navigator.userAgent），不传则回退 geo:。
function buildNavLink(lat, lng, label, ua) {
  if (ua && /iPhone|iPad|iPod/.test(ua)) {
    return 'https://maps.apple.com/?ll=' + lat + ',' + lng + '&q=' + encodeURIComponent(label);
  }
  return 'geo:' + lat + ',' + lng + '?q=' + lat + ',' + lng + '(' + encodeURIComponent(label) + ')';
}

// 常用地图 App 的点位链接（免 key 的官方 URI 规范：高德 URI API、Google Maps URLs）。
// 这不是 page-contract 的 actionLink——不承载实时数据主张，只是"打开地图看这个点"。
// 境内点只给高德（Google 地图境内不可用、底图坐标系还会偏移）；境外点给 Google + 高德。
// 输入坐标一律 WGS-84：高德 URI 用 coordinate=wgs84 声明由其换算，Google 本身即 WGS-84。
// isInChinaBBox 声明在下方 GCJ 区块（函数声明有提升，此处可用）。
function buildMapAppLinks(lat, lng, label) {
  var amap = {
    label: '高德地图',
    url: 'https://uri.amap.com/marker?position=' + lng + ',' + lat
      + '&name=' + encodeURIComponent(label)
      + '&coordinate=wgs84&callnative=1&src=travel-plan-viz',
  };
  var google = {
    label: 'Google 地图',
    url: 'https://www.google.com/maps/search/?api=1&query=' + encodeURIComponent(lat + ',' + lng),
  };
  return isInChinaBBox(lat, lng) ? [amap] : [google, amap];
}

// 「高德打开当日点位」链接（免 key 官方多点标注 URI：uri.amap.com/marker?markers=…）。
// 高德路书无公开创建接口，这是官方通道里最接近"带着整天点位去高德"的能力：
//   - markers 最多 10 点/链接（官方文档上限），超出自动按序切块，返回多条；
//   - 每点可带名称（/,/ 和 /|/ 是分隔符，名称里出现会被替换成空格，防串位）；
//   - 该 URI 无 coordinate 参数（默认 GCJ-02），坐标先经 wgs84ToGcj02 转换；
//   - 进高德后只是带名称的点位集合（无连线），想存路书须在高德内收藏或手动创建。
// points: [{lat, lng, name}]（按行程顺序，WGS-84）；残缺/非数值坐标的条目跳过。
// 返回 [{url, count, first, last}]（first/last 为该块覆盖的原数组下标，从 0 计），无有效点返回 []。
var AMAP_MARKERS_MAX = 10;

function buildAmapDayMarkersLinks(points) {
  var valid = (Array.isArray(points) ? points : []).filter(function (p) {
    return p && typeof p.lat === 'number' && isFinite(p.lat)
      && typeof p.lng === 'number' && isFinite(p.lng);
  });
  var links = [];
  for (var start = 0; start < valid.length; start += AMAP_MARKERS_MAX) {
    var chunk = valid.slice(start, start + AMAP_MARKERS_MAX);
    var markers = chunk.map(function (p) {
      var gcj = wgs84ToGcj02(p.lat, p.lng);
      var name = String(p.name || '').replace(/[,|]/g, ' ').trim();
      return gcj.lng.toFixed(6) + ',' + gcj.lat.toFixed(6)
        + (name ? ',' + encodeURIComponent(name) : '');
    }).join('|');
    links.push({
      url: 'https://uri.amap.com/marker?markers=' + markers
        + '&src=travel-plan-viz&callnative=1',
      count: chunk.length,
      first: start,
      last: start + chunk.length - 1,
    });
  }
  return links;
}

// —— GCJ-02 → WGS-84 坐标转换 ——
// 高德/腾讯地图返回的坐标是 GCJ-02（国测局加密），直接画在 OSM（WGS-84）瓦片上
// 会偏移一百到几百米。凡坐标来自高德/腾讯类 skill，必须先经此函数转换。
// 中国境外坐标原样返回（GCJ-02 仅在境内加偏）。
var GCJ_A = 6378245.0;
var GCJ_EE = 0.00669342162296594323;

function isInChinaBBox(lat, lng) {
  return lng >= 72.004 && lng <= 137.8347 && lat >= 0.8293 && lat <= 55.8271;
}

function gcjTransformLat(x, y) {
  var ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * Math.sqrt(Math.abs(x));
  ret += (20.0 * Math.sin(6.0 * x * Math.PI) + 20.0 * Math.sin(2.0 * x * Math.PI)) * 2.0 / 3.0;
  ret += (20.0 * Math.sin(y * Math.PI) + 40.0 * Math.sin(y / 3.0 * Math.PI)) * 2.0 / 3.0;
  ret += (160.0 * Math.sin(y / 12.0 * Math.PI) + 320.0 * Math.sin(y * Math.PI / 30.0)) * 2.0 / 3.0;
  return ret;
}

function gcjTransformLng(x, y) {
  var ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * Math.sqrt(Math.abs(x));
  ret += (20.0 * Math.sin(6.0 * x * Math.PI) + 20.0 * Math.sin(2.0 * x * Math.PI)) * 2.0 / 3.0;
  ret += (20.0 * Math.sin(x * Math.PI) + 40.0 * Math.sin(x / 3.0 * Math.PI)) * 2.0 / 3.0;
  ret += (150.0 * Math.sin(x / 12.0 * Math.PI) + 300.0 * Math.sin(x / 30.0 * Math.PI)) * 2.0 / 3.0;
  return ret;
}

function gcj02ToWgs84(lat, lng) {
  if (!isInChinaBBox(lat, lng)) return { lat: lat, lng: lng };
  var dLat = gcjTransformLat(lng - 105.0, lat - 35.0);
  var dLng = gcjTransformLng(lng - 105.0, lat - 35.0);
  var radLat = lat / 180.0 * Math.PI;
  var magic = Math.sin(radLat);
  magic = 1 - GCJ_EE * magic * magic;
  var sqrtMagic = Math.sqrt(magic);
  dLat = (dLat * 180.0) / ((GCJ_A * (1 - GCJ_EE)) / (magic * sqrtMagic) * Math.PI);
  dLng = (dLng * 180.0) / (GCJ_A / sqrtMagic * Math.cos(radLat) * Math.PI);
  return { lat: lat - dLat, lng: lng - dLng };
}

// —— WGS-84 → GCJ-02 坐标转换 ——
// gcj02ToWgs84 的逆变换：在 WGS 点处求偏移量再加回（与正向同为单次近似，往返误差米级，
// 对锚点/导航吸附足够）。高德导航 URI 与多点标注 URI 的参数表均无 coordinate 参数
// （默认即 GCJ-02），所以这两个通道的坐标必须先经此函数转换。
// 中国境外坐标原样返回（GCJ-02 仅在境内加偏）。
function wgs84ToGcj02(lat, lng) {
  if (!isInChinaBBox(lat, lng)) return { lat: lat, lng: lng };
  var dLat = gcjTransformLat(lng - 105.0, lat - 35.0);
  var dLng = gcjTransformLng(lng - 105.0, lat - 35.0);
  var radLat = lat / 180.0 * Math.PI;
  var magic = Math.sin(radLat);
  magic = 1 - GCJ_EE * magic * magic;
  var sqrtMagic = Math.sqrt(magic);
  dLat = (dLat * 180.0) / ((GCJ_A * (1 - GCJ_EE)) / (magic * sqrtMagic) * Math.PI);
  dLng = (dLng * 180.0) / (GCJ_A / sqrtMagic * Math.cos(radLat) * Math.PI);
  return { lat: lat + dLat, lng: lng + dLng };
}

// 从有序点位提取 [lat,lng] 数组，用于连线
function routeCoordinates(points) {
  return points.map(function (p) { return [p.lat, p.lng]; });
}

// 住宿锚点过滤：只留 name 与数值 lat/lng 齐全的条目（城区级近似坐标，缺坐标的片区直接跳过，不猜）。
// stays: [{lat, lng, name, note?}]
function normalizeStays(stays) {
  if (!Array.isArray(stays)) return [];
  return stays.filter(function (s) {
    return s && typeof s.name === 'string' && s.name
      && typeof s.lat === 'number' && isFinite(s.lat)
      && typeof s.lng === 'number' && isFinite(s.lng);
  });
}

// 初始化地图：编号 divIcon 标记、按序虚线路线、点击弹出 名称+时间+导航链接。
// elementId: 容器 id；points: [{lat, lng, name, time}]（按行程顺序，坐标须为 WGS-84）
// opts 可选：{ tileUrl, attribution } 替换默认 OSM 瓦片源（如 OSM 访问不稳时换镜像）；
//   { stays } 住宿片区锚点 [{lat, lng, name, note?}]，画 🏨 标记（不编号、不进路线），
//   缺数值坐标的条目会被 normalizeStays 跳过——锚点是城区级近似，宁缺勿猜。
function initTravelMap(elementId, points, opts) {
  opts = opts || {};
  var map = L.map(elementId);
  L.tileLayer(opts.tileUrl || 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: opts.attribution || '© OpenStreetMap contributors',
    maxZoom: 19,
  }).addTo(map);

  var ua = (typeof navigator !== 'undefined' && navigator.userAgent) || '';
  points.forEach(function (p, i) {
    var icon = L.divIcon({
      className: 'route-pin',
      html: '<span class="route-pin__num">' + (i + 1) + '</span>',
      iconSize: [28, 28],
      iconAnchor: [14, 14],
    });
    var navLinks = [{ label: '导航', url: buildNavLink(p.lat, p.lng, p.name, ua) }]
      .concat(buildMapAppLinks(p.lat, p.lng, p.name));
    L.marker([p.lat, p.lng], { icon: icon }).addTo(map).bindPopup(
      '<b>' + (i + 1) + '. ' + escapeHTML(p.name) + '</b><br>'
      + (p.time ? escapeHTML(p.time) + '<br>' : '')
      + navLinks.map(function (l) {
          return '<a href="' + l.url + '">' + escapeHTML(l.label) + '</a>';
        }).join(' · ')
    );
  });

  normalizeStays(opts.stays).forEach(function (s) {
    var icon = L.divIcon({
      className: 'route-pin route-pin--stay',
      html: '<span class="route-pin__num">🏨</span>',
      iconSize: [28, 28],
      iconAnchor: [14, 14],
    });
    var navLinks = [{ label: '导航', url: buildNavLink(s.lat, s.lng, s.name, ua) }]
      .concat(buildMapAppLinks(s.lat, s.lng, s.name));
    L.marker([s.lat, s.lng], { icon: icon }).addTo(map).bindPopup(
      '<b>🏨 ' + escapeHTML(s.name) + '</b><br>'
      + (s.note ? escapeHTML(s.note) + '<br>' : '')
      + navLinks.map(function (l) {
          return '<a href="' + l.url + '">' + escapeHTML(l.label) + '</a>';
        }).join(' · ')
    );
  });

  var coords = routeCoordinates(points);
  if (coords.length > 1) {
    L.polyline(coords, { dashArray: '6 8', weight: 2 }).addTo(map);
  }
  // 住宿锚点只参与视野适配，不进路线连线（片区近似坐标，连线会误导）
  var allCoords = coords.concat(normalizeStays(opts.stays).map(function (s) { return [s.lat, s.lng]; }));
  map.fitBounds(allCoords.length ? allCoords : [[0, 0]], { padding: [30, 30] });
  return map;
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    buildNavLink: buildNavLink,
    buildMapAppLinks: buildMapAppLinks,
    buildAmapDayMarkersLinks: buildAmapDayMarkersLinks,
    routeCoordinates: routeCoordinates,
    gcj02ToWgs84: gcj02ToWgs84,
    wgs84ToGcj02: wgs84ToGcj02,
    normalizeStays: normalizeStays,
    initTravelMap: initTravelMap,
  };
}
