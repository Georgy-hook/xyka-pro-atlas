/* Translate the authored HTML before controllers add data rows. A nested icon or folio stays in place. */
(() => {
  'use strict';
  const {lang, t} = window.AtlasLocale;
  const strings = [
    ['XYKA PRO изнутри. Отделки корпуса, интерактивная 3D-сборка, платы и чертежи одного устройства.', 'Inside the XYKA PRO. Explore the finishes, 3D teardown, circuit boards and drawings of one electronic hookah head.', '走进 XYKA PRO：探索机身配色、3D 拆解、电路板和工程图。'],
    ['XYKA PRO изнутри · Интерактивный атлас', 'Inside XYKA PRO · Interactive teardown atlas', 'XYKA PRO 内部图解 · 交互式拆解图集'],
    ['Перейти к содержанию листа', 'Skip to content', '跳至主要内容'],
    ['XYKA PRO — к обзору', 'XYKA PRO — product overview', 'XYKA PRO — 产品概览'],
    ['Листы атласа', 'Atlas sections', '图集栏目'],
    ['01 Сборка', '01 Assembly', '01 装配模型'],
    ['Сборка', 'Assembly', '装配模型'],
    ['02 Размеры и материалы', '02 Dimensions & materials', '02 尺寸与材料'],
    ['Размеры и материалы', 'Dimensions & materials', '尺寸与材料'],
    ['Чертежи', 'Drawings', '工程图'],
    ['Интерактивный атлас', 'Interactive teardown atlas', '交互式拆解图集'],
    ['изнутри.', 'XYKA PRO.', '内部一览。'],
    ['От тонированного стекла до медных дорожек — в одной 3D-модели.', 'From tinted glass to copper traces, all in one 3D model.', '从深色玻璃到铜箔走线，一套 3D 模型看清内部构造。'],
    ['Открыть в 3D', 'Explore in 3D', '查看 3D 模型'],
    ['Начать разборку', 'Start teardown', '开始拆解'],
    ['Чаша XYKA PRO в графитовой отделке, вид со стороны экрана', 'Graphite XYKA PRO, viewed from the display side', '石墨色 XYKA PRO，屏幕侧视图'],
    ['Состав цифровой модели', 'Inside the model', '模型概况'],
    ['Деталей', 'Parts', '零件'],
    ['Печатные платы — осмотреть основную плату', 'Circuit boards — inspect the mainboard', '电路板 — 查看主板'],
    ['Печатные платы', 'Circuit boards', '电路板'],
    ['Лист чертежей', 'Drawing sheets', '工程图页数'],
    ['Отделка', 'Finish', '机身配色'],
    ['Графит', 'Graphite', '石墨色'],
    ['Отделка на предметном виде', 'Studio finish', '展示图配色'],
    ['Интерактивная модель', 'Interactive model', '交互模型'],
    ['Конструкция в 3D.', 'Explore the assembly.', '探索装配结构。'],
    ['Выберите узел для осмотра или деталь, чтобы открыть её паспорт.', 'Choose an assembly to inspect, or select a part for its record.', '选择组件查看结构，或点选零件打开档案。'],
    ['Узлы модели', 'Model assemblies', '模型组件'],
    ['Фиг. 00', 'Fig. 00', '图 00'],
    ['К выбору этапа', 'Choose a teardown stage', '选择拆解阶段'],
    ['Общий вид', 'Assembly overview', '装配总览'],
    ['Вся сборка: изометрия, без разноса, исходная отделка и без фильтров', 'Restore the assembled view, original finish and unfiltered parts list', '恢复整体轴测视图和原始配色，清除分解和筛选'],
    ['Сбросить', 'Reset', '重置'],
    ['Интерактивная модель XYKA PRO. Детали также доступны в ведомости.', 'Interactive XYKA PRO model. Parts are also available in the parts list.', 'XYKA PRO 交互模型。也可从零件清单选择零件。'],
    ['Статичный вид собранной модели XYKA PRO со стороны экрана', 'Static CAD view of the assembled XYKA PRO from the display side', 'XYKA PRO 装配模型的静态屏幕侧视图'],
    ['3D недоступен. Показан общий вид из CAD; ведомость остаётся доступной.', '3D is unavailable. This is a CAD view of the assembly; the parts list remains available.', '无法显示 3D。此处显示 CAD 装配图，零件清单仍可使用。'],
    ['Открытие 3D-модели…', 'Opening the 3D model…', '正在打开 3D 模型…'],
    ['К общему виду', 'Back to assembly', '返回装配视图'],
    ['Вписать вид в поле', 'Fit model to view', '缩放至完整模型'],
    ['Выбрано', 'Selected', '已选'],
    ['Проекция модели', 'Model view', '模型视图'],
    ['Изометрия', 'Isometric view', '轴测视图'],
    ['Изо', 'Iso', '轴测'],
    ['Спереди', 'Front', '正面'],
    ['Сзади', 'Back', '背面'],
    ['Слева', 'Left', '左侧'],
    ['Справа', 'Right', '右侧'],
    ['Сверху', 'Top', '顶部'],
    ['Снизу', 'Bottom', '底部'],
    ['Каталожная заставка экрана', 'Display the catalogue screen artwork', '显示产品图中的屏幕图案'],
    ['Экран: выкл.', 'Screen: off', '屏幕：关'],
    ['Тянуть — поворот · Колесо — масштаб', 'Drag to rotate · Scroll to zoom', '拖动旋转 · 滚轮缩放'],
    ['Один палец — поворот · Щипок — масштаб', 'Drag to rotate · Pinch to zoom', '单指旋转 · 双指缩放'],
    ['К ведомости', 'Parts list', '零件清单'],
    ['Разнос узлов', 'Exploded view', '分解视图'],
    ['Расцветка корпуса', 'Housing finish', '外壳配色'],
    ['Порядок разборки', 'Teardown stages', '拆解阶段'],
    ['К виду модели', 'View model', '查看模型'],
    ['Этап разборки модели', 'Model teardown stage', '模型拆解阶段'],
    ['00 · В сборе', '00 · Assembled', '00 · 装配状态'],
    ['Предыдущий этап', 'Previous stage', '上一阶段'],
    ['Назад', 'Back', '上一步'],
    ['Следующий этап', 'Next stage', '下一阶段'],
    ['Далее', 'Next', '下一步'],
    ['Вернуть все детали в сборку', 'Return all parts to the assembly', '将所有零件恢复至装配状态'],
    ['В сборе', 'Assembled', '装配状态'],
    ['Детали этапа', 'Parts in this stage', '本阶段零件'],
    ['Выбор детали возвращает узел в исходное положение и открывает её паспорт.', 'Select a part to return its assembly to rest and open its record.', '选中零件后，组件将恢复原位并打开零件档案。'],
    ['Положения показаны для изучения CAD. Смещения условны, это не инструкция по обслуживанию прибора.', 'These positions are for exploring the CAD model. Offsets are illustrative, not servicing instructions.', '各位置仅供查看 CAD 模型，位移为示意值，不作为设备维修说明。'],
    ['Ведомость и паспорт детали', 'Parts list and part record', '零件清单与零件档案'],
    ['Ведомость деталей', 'Parts list', '零件清单'],
    ['Элементов CAD в узле', 'CAD parts in this assembly', '该组件的 CAD 零件数'],
    ['Найти по названию, CAD ID или подразделу', 'Search by name, CAD ID or section', '按名称、CAD ID 或分类搜索'],
    ['Найти деталь или CAD ID', 'Find a part or CAD ID', '搜索零件或 CAD ID'],
    ['Подраздел', 'Section', '分类'],
    ['Все подразделы', 'All sections', '全部分类'],
    ['Поз. / Наименование', 'Item / Part name', '序号 / 零件名称'],
    ['Результаты поиска деталей', 'Part search results', '零件搜索结果'],
    ['Паспорт детали', 'Part record', '零件档案'],
    ['Осмотреть отдельно', 'Isolate part', '单独查看'],
    ['Атлас реконструкции. Размеры по фотографиям — оценочные.', 'Reconstruction atlas. Dimensions derived from photos are estimates.', '逆向重建图集。由照片推算的尺寸均为估算值。'],
    ['Файлы проекта', 'Project files', '项目文件'],
    ['Модель', 'Model', '模型'],
    ['Закрыть выбор языка', 'Close language selector', '关闭语言选择'],
    ['Выберите язык.', 'Choose your language.', '选择语言。'],
    ['Одна модель. Три языка.', 'One model. Three languages.', '一套模型，三种语言。'],
  ];
  if (lang === 'ru') return;
  const labels = new Map(strings.map(([ru, en, zh]) => [ru, t(ru, en, zh)]));
  const localize = value => value.replace(/^(\s*)([\s\S]*?)(\s*)$/, (_, before, phrase, after) => before + (labels.get(phrase) ?? phrase) + after);
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const node = walker.currentNode;
    if (node.parentElement?.closest('noscript, script, [translate="no"]')) continue;
    if (labels.has(node.data.trim())) node.data = localize(node.data);
  }
  for (const attr of ['aria-label', 'title', 'alt', 'placeholder']) {
    for (const el of document.querySelectorAll(`[${attr}]`)) el.setAttribute(attr, localize(el.getAttribute(attr)));
  }
  document.title = localize(document.title);
  const desc = document.querySelector('meta[name="description"]');
  desc.content = localize(desc.content);
  if (lang === 'en') document.getElementById('product-title').firstChild.data = 'Inside ';
})();
