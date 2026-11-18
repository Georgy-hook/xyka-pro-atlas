"""Ten through-board terminations plus a keyed side-entry 4-way receptacle.

No wire lengths are generated here. ANCHORS in the caller denotes the solder
summit or plug mouth, never the geometric centre of the whole component.
"""
import FreeCAD as App
import Part

from pcb_surface import INK, box_centre, frame, label, ring

V = App.Vector
SOLDER = (.69, .70, .70)
LAND = (.72, .60, .33)
TERMINAL_SRC = 'IMG_8914/8920/8921/AD206911; 10 independent solder joints, owner colour correction'
HEADER_SRC = 'IMG_8913/8915/8916/8919/AD206911; four-way side-entry plug; actual brand and pinout UNKNOWN'
EST = 'ВИДИМО ПО ФОТО / РАЗМЕР ОЦЕНОЧНЫЙ'
SUFFIX = {'B+':'BPlus','B-':'BMinus','F+':'FPlus','F-':'FMinus','GND':'GND','KEY+':'KeyPlus',
          'S-':'SMinus','S+':'SPlus','Clear1':'Clear1','Clear2':'Clear2'}


def drill_for(key):
    if key.startswith(('B', 'F')):
        return 1.39
    if key.startswith('Clear'):
        return .84
    return .86


def _round_section(radius, z, x, y):
    return Part.Wire([Part.makeCircle(radius, V(x,y,z), V(0,0,1))])


def meniscus(radius, height, bore, i):
    """Flared convex solder, with minor hand-soldered eccentricity and exit flat."""
    # A pinhole at the substrate rim is intentionally not a solid metal rod.
    s = 1 if i % 2 else -1
    fr = .39 if radius > 1.35 else .21
    profiles = [_round_section(bore/2-.043, -.12, 0, 0),
                _round_section(bore/2-.043, .029, 0, 0),
                _round_section(.92*radius, .05, 0, 0),
                _round_section(.90*radius, height*.31, .035*s, .055),
                _round_section(.66*radius, height*.70, .06*s, .055),
                _round_section(fr, height, 0, 0)]
    # Ruled sections avoid overshoot below the mask / into neighbouring joints.
    return Part.makeLoft(profiles, True, True)


def _solders(c, group, anchors, at_mm):
    def add(key, name, title, shape, color, point, z=0, note=''):
        obj = c.solid(group, 'Pc'+name+SUFFIX[key], title, shape, color, TERMINAL_SRC, EST, note)
        return at_mm(obj, *point, z=z)

    signal_labels = {'GND':(1.99, .1, .65),'KEY+':(1.99,.0,.59),'S-':(1.95,.0,.77),
                     'S+':(1.95,.0,.77),'B-':(2.12,.22,.78),'B+':(-1.90,.18,.78),
                     'F-':(.10,2.05,.70),'F+':(2.27,1.29,.95)}
    for i, key in enumerate(SUFFIX):
        u,v,w = anchors[key]
        power = key.startswith(('B','F'))
        r = 1.53 if key.startswith('B') else (1.43 if power else 1.24)
        hole = drill_for(key)
        add(key,'SolderLand','Паяльная площадка · '+key,ring(r,hole/2,.03),LAND,(u,v))
        add(key,'Joint','Пайка · '+key,meniscus(r,w,hole,i),SOLDER,(u,v),
            note='Центр и вершина под фактический выход жилы; высота по фото. Не длина провода.')
        rr = r + .23
        add(key,'LandPrint','Обводка площадки · '+key,ring(rr,rr-.13),INK,(u,v))
        if key in signal_labels:
            du,dv,size = signal_labels[key]
            label(c,group,'PcLeadText'+SUFFIX[key],key,at_mm,u+du,v+dv,size,90,photo=TERMINAL_SRC)
    item = c.solid(group,'PcClearBracket','Пара прозрачных жил · контур видимой группы',
                   Part.makeCompound([box_centre(.10, 3.82,.012,2.98,.13),
                                      box_centre(4.53,.10,.012,.77,2.0)]),INK,TERMINAL_SRC,EST,
                   'Шелкография частично скрыта; имена и назначение не восстановлены.')
    at_mm(item,-4.26,3.53)


def _wire_profile_xz(points, y0, depth):
    poly = [V(x,y0,z) for x,z in points]
    return Part.Face(Part.makePolygon(poly+[poly[0]])).extrude(V(0,depth,0))


def _lead_yz(x, width, points):
    poly = [V(x-width/2,y,z) for y,z in points]
    return Part.Face(Part.makePolygon(poly+[poly[0]])).extrude(V(width,0,0))


