/* Housing, battery, pod, heater, front cassette and wiring. These names describe
   what is modeled, not unobserved materials, electrical functions or processes. */
(() => {
  'use strict';

  const labels = {
    // Upper housing and the battery well that stays in it when the pack is removed.
    MechUpperFairing: ['Upper shell · U-shaped opening, side shoulders and rear slots',
      '上部外壳 · U 形开口、两侧肩部与后部狭槽'],
    MechNoseBridge: ['Upper crossbar of the service opening', '检修口顶部横梁'],
    MechBrandMark: ['XYKA · exterior marking on the owner’s unit', 'XYKA · 机主实物上的外壳标记'],
    MechPackReleaseKey: ['Rear battery release button', '后部电池释放按钮'],
    MechPackReleaseKeyField: ['Rear battery release button · faceted grip surface', '后部电池释放按钮 · 棱面纹理区'],
    MechRearHingeLeaf: ['Sloping hinge back · full-width shoulders and narrow tongue', '倾斜的铰链背板 · 全宽肩部与窄舌片'],
    MechClosurePinGuide: ['Guide bushing for the push pin · EST', '压销导向套 · 估测（EST）'],
    MechServiceBaseGasket: ['Removable heater gasket · covers 3 screw heads', '可拆卸加热器密封垫 · 遮住 3 颗螺钉头'],
    MechServiceBaseInsert: ['Service insert · 4 screw wells and one visible catch', '检修嵌件 · 4 个螺钉凹孔和一个可见卡钩'],
    MechPackWell: ['Housing sleeve · well for the removable battery', '壳体套筒 · 容纳可拆卸电池的仓位'],
    MechPackWellMouth: ['Fixed collar · keyed battery opening', '固定套环 · 有定位平面的电池仓口'],
    MechPackSeatCarrier: ['Four-contact holder at the bottom of the battery well', '电池仓底部的四触点支架'],
    MechPackSeatSockets: ['Four fixed gold-colored contacts in the battery well', '电池仓内的四个固定金色触点'],

    // Detachable base, stem connection and fixed pod seat.
    MechReceiverLegendRing: ['Dark ring around the pod seat in the base', '底座烟锅槽口的深色环'],
    MechReceiverLegendInk: ['Lettering and side triangles on the lower pod seat', '底部烟锅槽口的文字与两侧三角标记'],
    MechLowerShroud: ['Base shell · contoured joint and seating band', '底座外壳 · 非平面接合部与环形配合面'],
    MechBevelGrip: ['Lower bevel · recessed facets and spaced openings', '底部斜面 · 凹入的棱面与间隔分布的开口'],
    MechFrontUnlockBezel: ['Bezel around the base release button', '底座解锁按钮的外圈'],
    MechFrontUnlockKey: ['Round release button', '圆形解锁按钮'],
    MechFrontUnlockKeyField: ['Round release button · faceted grip surface', '圆形解锁按钮 · 棱面纹理区'],
    MechRearClevis: ['Flared hinge base curving around the housing', '铰链底座 · 加宽部分沿壳体弯曲延伸'],
    MechRearEjectKey: ['Rear base release button', '后部底座释放按钮'],
    MechRearEjectKeyField: ['Rear base release button · faceted grip surface', '后部底座释放按钮 · 棱面纹理区'],
    MechHingeAxle: ['Concealed transverse hinge pin · EST', '隐藏的横向铰链轴 · 估测（EST）'],
    MechFrontHook: ['Front lug that mates with the cover · EST', '前部与盖体配合的凸耳 · 估测（EST）'],
    MechStemSocket: ['Stem socket · internal taper opening at the bottom', '水烟壶立管插口 · 从底面开口的内锥孔'],
    MechStemFacePlate: ['Light-colored bottom flange · four dark slots', '底面浅色法兰 · 四道深色狭槽'],
    MechFootWelt: ['Dark support ring with solid backing behind the slots', '深色支承环 · 狭槽背后有实体衬底'],
    MechBaseReturn: ['Inner return flange of the bottom assembly', '底部组件的内翻边'],
    MechChamberInsert: ['Pod seat · fits inside the lower base', '烟锅托座 · 安装在下部底座内'],

    // Front cassette and the fixed crown above it. The tinted window belongs to
    // the removable face film, not the separate LCD glass on the display PCB.
    MechServiceCover: ['Front film · dark U-shaped mask', '前面板薄膜 · 深色 U 形遮光区'],
    MechCoverWindow: ['Front film · tinted window', '前面板薄膜 · 着色透光窗'],
    MechKeyCarrier: ['Rigid backing plate · button seats and cutouts', '刚性衬板 · 按键安装位与开口'],
    MechCartridgeFrame: ['Open board frame · four aligned holes', '开口式电路板支架 · 四个对准电路板的孔'],
    MechTopBridge: ['Crown · panel bridge and battery-well lip', '顶冠 · 面板横梁与电池仓口凸缘'],
    MechLightRing: ['Indicator ring · light diffuser', '指示灯环 · 扩散罩'],

    // Sealed, removable battery. The two bright/dark pairs are finishes on the
    // same four contacts, not more pins. XYKA artwork stays on the native model.
    MechPackEndPlate: ['Battery end plate · cutout for four windows', '电池端面板 · 为四个窗口留出的缺口'],
    MechPackEndArc: ['Bottom of battery · arc with four windows', '电池底端 · 带四个窗口的弧形区'],
    MechPackEndWindows: ['Bottom of battery · four dark inserts', '电池底端 · 四个深色嵌件'],
    MechPackContactPaleFaces: ['Two light contact centers along Y · visible finish', '沿 Y 轴排列的两个浅色触点中心 · 可见表面'],
    MechPackContactDarkFaces: ['Two dark contact centers along X · visible finish', '沿 X 轴排列的两个深色触点中心 · 可见表面'],
    MechPackEndContacts: ['Removable battery · four end contacts', '可拆卸电池 · 四个端面触点'],
    MechBatteryEnvelope: ['Removable XYKA PRO battery · housing with a flat at the rear', 'XYKA PRO 可拆卸电池 · 背部带平面的外壳'],
    MechPackCap: ['Battery top · flat, 20 slots and a central dimple', '电池顶部 · 侧边平面、20 道狭槽与中央凹窝'],
    MechPackSlotWells: ['Dark floors of the 20 slots · appearance only', '20 道狭槽的深色槽底 · 仅表示外观'],
    MechPackRearRecess: ['Rear recess above USB-C · dark floor', 'USB-C 接口上方的后部凹槽 · 深色槽底'],
    MechPackUsbRim: ['USB-C · rim of recessed port', 'USB-C · 内凹接口的边缘'],
    MechPackUsbTongue: ['USB-C · visible center tongue', 'USB-C · 可见的中央舌片'],
    MechRetailBatteryRuCarrier: ['XYKA · printed label backing', 'XYKA · 标签印刷底层'],
    MechRetailBatteryRuSpecPanel: ['XYKA · specification panel', 'XYKA · 规格参数区'],
    MechRetailBatteryRuWarningPanel: ['XYKA · warning panel', 'XYKA · 警示区'],
    MechRetailBatteryRuSpecInk: ['XYKA · specifications and symbols', 'XYKA · 规格参数与符号'],
    MechRetailBatteryRuBrandInk: ['XYKA · logo, website and divider', 'XYKA · 标志、网址与分隔线'],
    MechRetailBatteryRuCautionInk: ['XYKA · yellow warning symbol', 'XYKA · 黄色警示符号'],
    MechRetailBatteryRuWarningInk: ['XYKA · instructions, authorization and country of origin', 'XYKA · 使用说明、授权信息与产地'],
    MechRetailBatteryRuOpticalPaper: ['XYKA · light background of the optical mark', 'XYKA · 光学标记的浅色底'],
    MechRetailBatteryRuOpticalInk: ['XYKA · visible pattern of the optical mark', 'XYKA · 光学标记的可见图案'],
    MechPackEndInk: ['XYKA · markings on the bottom of the battery', 'XYKA · 电池底端标记'],

    // The pod, its removable screen and its lid are distinct from the upper heat guard.
    MechRemovablePod: ['Removable steel pod body · wall and stamped bottom', '可拆卸不锈钢烟锅本体 · 锅壁与冲压锅底'],
    MechPodLid: ['Pod lid · staggered perforations and four folded tabs', '烟锅盖 · 交错排列的孔与四个折弯耳片'],
    MechPodScreen: ['Removable mesh screen · inside the pod next to its fixed bottom', '可取出的滤网 · 位于烟锅内部，靠近固定锅底'],
    MechPodWallMark: ['XYKA · marking on the removable pod wall', 'XYKA · 可拆卸烟锅外壁标记'],
    MechHeatGuard: ['Heat guard · perforated disk facing the pod', '加热器护板 · 朝向烟锅的多孔圆盘'],
    MechHeatGuardRim: ['Heat guard · separate rim with warning', '加热器护板 · 带警示标记的独立边环'],
    MechHeatGuardHotSymbol: ['Heat guard · triangle with three heat waves', '加热器护板 · 三角形与三条热浪波纹'],
    MechHeatGuardCaption: ['Heat guard · Caution Hot !', '加热器护板 · Caution Hot !'],
    MechHeatGuardRimLegend: ['Guard rim · two inscriptions and side symbols', '护板边环 · 两段文字与两侧符号'],
    MechHeatGuardFixingMarks: ['Heat guard · three visible fastener marks', '加热器护板 · 三处可见的紧固件标记'],
    MechHeatGuardCenterMark: ['Heat guard · dark circle in the center of the US reference view', '加热器护板 · 美国参考图中央的深色圆形标记'],
    MechHeaterPlate: ['Heater substrate · exposed face', '加热器基板 · 外露面'],
    MechHeaterFaceBands: ['Contrasting pattern on the exposed face · appearance only', '外露面上的对比色图案 · 仅表示外观'],
    MechHeaterCarrier: ['Holder for the guard and heater plate · EST', '护板与加热板的固定座 · 估测（EST）'],
    MechClosurePin: ['Metal closure pin · circuit UNKNOWN', '金属闭合销 · 所属电路未知（UNKNOWN）']
  };

  // Installation-site codes are used by the CAD tree and are not localized.
  const lugSites = {TopL: '左上', TopR: '右上', SideR: '右侧', Foot: '底部', SideL: '左侧'};
  for (const [site, position] of Object.entries(lugSites)) {
    labels[`MechPanelEar${site}`] = [
      `Housing mounting lug ${site} · coordinates EST`, `壳体安装耳 ${site}（${position}）· 坐标估测（EST）`
    ];
    labels[`MechServiceScrew${site}`] = [
      `Recessed cassette screw ${site} · EST`, `前面板组件的内凹安装螺钉 ${site}（${position}）· 估测（EST）`
    ];
  }

  const sealSites = [['Left', '左侧'], ['Right', '右侧'], ['Rear', '后侧']];
  sealSites.forEach(([site, position], i) => {
    labels[`MechServiceBaseSealScrew${site}`] = [
      `Screw ${i + 1}/3 · under the gasket, head facing down · ${site} EST`,
      `螺钉 ${i + 1}/3 · 密封垫下方，头部朝下 · ${position}（${site}，EST）`
    ];
  });
  const innerSites = [['FrontL', '左前'], ['FrontR', '右前'], ['RearL', '左后'], ['RearR', '右后']];
  innerSites.forEach(([site, position], i) => {
    labels[`MechServiceBaseInnerScrew${site}`] = [
      `Screw ${i + 1}/4 · on the pulled-out service base, head facing up · ${site} EST`,
      `螺钉 ${i + 1}/4 · 位于抽出的检修底件上，头部朝上 · ${position}（${site}，EST）`
    ];
  });

  const buttonMarks = {
    L: ['downward chevron', '向下箭形符号'],
    C: ['lightning bolt', '闪电符号'],
    R: ['upward chevron', '向上箭形符号']
  };
  for (const [side, [mark, markZh]] of Object.entries(buttonMarks)) {
    const id = `MechOuterKey${side}`;
    labels[id] = [`Outer button ${side}`, `外侧按键 ${side}`];
    labels[`${id}Mark`] = [`Outer button ${side} · ${mark}`, `外侧按键 ${side} · ${markZh}`];
    labels[`${id}Field`] = [`Outer button ${side} · faceted grip surface`, `外侧按键 ${side} · 棱面纹理区`];
    labels[`${id}Foot`] = [`Actuating foot of outer button ${side}`, `外侧按键 ${side} 的传力脚`];
  }
  for (const side of ['L', 'R']) {
    labels[`MechDisplaySeat${side}`] = [`20260305A board support ${side} · EST`, `20260305A 电路板支座 ${side} · 估测（EST）`];
  }

  const groups = ['Housing', 'LowerBody', 'Fascia', 'LightRing', 'Battery', 'Pod', 'Heater', 'Mounts'];
  for (const group of groups) {
    window.AtlasPartNames.registerLabels(group, part => labels[part.id] || null);
  }

  // Read the wire identifier and visible insulation color independently. No
  // electrical function or association between a wire color and a net is inferred.
  const colors = {red: '红色', black: '黑色', blue: '蓝色', white: '白色'};
  window.AtlasPartNames.registerLabels('Harness', part => {
    const clear = /^Прозрачная (\d+)\s+·\s+clear$/.exec(part.label);
    if (clear) return [`Clear${clear[1]} · clear insulation`, `Clear${clear[1]} · 透明绝缘层`];
    const wire = /^(\S+)\s+·\s+(red|black|blue|white)$/.exec(part.label);
    return wire ? [part.label, `${wire[1]} · ${colors[wire[2]]}`] : null;
  });
})();
