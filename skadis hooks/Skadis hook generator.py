import adsk.core, adsk.fusion, traceback
from typing import Optional, Tuple, List

# -----------------------------
# Constants (mm)
# -----------------------------
WIDTH_MM            = 4.8
HEIGHT_MM           = 7.5
BOARD_DEPTH_MM      = 5.0
HOOK_LENGTH_MM      = 6.0
FILLET_RADIUS_MM    = 1.5
PATTERN_DISTANCE_MM = 40.0   # Skådis grid
DIST_FROM_BOTTOM_MM = 30.0

# -----------------------------
# Unit helper (Fusion API werkt in cm)
# -----------------------------
def mm(value: float) -> float:
    """mm -> cm (Fusion interne units)."""
    return value / 10.0

# -----------------------------
# UI helpers
# -----------------------------
def fail(ui: adsk.core.UserInterface, msg: str) -> None:
    ui.messageBox(msg)
    raise RuntimeError(msg)

def select_linear_edge(ui: adsk.core.UserInterface, prompt: str) -> adsk.fusion.BRepEdge:
    sel = ui.selectEntity(prompt, 'LinearEdges')
    if not sel:
        raise RuntimeError('Selection cancelled')
    edge = adsk.fusion.BRepEdge.cast(sel.entity)
    if not getattr(edge, 'geometry', None):
        fail(ui, 'Selecteer a linear face edge.')
    return edge

# -----------------------------
# Geometry helpers (2D sketch space)
# -----------------------------
def find_common_face(h_edge: adsk.fusion.BRepEdge, v_edge: adsk.fusion.BRepEdge) -> Optional[adsk.fusion.BRepFace]:
    for fh in h_edge.faces:
        for fv in v_edge.faces:
            if fh.tempId == fv.tempId:
                return fh
    return None

def find_common_vertex(h_edge: adsk.fusion.BRepEdge, v_edge: adsk.fusion.BRepEdge) -> Optional[adsk.fusion.BRepVertex]:
    for vh in (h_edge.startVertex, h_edge.endVertex):
        for vv in (v_edge.startVertex, v_edge.endVertex):
            if vh.tempId == vv.tempId:
                return vh
    return None

def unit_vec_2d(a: adsk.core.Point2D, b: adsk.core.Point2D) -> adsk.core.Vector2D:
    v = a.vectorTo(b)
    v.normalize()
    return v

def rel_point_2d(base: adsk.core.Point2D, du: float, dv: float,
                 u: adsk.core.Vector2D, v: adsk.core.Vector2D) -> adsk.core.Point2D:
    """base + du*u + dv*v (alles in cm)"""
    p = adsk.core.Point2D.create(base.x, base.y)
    mu = adsk.core.Vector2D.create(u.x, u.y); mu.scaleBy(du); p.translateBy(mu)
    mv = adsk.core.Vector2D.create(v.x, v.y); mv.scaleBy(dv); p.translateBy(mv)
    return p

def add_rectangle_by_lb_rt(sk: adsk.fusion.Sketch,
                           p_lb: adsk.core.Point2D,
                           p_rt: adsk.core.Point2D) -> adsk.fusion.SketchLine:
    """Teken rechthoek via LB/RT in sketch space (1 API-call)."""
    return sk.sketchCurves.sketchLines.addTwoPointRectangle(
        adsk.core.Point3D.create(p_lb.x, p_lb.y, 0),
        adsk.core.Point3D.create(p_rt.x, p_rt.y, 0)
    )

def smallest_profile(sk: adsk.fusion.Sketch) -> adsk.fusion.Profile:
    """Kies kleinste gesloten regio (robuustste keuze voor jouw scenario)."""
    return min(sk.profiles, key=lambda p: p.areaProperties().area)

# -----------------------------
# Features helpers
# -----------------------------
def extrude(root: adsk.fusion.Component,
            profile: adsk.fusion.Profile,
            distance_cm: float,
            op: adsk.fusion.FeatureOperations = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
           ) -> adsk.fusion.ExtrudeFeature:
    ex = root.features.extrudeFeatures
    inp = ex.createInput(profile, op)
    inp.setDistanceExtent(False, adsk.core.ValueInput.createByReal(distance_cm))
    return ex.add(inp)

