import adsk.core, adsk.fusion, traceback

# Constanten
WIDTH_MM = 4.8
HEIGHT_MM = 7.5
BOARD_DEPTH_MM = 5.0
HOOK_LENGTH_MM = 6.0
FILLET_RADIUS_MM = 1.5
PATTERN_DISTANCE_MM = 40.0

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui  = app.userInterface
        design = adsk.fusion.Design.cast(app.activeProduct)
        rootComp = design.rootComponent
        
        # 1. Gebruiker selecties
        (input_val, cancelled) = ui.inputBox('Hoeveel haken?', 'Aantal', '3')
        if cancelled: return
        quantity = int(input_val)

        sel_face = ui.selectEntity('Selecteer het paneelvlak', 'PlanarFaces')
        if not sel_face: return
        face = sel_face.entity

        filter_str = 'LinearEdges,SketchLines'
        sel_h_axis = ui.selectEntity('Selecteer horizontale as (voor patroon)', filter_str)
        if not sel_h_axis: return
        h_axis = sel_h_axis.entity

        sel_v_axis = ui.selectEntity('Selecteer verticale as', filter_str)
        if not sel_v_axis: return
        v_axis = sel_v_axis.entity

        # 2. Richting van de verticale as bepalen
        if hasattr(v_axis, 'geometry') and hasattr(v_axis.geometry, 'direction'):
            v_dir_world = v_axis.geometry.direction
        else:
            v_dir_world = v_axis.geometry.asInfiniteLine().direction
        v_dir_world.normalize()

        # 3. Schets 1: De Basis
        sketches = rootComp.sketches
        sketch1 = sketches.add(face)
        sketch1.name = "Basis Haak"
        center_2d = sketch1.modelToSketchSpace(face.geometry.origin)

        sketch_transform = sketch1.transform
        sketch_transform.invert()
        v_dir_sketch = v_dir_world.copy()
        v_dir_sketch.transformBy(sketch_transform)
        
        is_x_vertical = abs(v_dir_sketch.x) > abs(v_dir_sketch.y)
        w_cm, h_cm = WIDTH_MM / 10.0, HEIGHT_MM / 10.0
        actual_w = h_cm if is_x_vertical else w_cm
        actual_h = w_cm if is_x_vertical else h_cm
        
        sketch1.sketchCurves.sketchLines.addCenterPointRectangle(center_2d, adsk.core.Point3D.create(center_2d.x + (actual_w / 2.0), center_2d.y + (actual_h / 2.0), 0))
        
        # 4. Extrusie 1
        prof1 = sorted(sketch1.profiles, key=lambda p: p.areaProperties().area)[0]
        extrudes = rootComp.features.extrudeFeatures
        dist1 = adsk.core.ValueInput.createByReal((BOARD_DEPTH_MM + WIDTH_MM) / 10.0)
        ext_input1 = extrudes.createInput(prof1, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        ext_input1.setDistanceExtent(False, dist1)
        ext_feat1 = extrudes.add(ext_input1)
        hook_body = ext_feat1.bodies.item(0)
        hook_body.name = "Haak"

        # 5. Schets 2: Het haakje (Vlak-selectie geforceerd op laagste punt langs v_axis)
        target_face = None
        min_score = -1e10
        
        for f in hook_body.faces:
            if abs(f.geometry.normal.dotProduct(face.geometry.normal)) < 0.001:
                # We pakken het middelpunt van het vlak handmatig uit de BoundingBox
                bbox = f.boundingBox
                f_center = adsk.core.Point3D.create(
                    (bbox.minPoint.x + bbox.maxPoint.x) / 2.0,
                    (bbox.minPoint.y + bbox.maxPoint.y) / 2.0,
                    (bbox.minPoint.z + bbox.maxPoint.z) / 2.0
                )
                # Bereken score langs de verticale as
                score = f_center.asVector().dotProduct(v_dir_world)
                if score > min_score:
                    min_score = score
                    target_face = f

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
        pattern_input = pattern_features.createInput(ents, h_axis, adsk.core.ValueInput.createByString(str(quantity)), adsk.core.ValueInput.createByReal(PATTERN_DISTANCE_MM / 10.0), adsk.fusion.PatternDistanceType.SpacingPatternDistanceType)
        
        # FORCEER: Zet de tweede richting op 1 (dus geen patroon de andere kant op)
        #pattern_input.directionTwoQuantity = adsk.core.ValueInput.createByReal(1)

        pattern_input.quantityTwo = adsk.core.ValueInput.createByReal(1)
        pattern_input.isSymmetricInDirectionOne = True
        
        # Voer de pattern uit
        pattern_features.add(pattern_input)
        sketch1.isVisible = False
        if 'sketch2' in locals(): sketch2.isVisible = False

    except:
        if ui: ui.messageBox(traceback.format_exc())
