/* Specification sheet and part materials: Russian source, English, Simplified Chinese. */
(() => {
  'use strict';

  const { register } = window.AtlasNotesLocale;

  // Finish names only (no changes to swatches or CAD color assignments).
  register([
    ["Графит", "Graphite", "石墨色"],
    ["Серебро", "Silver", "银色"],
    ["Синий", "Blue", "蓝色"],
    ["Розовый", "Pink", "粉色"],
  ]);

  // Material descriptions shared by parts with identical published notes.
  register([
    [
      "Кожух: алюминий по карточке дилера. Сплав и способ получения оттенка неизвестны.",
      "The dealer lists the housing as aluminum. The alloy and the process used to produce the color are unknown.",
      "经销商的产品页称外壳为铝制。具体合金和着色工艺未知。"
    ],
    [
      "Съёмная чаша: нержавеющая сталь по региональному описанию XYKA. Марка стали не указана.",
      "XYKA’s regional product description lists the removable pod as stainless steel. The steel grade is not specified.",
      "XYKA 的地区产品说明称可拆卸烟锅为不锈钢制，未注明钢材牌号。"
    ],
    [
      "Нижний ложемент: силикон по описанию XYKA. Профиль и твёрдость не измерялись.",
      "XYKA describes the lower seat as silicone. Its profile and hardness were not measured.",
      "XYKA 的说明称下部托座为硅胶制。托座的轮廓和硬度均未测量。"
    ],
    [
      "В фоторазборке накладка описана как пластиковая. Полимер и артикул не опубликованы.",
      "The photo teardown describes the cover as plastic. Neither the polymer nor the part number has been published.",
      "图文拆解称这块盖板为塑料制。聚合物种类和零件编号均未公开。"
    ],
    [
      "На опубликованной разборке Pro щиток описан как перфорированная нержавеющая сталь; марка неизвестна.",
      "A published Pro teardown describes the shield as perforated stainless steel. The steel grade is unknown.",
      "一篇已发布的 Pro 拆解记录称护罩为多孔不锈钢制，钢材牌号未知。"
    ],
    [
      "Синяя сторона и светлые дуги видны на фото. Материал основы, покрытия и скрытых слоёв не установлен.",
      "The photo shows a blue face and light-colored arcs. The materials of the substrate, coating and hidden layers have not been identified.",
      "照片可见蓝色表面和浅色弧线。基材、涂层和隐藏层的材料均未确定。"
    ],
    [
      "Светлая отделка с металлическим блеском. По снимкам не отличить цельный металл от металлизированного пластика.",
      "Light-colored finish with a metallic sheen. The photos do not distinguish solid metal from metallized plastic.",
      "浅色表面带有金属光泽。仅凭照片无法区分实心金属与表面金属化的塑料。"
    ],
    [
      "Светлая металлическая область у толкателя; сплав и функция неизвестны.",
      "Light-colored metal area beside the plunger. Its alloy and function are unknown.",
      "推杆旁有一片浅色金属区域，合金种类和用途均未知。"
    ],
    [
      "Съёмная силиконовая прокладка на трёх кнопках платы 20260305A: материал подтверждён владельцем. Толщина и изнанка — оценки.",
      "The owner confirmed that the removable pad over the three switches on board 20260305A is silicone. Its thickness and underside shape are estimates.",
      "20260305A 板上的三个开关覆盖着可拆卸的硅胶垫，材质已由设备所有者确认。垫片的厚度和背面形状均为估计。"
    ],
    [
      "Кремовая подвижная головка внутри штампованной рамки. Марка материала не установлена.",
      "A cream-colored moving head sits inside a stamped frame. Its material grade has not been identified.",
      "冲压框内有一个米白色的活动头，其材料牌号未确定。"
    ],
    [
      "Чёрная оболочка съёмного блока. Пластик по виду; состав, элементы и внутренние соединения не устанавливались.",
      "The removable pack has a black casing. It looks like plastic; its composition, the cells and the internal connections have not been identified.",
      "可拆卸电池组的外壳为黑色，外观像塑料。外壳成分、电芯和内部连接均未确定。"
    ],
    [
      "Янтарная гибкая лента с отдельными контактами; материал и пакет плёнок документально не подтверждены.",
      "Amber flexible ribbon with individual contacts. No documentation confirms its material or film stack.",
      "琥珀色柔性带上有独立触点。其材质和薄膜叠层结构均无文献证实。"
    ],
  ]);

  // Dimensions: name, CAD value, reference value and interpretation.
  register([
    ["Высота закрытого корпуса · Z", "Closed housing height · Z", "外壳闭合时的高度 · Z"],
    ["154 ± 9 мм", "154 ± 9 mm", "154 ± 9 mm"],
    [
      "160 мм — SmokeDex и HookahMinistry, округлено",
      "160 mm — SmokeDex and HookahMinistry, rounded",
      "160 mm，据 SmokeDex 和 HookahMinistry，已取整"
    ],
    [
      "Оценка CAD согласуется с каталогами. Крайние точки размера не заданы.",
      "The CAD estimate agrees with the catalogs. The measurement endpoints are not specified.",
      "CAD 估算值与产品目录一致。尺寸的两个测量端点未注明。"
    ],
    ["Поперечный габарит · X", "Overall width · X", "总宽度 · X"],
    ["78 ± 7 мм", "78 ± 7 mm", "78 ± 7 mm"],
    ["75 мм — ширина (SmokeDex)", "75 mm — width (SmokeDex)", "75 mm，宽度（SmokeDex）"],
    [
      "Не заменяет обмер максимальной ширины A4.3.",
      "This does not replace a measurement of the maximum width of the A4.3 unit.",
      "该数值不能代替对 A4.3 实物最大宽度的测量。"
    ],
    ["Диаметр из карточки продавца", "Diameter in the retailer’s listing", "零售商产品页标注的直径"],
    ["Не отдельный габарит CAD", "Not a separate CAD dimension", "不是单独的 CAD 尺寸"],
    [
      "≈70 мм — диаметр, сечение не указано",
      "≈70 mm — diameter; cross section not specified",
      "直径 ≈70 mm，未注明对应截面"
    ],
    [
      "Не приравнивать ни к ширине 75 мм, ни к глубине с шарниром.",
      "Do not equate this diameter with either the 75 mm width or the depth including the hinge.",
      "不能把此直径当作 75 mm 的宽度，也不能把它当作含铰链的深度。"
    ],
    ["Глубина с шарниром · Y", "Depth including the hinge · Y", "含铰链的深度 · Y"],
    ["98 ± 9 мм", "98 ± 9 mm", "98 ± 9 mm"],
    [
      "На боковом фото Y/Z ≈504/788. При Z=154…160 мм получаем ≈99…102 мм.",
      "In the side photo, Y/Z ≈504/788. With Z=154…160 mm, this gives ≈99…102 mm.",
      "侧面照片中 Y/Z ≈504/788。取 Z=154…160 mm，可得深度 ≈99…102 mm。"
    ],
    [
      "Опорный масштаб шасси, не обмер по крайним точкам выступов. Фактическая огибающая CAD включает наклонную панель и шарнир.",
      "This sets the scale of the chassis; it is not a measurement across the outermost projections. The actual CAD envelope includes the angled front panel and the hinge.",
      "这是机架的比例基准，并非对最外侧凸起端点的实测。CAD 模型的实际外包络包括倾斜的前面板和铰链。"
    ],
    ["Наклон лицевой панели", "Front panel tilt", "前面板倾角"],
    ["7,5° верхом внутрь", "7.5°, top tilted inward", "7.5°，上缘向内倾斜"],
    [
      "На закрытом боковом виде край панели наклонён примерно на 8–9° в проекции.",
      "In the closed side view, the projected panel edge is tilted by about 8–9°.",
      "在闭合状态的侧视图中，面板边缘的投影倾斜约 8–9°。"
    ],
    [
      "Установочная оценка в CAD. Наклонены стекло и обе платы, а не весь корпус.",
      "Estimated mounting angle in CAD. The glass and both boards are tilted, not the entire housing.",
      "这是 CAD 中估算的安装角度。倾斜的是玻璃和两块电路板，而非整个外壳。"
    ],
    ["Порт снизу / у горла", "Port diameter at the bottom / at the throat", "接口直径：底部 / 喉部"],
    ["21,5 ± 1 / 16 ± 1 мм", "21.5 ± 1 / 16 ± 1 mm", "21.5 ± 1 / 16 ± 1 mm"],
    [
      "Ø21,5 → Ø16 мм внутри (FAQ); «21 мм» — краткое описание",
      "Ø21.5 → Ø16 mm inside (FAQ); the short description says “21 mm”",
      "内径为 Ø21.5 → Ø16 mm（常见问题）；产品简介只写了“21 mm”"
    ],
    [
      "Справка по серии; не наружный диаметр. Проверить на конкретном экземпляре.",
      "Series reference values, not an outside diameter. Check the individual unit.",
      "这是该系列的参考值，不是外径。请以具体实物的测量为准。"
    ],
    ["Сменная чашка · ширина × высота", "Removable pod · width × height", "可拆卸烟锅 · 宽 × 高"],
    ["42 ± 1,6 × 23,3 ± 1,3 мм", "42 ± 1.6 × 23.3 ± 1.3 mm", "42 ± 1.6 × 23.3 ± 1.3 mm"],
    [
      "42 × 23,3 мм у сменного pod",
      "42 × 23.3 mm for the replacement pod",
      "替换烟锅的尺寸为 42 × 23.3 mm"
    ],
    [
      "Размер аксессуара по продавцу, не корпуса и не нагревательного диска.",
      "The retailer gives these dimensions for the accessory, not the housing or the heater disc.",
      "零售商给出的是配件尺寸，不是外壳或加热盘的尺寸。"
    ],
    ["Основная PCB · Ш × Д × Т", "Main PCB · W × L × T", "主电路板 · 宽 × 长 × 厚"],
    ["29,3 × 64,2 × 1,45 мм", "29.3 × 64.2 × 1.45 mm", "29.3 × 64.2 × 1.45 mm"],
    ["±2 / ±4 / ±0,45 мм", "±2 / ±4 / ±0.45 mm", "±2 / ±4 / ±0.45 mm"],
    [
      "Оценка по фото A4.3 и номиналу корпуса U3; не измерено.",
      "Estimated from A4.3 photos and the nominal U3 package dimensions; not measured.",
      "依据 A4.3 照片和 U3 封装标称尺寸估算，未经实测。"
    ],
    ["Дисплейная PCB · Ш × Д × Т", "Display PCB · W × L × T", "显示电路板 · 宽 × 长 × 厚"],
    ["28,2 × 50,4 × 0,8 мм", "28.2 × 50.4 × 0.8 mm", "28.2 × 50.4 × 0.8 mm"],
    ["±3,5 / ±6 / ±0,25 мм", "±3.5 / ±6 / ±0.25 mm", "±3.5 / ±6 / ±0.25 mm"],
    [
      "Оценка по IMG_8917/18. Верх обрезан; масштаб слабее, чем у основной PCB.",
      "Estimated from IMG_8917/18. The top is cropped, so the scale is less certain than for the main PCB.",
      "依据 IMG_8917/18 估算。照片上端被裁切，比例尺的可靠性低于主电路板。"
    ],
    ["Фактура клавиш · шаг / глубина", "Key texture · pitch / depth", "按键表面纹理 · 间距 / 深度"],
    ["0,74 / 0,095 мм", "0.74 / 0.095 mm", "0.74 / 0.095 mm"],
    [
      "На центральной клавише поле ≈71 × 80 px внутри ≈94 × 125 px",
      "On the center key, the textured field is ≈71 × 80 px within an area of ≈94 × 125 px",
      "中央按键的纹理区 ≈71 × 80 px，位于 ≈94 × 125 px 的按键区域内"
    ],
    [
      "Параметры визуальной модели; глубину текстуры по фотографии измерить нельзя.",
      "These are visual model parameters. The texture depth cannot be measured from the photograph.",
      "这些是外观模型的参数，无法从照片中测出纹理深度。"
    ],
  ]);

  // Regional package contents. Quantities and citations stay with the original records.
  register([
    ["Устройство XYKA PRO", "XYKA PRO electronic hookah head", "XYKA PRO 电子水烟头"],
    [
      "Верхний корпус с нагревателем и отсоединяемое основание.",
      "Upper housing with heater and detachable base.",
      "上部外壳内有加热器，底座可拆卸。"
    ],
    ["Съёмный аккумулятор", "Removable battery pack", "可拆卸电池组"],
    [
      "Показан в верхней части. Зарядный кабель — отдельная принадлежность.",
      "Shown in the upper unit. The charging cable is a separate accessory.",
      "模型中电池组位于上部组件内。充电线是单独的配件。"
    ],
    ["Многоразовая чаша", "Reusable pod", "可重复使用的烟锅"],
    [
      "В модели установлена одна: корпус, сетка и крышка. Вторая — запасная.",
      "One pod is installed in the model: pod body, mesh screen and lid. The second pod is a spare.",
      "模型只装有一个烟锅，由烟锅本体、滤网和烟锅盖组成。另一个为备用件。"
    ],
    ["Уплотнитель для установки на шахту", "Seal for mounting on the hookah stem", "水烟管柱安装密封件"],
    [
      "Принадлежность комплекта, не силиконовая прокладка кнопок.",
      "A kit accessory, not the silicone pad over the switches.",
      "这是随附配件，不是按键上的硅胶垫。"
    ],
    ["Щипцы для чаши", "Pod tongs", "烟锅夹"],
    ["Отдельный инструмент.", "A separate tool.", "单独的工具。"],
    ["Шило-вилка", "Fork and poker tool", "叉锥两用工具"],
    ["Зарядный кабель USB-C", "USB-C charging cable", "USB-C 充电线"],
    [
      "Отдельно от съёмного аккумулятора.",
      "Separate from the removable battery pack.",
      "与可拆卸电池组分开。"
    ],
    ["Мешок для переноски", "Carrying bag", "便携袋"],
    ["Принадлежность комплекта.", "A kit accessory.", "随附配件。"],
    ["Руководство по быстрому старту", "Quick start guide", "快速入门指南"],
    ["Документация.", "Documentation.", "说明文件。"],
    ["Инструкция пользователя", "User manual", "用户手册"],
    ["XYKA · комплектация Pro", "XYKA · Pro package contents", "XYKA · Pro 包装清单"],
  ]);
})();