def _header(c, group, anchors, at_mm):
    # Local origin at the front plane of the *plug*, facing +v. The socket
    # solder toes sit behind the casing (-v). The four colors are separate
    # from the four silk legends, which do not prove an electrical assignment.
    x0 = sum(anchors[f'RGB{i}'][0] for i in range(1,5))/4
    y0 = anchors['RGB1'][1]
    nu = [anchors[f'RGB{i}'][0]-x0 for i in range(1,5)]
    socket = c.sub(group, 'PcRGBReceptacle', 'Колодка на плате · 4 боковых контакта')
    plug = c.sub(group, 'PcRGBPlug', 'Вилка жгута подсветки · ключ и четыре устья')
    at_mm(socket,x0,y0)
    at_mm(plug,x0,y0)
    def piece(parent, name, title, shape, color, note=''):
        return c.solid(parent,name,title,shape,color,HEADER_SRC,EST,note)

    # One opaque shroud with an actual open, keyed pocket, not four cylinders
    # sitting on a box. Side ears follow the two photographed retention lugs.
    outer = _wire_profile_xz([(-3.53,.10),(3.53,.10),(3.53,2.94),(3.23,3.29),
                              (-3.27,3.29),(-3.53,3.00)],-4.74,3.25)
    cavity = box_centre(5.92,3.27,2.45,0,-2.46,.55)
    shroud = outer.cut(cavity)
    for side in (-1,1):
        wing = box_centre(.70,2.21,1.04,side*3.83,-2.79,.10)
        shroud = shroud.fuse(wing)
    # Open witness relief on the roof and the polarizing groove at the mouth.
    shroud = shroud.cut(box_centre(2.24,1.15,.73,0,-2.0,2.92))
    shroud = shroud.removeSplitter()
    piece(socket,'PcRGBShroud','Фиксированная колодка с боковым окном',shroud,(.82,.79,.69),
          'Нет подтверждения марки или товарного артикула; ориентация по выводам и проводам.')
    feet = []
    leads = []
    for x in nu:
        feet.append(box_centre(.54,1.62,.028,x,-5.33))
        leads.append(_lead_yz(x,.27,[(-5.94,.028),(-5.34,.028),(-5.02,.44),(-4.69,.52),
                                     (-4.69,.69),(-5.12,.62),(-5.45,.18),(-5.94,.18)]))
    for side in (-1,1):
        feet.append(box_centre(1.06,2.00,.028,side*4.10,-3.16))
        leads.append(box_centre(.78,1.35,.12,side*4.16,-3.33,.028))
    piece(socket,'PcRGBFootprints','Площадки · 4 хвостовика и две лапки',Part.makeCompound(feet),(.59,.57,.50))
    piece(socket,'PcRGBTails','Лужёные хвостовики и лапки колодки',Part.makeCompound(leads),(.69,.69,.65))

    nose = _wire_profile_xz([(-2.80,.66),(2.80,.66),(2.80,2.61),(2.52,2.84),(-2.52,2.84),(-2.80,2.61)],
                            -3.50,2.05)
    # The projecting wire-entry flange is wider than the inserted keyed nose.
    nose = nose.fuse(_wire_profile_xz([(-2.91,.72),(2.91,.72),(3.07,.87),(3.07,2.83),
                                       (2.90,3.05),(-2.90,3.05),(-3.07,2.83),(-3.07,.87)],-1.47,1.47))
    tongue = box_centre(1.88,1.05,.16,0,-1.95,2.82)
    nose = nose.fuse(tongue)
    for x in nu:
        # Four separate circular throats and visible pick-tool slots.
        drill = Part.makeCylinder(.522,2.86,V(x,.02,2.15),V(0,-1,0))
        slot = box_centre(.50,.80,.56,x,-.81,2.55)
        nose = nose.cut(drill).cut(slot)
    piece(plug,'PcRGBPlugBody','Подвижная вилка · четыре устья с фасками',nose.removeSplitter(),(.94,.895,.72))
    for i,x in enumerate(nu,1):
        sleeve = Part.makeCylinder(.463,.31,V(0,-.365,0),V(0,1,0)).cut(
            Part.makeCylinder(.382,.35,V(0,-.38,0),V(0,1,0)))
        # The four independent receiver mouths are paired with ANCHORS and the
        # harness. They are contact sleeves, not wire lengths.
        entry = piece(plug, 'PcRGBEntry' + str(i), 'Устье ' + str(i) + ' · гильза контакта',
                      sleeve, (.56, .49, .32),
                      'Порядок по u: белый, синий, чёрный, красный. Нет подтверждённой распиновки.')
        c.at(entry, x, 0, 2.15)
    for i,k in enumerate(('V','R','G','B')):
        label(c,group,'PcRGBPrint'+k,k,at_mm,x0+nu[i],y0-6.62,.58,90,photo=HEADER_SRC)


def build_connections(c, joints, sockets, anchors, at_mm, ink):
    _solders(c,joints,anchors,at_mm)
    _header(c,sockets,anchors,at_mm)
