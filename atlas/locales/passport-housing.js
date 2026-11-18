window.AtlasPartEvidence.addNotes(function ({ fromRu, fromEn, fromMixed }) {
  // Shared qualifications for the key surfaces, rims and symbols.
  const textureRu = " Шаг, глубина и материал оценочны."
    + " Цвет условный, передаёт контраст, не установленный химсостав. Разбиение поверхностей для выбора в CAD.";
  const textureEn = " The pitch, depth and material are estimates."
    + " The colour indicates contrast only; it does not identify the chemical composition. The faces are split for individual selection in CAD.";
  const textureZh = "节距、深度和材质均为估计。颜色仅用于表示明暗对比，不代表已确定的化学成分。表面经分割，以便在 CAD 中单独选取。";

  const rimRu = " Гладкий светлый кант вокруг глухого поля." + textureRu;
  const rimEn = " A smooth, light-coloured rim surrounds the area, which is not cut through." + textureEn;
  const rimZh = "该区域不贯通，四周有光滑的浅色边缘。" + textureZh;

  const symbolRu = " Тональная вставка по фото HookahCat; на региональном графите блик светлый." + textureRu;
  const symbolEn = " The tone of the insert is based on the HookahCat photo; the regional graphite-coloured version shows a pale highlight." + textureEn;
  const symbolZh = "嵌件的色调依据 HookahCat 的照片；在地区版的石墨色款上可见浅色反光。" + textureZh;

  // 001–004: Upper shroud, panel opening and lugs.
  fromRu(
    "Наклон панели 7.5° и кривизна EST: тонкая U-кромка плавно переходит в конус. Глубина полости и стенка оценочны.",
    "The 7.5° panel tilt and the curvature are estimates (EST): the thin U-shaped edge blends smoothly into the cone. The cavity depth and wall thickness are also estimated.",
    "面板倾角 7.5° 和曲率均为估计值（EST）：薄的 U 形边缘平滑过渡到锥面。腔深和壁厚也为估计值。"
  );
  fromRu(
    "Четыре провода исчезают позади перекладины, а не в контактах дисплея.",
    "The four wires disappear from view behind the crossbar, not at the display contacts.",
    "四根导线隐没在横梁后方，而非显示屏的触点处。"
  );
  fromRu(
    "Печатный знак на верхнем кожухе, между кончиком U и швом; не часть плёнки.",
    "The printed mark is on the upper shroud, between the tip of the U-shaped opening and the seam. It is not part of the film.",
    "印记位于上罩壳上，在 U 形开口的尖端与接缝之间，不属于薄膜。"
  );
  fromRu(
    "Сквозной канал Ø1.80 EST; проушина остаётся с верхним кожухом, не отверстие PCB.",
    "The lug has a Ø1.80 through bore (EST). The lug stays with the upper shroud; this is not a hole in the PCB.",
    "凸耳上有 Ø1.80 的通孔（EST，估计值）。凸耳留在上罩壳上；这不是 PCB 上的孔。"
  );

  // 005–008: Release keys, surface relief and rear hinge in the closed position.
  fromRu(
    "Видимая клавиша с выпуклыми торцами, утопленным рифлёным полем и глухим нахлёстом. Зазор, скрытая ступень и ход оценочны, маркировка не считывается." + rimRu,
    "The visible key has convex ends, a recessed textured area and a solid overlap. The clearance, hidden step and key travel are estimates; the marking is illegible." + rimEn,
    "可见按键的两端凸起，有下沉的纹理区和不贯通的搭接部。间隙、隐藏台阶和按键行程均为估计值，标记无法辨认。" + rimZh
  );
  fromRu(
    "Диагональные ряды: повтор 0.74 мм, дно ячейки на 0.095 мм ниже площадки, площадка на 0.115 мм ниже канта. Не сквозное сверление." + textureRu,
    "The diagonal rows repeat at a pitch of 0.74 mm. The bottom of each cell is 0.095 mm below the surrounding flat surface, which is 0.115 mm below the rim. These are not through holes." + textureEn,
    "斜排纹路的重复间距为 0.74 mm。每个凹格的底面比台面低 0.095 mm，台面又比边缘低 0.115 mm。这些凹格不是贯通的钻孔。" + textureZh
  );
  fromRu(
    "Составная кромка в закрытом состоянии. Узкий носик продолжает внешнюю скруглённую спинку; ход не задан.",
    "In the closed position the parts form a composite edge. The narrow tip continues the rounded outer contour of the back; no travel is specified.",
    "闭合时，各部分共同构成这条边缘。窄尖端延续背部外侧的圆滑轮廓；未规定行程。"
  );
  fromRu(
    "Закрытое положение. Направляющая, ход и положение относительно шарнира не измерены.",
    "Shown in the closed position. The guide, travel and position relative to the hinge have not been measured.",
    "图示为闭合状态。导向件、行程及其相对铰链的位置均未经测量。"
  );

  // 009–011: Service-base seal, fasteners and insert.
  fromRu(
    "Только уплотнитель сервисной основы сверху от нижней чаши. Сечение, материал и глубина EST.",
    "Only the service-base gasket above the lower bowl is shown. Its cross-section, material and depth are estimates (EST).",
    "此处仅示出下部碗体上方的检修底座密封垫。其截面、材质和深度均为估计（EST）。"
  );
  fromRu(
    "Число креплений подтверждено разборкой. XY из косого/перевёрнутого снимка; Z, диаметр и длина видимого контура EST."
      + " Показан короткий гладкий стержень, не тип резьбы или шлица.",
    "Disassembly confirmed the fastener count. The XY position comes from an oblique/inverted photo; Z and the diameter and length of the visible outline are estimates (EST)."
      + " The short, smooth shank shown does not specify a thread type or drive recess.",
    "紧固件数量经拆解确认。XY 位置取自斜拍／倒置的照片；Z 位置以及可见轮廓的直径和长度均为估计值（EST）。图中只画出一段光滑的短杆，并未指明螺纹类型或头部槽型。"
  );
  fromRu(
    "Сопряжение с четырьмя стойками MechHeaterCarrier. Один передний зацеп входит в глухой карман MechUpperFairing. Его сечение/азимут EST, полное число защёлок UNKNOWN."
      + " Центр не заполнен гипотетическим механизмом. Не нижняя чаша, не экран, не кольцо подсветки.",
    "The insert mates with the four posts of MechHeaterCarrier. One front catch fits into a blind pocket in MechUpperFairing. The catch cross-section and azimuth are estimates (EST); the total number of latches is marked UNKNOWN."
      + " No hypothetical mechanism has been added at the centre. The insert is not the lower bowl body, a screen or the illumination ring.",
    "嵌件与 MechHeaterCarrier 的四根支柱配合。一个前部卡钩嵌入 MechUpperFairing 的不贯通凹槽。卡钩的截面和方位角为估计（EST），卡扣总数未知（UNKNOWN）。中央未填入假设的机构。此嵌件不是下部碗体，也不是屏板或照明环。"
  );

  // 012–015: Fixed battery well, locating flat and contact seat.
  fromRu(
    "Ось вертикальна. Сохранён исходный радиальный номинальный зазор 0.55 мм к телу без печати, прежние наружная стенка и дно. Не часть съёмного блока.",
    "The axis is vertical. The original nominal radial clearance of 0.55 mm to the pack body, excluding the printing, is retained. The outer wall and bottom are unchanged. The well is not part of the removable pack.",
    "轴线竖直。保留了相对于电池组本体（不计印刷层）的原标称径向间隙 0.55 mm；外壁和底部也保持原样。该容腔不属于可拆卸电池组。"
  );
  fromRu(
    "Отдельно от головки батареи. Лыска ориентирована к тылу, как и USB. Наружный радиус 24.60 при номинале. Посадка — оценка, не заводской зазор.",
    "Separate from the battery head. The flat faces the rear, as does the USB port. The nominal outer radius is 24.60. The fit is estimated, not a factory clearance specification.",
    "此件与电池头部分开。削平面与 USB 口一样朝后。标称外半径为 24.60。配合关系是估计的，并非出厂间隙值。"
  );
  fromRu(
    "Тёмная площадка в центре дна гнезда; видна на другом Pro. Диаметры, ступени и установочные высоты оценочные. Белая обводка на фото — аннотация автора.",
    "A dark platform at the bottom centre of the well can be seen on another Pro unit. The diameters, steps and mounting heights are estimates. The white outline in the photo is the author’s annotation.",
    "容腔底部中央的深色座面在另一台 Pro 上可见。各处的直径、台阶和安装高度均为估计值。照片中的白色轮廓线是作者添加的标注。"
  );
  fromRu(
    "Четыре отдельных круглых золотистых торца с тёмными центрами. Длинная ось ромба направлена примерно от панели к тылу; координаты/Ø/глубина оценочные."
      + " Не назначены ни полярность, ни материал покрытия, ни тип внутренней пружины.",
    "Four separate, round, gold-coloured end faces with dark centres. The long axis of their diamond-shaped layout runs roughly from the panel towards the rear; the coordinates, diameters (Ø) and depths are estimates."
      + " No polarity, coating material or internal spring type is assigned.",
    "四个彼此分开的金色圆形端面，中心均呈深色。四者呈菱形排列，长轴大致从面板指向后方；坐标、直径（Ø）和深度均为估计值。未指定极性、覆层材料或内部弹簧类型。"
  );

  // 016–019: Bowl-seat ring, warning text, lower shroud and grip.
  fromRu(
    "Нижнее штатное основание. Кольцо утоплено в волнистый посадочный пояс; передний зацеп и отверстие штырька свободны. Материал и сечение EST.",
    "On the standard lower base, the ring is recessed into the undulating seating band. The front catch and the pin hole remain clear. The material and cross-section are estimates (EST).",
    "环件嵌在原装下底座的波状环形座面中；前部卡钩和销孔均未被遮挡。材质和截面均为估计（EST）。"
  );
  fromMixed(
    "DO NOT TOUCH WHEN IN USE / REFER TO INSTRUCTION MANUAL. По часовой от петли, вершины двух треугольников наружу. Середина IN…CTION закрыта зацепом на фото."
      + " Тонкий условный слой; способ нанесения, профиль и глубина не измерены.",
    "Надписи: «DO NOT TOUCH WHEN IN USE / REFER TO INSTRUCTION MANUAL». Читаются по часовой стрелке от петли; вершины двух треугольников направлены наружу."
      + " На фото зацеп закрывает середину слова «IN…CTION». Показан тонкий условный слой; способ нанесения, профиль и глубина не измерены.",
    "Inscriptions: “DO NOT TOUCH WHEN IN USE / REFER TO INSTRUCTION MANUAL”. They read clockwise from the hinge; the two triangles point outwards."
      + " In the photo the catch obscures the middle of the word shown as “IN…CTION”. The thin layer is schematic; the application method is undetermined and the profile and depth have not been measured.",
    "铭文：“DO NOT TOUCH WHEN IN USE / REFER TO INSTRUCTION MANUAL”。从铰链处起按顺时针方向排列，两个三角形的尖端均朝外。照片中，卡钩遮住了“IN…CTION”一词的中间部分。标记仅以薄层示意；其形成方式尚未确定，轮廓和深度均未经测量。"
  );
  fromRu(
    "Нижняя половина съёмная. Неподтверждённая внутренняя полка оставляет свободное место для чаши.",
    "The lower half is removable. The modelled internal ledge leaves room for the tobacco bowl; the ledge itself is unconfirmed.",
    "下半壳可拆。模型中的内侧台肩为烟锅留出了空间；这个台肩是否存在尚未证实。"
  );
  fromRu(
    "Ряды рельефа не все вырезаны насквозь; период повторения и глубина предполагаются. Внутреннее продолжение неизвестно.",
    "Not all the rows of surface relief are cut through. Their repeat spacing and depth are assumed; how the pattern continues on the inside is unknown.",
    "并非每排表面纹路都切穿了壳壁。重复间距和深度为推定值；纹路在内侧如何延续尚不清楚。"
  );

  // 020 has no note. 021–024: Unlock key, hinge clevis and pin, and opposite catch.
  fromRu(
    "На круглом поле видны грани, не знак. Скрытый привод и пружина неизвестны." + rimRu,
    "Facets, not a symbol, are visible on the round area. The concealed actuating mechanism and spring are unknown." + rimEn,
    "圆形区域上可见的是棱面，而非符号。隐藏的驱动机构和弹簧情况不明。" + rimZh
  );
  fromRu(
    "Две гладкие наружные щеки; ось снаружи не оголена. Обвод и положение по видам готового изделия, внутренний паз EST.",
    "The clevis has two smooth outer cheeks; the axle is not exposed on the outside. The outline and position are based on views of the finished product; the internal slot is an estimate (EST).",
    "叉座外侧有两片光滑的侧板，轴未外露。外轮廓和位置取自成品视图；内槽为估计（EST）。"
  );
  fromRu(
    "Оба конца утоплены внутри проушин. Фиксация и диаметр пальца не измерены.",
    "Both ends are recessed within the hinge lugs. Neither the retention details nor the pin diameter have been measured.",
    "销的两端均沉入铰耳内。固定结构和销径均未经实测。"
  );
  fromRu(
    "Один видимый выступ на стороне, противоположной петле. Скрытый кинематический привод неизвестен.",
    "One projection is visible on the side opposite the hinge. The concealed mechanism that actuates it is unknown.",
    "在铰链对侧可见一个凸起。带动它的隐藏机构尚不清楚。"
  );

  // 025–029: Stem socket, bottom flange, supporting bands and bowl cradle.
  fromRu(
    "Узкая светлая отбортовка устья. Диаметры внутреннего конуса — сведения для семейства, не промер конкретной чаши. Тёмные участки не обозначают винты.",
    "The mouth of the stem socket has a narrow, light-coloured flange. The internal taper diameters come from data for the product family, not from measurements on this unit. The dark areas do not denote screws.",
    "烟杆接口的开口处有窄而浅色的翻边。内锥面的直径数据来自该产品系列的资料，并非本机的实测值。深色区域不表示螺钉。"
  );
  fromRu(
    "Виден плоский светлый фланец Ø39.5 с четырьмя тёмными тангенциальными прорезями. Тип крепления и внутреннее назначение проёмов снаружи не определяются.",
    "A flat, light-coloured flange of Ø39.5 with four dark tangential slots is visible. Neither the fastening method nor the internal function of the openings can be determined from the outside.",
    "可见一块 Ø39.5 的浅色平法兰，上有四道深色的切向槽。从外部无法判断紧固方式，也无法确定这些开口在内部的作用。"
  );
  fromRu(
    "Широкий чёрный пояс Ø55.7; под прорезями видна тёмная поверхность, а не случайная полость. Тип материала по снимкам не определён.",
    "A broad black band of Ø55.7. A dark surface is visible beneath the slots, not an incidental void. The material has not been identified from the photos.",
    "黑色宽环带的直径为 Ø55.7。透过槽口可见下方的深色表面，并非偶然形成的空腔。无法根据照片判定材质。"
  );
  fromRu(
    "Внутренний несущий пояс: форма оценочная. Не является предполагаемым воздушным коллектором.",
    "The shape of the internal load-bearing band is estimated. It does not represent a hypothetical air manifold.",
    "内部承力环带的形状是估计所得。该环带并不代表假设的空气歧管。"
  );
  fromRu(
    "Силиконовый ложемент нижней части, не вторая табачная чаша. Кольцевая опора оставляет свободным перфорированное поле крышки. Скрытый профиль и зазоры оценочные, не размеры пресс-формы.",
    "A silicone cradle in the lower section, not a second tobacco bowl. The annular support leaves the perforated area of the lid unobstructed. The concealed profile and clearances are estimates, not mould dimensions.",
    "这是下部的硅胶托座，不是第二个烟锅。环形支承不遮挡盖上的穿孔区。隐藏的截面轮廓和间隙均为估计值，并非模具尺寸。"
  );

  // 030–032: Front film, window and rigid key carrier.
  fromRu(
    "Одна съёмная облицовка. Три отверстия под клавиши; светопропускающее окно — смежная часть этой же плёнки, не ещё одна наклейка."
      + " Снимать группу MechFrontFilm наружу по локальной −Y. Толщина 0,18 мм оценочна.",
    "A single removable overlay with three openings for the keys. The light-transmitting window is an adjoining region of the same film, not a separate sticker."
      + " Remove the MechFrontFilm group outwards along the local −Y axis. The thickness of 0.18 mm is estimated.",
    "这是一片可拆卸的面板覆膜，上有三个按键孔。透光窗是同一片薄膜上相邻的区域，并非另一张贴膜。沿局部坐标系的 −Y 方向向外移出 MechFrontFilm 组。厚度 0.18 mm 为估计值。"
  );
  fromRu(
    "Окно заподлицо с маской. Степень прозрачности условна; химсостав не установлен. Контур окна НЕ контур активных пикселей.",
    "The window is flush with the mask. The transparency shown is schematic; the chemical composition has not been established. The window outline is NOT the outline of the active pixel area.",
    "窗口与遮罩齐平。透明程度仅为示意；化学成分尚未确定。窗口轮廓并不是有效像素区的轮廓。"
  );
  fromRu(
    "Отдельная жёсткая подложка под плёнкой: ступенчатые углубления под крепёж. За клавишами — непрозрачные буртики, открытые только для пяты."
      + " Оптический проём носителя раскрыт под плёнкой на 0,60 мм сверху/снизу и 0,05 мм по бокам (оценка). Боковые стенки отсекают косой луч мимо стекла; верхнего уступа в поле нет. Силикон UiKeyMembrane на плате.",
    "A separate rigid backing beneath the film has stepped recesses for the fasteners. Behind the keys are opaque rims with openings only for the key feet."
      + " Under the film, the optical aperture in the backing is enlarged by 0.60 mm at the top and bottom and by 0.05 mm at each side (estimated). The side walls block oblique rays that would pass beside the glass; there is no upper ledge in the field of view. The silicone UiKeyMembrane is on the PCB.",
    "薄膜下方是独立的刚性衬板，板上有用于容纳紧固件的阶梯形凹槽。按键背面是不透光的凸缘，只留出供压脚通过的开口。"
      + "衬板的光学开口在膜下向上、下各扩出 0.60 mm，向两侧各扩出 0.05 mm（估计值）。侧壁挡住本会从玻璃旁斜穿而过的光线；视场内没有上部台阶。硅胶件 UiKeyMembrane 位于电路板上。"
  );

  // 033–037: Outer keys and feet; left and right chevrons and centre lightning bolt.
  fromRu(
    "Габарит и шаг наружных клавиш по лицевому виду товара. Пята отдельно на исходной оси UiSw; это не кремовый толкатель 20260305A." + rimRu,
    "The overall dimensions and pitch of the external keys are taken from the front view of the product. The key foot is a separate part on the original UiSw axis; it is not the cream-coloured 20260305A plunger." + rimEn,
    "外部按键的外形尺寸和间距取自产品正面视图。压脚是独立件，位于原 UiSw 轴线上，并非 20260305A 的奶油色推杆。" + rimZh
  );
  fromRu(
    "Экран сверху: вершина шеврона ниже концов." + symbolRu,
    "With the display at the top, the chevron points down: its vertex lies below both ends." + symbolEn,
    "以屏幕在上方为准，折角标记的尖端朝下，低于两端。" + symbolZh
  );
  fromRu(
    "Пята на оси UiSw; задняя поверхность касается верхнего пятачка силикона без сжатия. Скрытая форма условна. Не кремовый толкатель и не вторая прокладка.",
    "The key foot lies on the UiSw axis. Its rear surface touches the upper silicone pad without compressing it. The concealed shape is schematic. This is neither the cream-coloured plunger nor a second spacer.",
    "压脚位于 UiSw 轴线上，其背面接触硅胶件顶部的小接触面，但不使其受压变形。隐藏部分的形状仅为示意。它既不是奶油色推杆，也不是第二片垫片。"
  );
  fromRu(
    "Верхнее остриё справа, нижнее слева; ширина ~0.40 и высота ~0.65 поля." + symbolRu,
    "The upper tip of the lightning bolt is on the right and the lower tip on the left. Its width is ~0.40 of the field width and its height is ~0.65 of the field height." + symbolEn,
    "闪电符号的上尖端在右，下尖端在左；符号的宽度约为所在区域宽度的 0.40 倍，高度约为该区域高度的 0.65 倍。" + symbolZh
  );
  fromRu(
    "Экран сверху: вершина шеврона выше концов." + symbolRu,
    "With the display at the top, the chevron points up: its vertex lies above both ends." + symbolEn,
    "以屏幕在上方为准，折角标记的尖端朝上，高于两端。" + symbolZh
  );

  // 038–040: Board frame, display supports and battery-well rim.
  fromRu(
    "Рамка лежит между обратными сторонами плат. Четыре канала привязаны к отверстиям основной PCB; винт в каждом не предполагается.",
    "The frame sits between the backs of the boards. The four channels are positioned relative to the holes in the main PCB; the model does not assume a screw in every channel.",
    "框架位于两块电路板的背面之间。四个通道的位置以主 PCB 的孔位为基准；模型并未假定每个通道都有螺钉。"
  );
  fromRu(
    "Втулка у поверхности маски, не винт в припое. Глубина и реальность отдельной втулки UNKNOWN.",
    "A bushing is shown near the mask surface, not a screw in the solder. Its depth and whether a separate bushing actually exists are both marked UNKNOWN.",
    "遮罩表面附近示意的是衬套，而不是嵌在焊料中的螺钉。衬套的深度以及是否确有独立衬套均属未知（UNKNOWN）。"
  );
  fromRu(
    "Буртик не является частью батарейного блока; сверху оставлено открытое гнездо.",
    "The raised rim is not part of the battery pack; the well is left open at the top.",
    "凸缘不属于电池组；电池容腔的顶部保持敞开。"
  );

  // 144–146: Four housing hole positions, a comparative fifth axis, and the unassigned closure pin.
  const screwRu = " Головка, длина, резьба и профиль привода не измерены; не винт платы.";
  const screwEn = " The head, length, thread and drive profile have not been measured; this is not a PCB screw.";
  const screwZh = "螺钉的头部、长度、螺纹和驱动部轮廓均未经测量；这不是用于固定电路板的螺钉。";
  fromRu(
    "Одна из четырёх позиций по видимому отверстию нашего корпуса." + screwRu,
    "One of four positions. This one is based on a hole visible in our housing." + screwEn,
    "这是四个位置之一，依据本机壳体上可见的孔定位。" + screwZh
  );
  fromRu(
    "Пятая ось получена по левой стороне sep01 с поправкой на перспективу, без отражения правой." + screwRu,
    "The fifth screw axis was derived from the left side of the comparison image sep01, with perspective correction, not by mirroring the right side." + screwEn,
    "第五处螺钉的轴线取自对照图 sep01 的左侧，并作了透视校正，而非由右侧镜像得出。" + screwZh
  );
  fromMixed(
    "Назначение контактов KEY/GND и S± не установлено; ни к одной паре не привязан.",
    "Назначение пар контактов KEY/GND и S± не установлено; штырёк закрытия не привязан ни к одной из этих пар.",
    "The functions of the KEY/GND and S± contact pairs have not been established; the closure pin is not assigned to either pair.",
    "KEY/GND 和 S± 这两对触点的用途尚未确定；模型未将闭合销与其中任何一对触点关联。"
  );
});
