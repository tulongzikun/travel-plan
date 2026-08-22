const { test } = require('node:test');
const assert = require('node:assert');
const { buildNavLink, buildMapAppLinks, buildAmapDayMarkersLinks, routeCoordinates, gcj02ToWgs84, wgs84ToGcj02, normalizeStays } = require('../travel-plan-viz/assets/map.js');

// 注：initTravelMap 依赖浏览器 + Leaflet，单测只覆盖纯函数，地图初始化由端到端手动验证。

test('buildNavLink 默认（无 ua）生成带 label 的 geo 链接', () => {
  const link = buildNavLink(31.23, 121.47, '外滩');
  assert.strictEqual(link, 'geo:31.23,121.47?q=31.23,121.47(%E5%A4%96%E6%BB%A9)');
});

test('buildNavLink 在 iOS ua 下生成 Apple Maps https 链接（iOS 不识别 geo:）', () => {
  const ua = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15';
  const link = buildNavLink(31.23, 121.47, '外滩', ua);
  assert.strictEqual(link, 'https://maps.apple.com/?ll=31.23,121.47&q=%E5%A4%96%E6%BB%A9');
});

test('buildNavLink 在 Android ua 下仍用 geo 链接', () => {
  const ua = 'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36';
  const link = buildNavLink(31.23, 121.47, '外滩', ua);
  assert.ok(link.startsWith('geo:31.23,121.47'));
});

test('buildMapAppLinks 境内点只给高德，position 须为 lng,lat 序且声明 wgs84', () => {
  const links = buildMapAppLinks(39.90923, 116.397428, '故宫');
  assert.strictEqual(links.length, 1);
  assert.strictEqual(links[0].label, '高德地图');
  // position 参数是 经度,纬度（写反点位会飘到别处）
  assert.ok(links[0].url.startsWith('https://uri.amap.com/marker?position=116.397428,39.90923&'), links[0].url);
  assert.ok(links[0].url.includes('coordinate=wgs84'));
  assert.ok(links[0].url.includes('callnative=1'));
  assert.ok(links[0].url.includes('name=%E6%95%85%E5%AE%AB'));
});

test('buildMapAppLinks 境外点给 Google 地图在前、高德在后', () => {
  const links = buildMapAppLinks(35.6595, 139.7005, '涩谷');
  assert.deepStrictEqual(links.map((l) => l.label), ['Google 地图', '高德地图']);
  assert.strictEqual(links[0].url, 'https://www.google.com/maps/search/?api=1&query=35.6595%2C139.7005');
  assert.ok(links[1].url.includes('position=139.7005,35.6595'));
});

test('routeCoordinates 按顺序提取 [lat,lng]', () => {
  const out = routeCoordinates([
    { lat: 1, lng: 2, name: 'A' },
    { lat: 3, lng: 4, name: 'B' },
  ]);
  assert.deepStrictEqual(out, [[1, 2], [3, 4]]);
});

test('normalizeStays 留下 name+数值坐标齐全的锚点，滤掉残缺与非数组输入', () => {
  const out = normalizeStays([
    { name: '北留镇', lat: 35.505, lng: 112.585, note: '皇城相府旁' },
    { name: '缺坐标的片区' },
    { name: '缺经度', lat: 35.5 },
    { lat: 35.5, lng: 112.5 }, // 缺 name
    { name: '坐标非数字', lat: '35.5', lng: 112.5 },
  ]);
  assert.strictEqual(out.length, 1);
  assert.strictEqual(out[0].name, '北留镇');
  assert.deepStrictEqual(normalizeStays(undefined), []);
  assert.deepStrictEqual(normalizeStays(null), []);
});

test('gcj02ToWgs84 对境内坐标做百米级纠偏（天安门）', () => {
  // GCJ-02 的天安门（高德坐标），转 WGS-84 后应向西南偏约 0.002–0.007°
  const { lat, lng } = gcj02ToWgs84(39.90875, 116.39723);
  const dLat = 39.90875 - lat;
  const dLng = 116.39723 - lng;
  assert.ok(dLat > 0.001 && dLat < 0.01, `lat 偏移量异常: ${dLat}`);
  assert.ok(dLng > 0.001 && dLng < 0.01, `lng 偏移量异常: ${dLng}`);
});

test('gcj02ToWgs84 对境外坐标原样返回（东京）', () => {
  assert.deepStrictEqual(gcj02ToWgs84(35.6595, 139.7005), { lat: 35.6595, lng: 139.7005 });
});

