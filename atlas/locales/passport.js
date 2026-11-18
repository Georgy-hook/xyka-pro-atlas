/* Issued A4.3 part passports. Keep the engineering record as the lookup key;
 * never attach translations to the scene or match a note by a part's position.
 * Load the source captions and the three note dictionaries after this script.
 */
(() => {
  'use strict';

  const confidence = new Map();
  const notes = new Map();
  const languages = new Set(['en', 'ru', 'zh-CN']);
  let sourceText = text => text;

  function entries(table) {
    function fromMixed(source, ru, en, zh) {
      if (table.has(source)) throw new Error(`Duplicate passport entry: ${source}`);
      table.set(source, {ru, en, 'zh-CN': zh});
    }
    return {
      fromMixed,
      fromRu: (ru, en, zh) => fromMixed(ru, ru, en, zh),
      fromEn: (en, ru, zh) => fromMixed(en, ru, en, zh)
    };
  }

  // Confidence is per observation: an observed bore or leg count does not
  // imply that the hidden hardware, location or package size was measured.
  const {fromRu, fromEn, fromMixed} = entries(confidence);
  fromEn('OWNER PHOTO / ESTIMATE',
    'ФОТО ВЛАДЕЛЬЦА / ОЦЕНКА (ESTIMATE)',
    '机主照片 / 估算（ESTIMATE）');
  fromEn('OWNER PHOTO / SEEN BORE, POSITION EST',
    'ФОТО ВЛАДЕЛЬЦА / ОТВЕРСТИЕ ВИДНО, ПОЛОЖЕНИЕ ОЦЕНОЧНОЕ (EST)',
    '机主照片 / 可见孔，位置为估算值（EST）');
  const comparison = 'СРАВНИТЕЛЬНЫЙ A4.3 / положение EST, на снимке владельца закрыто платой';
  const comparisonEn = 'COMPARISON A4.3 / position estimated (EST); obscured by the board in the owner’s photo';
  const comparisonZh = '对比样机 A4.3 / 位置为估算值（EST），在机主照片中被电路板遮挡';
  fromRu(comparison, comparisonEn, comparisonZh);
  fromEn('PRODUCT VIEW / ESTIMATE; A4.3 not dimensioned',
    'ВИД ИЗДЕЛИЯ / ОЦЕНКА (ESTIMATE); размеры A4.3 не указаны',
    '产品视图 / 估算（ESTIMATE）；未给出 A4.3 的尺寸');
  fromEn('CONCEPTUAL FIT / UNVERIFIED',
    'ПРЕДПОЛАГАЕМОЕ СОПРЯЖЕНИЕ / НЕ ПРОВЕРЕНО',
    '假设的配合关系 / 未验证');
  fromEn('RETAIL TEARDOWN / COUNT OBSERVED; POSITION, SECTION AND REVISION EST',
    'РАЗБОРКА РОЗНИЧНОГО ИЗДЕЛИЯ / КОЛИЧЕСТВО ВИДНО; ПОЛОЖЕНИЕ, СЕЧЕНИЕ И РЕВИЗИЯ ОЦЕНОЧНЫЕ (EST)',
    '零售样机拆解 / 可确认数量；位置、截面及版本均为估计（EST）');
  fromEn('REGIONAL RETAIL IMAGE / VISUAL REPRODUCTION, NOT CERTIFICATION',
    'РЕГИОНАЛЬНОЕ ФОТО ТОВАРА / ВОСПРОИЗВЕДЕНИЕ ВНЕШНЕГО ВИДА, НЕ СЕРТИФИКАЦИЯ',
    '地区零售产品图 / 仅复现外观，不是认证');
  fromEn('PHOTO TRACE / ESTIMATED REGISTRATION',
    'ОБВОДКА ПО ФОТО / ПРИВЯЗКА ОЦЕНОЧНАЯ',
    '依照片描摹 / 配准位置为估算值');

  fromRu('ФОТО / ОЦЕНКА', 'PHOTO / ESTIMATE', '照片 / 估算');
  fromRu('ВИДИМО ПО ФОТО / РАЗМЕР ОЦЕНОЧНЫЙ',
    'VISIBLE IN PHOTO / SIZE ESTIMATED', '照片中可见 / 尺寸为估算值');
  fromRu('НАДПИСЬ / ФОРМА ПО ФОТО',
    'INSCRIPTION / SHAPE FROM PHOTO', '铭文 / 形状依据照片');
  fromRu('ОЦЕНКА ПО ВИДИМЫМ ОТМЕТКАМ',
    'ESTIMATE FROM VISIBLE MARKS', '依据可见痕迹估算');
  fromRu('ФОТО + НОМИНАЛ ДАТАШИТА',
    'PHOTO + DATASHEET NOMINAL', '照片 + 数据手册标称值');
  fromRu('ОЦЕНКА / ESTIMATE', 'ESTIMATE', '估算（ESTIMATE）');
  fromRu('НАДПИСЬ ПО ФОТО', 'INSCRIPTION FROM PHOTO', '铭文依据照片');
  fromRu('ФОРМА ПО ФОТО; РАЗМЕРЫ ПО ТИПОВОМУ ЧЕРТЕЖУ',
    'SHAPE FROM PHOTO; DIMENSIONS FROM A TYPICAL PACKAGE DRAWING',
    '形状依据照片；尺寸取自典型封装图');
  fromRu('5 × 4 ПО ФОТО; ГАБАРИТЫ ОЦЕНОЧНЫЕ',
    '5 × 4 CONTACT LAYOUT FROM PHOTO; OVERALL DIMENSIONS ESTIMATED', '5 × 4 触点布局依据照片；外形尺寸为估算值');
  fromRu('ТЕКСТ ЗАДАН ВЫЗОВОМ package()',
    'TEXT SUPPLIED BY THE package() CALL', '文字由 package() 调用指定');
  fromRu('ФОТО / ESTIMATE', 'PHOTO / ESTIMATE', '照片 / 估算（ESTIMATE）');

  fromEn('OBSERVED / physical dimensions ESTIMATE',
    'НАБЛЮДАЕТСЯ / физические размеры оценочные (ESTIMATE)',
    '实物可见 / 实物尺寸为估算值（ESTIMATE）');
  fromEn('CONFIRMED inscription / placement ESTIMATE',
    'НАДПИСЬ ПОДТВЕРЖДЕНА / положение оценочное (ESTIMATE)',
    '铭文已确认 / 位置为估算值（ESTIMATE）');
  fromRu('Материал и место: подтверждены владельцем. Контур: фото. Размеры и скрытый профиль: ESTIMATE.',
    'Material and location: confirmed by the owner. Outline: from photos. Dimensions and hidden profile: estimated (ESTIMATE).',
    '材料和位置由机主确认；轮廓依据照片；尺寸和隐藏部分的断面轮廓为估算值（ESTIMATE）。');
  fromEn('ESTIMATE / obscured extent or height UNKNOWN',
    'ОЦЕНКА (ESTIMATE) / скрытые границы или высота неизвестны (UNKNOWN)',
    '估算（ESTIMATE）/ 被遮挡部分的范围或高度未知（UNKNOWN）');
  fromRu('Наличие и цвет: фото + владелец. Объёмная укладка в закрытой кассете: ESTIMATE.',
    'Presence and colour: photos + owner. 3D routing in the closed cassette: estimated (ESTIMATE).',
    '有无及线色：依据照片和机主说明。闭合组件内部的空间走线为估计（ESTIMATE）。');
  fromEn('OWNER PHOTO / SEEN BORE, POSITION EST / HARDWARE EST',
    'ФОТО ВЛАДЕЛЬЦА / ОТВЕРСТИЕ ВИДНО, ПОЛОЖЕНИЕ ОЦЕНОЧНОЕ (EST) / КРЕПЁЖ ОЦЕНОЧНЫЙ (EST)',
    '机主照片 / 可见孔，位置为估算值（EST）/ 紧固件为估计（EST）');
  fromMixed(comparison + ' / HARDWARE EST',
    comparison + ' / крепёж оценочный (EST)',
    comparisonEn + ' / hardware estimated (EST)',
    comparisonZh + ' / 紧固件为估计（EST）');
  fromEn('OWNER-REPORTED / POSITION ESTIMATE',
    'СО СЛОВ ВЛАДЕЛЬЦА / ПОЛОЖЕНИЕ ОЦЕНОЧНОЕ (ESTIMATE)',
    '据机主描述 / 位置为估算值（ESTIMATE）');

  function stringOrEmpty(value) {
    return typeof value === 'string' ? value : '';
  }

  function part(rawPart, lang) {
    const evidence = stringOrEmpty(rawPart?.evidence);
    const status = stringOrEmpty(rawPart?.confidence);
    const note = stringOrEmpty(rawPart?.note);
    if (!languages.has(lang)) return {evidence, confidence: status, note};
    return {
      evidence: sourceText(evidence, lang),
      confidence: confidence.get(status)?.[lang] ?? status,
      // Empty notes and literal board inscriptions do not need translations.
      note: notes.get(note)?.[lang] ?? note
    };
  }

  window.AtlasPartEvidence = Object.freeze({
    part,
    addNotes(register) { register(entries(notes)); },
    useSourceText(translate) { sourceText = translate; }
  });
})();
