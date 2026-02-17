import adsk.core, adsk.fusion, traceback

# Constanten
WIDTH_MM = 4.8
HEIGHT_MM = 7.5
BOARD_DEPTH_MM = 5.0
HOOK_LENGTH_MM = 6.0
FILLET_RADIUS_MM = 1.5
PATTERN_DISTANCE_MM = 40.0
DIST_FROM_BOTTOM_MM = 30

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui  = app.userInterface
        design = adsk.fusion.Design.cast(app.activeProduct)
        rootComp = design.rootComponent

        filter_str = 'LinearEdges' # ,SketchLines

        sel_h_axis = ui.selectEntity('Selecteer onderste horizontale edge van de face ', filter_str)
        if not sel_h_axis: return
        h_axis = sel_h_axis.entity
        if not hasattr(h_axis,'geometry'):
            ui.messageBox('Deze as is geen edge van een object')
            return
        
        sel_v_axis = ui.selectEntity('Selecteer linker verticale edge van de face ', filter_str)
        if not sel_v_axis: return
        v_axis = sel_v_axis.entity
        if not hasattr(v_axis,'geometry'):
            ui.messageBox('Deze as is geen edge van een object')
            return
        
        # 2. Zoek het gemeenschappelijke vlak
        face = None
        for face_h in h_axis.faces:
            for face_v in v_axis.faces:
                if face_h.tempId == face_v.tempId:
                    face = face_h
                    break
            if face:
                break

        # 3. Foutcontrole
        if not face:
            ui.messageBox('Fout: De twee geselecteerde edges liggen niet op hetzelfde vlak.')
            return        
        
        # 1. Haal de hoekpunten op van beide edges
        h_points = [h_axis.startVertex, h_axis.endVertex]
        v_points = [v_axis.startVertex, v_axis.endVertex]

        common_vertex = None

        # 2. Zoek naar een match tussen de twee lijsten
        for v_h in h_points:
            for v_v in v_points:
                # We vergelijken de vertices op basis van hun interne tempId
                if v_h.tempId == v_v.tempId:
                    common_vertex = v_h
                    break

        # 3. Resultaat afhandelen
        if not common_vertex:
            ui.messageBox('Fout: De geselecteerde edges raken elkaar niet.')
            return

        # 1. Bepaal de hoekpunten die NIET het gedeelde punt zijn
        # De overkant van de horizontale as (Rechtsonder)
        p_right_bottom = h_axis.startVertex.geometry if h_axis.endVertex.tempId == common_vertex.tempId else h_axis.endVertex.geometry

        # De overkant van de verticale as (Linksboven)
        p_left_top = v_axis.startVertex.geometry if v_axis.endVertex.tempId == common_vertex.tempId else v_axis.endVertex.geometry

        # 2. Bereken de vector van Linksonder naar Linksboven
        # Dit vertelt ons hoe ver en in welke richting we 'omhoog' moeten
        vec_up = common_vertex.geometry.vectorTo(p_left_top)

        # 3. Pas deze vector toe op het punt Rechtsonder
        # We maken een nieuw punt aan op de locatie van Rechtsonder
        p_right_top = adsk.core.Point3D.create(p_right_bottom.x, p_right_bottom.y, p_right_bottom.z)

        # Verplaats dit nieuwe punt met de 'omhoog' vector
        p_right_top.translateBy(vec_up)

        # 1. Maak de sketch op de face
        sketches = design.rootComponent.sketches
        sketch1 = sketches.add(face)

        # 2. Pak de 3D punten van jouw gekozen edges
        # We gebruiken de common_vertex (linksonder) die we eerder vonden
        p_lb_3d = common_vertex.geometry

        # Vind het uiteinde van de horizontale as (rechtsonder)
        p_rb_3d = h_axis.startVertex.geometry if h_axis.endVertex.tempId == common_vertex.tempId else h_axis.endVertex.geometry

        # Vind het uiteinde van de verticale as (linksboven)
        p_lt_3d = v_axis.startVertex.geometry if v_axis.endVertex.tempId == common_vertex.tempId else v_axis.endVertex.geometry

        # 3. Vertaal deze SPECIFIEKE punten naar de 2D sketch ruimte
        p_lb_2d = sketch1.modelToSketchSpace(p_lb_3d)
        p_rb_2d = sketch1.modelToSketchSpace(p_rb_3d)
        p_lt_2d = sketch1.modelToSketchSpace(p_lt_3d)

        # 4. Bereken nu het punt 'rechtsboven' in 2D
        # We gebruiken 2D vectoren in de sketch om het vierde punt te vinden
        vec_h_2d = adsk.core.Vector2D.create(p_rb_2d.x - p_lb_2d.x, p_rb_2d.y - p_lb_2d.y)
        vec_v_2d = adsk.core.Vector2D.create(p_lt_2d.x - p_lb_2d.x, p_lt_2d.y - p_lb_2d.y)

        # Het punt rechtsboven is: Linksonder + Horizontale vector + Verticale vector
        p_rt_2d = adsk.core.Point2D.create(p_lb_2d.x, p_lb_2d.y)
        p_rt_2d.translateBy(vec_h_2d)
        p_rt_2d.translateBy(vec_v_2d)

        # 1. Definieer de basis-vectoren van jouw gekozen assen
        u_vec = p_lb_2d.vectorTo(p_rb_2d)
        u_vec.normalize()

        v_vec = p_lb_2d.vectorTo(p_lt_2d)
        v_vec.normalize()

        # 2. Afmetingen (Width/Height van de hook-basis)
        w_cm = WIDTH_MM / 10.0
        h_cm = HEIGHT_MM / 10.0
        
        # Totale lengte van de face om te centreren
        face_length_u = p_lb_2d.distanceTo(p_rb_2d)
        
        # 1. Lengte van de verticale as
        v_length = face_length_u
        
        # 2. Instellingen
        margin_v = 0 # 0.6     
        hook_spacing = PATTERN_DISTANCE_MM / 10 + w_cm / 2 # 40 mm (Skadis grid)

        # 3. Berekening
        # Beschikbare lengte voor het grid
        netto_lengte = v_length - margin_v
        
        if netto_lengte < 0:
            quantity = 1
        else:
            # We tellen de eerste haak (op 0) + het aantal keer dat de spacing past
            quantity = int(netto_lengte // hook_spacing) + 1  

        # 3. Bereken de startpositie voor de EERSTE haak
        # (Als je er later 3 wilt, moet de eerste op de juiste plek starten voor het pattern)
        total_hooks_width = ((quantity - 1) * 4.0) + w_cm
        margin_u = (face_length_u - total_hooks_width) / 2.0
        margin_v = DIST_FROM_BOTTOM_MM / 10 # mm vanaf de onderkant

        # Helper om punten te berekenen langs jouw assen
        def get_rel_point(base_pt, dist_u, dist_v, u_dir, v_dir):
            # We maken nieuwe vectoren op basis van de richtingen en schalen ze
            move_u = adsk.core.Vector2D.create(u_dir.x, u_dir.y)
            move_u.scaleBy(dist_u)
            move_v = adsk.core.Vector2D.create(v_dir.x, v_dir.y)
            move_v.scaleBy(dist_v)
            
            new_pt = adsk.core.Point2D.create(base_pt.x, base_pt.y)
            new_pt.translateBy(move_u)
            new_pt.translateBy(move_v)
            return new_pt

        # 4. Bereken de hoekpunten van de master-rechthoek
        # Linksonder van de eerste haak
        p1 = get_rel_point(p_lb_2d, margin_u, margin_v, u_vec, v_vec)
        # Rechtsboven van de eerste haak
        p2 = get_rel_point(p_lb_2d, margin_u + w_cm, margin_v + h_cm, u_vec, v_vec)

        # 5. Teken de rechthoek
        # We gebruiken 4 lijnen in plaats van addTwoPointRectangle omdat we 
        # dan zeker weten dat hij de rotatie van onze vectoren volgt
        p1_3d = adsk.core.Point3D.create(p1.x, p1.y, 0)
        
        # Bereken de andere twee hoeken voor een perfecte rotatie
        corner2 = get_rel_point(p_lb_2d, margin_u + w_cm, margin_v, u_vec, v_vec)
        corner4 = get_rel_point(p_lb_2d, margin_u, margin_v + h_cm, u_vec, v_vec)
        
        lines = sketch1.sketchCurves.sketchLines
        lines.addByTwoPoints(p1_3d, adsk.core.Point3D.create(corner2.x, corner2.y, 0))
        lines.addByTwoPoints(adsk.core.Point3D.create(corner2.x, corner2.y, 0), adsk.core.Point3D.create(p2.x, p2.y, 0))
        lines.addByTwoPoints(adsk.core.Point3D.create(p2.x, p2.y, 0), adsk.core.Point3D.create(corner4.x, corner4.y, 0))
        lines.addByTwoPoints(adsk.core.Point3D.create(corner4.x, corner4.y, 0), p1_3d)

        # 4. Extrusie 1
        prof1 = sorted(sketch1.profiles, key=lambda p: p.areaProperties().area)[0]
        extrudes = rootComp.features.extrudeFeatures
        dist1 = adsk.core.ValueInput.createByReal((BOARD_DEPTH_MM + WIDTH_MM) / 10.0)
        ext_input1 = extrudes.createInput(prof1, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        ext_input1.setDistanceExtent(False, dist1)
        ext_feat1 = extrudes.add(ext_input1)
        hook_body = ext_feat1.bodies.item(0)
        hook_body.name = "Haak"

        # 1. Richting bepalen (Verticale vector)
        v_geom = v_axis.geometry
        v_dir = v_geom.startPoint.vectorTo(v_geom.endPoint)
        v_dir.normalize()

        # 2. Referentiepunt op de onderste as
        h_start = h_axis.geometry.startPoint

        target_face = None
        min_dist = float('inf')

        for face in hook_body.faces:
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

        if target_face:
            sketch2 = sketches.add(target_face)
            sketch2.name = "90 graden haak"
            
            # Verste punt zoeken
            start_3d = face.geometry.origin
            best_pt_3d = None
            max_d = -1.0
            for edge in target_face.edges:
                for v in [edge.startVertex, edge.endVertex]:
                    d = v.geometry.distanceTo(start_3d)
                    if d > max_d:
                        max_d = d
                        best_pt_3d = v.geometry
            
            target_2d = sketch2.modelToSketchSpace(best_pt_3d)
            
            # Bepaal het midden van de schets voor de verschuivingsrichting
            # We berekenen het midden van de bounding box van het vlak opnieuw
            bb = target_face.boundingBox
            mid_3d = adsk.core.Point3D.create((bb.minPoint.x + bb.maxPoint.x)/2, (bb.minPoint.y + bb.maxPoint.y)/2, (bb.minPoint.z + bb.maxPoint.z)/2)
            mid_2d = sketch2.modelToSketchSpace(mid_3d)
            
            half_w = (WIDTH_MM / 10.0) / 2.0
            s_x = -half_w if target_2d.x > mid_2d.x else half_w
            s_y = -half_w if target_2d.y > mid_2d.y else half_w
            
            final_center = adsk.core.Point3D.create(target_2d.x + s_x, target_2d.y + s_y, 0)
            p1 = adsk.core.Point3D.create(final_center.x - half_w, final_center.y - half_w, 0)
            p2 = adsk.core.Point3D.create(final_center.x + half_w, final_center.y + half_w, 0)
            sketch2.sketchCurves.sketchLines.addTwoPointRectangle(p1, p2)
            
            prof2 = sorted(sketch2.profiles, key=lambda p: p.areaProperties().area)[0]
            dist2 = adsk.core.ValueInput.createByReal(HOOK_LENGTH_MM / 10.0)
            ext_input2 = extrudes.createInput(prof2, adsk.fusion.FeatureOperations.JoinFeatureOperation)
            ext_input2.setDistanceExtent(False, dist2)
            extrudes.add(ext_input2)

        # 6. Fillets & Pattern
        edge_col = adsk.core.ObjectCollection.create()
        start_ids = [sf.tempId for sf in ext_feat1.startFaces]
        for edge in hook_body.edges:
            if not any(f.tempId in start_ids for f in edge.faces):
                edge_col.add(edge)
        
        if edge_col.count > 0:
            f_in = rootComp.features.filletFeatures.createInput()
            f_in.addConstantRadiusEdgeSet(edge_col, adsk.core.ValueInput.createByReal(FILLET_RADIUS_MM / 10.0), True)
            rootComp.features.filletFeatures.add(f_in)

        # 6. Rectangular Pattern (Alleen langs Axis 1)
        ents = adsk.core.ObjectCollection.create()
        ents.add(hook_body)
        
        # Maak de input voor het patroon
        pattern_features = rootComp.features.rectangularPatternFeatures
        pattern_input = pattern_features.createInput(ents, h_axis, adsk.core.ValueInput.createByString(str(quantity)), adsk.core.ValueInput.createByReal(-PATTERN_DISTANCE_MM / 10.0), adsk.fusion.PatternDistanceType.SpacingPatternDistanceType)
        
        # FORCEER: Zet de tweede richting op 1 (dus geen patroon de andere kant op)
        #pattern_input.directionTwoQuantity = adsk.core.ValueInput.createByReal(1)

        pattern_input.quantityTwo = adsk.core.ValueInput.createByReal(1)
        pattern_input.isSymmetricInDirectionOne = False
        
        # Voer de pattern uit
        pattern_features.add(pattern_input)
        sketch1.isVisible = False
        if 'sketch2' in locals(): sketch2.isVisible = False

    except:
        if ui: ui.messageBox(traceback.format_exc())
