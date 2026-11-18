/* Captions in part.evidence. The same manual, photo set or package drawing
 * can support many parts. Translate the captions once; copy the actual URLs,
 * IMG references, drawing callouts, pixel locations and checksums from source.
 */
(() => {
  'use strict';

  const captions = new Map();
  function caption(source, ru, en, zh) {
    captions.set(source, {ru, en, 'zh-CN': zh});
  }
  function fromEn(en, ru, zh) {
    caption(en, ru, en, zh);
  }
  function fromRu(ru, en, zh) {
    caption(ru, ru, en, zh);
  }

  // Manual, patent views and product photographs.
  fromEn('XKAH Pro User Manual, printed pp.03–04 (PDF pp.6–7)',
    'Руководство пользователя XKAH Pro, с. 03–04 печатного издания (с. 6–7 PDF)',
    '《XKAH Pro 用户手册》，印刷版第 03–04 页（PDF 第 6–7 页）');
  fromEn('XKAH Pro User Manual', 'Руководство пользователя XKAH Pro', '《XKAH Pro 用户手册》');
  fromEn('pp.04–05', 'с. 04–05', '第 04–05 页');
  fromEn('p.04', 'с. 04', '第 04 页');
  fromEn('p.05', 'с. 05', '第 05 页');
  fromEn('Figs.', 'рис. ', '图 ');
  caption('立体图1', 'вид в перспективе 1', 'perspective view 1', '立体图1');

  fromEn('XKAH Pro US gallery ', 'XKAH Pro, галерея США, фото ', 'XKAH Pro 美国站产品图 ');
  fromEn('XKAH US gallery ', 'XKAH, галерея США, фото ', 'XKAH 美国站产品图 ');
  fromEn('XKAH Pro, gallery 4', 'XKAH Pro, фото 4 из галереи', 'XKAH Pro 产品图 4');
  fromEn('gallery 3', 'фото 3 из галереи', '产品图 3');
  fromEn('XKAH US Replacement Base, Graphite/Blue',
    'Сменное основание XKAH (США), графитовое/синее', 'XKAH 美国站替换底座，石墨色/蓝色');
  fromEn('XKAH US', 'XKAH (США)', 'XKAH 美国站');
  fromEn('XYKA product image', 'фото изделия XYKA', 'XYKA 产品图');
  fromEn('XYKA rear/underside image', 'XYKA, вид сзади/снизу', 'XYKA 后视/仰视图');
  fromEn('XYKA left profile', 'XYKA, вид слева', 'XYKA 左视图');
  fromEn('XYKA Graphite', 'XYKA, графитовый вариант', '石墨色 XYKA');
  fromEn('XYKA Silver', 'XYKA, серебристый вариант', '银色 XYKA');
  fromEn('(front, three-quarter and side)', '(спереди, в три четверти и сбоку)', '（正面、四分之三角度和侧面）');
  fromEn('(front)', '(вид спереди)', '（正面）');
  fromEn('graphite and silver regional front views 01 (1500²)',
    'региональные изображения 01 (1500²), вид спереди в графитовом и серебристом цветах',
    '地区产品图 01（1500²），石墨色和银色正视图');
  fromEn('actual XYKA / triangular A',
    'фактическая надпись XYKA / треугольная буква A', '实物上的“XYKA”字样 / 三角形的字母 A');
  fromEn('FAQ', 'раздел вопросов и ответов', '常见问题');

  // Owner's specimen versus comparison devices, retailer images and teardowns.
  fromEn('Owner A4.3/20260305A', 'A4.3/20260305A владельца', '机主的 A4.3/20260305A');
  fromEn('Owner ', 'Фото владельца: ', '机主照片：');
  fromRu('описание владельца §4', 'owner’s description, §4', '机主描述，§4');
  fromRu('уточнение владельца', 'clarification from the owner', '机主补充说明');
  fromRu('00_START_HERE §4, владелец', '00_START_HERE §4, owner', '00_START_HERE §4，机主说明');
  fromRu('два сквозных отверстия', 'two through-holes', '两个通孔');
  fromEn('September teardown', 'сентябрьская разборка', '9 月拆解记录');
  fromEn('September album, photos 6, 12, 16–17',
    'сентябрьский альбом, фото 6, 12, 16–17', '9 月相册，照片 6、12、16–17');
  fromEn('album 1xat220, image 3', 'альбом 1xat220, фото 3', '相册 1xat220，照片 3');
  fromEn('steps 1/4; images 1, 7, 8', 'шаги 1/4; фото 1, 7, 8', '步骤 1/4；照片 1、7、8');
  fromEn('detached trim:', 'снятая накладка:', '拆下的饰面片：');
  fromEn('(image 8)', '(фото 8)', '（照片 8）');
  fromRu('три стрелки', 'three arrows', '三个箭头');
  fromRu('выступ под передней кромкой', 'projection under the front edge', '前缘下方的凸起');
  fromRu('для сравнения:', 'for comparison:', '对照图：');

  fromEn('XYKA cutaway with pod raised', 'разрез XYKA с приподнятой чашей', 'XYKA 剖视图，烟锅已提起');
  fromEn('Regional XYKA mech_xy01: black XYKA on the near side of the metal pod below the rolled rim',
    'Региональное фото XYKA mech_xy01: чёрная надпись XYKA на ближней стороне металлической чаши под завальцованным краем',
    '地区产品图 XYKA mech_xy01：金属烟锅的近侧、卷边下方可见黑色“XYKA”字样');
  fromEn('mech_xy05 shows a DIFFERENT side/orientation. Exact clocking, finish and identity of the owner’s pod are UNKNOWN.',
    'На mech_xy05 видна ДРУГАЯ сторона/ориентация. Точная угловая ориентация, отделка и соответствие чаше владельца неизвестны (UNKNOWN).',
    'mech_xy05 展示的是另一侧或另一朝向。周向角度、表面处理及是否与机主的烟锅相同均未知（UNKNOWN）。');

  // Battery video and regional label. The optical field is a photographic
  // reference, not a payload to decode. Keep the unmodified file/hash tokens.
  fromRu('XYKA «Комплектация и распаковка»', 'XYKA, “Package contents and unboxing”', 'XYKA《包装清单与开箱》');
  fromRu('исходный 3840×2160', 'source resolution 3840×2160', '原始分辨率 3840×2160');
  fromEn('XYKA regional battery', 'региональная версия аккумулятора XYKA', 'XYKA 地区版电池');
  fromEn('supplied regional-1.webp, front elevation. The other two regional views do not supply additional lettering.',
    'предоставленное изображение regional-1.webp, вид спереди. На двух других региональных видах дополнительных надписей нет.',
    '所提供的 regional-1.webp，正视图。其余两张地区版视图未提供更多文字。');

  // Main board: registration, visible joints and package shape comparisons.
  fromEn('projected mask edges, not Gerber data',
    'проекция кромок паяльной маски, не данные Gerber', '阻焊层边缘的投影，并非 Gerber 数据');
  fromEn('10 independent solder joints, owner colour correction',
    '10 отдельных паяных соединений; цвет уточнён владельцем', '10 个独立焊点；颜色经机主校正');
  fromEn('rectified soldermask plane', 'плоскость паяльной маски после устранения перспективы', '经透视校正的阻焊层平面');
  fromEn('Artery DS_AT32F421 v2.02 §6.5, fig.32 / table 50, pp.65–66',
    'Artery DS_AT32F421 v2.02 §6.5, рис. 32 / табл. 50, с. 65–66',
    'Artery DS_AT32F421 v2.02 §6.5，图 32 / 表 50，第 65–66 页');
  fromEn('Hongchip QA-DT-176 rev.1.1, §9.1 p.84, §10 pp.90–91',
    'Hongchip QA-DT-176, ред. 1.1, §9.1 с. 84, §10 с. 90–91',
    'Hongchip QA-DT-176 修订版 1.1，§9.1 第 84 页，§10 第 90–91 页');
  caption('аналог геометрии, Nexperia SOT89 fig.1',
    'аналог геометрии, Nexperia SOT89 рис. 1',
    'shape comparison, Nexperia SOT89 fig. 1', '形状参照：Nexperia SOT89 图 1');
  caption('аналог SMA (DO-214AC), Vishay 88746 p.4',
    'аналог SMA (DO-214AC), Vishay 88746 с. 4',
    'SMA (DO-214AC) comparison, Vishay 88746 p. 4', 'SMA（DO-214AC）对照封装，Vishay 88746 第 4 页');
  caption('аналог Nexperia SOT23 fig.1',
    'аналог Nexperia SOT23, рис. 1', 'Nexperia SOT23 comparison, fig. 1', '参照 Nexperia SOT23 图 1');
  fromEn('Nexperia SO8 SOT96-1 fig.1', 'Nexperia SO8 SOT96-1, рис. 1', 'Nexperia SO8 SOT96-1 图 1');
  fromRu('Типовой корпус, не идентификация микросхемы',
    'Typical package, not an identification of the IC', '典型封装，并非对芯片型号的鉴定');
  fromRu('внешняя форма по фото', 'external shape from photographs', '外形依据照片');
  fromEn('ROI x835:973 y764:910', 'область (ROI) x835:973 y764:910', '感兴趣区域（ROI）x835:973 y764:910');
  fromEn('four-way side-entry plug', 'четырёхконтактный штекер с боковым вводом', '侧插式四位插头');
  fromEn('actual brand and pinout UNKNOWN',
    'марка и распиновка неизвестны (UNKNOWN)', '实际品牌和引脚定义未知（UNKNOWN）');

  // Display PCB, optical layers and flex. The spaced and unspaced image
  // shorthands in the source remain as written; neither implies a new file.
  fromEn('rectified on round contacts and PCB rails',
    'перспектива исправлена по круглым контактам и боковым кромкам платы', '以圆形触点和电路板侧边为基准进行透视校正');
  fromEn('IMG_8917 independent view', 'IMG_8917 — независимый ракурс', 'IMG_8917 为另一独立视角');
  fromEn('silhouette against main carrier', 'силуэт на фоне основного держателя', '以主支架为背景可见的轮廓');
  fromEn('far LCD/PCB ends cropped in 8917/18',
    'дальние концы LCD и платы обрезаны на 8917/18', '8917/18 的画面裁掉了 LCD 与电路板的远端');
  fromEn('two original macro views', 'два исходных макроснимка', '两张原始微距照片');
  fromEn('estimated from ~3 × 4 mm tactile case, type UNKNOWN',
    'оценка по корпусу тактовой кнопки ~3 × 4 мм, тип неизвестен (UNKNOWN)',
    '依据约 3 × 4 mm 的轻触开关封装估算，型号未知（UNKNOWN）');
  caption('Владелец: силиконовая прокладка на кнопках 20260305A',
    'Владелец: силиконовая прокладка на кнопках 20260305A',
    'Owner: silicone membrane over the pushbuttons on 20260305A',
    '据机主描述：20260305A 的按钮上覆盖有硅胶垫');
  caption('Displaymodul, dim_deui.jpg',
    'раздел «Displaymodul» (модуль дисплея), dim_deui.jpg',
    '“Displaymodul” (display module), dim_deui.jpg',
    '“Displaymodul”（显示模块）一节，dim_deui.jpg');
  fromRu('нижняя вырезка того же фото', 'crop from the bottom of the same photo', '同一照片下部的裁剪图');
  fromRu('без прокладки.', 'without the membrane.', '未装硅胶垫。');
  fromEn('oblique layer edges', 'кромки слоёв под косым углом', '从斜向看到的各层边缘');
  fromEn('confirms closely stacked boards', 'подтверждает тесное расположение плат в стопке', '证实两板紧密叠放');
  fromEn('comparison:', 'для сравнения:', '对照图：');
  fromEn('image 8 (glass, rim, flex)', 'фото 8 (стекло, ободок, шлейф)', '照片 8（玻璃、边框、柔性排线）');
  fromEn('image 8 (detached trim)', 'фото 8 (снятая накладка)', '照片 8（拆下的饰面片）');

  // A single pass is important: a translated title is never translated again.
  // URLs have first priority; even an English word inside a path or query is
  // part of its literal address. Prefer a long caption to a shorter prefix.
  const literal = text => text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const lookup = [...captions.keys()].sort((a, b) => b.length - a.length).map(literal);
  const url = /https?:\/\/[^\s<>"'«»]+/;
  const token = new RegExp([url.source, ...lookup].join('|'), 'g');
  window.AtlasPartEvidence.useSourceText((source, lang) =>
    source.replace(token, text => captions.get(text)?.[lang] ?? text));
})();