test('wgs84ToGcj02 对境内坐标做百米级加偏，境外原样返回', () => {
  // WGS-84 的天安门，转 GCJ-02 后应向东北偏约 0.002–0.007°
  const { lat, lng } = wgs84ToGcj02(39.90655, 116.39135);
  assert.ok(lat - 39.90655 > 0.001 && lat - 39.90655 < 0.01, `lat 偏移量异常: ${lat - 39.90655}`);
  assert.ok(lng - 116.39135 > 0.001 && lng - 116.39135 < 0.01, `lng 偏移量异常: ${lng - 116.39135}`);
  assert.deepStrictEqual(wgs84ToGcj02(35.6595, 139.7005), { lat: 35.6595, lng: 139.7005 });
});

test('wgs84ToGcj02 与 gcj02ToWgs84 互逆（往返误差米级）', () => {
  // 长治市区一带：WGS→GCJ→WGS 应回到原点附近（同为单次近似，容差 1e-4° ≈ 11m）
  const gcj = wgs84ToGcj02(36.2, 113.11);
  const back = gcj02ToWgs84(gcj.lat, gcj.lng);
  assert.ok(Math.abs(back.lat - 36.2) < 1e-4, `lat 往返误差: ${Math.abs(back.lat - 36.2)}`);
  assert.ok(Math.abs(back.lng - 113.11) < 1e-4, `lng 往返误差: ${Math.abs(back.lng - 113.11)}`);
});

test('buildAmapDayMarkersLinks 拼多点标注 URI：markers 为 lng,lat,名称（GCJ-02）', () => {
  const links = buildAmapDayMarkersLinks([
    { lat: 36.2, lng: 113.11, name: '上党门' },
    { lat: 35.505, lng: 112.585, name: '北留镇' },
  ]);
  assert.strictEqual(links.length, 1);
  const url = links[0].url;
  assert.ok(url.startsWith('https://uri.amap.com/marker?markers='), url);
  assert.ok(url.includes('&src=travel-plan-viz&callnative=1'), url);
  // 境内点必须已转 GCJ-02（不能原样出现 WGS 坐标对），名称须 URL 编码
  assert.ok(!url.includes('113.110000,36.200000') && !url.includes('112.585000,35.505000'), url);
  assert.ok(url.includes(encodeURIComponent('上党门')), url);
  // 块元数据：覆盖下标 0–1
  assert.deepStrictEqual(
    { count: links[0].count, first: links[0].first, last: links[0].last },
    { count: 2, first: 0, last: 1 },
  );
});

test('buildAmapDayMarkersLinks 超过 10 点按序切块（官方单链接上限 10 点）', () => {
  const points = Array.from({ length: 13 }, (_, i) => ({ lat: 35 + i * 0.01, lng: 112 + i * 0.01, name: 'P' + i }));
  const links = buildAmapDayMarkersLinks(points);
  assert.strictEqual(links.length, 2);
  assert.deepStrictEqual(
    links.map((l) => [l.count, l.first, l.last]),
    [[10, 0, 9], [3, 10, 12]],
  );
  // 两块各自的 markers 都不超过 10 个点
  links.forEach((l) => {
    const markers = decodeURIComponent(l.url.split('markers=')[1].split('&')[0]);
    assert.ok(markers.split('|').length === l.count, l.url);
  });
});

test('buildAmapDayMarkersLinks 名称中的分隔符被替换，残缺点位被跳过', () => {
  const links = buildAmapDayMarkersLinks([
    { lat: 36.2, lng: 113.11, name: 'A,B|C' },      // 名称含分隔符
    { lat: 35.5, name: '缺经度' },                    // 残缺，跳过
    { lng: 112.5, name: '缺纬度' },                   // 残缺，跳过
    { lat: 35.505, lng: 112.585 },                    // 无名称，只给坐标
  ]);
  assert.strictEqual(links.length, 1);
  const markers = links[0].url.split('markers=')[1].split('&src=')[0];
  assert.strictEqual(markers.split('|').length, 2, links[0].url);
  assert.ok(!markers.includes('A%2CB'), markers);       // 逗号被换成空格，不得原样编码出现
  assert.ok(markers.includes(encodeURIComponent('A B C')), markers);
  // 第二点无名称：条目就是"lng,lat"两段
  const second = markers.split('|')[1];
  assert.ok(/^\d+\.\d{6},\d+\.\d{6}$/.test(second), second);
});

test('buildAmapDayMarkersLinks 全残缺或非数组输入返回空数组', () => {
  assert.deepStrictEqual(buildAmapDayMarkersLinks([]), []);
  assert.deepStrictEqual(buildAmapDayMarkersLinks(undefined), []);
  assert.deepStrictEqual(buildAmapDayMarkersLinks(null), []);
  assert.deepStrictEqual(buildAmapDayMarkersLinks([{ name: '无坐标' }]), []);
});