def add_edge_fillet(root: adsk.fusion.Component,
                    body: adsk.fusion.BRepBody,
                    exclude_faces: List[adsk.fusion.BRepFace],
                    radius_cm: float) -> None:
    """Fillet op alle body-randen die NIET grenzen aan exclude_faces."""
    exclude = {f.tempId for f in exclude_faces}
    edges = [e for e in body.edges if all(f.tempId not in exclude for f in e.faces)]
    if not edges:
        return
    col = adsk.core.ObjectCollection.create()
    for e in edges:
        col.add(e)
    ff = root.features.filletFeatures
    fi = ff.createInput()
    fi.addConstantRadiusEdgeSet(col, adsk.core.ValueInput.createByReal(radius_cm), True)
    ff.add(fi)

def pattern_linear(root: adsk.fusion.Component,
                   entities: List[adsk.core.Base],
                   axis: adsk.fusion.BRepEdge,
                   qty: int,
                   spacing_cm: float) -> adsk.fusion.RectangularPatternFeature:
    """Lineair patroon langs 'axis' met qty en spacing (alleen richting 1)."""
    col = adsk.core.ObjectCollection.create()
    for e in entities:
        col.add(e)
    pf = root.features.rectangularPatternFeatures
    inp = pf.createInput(
        col,
        axis,
        adsk.core.ValueInput.createByString(str(max(1, qty))),
        adsk.core.ValueInput.createByReal(-spacing_cm),
        adsk.fusion.PatternDistanceType.SpacingPatternDistanceType
    )
    inp.quantityTwo = adsk.core.ValueInput.createByReal(1)
    inp.isSymmetricInDirectionOne = False
    return pf.add(inp)

