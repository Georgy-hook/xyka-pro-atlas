(function () {
  'use strict';

  // Exact source labels only: a new label must not inherit an old translation.
  const labels = new Map();
  const unknownZh = '未知（UNKNOWN）';

  function add(ru, en, zh) {
    labels.set(ru, [en, zh]);
  }

  // Board, holes and exposed pads.
  add('20260305A · основание PCB / вырезы и сверления',
      '20260305A · PCB substrate / cutouts and drilled holes',
      '20260305A · PCB 基板 / 缺口与钻孔');
  for (const side of ['L', 'R']) {
    add(`Отверстие ${side} · кромка и открытый просвет`,
        `Hole ${side} · rim and clear bore`, `${side} 孔 · 孔缘与无遮挡的孔口`);
  }

  for (let n = 1; n <= 6; n++) {
    add(`Круглая площадка ${n} / назначение UNKNOWN`,
        `Round contact pad ${n} / function UNKNOWN`, `圆形焊盘 ${n} / 用途${unknownZh}`);
    add(`Центр площадки ${n}`, `Center of pad ${n}`, `焊盘 ${n} 的中心`);
    add(`Кольцо маркировки площадки ${n}`, `Marking ring around pad ${n}`, `焊盘 ${n} 的环形标记`);
  }
  add('Шелкография у левого отверстия', 'Silkscreen by the left hole', '左侧孔旁的丝印');

  for (let n = 1; n <= 4; n++) {
    add(`Краевая площадка ${n} / UNKNOWN`, `Edge pad ${n} / UNKNOWN`, `板边焊盘 ${n} / ${unknownZh}`);
    add(`Центр краевой площадки ${n}`, `Center of edge pad ${n}`, `板边焊盘 ${n} 的中心`);
    add(`Контур краевой площадки ${n}`, `Outline of edge pad ${n}`, `板边焊盘 ${n} 的轮廓`);
  }
  add('Малая открытая площадка слева от FPC / UNKNOWN',
      'Small exposed pad to the left of the FPC / UNKNOWN', `FPC 左侧的小型裸露焊盘 / ${unknownZh}`);
  for (let n = 1; n <= 2; n++) {
    add(`Паяная площадка слева ${n} / UNKNOWN`,
        `Soldered pad ${n} on the left / UNKNOWN`, `左侧带焊料的焊盘 ${n} / ${unknownZh}`);
  }
  add('Прямоугольная металлическая область · поле отверстий',
      'Rectangular metal area · hole array', '矩形金属区 · 孔阵列');
  add('Светлые точки в поле перфорации', 'Bright spots in the perforated area', '穿孔区域内的亮点');
  for (let n = 1; n <= 5; n++) {
    add(`Малые металлизированные контуры ${n} / UNKNOWN`,
        `Small metallized outlines, group ${n} / UNKNOWN`, `第 ${n} 组小型金属化轮廓 / ${unknownZh}`);
  }

  // Printed board markings, not signal names.
  add('Маркировка PCB: 20260305A', 'PCB marking: 20260305A', 'PCB 标记：20260305A');
  add('Штрих у центральных площадок', 'Line mark by the central pads', '中央焊盘旁的短线标记');
  add('Угловая метка у шлейфа', 'Corner mark by the flex cable', '排线旁的角形标记');
  add('Штрих у паяной площадки', 'Line mark by the soldered pad', '带焊料的焊盘旁的短线标记');
  add('Белая метка у левого угла LCD', 'White mark near the left corner of the LCD', 'LCD 左角附近的白色标记');

  // The hardware labels use L/C/R; the plunger labels spell out each position.
  const switches = [
    ['L', 'левая', 'left', '左侧'],
    ['C', 'средняя', 'center', '中间'],
    ['R', 'правая', 'right', '右侧']
  ];
  for (const [side, ruPos, enPos, zhPos] of switches) {
    add(`Четыре паяльных площадки ${side}`, `Four solder pads (${side})`, `四个焊盘（${side}）`);
    add(`Загнутые лапки ${side}`, `Bent leads (${side})`, `弯折引脚（${side}）`);
    add(`Основание контактного блока ${side}`, `Contact block base (${side})`, `触点组件底座（${side}）`);
    add(`Штампованная рамка с окном ${side}`,
        `Stamped frame with a window (${side})`, `带窗口的冲压框架（${side}）`);
    add(`Четыре прижимных язычка ${side}`, `Four hold-down tabs (${side})`, `四个压紧舌片（${side}）`);
    add(`Кремовый толкатель · ${ruPos}`, `Cream-colored plunger · ${enPos}`, `奶油色推杆 · ${zhPos}`);
  }
  add('20260305A · съёмная силиконовая прокладка трёх кнопок',
      '20260305A · removable silicone pad for the three buttons', '20260305A · 三个按键共用的可拆卸硅胶垫');

  add('Опора LCD / тыльный носитель · материал UNKNOWN',
      'LCD support / rear carrier · material UNKNOWN', `LCD 支撑件 / 背部托架 · 材料${unknownZh}`);
  add('LCD · непрерывный металлический обод', 'LCD · continuous metal rim', 'LCD · 连续金属边框');
  add('LCD · тёмный пакет под стеклом', 'LCD · dark layer stack beneath the glass', 'LCD · 玻璃下方的深色叠层');
  add('LCD · покровное стекло, погашенный экран', 'LCD · cover glass (screen off)', 'LCD · 盖板玻璃（熄屏状态）');

  // FPC pad and finger indices count from the left; the printed end marks do not.
  add('FPC · плоская янтарная контактная лента',
      'FPC · flat amber-colored contact strip', 'FPC · 扁平的琥珀色接触带');
  for (let i = 1; i <= 15; i++) {
    const n = String(i).padStart(2, '0');
    add(`FPC · площадка пайки ${n} слева`, `FPC · solder pad ${n} from the left`, `FPC · 左起第 ${n} 个焊盘`);
    add(`FPC · облуженный палец ${n} слева`,
        `FPC · tinned contact finger ${n} from the left`, `FPC · 左起第 ${n} 个上锡触指`);
    add(`FPC · фрагмент рисунка ${n}`, `FPC · printed pattern segment ${n}`, `FPC · 印制图形片段 ${n}`);
  }
  for (const mark of ['15', '1']) {
    add(`Печать на FPC: ${mark}`, `Printed marking on FPC: ${mark}`, `FPC 印字：${mark}`);
  }
  add('FPC · точечные метки у краёв', 'FPC · dot marks near the edges', 'FPC · 边缘附近的点状标记');
  add('FPC · смещённое плечо и обратный сгиб с высечкой',
      'FPC · offset shoulder and notched return fold', 'FPC · 偏置肩部与带缺口的回折段');

  window.AtlasPartNames.registerLabels('DisplayPCB', part => labels.get(part && part.label) || null);
})();
