/* Offline catalogue vocabulary. The names-*.js scripts register part labels by group.
   These lookups return presentation fields only; they never write to the CAD scene. */
(() => {
  'use strict';

  const units = {
    UpperUnit: ['I  •  Upper unit: electronics, heater and removable battery',
      'I  •  上部总成：电子组件、加热器和可拆卸电池'],
    LowerUnit: ['II  •  Detachable base with pod seat', 'II  •  可拆卸底座，带烟锅安装槽']
  };

  // Long titles carry the drawing's section numbers. Short titles go on the tabs.
  const groups = {
    Housing: {
      label: ['01  Upper housing and structural supports', '01  上部外壳与支承件'],
      shortLabel: ['Upper housing', '上部外壳']
    },
    LowerBody: {
      label: ['02  Base and hookah stem connection', '02  底座与水烟壶立管接口'],
      shortLabel: ['Base', '底座']
    },
    Fascia: {
      label: ['03  Front cassette and removable face trim', '03  前面板组件与可拆卸面贴'],
      shortLabel: ['Front cassette', '前面板组件']
    },
    LightRing: {
      label: ['04  Light ring and retaining clips', '04  灯环与固定卡扣'],
      shortLabel: ['Light ring', '灯环']
    },
    Battery: {
      label: ['05  Removable battery', '05  可拆卸电池'],
      shortLabel: ['Battery', '电池']
    },
    Pod: {
      label: ['06  Removable steel pod: body, mesh screen and lid', '06  可拆卸不锈钢烟锅：烟锅本体、滤网和烟锅盖'],
      shortLabel: ['Steel pod', '不锈钢烟锅']
    },
    Heater: {
      label: ['07  Upper-unit heater', '07  上部总成的加热器'],
      shortLabel: ['Heater', '加热器']
    },
    MainPCB: {
      label: ['08  GYS005-S-088-A4.3 · main PCB', '08  GYS005-S-088-A4.3 · 主电路板'],
      shortLabel: ['Main PCB', '主电路板']
    },
    DisplayPCB: {
      label: ['09  20260305A · circuit board, silicone pad and display', '09  20260305A · 电路板、硅胶按键垫和显示屏'],
      shortLabel: ['Display PCB', '显示电路板']
    },
    Harness: {
      label: ['10  Wiring harness · 10 soldered wires and 4 lighting wires', '10  线束 · 10 根焊接导线和 4 根灯环导线'],
      shortLabel: ['Wiring harness', '线束']
    },
    Mounts: {
      label: ['11  Service fasteners', '11  检修紧固件'],
      shortLabel: ['Fasteners', '紧固件']
    }
  };

  // The exported subsection has no ID. Key by its original title rather than by
  // list position: the same section must compare equal across search results.
  const sections = {
    'Верхняя часть · кожух и корона':
      ['Upper unit · shell and crown', '上部总成 · 外壳与顶冠'],
    'Неподвижные проушины передней кассеты':
      ['Fixed mounting lugs for the front cassette', '前面板组件的固定安装耳'],
    'Основа верха · 01 / уплотнитель и 3 винта снизу':
      ['Upper-unit service base · 01 / gasket and 3 screws on the underside', '上部总成检修底件 · 01 / 密封垫和底面的 3 颗螺钉'],
    'Основа верха · 02 / вставка и 4 внутренних винта сверху':
      ['Upper-unit service base · 02 / insert and 4 internal screws on top', '上部总成检修底件 · 02 / 嵌件和顶面的 4 颗内部螺钉'],
    'Неподвижная посадка батареи · принадлежит верхнему корпусу':
      ['Fixed battery well · part of the upper housing', '固定电池仓 · 属于上部外壳'],
    'Основание · паз чаши и патрубок':
      ['Base · pod recess and stem socket', '底座 · 烟锅安装槽与立管插口'],
    'Съёмная U-накладка · маска и оптическое окно':
      ['Removable U-shaped face trim · mask and optical window', '可拆卸 U 形面贴 · 遮光层与透光窗'],
    'Лицевая кассета · наклонная система':
      ['Front cassette · inclined assembly', '前面板组件 · 倾斜安装'],
    'XYKA PRO · съёмная батарея с русской этикеткой':
      ['XYKA PRO · removable battery with Russian label', 'XYKA PRO · 带俄文标签的可拆卸电池'],
    'Нижняя сторона верхней части · нагреватель':
      ['Underside of upper unit · heater', '上部总成底面 · 加热器'],

    '01  Контур, сердцевина и маска':
      ['01  Board outline, core and solder mask', '01  板框、芯层与阻焊层'],
    '02  Припаянные жилы · отдельные вводы':
      ['02  Soldered wires · individual entries', '02  焊接导线 · 独立进线孔'],
    '03  Площадки и шелкография':
      ['03  Pads and silkscreen', '03  焊盘与丝印'],
    'U7 · 6209A · тип не установлен':
      ['U7 · 6209A · type not identified', 'U7 · 6209A · 型号未确定'],
    'D26 · SS14 · полоса к гребню платы':
      ['D26 · SS14 · band toward the top of the board', 'D26 · SS14 · 色带朝向电路板顶端'],
    'UNKNOWN · 5 контактов на грань':
      ['UNKNOWN · 5 contacts per side', 'UNKNOWN · 每侧 5 个触点'],
    'Зуммер · отверстие и литой знак +':
      ['Buzzer · opening and molded + sign', '蜂鸣器 · 开孔与模制的 + 号'],
    'UNKNOWN · корпус с 8 выводами у F+':
      ['UNKNOWN · 8-lead package near F+', 'UNKNOWN · F+ 附近的 8 引脚封装'],
    'Колодка на плате · 4 боковых контакта':
      ['Board connector · 4 side-entry contacts', '板端插座 · 4 个侧向插接触点'],
    'Вилка жгута подсветки · ключ и четыре устья':
      ['Lighting harness plug · locating key and four wire entries', '灯环线束插头 · 定位键与四个进线口'],
    '05  Подсветка · колодка и вилка':
      ['05  Lighting · socket and plug', '05  灯环 · 插座与插头'],
    '06  Двухвыводные компоненты':
      ['06  Two-terminal components', '06  双端元件'],

    '20260305A · плата и маркировка':
      ['20260305A · board and markings', '20260305A · 电路板与标记'],
    'Контактные площадки и металлография':
      ['Contact pads and exposed metal features', '接触焊盘与裸露金属图形'],
    'Шелкография 20260305A':
      ['20260305A silkscreen', '20260305A 丝印'],
    'Тактовая кнопка · левая':
      ['Tactile switch · left', '轻触开关 · 左'],
    'Тактовая кнопка · средняя':
      ['Tactile switch · center', '轻触开关 · 中'],
    'Тактовая кнопка · правая':
      ['Tactile switch · right', '轻触开关 · 右'],
    'LCD · опорный пакет, обод и стекло':
      ['LCD · support layers, bezel and glass', 'LCD · 支承层、边框与玻璃'],
    'FPC · 15 видимых пальцев / сгиб на экран':
      ['FPC · 15 visible contact fingers / fold toward the display', 'FPC · 15 个可见触指 / 向显示屏翻折'],

    '10  •  Раздельная пайка по двум кромкам':
      ['10  •  Individual solder joints along two edges', '10  •  沿两侧板边分布的独立焊点'],
    '04  •  Подсветка от белой колодки V/R/G/B':
      ['04  •  Lighting wires from the white V/R/G/B connector', '04  •  从白色 V/R/G/B 插座引出的灯环导线'],
    'Винты под съёмной облицовкой · 4 видимых места + 1 сравнительное':
      ['Screws under the removable trim · 4 positions visible + 1 from a comparison unit', '可拆卸面贴下的螺钉 · 4 处可见，另 1 处参照对比样机'],
    'Механика стыка · без электрической схемы':
      ['Body joint mechanism · no circuit diagram', '壳体接合机构 · 无电路图']
  };

  const resolvers = new Map();

  function registerLabels(groupId, resolver) {
    resolvers.set(groupId, resolver);
  }

  function inLanguage(pair, lang, original) {
    if (pair && lang === 'en') return pair[0];
    if (pair && lang === 'zh-CN') return pair[1];
    return original;
  }

  function subsection(raw, lang) {
    const type = /^([A-Za-z0-9]+) · тип UNKNOWN$/.exec(raw);
    if (type) {
      return inLanguage([`${type[1]} · type UNKNOWN`, `${type[1]} · 型号未知（UNKNOWN）`], lang, raw);
    }
    // Empty sections and titles made up entirely of CAD designators and physical
    // markings (e.g. U5 · 6209A / 2522/33) are intentionally language-neutral.
    return inLanguage(sections[raw], lang, raw);
  }

  function part(p, lang) {
    const {label, sub, unitLabel} = p;
    if (lang !== 'en' && lang !== 'zh-CN') return {label, sub, unitLabel};
    return {
      label: inLanguage(resolvers.get(p.group)?.(p), lang, label),
      sub: subsection(sub, lang),
      unitLabel: inLanguage(units[p.unit], lang, unitLabel)
    };
  }

  function group(g, lang) {
    const names = groups[g.id];
    return {
      label: inLanguage(names?.label, lang, g.label),
      shortLabel: inLanguage(names?.shortLabel, lang, g.shortLabel),
      unitLabel: inLanguage(units[g.unit], lang, g.unitLabel)
    };
  }

  function unit(u, lang) {
    return {label: inLanguage(units[u.id], lang, u.label)};
  }

  window.AtlasPartNames = Object.freeze({part, group, unit, registerLabels});
})();
