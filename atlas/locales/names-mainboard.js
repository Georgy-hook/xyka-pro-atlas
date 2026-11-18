/* MainPCB part labels. Keys are exported part IDs, not guesses from designators. */
(() => {
  'use strict';

  const labels = new Map();

  function add(id, en, zh, instance = '') {
    // CAD disambiguates duplicate labels with 001, 002, etc. These numbers
    // belong to catalogue positions, not to the physical markings (e.g. G).
    const suffix = instance ? ` · CAD ${instance}` : '';
    labels.set(id, [en + suffix, zh + suffix]);
  }

  function silk(id, mark, instance) {
    add(id, `${mark} · silkscreen`, `${mark} · 丝印`, instance);
  }

  function pad(id, mark, instance) {
    add(id, `${mark} pad`, `${mark} 焊盘`, instance);
  }

  add('PcLaminateCore', 'Glass-cloth laminate · visible edge', '玻璃布层压板 · 可见板边');
  add('PcMaskFace', 'Dark solder mask · component side', '深色阻焊层 · 元件面');
  add('PcMaskRear', 'Reverse side · routing not reconstructed', '背面 · 未重建布线');
  add('PcPlatedWalls', 'Walls of 10 soldered through-holes · hypothetical', '10 个焊接通孔的孔壁 · 推测');

  function solderSite(key, tag) {
    add(`PcSolderLand${key}`, `Solder pad · ${tag}`, `焊盘 · ${tag}`);
    add(`PcJoint${key}`, `Solder joint · ${tag}`, `焊点 · ${tag}`);
    add(`PcLandPrint${key}`, `Pad outline · ${tag}`, `焊盘轮廓线 · ${tag}`);
  }

  for (const [key, mark] of [
    ['BPlus', 'B+'], ['BMinus', 'B-'], ['FPlus', 'F+'], ['FMinus', 'F-'],
    ['GND', 'GND'], ['KeyPlus', 'KEY+'], ['SMinus', 'S-'], ['SPlus', 'S+']
  ]) {
    solderSite(key, mark);
    silk(`PcLeadText${key}`, mark);
  }
  // Clear1 and Clear2 identify the wires; they are not printed legends.
  for (const key of ['Clear1', 'Clear2']) solderSite(key, key);
  add('PcClearBracket', 'Pair of clear wires · outline of the visible group', '两根透明导线 · 可见线组的轮廓');

  // Pads and silkscreen are separate parts, even when the text is identical.
  for (const [mark, inkInstance] of [['VCC', ''], ['B1', ''], ['G', '001'], ['R', '001']]) {
    pad(`PcEdge${mark}`, mark);
    add(`PcEdge${mark}Print`, `Arc around the ${mark} pad`, `${mark} 焊盘周围的弧线`);
    silk(`PcEdge${mark}Mark`, mark, inkInstance);
  }
  for (const mark of ['VDD', 'SDA', 'SCK', 'GND']) pad(`PcAux${mark}`, mark);
  add('PcAuxFrame', 'Outline · GND / SDA / SCK / VDD', '轮廓线 · GND / SDA / SCK / VDD');
  silk('PcAuxVDDMark', 'VDD');
  silk('PcAuxGNDMark', 'GND', '001');
  silk('PcAuxSdaSckMark', 'SDA SCK');

  for (const mark of ['V', 'DIO', 'CLK']) pad(`PcDebug${mark}`, mark);
  pad('PcDebugG', 'G', '001');
  add('PcDebugFrame', 'Four pads · G / CLK / DIO / V', '四个焊盘 · G / CLK / DIO / V');
  silk('PcDebugGMark', 'G', '002');
  silk('PcDebugVMark', 'V', '001');
  silk('PcDebugClkMark', 'CLK DIO');
  for (const mark of ['RX', 'TX']) {
    pad(`Pc${mark}`, mark);
    silk(`Pc${mark}Mark`, mark);
  }

  for (const [id, mark] of [['PcU3IndexInk', 'U3'], ['PcFlashIndexInk', 'HCT']]) {
    add(id, `${mark} · package orientation dot`, `${mark} · 封装方向标记点`);
  }
  for (const n of [1, 2]) {
    add(`PcD27Foot${n}`, `D27 · exposed pad ${n}`, `D27 · 外露焊盘 ${n}`);
  }
  add('PcD27Bar', 'D27 · stripe outline', 'D27 · 条带轮廓');
  silk('PcBoardID', 'GYS005-S-088-A4.3');
  silk('PcBoardCode', '20260204');
  for (const ref of ['U3', 'U5', 'U7', 'D26', 'D27', 'Q5', 'Q6', 'Q7']) {
    silk(`Pc${ref}Print`, ref);
  }
  for (const ref of [
    'C39', 'R42', 'R40', 'C38', 'R43', 'R39', 'R30', 'R37', 'R35', 'C25', 'C24',
    'R19', 'R27', 'C56', 'C37', 'R13', 'R14', 'R16', 'C20', 'C30', 'C26', 'R50',
    'R47', 'R48', 'R49', 'R46', 'R15', 'R36', 'R44', 'C10', 'C27', 'C15', 'Q11'
  ]) {
    silk(`PcPhotoSilk${ref}`, ref);
  }

  // The two photo sets use different numbering in the displayed labels.
  for (const [photo, count, digits] of [['8915', 26, 1], ['8914', 5, 3]]) {
    for (let n = 1; n <= count; n++) {
      const id = `PcFootInk${photo}_${String(n).padStart(2, '0')}`;
      const tag = String(n).padStart(digits, '0');
      add(id, `Footprint outline · ${tag}`, `封装轮廓线 · ${tag}`);
    }
  }
  for (let n = 1; n <= 6; n++) {
    add(`PcMaskWitness${n}`, `Small ring-shaped marks · group ${n}`, `细小环形标记 · 第 ${n} 组`);
  }
  add('PcPaintWitness', 'White mark near the board shoulder', '电路板肩部附近的白色标记');
  add('PcBuzzerPrint', 'Silkscreen outline of the buzzer base', '蜂鸣器底座的丝印轮廓');
  add('PcRgbFootPrint', 'Lighting receptacle outline', '照明插座轮廓');

  const packageLayers = [
    ['Body', 'body', '本体'],
    ['Leads', 'leads', '引脚'],
    ['Lands', 'footprint pads', '封装焊盘'],
    ['Solder', 'solder fillets', '焊料圆角']
  ];

  function addPackage(id, en, {zh = en, instance = '', marked = false, markingInstance = instance} = {}) {
    for (const [role, enRole, zhRole] of packageLayers) {
      add(`${id}_${role}`, `${en} · ${enRole}`, `${zh} · ${zhRole}`, instance);
    }
    if (marked) add(`${id}_Legend`, `${en} · marking`, `${zh} · 标记`, markingInstance);
  }

  addPackage('PcU3', 'AT32F421G8U7 · QFN28', {marked: true});
  addPackage('PcFlash', 'HC25FQ128GSSIG · SOP8-208', {marked: true});
  for (const [id, instance] of [['PcU5', ''], ['PcU7', '001']]) {
    addPackage(id, '6209A · SOT-89-like', {zh: '6209A · 类 SOT-89 封装', instance, marked: true});
  }
  addPackage('PcD26', 'D26 · SS14', {marked: true});
  addPackage('PcUnknownQFN20', 'UNKNOWN · square 20-contact package', {zh: '未知（UNKNOWN） · 20 触点方形封装'});
  addPackage('PcUnknownBF', 'UNKNOWN · narrow SO8', {zh: '未知（UNKNOWN） · 窄体 SO8'});
  add('PcBuzzer_Body', 'Buzzer · housing', '蜂鸣器 · 外壳');

  for (const [id, instance] of [['PcQ5', ''], ['PcQ6', '001'], ['PcQ7', '002']]) {
    addPackage(id, 'SOT-23', {instance, marked: true});
  }
  for (const [id, instance] of [
    ['PcUnknownQ11', '003'], ['PcUnknownQ12', '004'], ['PcUnknownBesideR13', '005'],
    ['PcUnknownQ4', '006'], ['PcUnknownJ11', '008'], ['PcUnknownQ8', '009']
  ]) {
    addPackage(id, 'SOT-23', {instance});
  }
  // NearC18 is the eighth SOT-23 body, but only the fourth marking.
  addPackage('PcUnknownNearC18', 'SOT-23', {instance: '007', marked: true, markingInstance: '003'});

  add('PcRGBShroud', 'Fixed receptacle with a side opening', '带侧面开口的固定插座');
  add('PcRGBFootprints', 'Pads for 4 solder tails and 2 mounting tabs', '4 个焊尾和 2 个固定片的焊盘');
  add('PcRGBTails', 'Tinned solder tails and mounting tabs of the receptacle', '插座的镀锡焊尾和镀锡固定片');
  add('PcRGBPlugBody', 'Movable plug · four chamfered entries', '活动插头 · 四个带倒角的入口');
  for (let n = 1; n <= 4; n++) {
    add(`PcRGBEntry${n}`, `Entry ${n} · contact sleeve`, `入口 ${n} · 触点套筒`);
  }
  for (const mark of ['V', 'R', 'G', 'B']) silk(`PcRGBPrint${mark}`, mark);

  function passive(site, darkFace = false, enHint = '', zhHint = '') {
    const key = `PcSm${site}`;
    const en = enHint ? `${site} (${enHint})` : site;
    const zh = zhHint ? `${site}（${zhHint}）` : site;
    add(`${key}Body`, `${en} · body`, `${zh} · 本体`);
    add(`${key}Ends`, `${en} · two end terminations and their lands`, `${zh} · 两个端头及其焊盘`);
    if (darkFace) add(`${key}Face`, `${en} · dark surface`, `${zh} · 深色表面`);
  }

  for (const ref of [
    'C56', 'C37', 'C23', 'C22', 'C39', 'C38', 'C25', 'C24', 'C18', 'C20',
    'C30', 'C10', 'C26', 'C21', 'C15', 'C27', 'C35'
  ]) passive(ref);
  for (const ref of [
    'R42', 'R40', 'R43', 'R39', 'R19', 'R35', 'R37', 'R30', 'R27', 'R16',
    'R14', 'R34', 'R13', 'R18', 'R10', 'R45', 'R44', 'R36', 'R15', 'R46',
    'R49', 'R48', 'R47', 'R50', 'R23', 'R31', 'R20', 'R32', 'R33', 'R28'
  ]) passive(ref, true);

  // Site identifiers stand in for obscured designators. Keep the ID in both
  // labels, gloss its position/appearance, and do not assign a component type.
  for (const [site, enHint, zhHint, darkFace] of [
    ['BesideU7', 'beside U7', 'U7 旁'],
    ['NextToC37', 'next to C37', 'C37 旁'],
    ['DiodeSide', 'on the diode side', '靠二极管一侧'],
    ['AboveR19', 'above R19', 'R19 上方'],
    ['InnerTanByC30', 'inner tan part by C30', 'C30 旁靠内侧的浅棕色元件'],
    ['BesideR45', 'beside R45', 'R45 旁'],
    ['BesideC26', 'beside C26', 'C26 旁', true],
    ['FlashOuter', 'outer side of the flash chip', '闪存芯片外侧'],
    ['WireUpper', 'upper site by the wires', '导线旁的上方位置', true],
    ['WireMiddle', 'middle site by the wires', '导线旁的中间位置', true],
    ['UnderWhitePair', 'under the white pair', '两根白线下方'],
    ['BelowTrio', 'below the trio', '三个元件下方', true],
    ['WireTrioA', 'site A in the trio by the wires', '导线旁一组三个元件中的 A 位'],
    ['WireTrioB', 'site B in the trio by the wires', '导线旁一组三个元件中的 B 位', true],
    ['BroadMarked', 'wide marked part', '较宽的带标记元件', true]
  ]) passive(site, darkFace, enHint, zhHint);

  for (const [id, tag] of [
    ['PcDiscR45', 'R45'], ['PcDiscC56', 'C56'], ['PcDiscQ12', 'Q12'], ['PcDiscMarked', 'B/F']
  ]) {
    add(id, `Exposed disc · ${tag}`, `外露圆片 · ${tag}`);
  }
  for (const ref of ['R45', 'C18', 'C21']) {
    add(`PcSmInk${ref}`, `Silkscreen · ${ref}`, `丝印 · ${ref}`);
  }

  window.AtlasPartNames.registerLabels('MainPCB', part => {
    if (!part || (part.group != null && part.group !== 'MainPCB')) return null;
    const pair = labels.get(part.id);
    return pair ? pair.slice() : null;
  });
})();
