"""Photographed surface detail. Coordinates in original, unrotated image pixels.

Outlines and partial ridges are not an electrical netlist. Rectifying each
small cluster locally preserves editable positions without hardcoding pixel
pitch (perspective is appreciable even over the face of this one board).
"""
from math import hypot

import FreeCAD as App
import Part

from pcb_surface import INK, frame, label, ring

V = App.Vector

# x,y of printed reference baseline centre in IMG_8915; orientation in the
# upright board frame. Do not duplicate the three legends from pcb_passives.
_REFERENCES = (
    ('C39',303,530,90), ('R42',319,575,180), ('R40',292,575,180),
    ('C38',302,673,90), ('R43',319,716,180), ('R39',292,716,180),
    ('R30',176,834,90), ('R37',270,835,90), ('R35',357,836,90),
    ('C25',394,726,90), ('C24',325,807,90), ('R19',458,723,90),
    ('R27',534,696,90), ('C56',900,666,180), ('C37',821,563,90),
    ('R13',757,871,90), ('R14',611,844,180), ('R16',631,844,180),
    ('C20',586,843,180), ('C30',893,763,180), ('C26',986,829,90),
    ('R50',138,1028,90), ('R47',137,1122,180), ('R48',188,1122,180),
    ('R49',213,1122,180), ('R46',256,1019,90), ('R15',257,1069,90),
    ('R36',258,1114,90), ('R44',258,1155,90), ('C10',385,1037,180),
    ('C27',680,996,180), ('C15',897,1005,90), ('Q11',143,637,90),
)

# Bounding rectangles seen on the photo, some around two or three chips,
# others a single discrete. These are print outlines, not duplicate lands.
_BOXES_15 = (
    (217,511,279,607), (218,656,279,752), (146,847,205,881),
    (239,847,296,879), (328,848,386,881), (345,735,430,781),
    (345,780,428,824), (435,735,472,848), (508,703,568,741),
    (498,851,552,877), (569,765,650,818), (741,781,779,850),
    (784,732,879,782), (831,607,878,696), (965,833,1013,875),
    (694,980,725,1044), (882,997,930,1036), (181,1008,228,1044),
    (171,1042,231,1107), (121,1041,154,1111), (277,1005,338,1043),
    (277,1053,338,1088), (277,1097,338,1133), (277,1139,338,1174),
    (277,1180,338,1216), (333,1004,367,1067),
)
_BOXES_14 = ((324,1081,431,1127), (235,1109,276,1160), (301,927,358,959),
             (873,922,998,978), (950,1024,1065,1088))



def build_printmap(c, parent, project, at_mm, width, length):
    def xy(photo, x, y):
        u, v = project(photo, x, y)
        return u*width, v*length

    def solid(name, legend, shape, u, v, color=INK, photo='IMG_8915', note=''):
        obj = c.solid(parent, name, legend, shape, color, photo,
                      'ОЦЕНКА ПО ВИДИМЫМ ОТМЕТКАМ', note)
        return at_mm(obj, u, v)

    for ref, x, y, a in _REFERENCES:
        u, v = xy('8915', x, y)
        label(c, parent, 'PcPhotoSilk'+ref, ref, at_mm, u, v, .53, a, photo='IMG_8915')

    for photo, boxes in (('8915', _BOXES_15), ('8914', _BOXES_14)):
        for i, (x0, y0, x1, y1) in enumerate(boxes, 1):
            # Measured outer edges; line width and square corners simplified.
            # Approximation is local, never propagated to the rest of the photo.
            cx, cy = (x0+x1)/2, (y0+y1)/2
            u, v = xy(photo, cx, cy)
            p1, p2 = xy(photo,x0,cy), xy(photo,x1,cy)
            q1, q2 = xy(photo,cx,y0), xy(photo,cx,y1)
            lx = hypot(q2[0]-q1[0], q2[1]-q1[1])
            ly = hypot(p2[0]-p1[0], p2[1]-p1[1])
            solid(f'PcFootInk{photo}_{i:02d}', 'Контур посадки · '+str(i),
                  frame(lx, ly, .077), u, v, photo='IMG_'+photo)

    # Some vias have visible dark rings/highlights, while the large nearby
    # discs are flush and rimless. Do NOT add speculative small through holes.
    clusters = (
        ('8915', ((936,602),(950,603),(966,603),(936,619),(951,619),(965,619),(950,637),(965,636))),
        ('8915', ((1006,788),(1020,788),(1033,787))),
        ('8915', ((843,710),(844,724))),
        ('8915', ((284,640),(299,641),(298,629))),
        ('8909', ((263,204),(278,205),(266,221),(281,223))),
        ('8909', ((446,211),(462,214),(450,227),(464,229))),
    )
    for j, (photo, pts) in enumerate(clusters, 1):
        points = [xy(photo,x,y) for x,y in pts]
        u = sum(p[0] for p in points)/len(points)
        v = sum(p[1] for p in points)/len(points)
        dots = []
        for x,y in points:
            dot = ring(.106,.058,.009)
            dot.translate(V(x-u, y-v, 0))
            dots.append(dot)
        solid('PcMaskWitness'+str(j), 'Мелкие кольцевые отметки · группа '+str(j),
              Part.makeCompound(dots), u, v, color=(.235,.223,.224), photo='IMG_'+photo,
              note='Вид сверху; глубина и связь слоёв неизвестны.')

    # Asymmetric inspection paint near R45; present in 8909/8915/AD, unlike
    # an imagined polarity mark or logo. Smooth outline sampled by hand.
    outline = [(-.69,-1.96),(-.42,-2.30),(.17,-2.27),(.84,-1.95),(.85,-1.39),
               (.63,-.26),(.41,.85),(.00,1.90),(-.41,2.26),(-.67,2.13),
               (-.87,1.53),(-.89,.48),(-.82,-.70)]
    spline = Part.BSplineCurve()
    spline.interpolate([V(x,y,0) for x,y in outline], PeriodicFlag=True)
    paint = Part.Face(Part.Wire([spline.toShape()])).extrude(V(0,0,.022))
    solid('PcPaintWitness','Белая метка у плеча платы',paint,-12.68,58.45,
          color=(.90,.89,.89),photo='IMG_8909/8915/AD206911',note='Смысл метки неизвестен.')
    solid('PcBuzzerPrint','Шелковый контур основания зуммера',ring(6.07,5.93),7.77,17.97,
          photo='IMG_8908/8909/8916/8920')
    solid('PcRgbFootPrint','Контур колодки подсветки',frame(9.54,4.10,.095),-8.22,40.95,
          photo='IMG_8913/8914/8915')
