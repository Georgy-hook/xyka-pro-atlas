window.AtlasPartEvidence.addNotes(function ({ fromRu, fromEn, fromMixed }) {
  // Main PCB — laminate, solder, silkscreen and surface observations (077–088).
  fromRu(
    "Светлый торец по фото; фактический материал и стек стеклотекстолита не измерены.",
    "The photo shows a light-coloured edge; the actual material and layup of the glass-fibre laminate have not been measured.",
    "照片中板材端面呈浅色；玻纤层压板的实际材质及叠层结构未经实测。"
  );

  fromRu(
    "Внешняя поверхность w=0; толщина покрытия условная.",
    "The outer surface is at w=0; the coating thickness is provisional.",
    "外表面位于 w=0；涂层厚度为暂定值。"
  );

  fromRu(
    "Обратная разводка не сфотографирована; толщина маски условная.",
    "The routing on the reverse has not been photographed; the solder mask thickness is provisional.",
    "未拍摄背面的布线；阻焊层厚度为暂定值。"
  );

  fromRu(
    "Паяные поверхности видны; внутренняя металлизация и её толщина не подтверждены.",
    "The soldered surfaces are visible; the presence and thickness of internal plating are unconfirmed.",
    "可见焊接表面；内部是否有镀层及其厚度均未经证实。"
  );

  fromRu(
    "Центр и вершина под фактический выход жилы; высота по фото. Не длина провода.",
    "The centre and apex are positioned to match the actual conductor exit; the height is based on the photo. It is not the wire length.",
    "中心和顶点按芯线的实际引出位置定位；高度依据照片确定。该高度并非导线长度。"
  );

  fromRu(
    "Оцифровка видимой надписи, шрифт приближён.",
    "The visible inscription has been digitized; the typeface is approximate.",
    "按可见字样进行数字化描录，字形为近似还原。"
  );

  fromRu(
    "Шелкография частично скрыта; имена и назначение не восстановлены.",
    "Part of the silkscreen is obscured; the names and function could not be reconstructed.",
    "丝印部分被遮挡；未能还原名称和用途。"
  );

  fromRu(
    "Функция контактной группы не проверена. Центр в pcb_registration.json.",
    "The function of the contact group has not been verified. Its centre is recorded in pcb_registration.json.",
    "这组触点的功能未经验证。中心位置见 pcb_registration.json。"
  );

  fromRu(
    "Порядок по фото, электрически не проверено.",
    "The order is taken from the photo; it has not been electrically verified.",
    "排列顺序依据照片，未经电气验证。"
  );

  fromRu(
    "Фото IMG_8914; обозначение не подтверждает функцию или напряжение.",
    "Photo IMG_8914; the marking does not confirm the function or voltage.",
    "照片 IMG_8914；该标记不能证实功能或电压。"
  );

  fromRu(
    "Вид сверху; глубина и связь слоёв неизвестны.",
    "Top view; the depth and any connection between layers are unknown.",
    "俯视所见；深度以及板层之间是否连通均不明。"
  );

  fromRu(
    "Смысл метки неизвестен.",
    "The meaning of the mark is unknown.",
    "标记的含义不明。"
  );

  // Main PCB — RGB header, small components and visible discs (113–116).
  fromRu(
    "Нет подтверждения марки или товарного артикула; ориентация по выводам и проводам.",
    "Neither the make nor the catalogue part number is confirmed; orientation is based on the terminals and wires.",
    "品牌和商品料号均未经证实；朝向依据端子和导线判断。"
  );

  fromRu(
    "Порядок по u: белый, синий, чёрный, красный. Нет подтверждённой распиновки.",
    "Order along u: white, blue, black, red. The pinout is unconfirmed.",
    "沿 u 轴的排列顺序：白、蓝、黑、红。引脚定义未经证实。"
  );

  fromRu(
    "Видимый габарит и посадка оценочны; номинал, материал и цепь не установлены.",
    "The visible dimensions and seating are estimates; the nominal value, material and circuit connection have not been established.",
    "可见外形尺寸和贴装位置均为估计值；标称值、材料及所属电路尚未确定。"
  );

  fromRu(
    "Сплошной видимый диск без ободка; назначение не определено.",
    "The disc appears solid, with no rim; its purpose has not been determined.",
    "可见圆面呈实心状，无环边；用途未确定。"
  );

  // Packages — bodies, leads, lands and solder (089–112). Standalone legends pass through.
  fromRu(
    "4 × 4; A=0.75, A1=0.02; семь выводов на сторону, шаг 0.40 мм.",
    "4 × 4; A=0.75, A1=0.02; seven leads per side, pitch 0.40 mm.",
    "4 × 4；A=0.75，A1=0.02；每边七个引脚，间距 0.40 mm。"
  );

  fromRu(
    "28 × b=0.20, L=0.40, c=0.20; открытая EP 2.40 × 2.40 со срезом 0.35.",
    "28 × b=0.20, L=0.40, c=0.20; exposed pad EP 2.40 × 2.40 with a 0.35 chamfer.",
    "28 × b=0.20，L=0.40，c=0.20；外露焊盘 EP 为 2.40 × 2.40，切角为 0.35。"
  );

  fromRu(
    "Контур открытой металлизации оценочный, не Gerber.",
    "The outline of the exposed metallization is estimated, not taken from Gerber data.",
    "外露金属层的轮廓依据估计绘制，并非取自 Gerber 数据。"
  );

  fromRu(
    "Оценка: слой под выводом и вогнутая галтель снаружи.",
    "Estimated solder profile: a layer beneath the lead and a concave fillet on the outside.",
    "估计的焊料形状：引脚下方为一层焊料，外侧为凹弧形焊料圆角。"
  );

  fromRu(
    "SOP8 208 mil: D 5.00–5.33; E1 5.13–5.38; выбраны середины. E=7.90, A1=0.15, A2=1.80. IMG_8915: почти квадратное литьё (≈130 px вдоль ряда, шаг ≈31 px). Ключ -x,-y по §9.1 и IMG_8913–15.",
    "SOP8 208 mil: D 5.00–5.33; E1 5.13–5.38; the midpoints were selected. E=7.90, A1=0.15, A2=1.80. " +
      "IMG_8915: nearly square moulded body (≈130 px along the row, pitch ≈31 px). The orientation mark is at -x,-y per §9.1 and IMG_8913–15.",
    "SOP8 208 mil：D 5.00–5.33；E1 5.13–5.38；两者均取区间中点。E=7.90，A1=0.15，A2=1.80。" +
      "IMG_8915：模塑本体近似正方形（沿引脚排列方向 ≈130 px，间距 ≈31 px）。定位标记位于 -x,-y，依据 §9.1 和 IMG_8913–15。"
  );

  fromRu(
    "4 + 4; e=1.27 мм, размах 7.90; два радиуса изгиба и полка.",
    "4 + 4; e=1.27 mm, lead span 7.90; two bend radii and a flat foot.",
    "4 + 4；e=1.27 mm，引脚跨距 7.90；引脚有两个弯曲半径，脚端平直。"
  );

  fromMixed(
    "6209A; 4.50 × 2.50. Производитель не установлен.",
    "Маркировка «6209A»; 4.50 × 2.50. Производитель не установлен.",
    "Marked “6209A”; 4.50 × 2.50. The manufacturer has not been identified.",
    "标有“6209A”；4.50 × 2.50。制造商未确定。"
  );

  fromRu(
    "Три узких выхода -y, противоположный широкий выход +y; шаг 1.50 мм.",
    "Three narrow leads on the -y side, one wide lead opposite on the +y side; pitch 1.50 mm.",
    "-y 一侧有三个窄引脚，对面的 +y 一侧有一个宽引脚；间距为 1.50 mm。"
  );

  fromMixed(
    "SMA-подобный SS14: литьё 4.25 × 2.665, полоса +x (IMG_8915).",
    "SMA-подобный корпус с маркировкой «SS14»: литьё 4.25 × 2.665, полоса со стороны +x (IMG_8915).",
    "SMA-like package marked “SS14”: moulded body 4.25 × 2.665, band on the +x side (IMG_8915).",
    "类 SMA 封装，标有“SS14”：模塑本体为 4.25 × 2.665，条带位于 +x 一侧（IMG_8915）。"
  );

  fromRu(
    "Два широких J-образных вывода с подгибом под основание; размах 5.10 мм.",
    "Two wide J-shaped leads curl under the base; span 5.10 mm.",
    "两个宽 J 形引脚向内折至底部下方；跨距 5.10 mm。"
  );

  fromRu(
    "Не QFN16: на IMG_8915 верхние центры x≈885,894,904,914,924 px; также пять снизу и слева. Шаг ≈9.6 px против ≈9.5 px у U3 (0.40 мм). Литьё ≈74 px → ≈3 × 3 мм; высота не измерена.",
    "Not QFN16: in IMG_8915 the top contact centres are at x≈885,894,904,914,924 px; five are also visible on each of the bottom and left edges. " +
      "Pitch ≈9.6 px versus ≈9.5 px for U3 (0.40 mm). Moulded body ≈74 px → ≈3 × 3 mm; height was not measured.",
    "并非 QFN16：在 IMG_8915 中，上排触点的中心位于 x≈885,894,904,914,924 px；下边和左边也各可见五个。" +
      "间距 ≈9.6 px，U3 的间距为 ≈9.5 px（0.40 mm）。模塑本体 ≈74 px → ≈3 × 3 mm；高度未经测量。"
  );

  fromRu(
    "20 краевых контактов; шаг ≈0.40. Скрытая центральная площадка не установлена.",
    "20 edge contacts; pitch ≈0.40. The presence of a concealed centre pad has not been established.",
    "边缘有 20 个触点；间距 ≈0.40。是否有隐藏的中央焊盘尚未确定。"
  );

  fromMixed(
    "Ø11.74 × 8.3 мм, оценка; фаска, буртик, канал Ø2.17 и литой +. Содержимое, скрытые выводы и отверстия в плате не наблюдаются, не заданы.",
    "Ø11.74 × 8.3 мм, оценка; фаска, буртик, канал Ø2.17 и литой знак «+». Содержимое, скрытые выводы и отверстия в плате не наблюдаются, не заданы.",
    "Ø11.74 × 8.3 mm, estimated; chamfer, lip, Ø2.17 channel and moulded “+” mark. The internals, hidden leads and holes in the board are not visible and are not specified.",
    "估计尺寸为 Ø11.74 × 8.3 mm；带倒角、凸缘、Ø2.17 孔道和模制的“+”标记。内部构造、隐藏的引脚及板上孔均未观察到，也未作设定。"
  );

  fromRu(
    "Сменный типовой SO8 4.90 × 3.90; не Flash. Ключ и надпись не додуманы.",
    "Replaceable generic SO8 model, 4.90 × 3.90; not the Flash device. Neither an orientation mark nor an inscription has been assumed.",
    "可替换的通用 SO8 封装模型，4.90 × 3.90；并非 Flash 器件。未臆定定位标记或字样。"
  );

  fromRu(
    "4 + 4; e=1.27 мм, размах 6.00; два радиуса изгиба и полка.",
    "4 + 4; e=1.27 mm, lead span 6.00; two bend radii and a flat foot.",
    "4 + 4；e=1.27 mm，引脚跨距 6.00；引脚有两个弯曲半径，脚端平直。"
  );

  fromMixed(
    "2.90 × 1.30, один вывод +y; код Y1 только для явно указанных экземпляров.",
    "2.90 × 1.30, один вывод +y; код «Y1» только для явно указанных экземпляров.",
    "2.90 × 1.30, one lead on the +y side; the code “Y1” applies only to the explicitly indicated instances.",
    "2.90 × 1.30，+y 一侧有一个引脚；标记代码“Y1”仅适用于明确指出的实例。"
  );

  fromRu(
    "Два вывода с шагом 1.90 мм напротив одиночного; назначение не задано.",
    "Two leads on a 1.90 mm pitch are opposite the single lead; the lead functions are not specified.",
    "单个引脚的对面有两个引脚，间距为 1.90 mm；未指定引脚功能。"
  );

  // Display PCB and FPC — substrate, contacts and other visible surface features (117–127).
  fromEn(
    "Face w=0; FR4/mask combined. Lower chamfers and twin reliefs traced. Rear outline is cropped: closed under the glass without inventing mounts or a connector.",
    "Лицевая поверхность на w=0; FR4 и паяльная маска представлены вместе. Нижние фаски и парные выборки воспроизведены по видимому контуру. " +
      "Задняя часть контура обрезана на снимке: под стеклом контур замкнут без добавления неподтверждённых креплений или разъёма.",
    "正面位于 w=0；FR4 与阻焊层合并表示。下部倒角和成对的避空缺口按可见轮廓描出。后部轮廓在照片中被裁切，模型在玻璃下方将其闭合，未补画未经证实的安装结构或连接器。"
  );

  fromEn(
    "The dark through bore and pale rim are visible; finish, wall plating and fastening method UNKNOWN. The bare PCB drill is enlarged by the provisional 0.035 mm wall on each side.",
    "Видны тёмное сквозное отверстие и светлый ободок; вид обработки поверхности, металлизация стенок и способ крепления не установлены (UNKNOWN). " +
      "Отверстие в основе платы увеличено с каждой стороны на условную толщину стенки — 0.035 мм.",
    "可见深色贯通孔和浅色边环；表面处理、孔壁是否有镀层及固定方式均不明（UNKNOWN）。裸板钻孔按暂定的孔壁厚度在两侧各扩大 0.035 mm。"
  );

  fromEn(
    "Metal face with visible central witness; not an assigned signal.",
    "На металлической поверхности виден след в центре; сигнал не назначен.",
    "金属表面中央可见痕迹；未指定对应信号。"
  );

  fromEn(
    "Contrasting central witness; relief and finish estimated.",
    "В центре виден контрастный след; рельеф и характер обработки поверхности заданы по оценке.",
    "中央可见对比鲜明的痕迹；其起伏和表面处理均为估计。"
  );

  fromEn(
    "Visible dark centre; through-connection and function not established.",
    "Виден тёмный центр; наличие сквозного соединения и назначение не установлены.",
    "中央可见暗部；是否贯通连接及其用途均未确定。"
  );

  fromEn(
    "No wire or termination inferred.",
    "По этому следу не делается вывод о наличии провода или оконцовки.",
    "未据此推断存在导线或端接。"
  );

  fromEn(
    "64 resolved open/contrast pits in the irregular row pattern. Apertures pass through this visible metal layer ONLY. Board penetration, plating stack and purpose UNKNOWN.",
    "В нерегулярных рядах различимы 64 углубления — открытые или заметные по контрасту. В модели отверстия проходят ТОЛЬКО через этот видимый слой металла. " +
      "Неизвестно (UNKNOWN), проходят ли отверстия сквозь плату, какова структура слоёв металлизации и каково их назначение.",
    "在排列不规则的各行中可辨出 64 个凹点，表现为开口或明暗反差。在模型中，开口仅贯穿这一可见金属层。是否贯穿电路板、镀层的叠层结构及其用途均不明（UNKNOWN）。"
  );

  fromEn(
    "Bright/filled appearance on 8917/18; electrical path UNKNOWN.",
    "На снимках 8917/18 участки светлые, на вид заполненные; проводящий путь неизвестен (UNKNOWN).",
    "在照片 8917/18 中外观明亮、似已填充；导电路径不明（UNKNOWN）。"
  );

  fromEn(
    "Only resolved face witnesses, not implied through-drills, nets or components.",
    "Показаны только различимые следы на поверхности платы. По ним не делается вывод о наличии сквозных отверстий, электрических цепей или компонентов.",
    "仅表示板面可辨的痕迹，不据此推定有贯穿钻孔、电气网络或元件。"
  );

  fromEn(
    "Read directly; the string is not proof of date of manufacture.",
    "Надпись прочитана непосредственно; сама по себе эта строка не подтверждает дату изготовления.",
    "按可见字样直接读录；该字符串不能证明生产日期。"
  );

  fromEn(
    "Fragment of exposed silkscreen; symbol interpretation UNKNOWN.",
    "Фрагмент открытой шелкографии; значение символа неизвестно (UNKNOWN).",
    "露出的局部丝印；符号含义不明（UNKNOWN）。"
  );

  // Display controls, support and optical stack (128–135).
  fromEn(
    "Local visible terminal envelope, not a contact assignment.",
    "Показаны только видимые в этом месте габариты выводов; назначение контактов не задаётся.",
    "仅表示此处可见的端子外形范围，不指定触点功能。"
  );

  fromEn(
    "Part number and actuator travel UNKNOWN.",
    "Номер детали и ход толкателя неизвестны (UNKNOWN).",
    "零件编号及推杆行程均不明（UNKNOWN）。"
  );

  fromEn(
    "Cream PCB actuator only; no exterior keycap. Top referenced to w=0 via UiPlungerTop.",
    "Только толкатель кремового цвета на плате, без наружного колпачка клавиши. Положение верхней поверхности относительно w=0 задано параметром UiPlungerTop.",
    "仅表示板上米白色推杆，不含外部键帽。以 w=0 为基准，顶面高度由 UiPlungerTop 给出。"
  );

  fromRu(
    "Одна непрерывная деталь; скрытие открывает кремовые толкатели. L/C/R — только механические давления, не назначение электрических контактов. Верх = UiPlungerTop + 0.65 мм; степень обжатия и точный профиль изнанки UNKNOWN.",
    "One continuous part; hiding it reveals the cream-coloured plungers. L/C/R indicate mechanical press locations only, not electrical contact assignments. " +
      "Top = UiPlungerTop + 0.65 mm; the degree of compression and the exact underside profile are UNKNOWN.",
    "这是一个连续的整体零件；将其隐藏即可看到米白色推杆。L/C/R 仅指机械按压位置，不代表电气触点分配。顶面高度 = UiPlungerTop + 0.65 mm；压缩程度和底面的确切轮廓均不明（UNKNOWN）。"
  );

  fromEn(
    "Bearing face w=0. Concealed seating/adhesive details unknown; no mounting screw inferred.",
    "Опорная поверхность на w=0. Скрытые детали посадки и применения клея неизвестны; вывод о наличии крепёжного винта не делается.",
    "支承面位于 w=0。被遮挡处的安装配合和用胶细节不明；未推定存在固定螺钉。"
  );

  fromEn(
    "Thin hollow rim around cell; layer depths estimated from visible bright line.",
    "Вокруг ячейки дисплея — тонкий полый ободок; положение слоёв по глубине оценено по видимой светлой линии.",
    "显示单元外围是一圈薄的中空边框；各层深度按可见的亮线估计。"
  );

  fromEn(
    "Dark blue-grey laminate edge visible; optical/electrical layer construction UNKNOWN.",
    "Виден тёмный сине-серый торец ламината; строение оптических и электрических слоёв неизвестно (UNKNOWN).",
    "可见层压体的深蓝灰色端面；光学层和电气层的结构不明（UNKNOWN）。"
  );

  fromEn(
    "Dark face with photographed lower corners. Only its hidden distal optical margin is extended to back the retail opening; neither the supporting cell nor the PCB is stretched. Exact distal outline, optical composition, support and active-pixel extent UNKNOWN. Not the removable film.",
    "Тёмная лицевая поверхность; нижние углы видны на фото. На дальнем конце продлена только скрытая краевая зона оптической поверхности, чтобы стекло перекрывало проём серийного корпуса с внутренней стороны. " +
      "Ни опорную ячейку дисплея, ни плату не удлиняли. Точный контур дальнего края, состав оптических слоёв, характер опоры и границы области активных пикселей неизвестны (UNKNOWN). Это не съёмная плёнка.",
    "正面呈暗色，下方两角见于照片。为了让玻璃从内侧覆盖成品外壳的开窗，仅将其被遮挡的远端光学边缘区域延长；支承玻璃的显示单元和 PCB 均未拉伸。" +
      "远端的确切轮廓、光学构成、支承情况以及有效像素范围均不明（UNKNOWN）。这不是可揭除的薄膜。"
  );

  // FPC termination, printed features and folded return (136–140).
  fromEn(
    "Exposed termination observed. Film laminate thickness ESTIMATE.",
    "Видна открытая оконцовка. Толщина плёночного ламината указана ориентировочно (ESTIMATE).",
    "可见外露的端接部位。层压薄膜的厚度为估计值（ESTIMATE）。"
  );

  fromEn(
    "Observed index left-to-right, not a pin number.",
    "Порядковый номер по наблюдаемому ряду слева направо, а не номер вывода.",
    "按可见顺序从左到右编号，并非引脚号。"
  );

  fromEn(
    "Visible copper-toned printed stub. Geometric trace, UNKNOWN pinout.",
    "Виден короткий участок печатной дорожки медного цвета. Воспроизведена только геометрия; распиновка неизвестна (UNKNOWN).",
    "可见一小段铜色印制走线。仅描出几何形状；引脚定义不明（UNKNOWN）。"
  );

  fromEn(
    "End marking as seen 8917; obscured internal lot string not transcribed.",
    "Маркировка на конце передана по снимку 8917; скрытая внутренняя строка с обозначением партии не переписана.",
    "端部标记按照片 8917 中所见记录；内部的批次标识受到遮挡，未作转录。"
  );

  fromEn(
    "Observed folded tongue, traced off-centre wing and notch. Hidden bend radii approximate. Continuous to the front rim; unseen final LCD bond and pin assignment UNKNOWN.",
    "Виден сложенный язычок; смещённое от центра крыло и вырез обведены по контуру. Радиусы скрытых изгибов приближённые. " +
      "Шлейф непрерывен до переднего ободка. Конечного соединения с LCD не видно; ни оно, ни назначение выводов не подтверждены (UNKNOWN).",
    "可见折回的舌片；偏离中心的翼部和缺口按可见轮廓描出。隐藏弯折处的半径为近似值。排线连续延伸到前边框；与 LCD 的最终接合处不可见，接合情况和引脚分配均不明（UNKNOWN）。"
  );

  // Harness — routes at the service opening and at the upper lighting bar (141–143).
  const clippedRouteRu = "Трасса обрезана за нижней кромкой сервисного проёма. Скрытая оконцовка не установлена.";
  const clippedRouteEn = "The modelled route is truncated beyond the lower edge of the service opening. The concealed termination has not been identified.";
  const clippedRouteZh = "模型中的走线在检修口下缘以外截断。隐藏端的端接情况未确定。";

  fromRu(clippedRouteRu, clippedRouteEn, clippedRouteZh);

  fromRu(
    clippedRouteRu + " Назначение конечного устройства не установлено.",
    clippedRouteEn + " The function of the device at the far end has not been established.",
    clippedRouteZh + "末端设备的用途未确定。"
  );

  fromRu(
    "До видимой верхней планки подсветки. Порядок жил на скрытом конце, полярность и напряжение не определены.",
    "The route extends to the visible upper lighting bar. Conductor order at the concealed end, polarity and voltage have not been determined.",
    "走线延伸至可见的上部灯条。隐藏端的芯线顺序、极性及电压均未确定。"
  );
});