# -----------------------------
# Grid & positionering (strakke 40 mm logica)
# -----------------------------
def compute_row_on_grid(face_len_u_cm: float,
                        hook_width_cm: float,
                        grid_cm: float) -> Tuple[int, float]:
    """
    Bepaal exact:
      - qty = max aantal haken op hart-op-hart 'grid_cm'
      - margin_u = centrering zodat totale lengte w + (q-1)*grid_cm gecentreerd ligt
    Formules:
      q   = floor((L - w)/G) + 1  (minstens 1)
      mar = (L - (w + (q-1)*G)) / 2
    """
    if face_len_u_cm <= 0:
        return 1, 0.0
    G = grid_cm
    L = face_len_u_cm
    w = hook_width_cm
    if L < w:
        # Er past maar 1 haak; zet 'm midden
        return 1, (L - w) / 2.0
    q = int((L - w) // G) + 1
    q = max(1, q)
    total = w + (q - 1) * G
    margin_u = (L - total) / 2.0
    return q, margin_u

# -----------------------------
# Target-face voor 90° haak & hulpfuncties
# -----------------------------
def closest_face_along_edge_dir(body: adsk.fusion.BRepBody,
                                v_axis: adsk.fusion.BRepEdge,
                                h_axis: adsk.fusion.BRepEdge) -> Optional[adsk.fusion.BRepFace]:
        # 1. Richting bepalen (Verticale vector)
        v_geom = v_axis.geometry
        v_dir = v_geom.startPoint.vectorTo(v_geom.endPoint)
        v_dir.normalize()

        # 2. Referentiepunt op de onderste as
        h_start = h_axis.geometry.startPoint

        target_face = None
        min_dist = float('inf')

        for face in body.faces:
            # Pak het middelpunt van het vlak
            test_pt = face.pointOnFace
            
            # Maak een vector van de onderste as naar dit testpunt
            vec_to_pt = h_start.vectorTo(test_pt)
            
            # De 'Dot Product' geeft de afstand van het punt tot het vlak 
            # in de richting van de vector v_dir
            # Dit is de pure wiskundige afstand tot het vlak.
            dist = abs(vec_to_pt.dotProduct(v_dir))
            
            if dist < min_dist:
                min_dist = dist
                target_face = face
        return target_face



def farthest_vertex_on_face(face: adsk.fusion.BRepFace) -> adsk.core.Point3D:
    o = face.geometry.origin
    best_pt, best_d = None, -1.0
    for e in face.edges:
        for v in (e.startVertex, e.endVertex):
            d = v.geometry.distanceTo(o)
            if d > best_d:
                best_pt, best_d = v.geometry, d
    return best_pt

# -----------------------------
# Main
# -----------------------------
def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        design = adsk.fusion.Design.cast(app.activeProduct)
        root = design.rootComponent
        sketches = root.sketches

        # 1) Selecteer referentie-assen op de face
        h_axis = select_linear_edge(ui, 'Select lower horizontal face edge')
        v_axis = select_linear_edge(ui, 'Select left vertical face edge')

        # 2) Validaties: gemeenschappelijke face + hoekpunt
        face = find_common_face(h_axis, v_axis)
        if not face:
            fail(ui, 'Error: The two selected edges aren\'t on the same face.')

        common_vertex = find_common_vertex(h_axis, v_axis)
        if not common_vertex:
            fail(ui, 'Error: The selected faces do not cross at one point.')

        # 3) Sketch op face + 3D->2D referentiepunten
        sk1 = sketches.add(face)
        p_lb_3d = common_vertex.geometry
        p_rb_3d = h_axis.startVertex.geometry if h_axis.endVertex.tempId == common_vertex.tempId else h_axis.endVertex.geometry
        p_lt_3d = v_axis.startVertex.geometry if v_axis.endVertex.tempId == common_vertex.tempId else v_axis.endVertex.geometry

        p_lb = sk1.modelToSketchSpace(p_lb_3d)
        p_rb = sk1.modelToSketchSpace(p_rb_3d)
        p_lt = sk1.modelToSketchSpace(p_lt_3d)

        # 4) u/v-richtingen en afmetingen (cm)
        u_vec = unit_vec_2d(p_lb, p_rb)
        v_vec = unit_vec_2d(p_lb, p_lt)
        face_len_u = p_lb.distanceTo(p_rb)

        w_cm = mm(WIDTH_MM)
        h_cm = mm(HEIGHT_MM)
        grid_cm = mm(PATTERN_DISTANCE_MM)
        bottom_offset_cm = mm(DIST_FROM_BOTTOM_MM)

        # 5) Strakke grid-bepaling langs u-as
        qty, margin_u = compute_row_on_grid(face_len_u_cm=face_len_u,
                                            hook_width_cm=w_cm,
                                            grid_cm=grid_cm)
        margin_v = bottom_offset_cm

        # 6) Rechthoek van eerste haak
        p1 = rel_point_2d(p_lb, margin_u,            margin_v,            u_vec, v_vec)       # LB
        p2 = rel_point_2d(p_lb, margin_u + w_cm,     margin_v + h_cm,     u_vec, v_vec)       # RT
        add_rectangle_by_lb_rt(sk1, p1, p2)

        # 7) Extrusie: nieuw body
        prof1 = smallest_profile(sk1)
        ext1  = extrude(root, prof1, mm(BOARD_DEPTH_MM + WIDTH_MM))
        hook_body = ext1.bodies.item(0)
        hook_body.name = 'Haak'

        # 8) 90° haak: kies target-face en maak kleine rechthoek (vierkant)
        target_face = closest_face_along_edge_dir(hook_body, v_axis, h_axis)
        if target_face:
            sk2 = sketches.add(target_face)
            sk2.name = '90 graden haak'

            best_3d = farthest_vertex_on_face(target_face)
            target_2d = sk2.modelToSketchSpace(best_3d)

            # center afleiden via face-bounding box
            bb = target_face.boundingBox
            mid_3d = adsk.core.Point3D.create(
                (bb.minPoint.x + bb.maxPoint.x)/2,
                (bb.minPoint.y + bb.maxPoint.y)/2,
                (bb.minPoint.z + bb.maxPoint.z)/2
            )
            mid_2d = sk2.modelToSketchSpace(mid_3d)

            half_w = w_cm / 2.0
            s_x = -half_w if target_2d.x > mid_2d.x else half_w
            s_y = -half_w if target_2d.y > mid_2d.y else half_w
            center = adsk.core.Point3D.create(target_2d.x + s_x, target_2d.y + s_y, 0)

            p1sq = adsk.core.Point3D.create(center.x - half_w, center.y - half_w, 0)
            p2sq = adsk.core.Point3D.create(center.x + half_w, center.y + half_w, 0)
            sk2.sketchCurves.sketchLines.addTwoPointRectangle(p1sq, p2sq)

            prof2 = smallest_profile(sk2)
            extrude(root, prof2, mm(HOOK_LENGTH_MM),
                    adsk.fusion.FeatureOperations.JoinFeatureOperation)
            sk2.isVisible = False

        # 9) Fillets (alle randen behalve startFaces van eerste extrusie)
        add_edge_fillet(root, hook_body, [f for f in ext1.startFaces], mm(FILLET_RADIUS_MM))

        # 10) Lineair pattern langs h-as met exact grid_cm spacing
        pattern_linear(root, [hook_body], h_axis, qty, grid_cm)

        # Opruimen
        sk1.isVisible = False

    except Exception:
        if ui:
            ui.messageBox(traceback.format_exc())
