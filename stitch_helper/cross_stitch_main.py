#!/usr/bin/env python3
import inkex
from inkex import PathElement, Group, units
from lxml import etree
import math

class CrossStitchMain(inkex.EffectExtension):
    def add_arguments(self, pars):
        pars.add_argument("--layer_mode", type=str, default="same")

    def effect(self):
        self.generate_stitch()

    def generate_stitch(self):
        if not self.svg.selection:
            inkex.errormsg("矩形を選択してください。")
            return
        # Ink/Stitchの名前空間URIを定義
        INKSTITCH_NS = "http://inkstitch.org/namespace"
        # nkexのNSS辞書に登録（lxmlにこのプレフィックスを使わせるため）
        inkex.NSS['inkstitch'] = INKSTITCH_NS
        if "inkstitch" not in self.svg.nsmap:
            #強制的に属性を追加
            self.svg.set('xmlns:inkstitch', INKSTITCH_NS)
        
        # add inkstitch version
        SVG_NS = inkex.NSS['svg']
        metadata = self.svg.find(f'{{{SVG_NS}}}metadata')
        if metadata is None:
            metadata = etree.Element(f'{{{SVG_NS}}}metadata')
            self.svg.insert(0, metadata)
        target_tag_name = f'{{{INKSTITCH_NS}}}inkstitch_svg_version'
        
        for child in metadata.findall(target_tag_name):
            metadata.remove(child)
        new_elem = etree.SubElement(metadata, target_tag_name)
        new_elem.text = "3"


        layer_mode = self.options.layer_mode
        base_layer = None

        # 現在アクティブなレイヤー（矩形があるレイヤー）を取得
        source_layer = self.svg.get_current_layer()
        # なければ最背面のレイヤーを取得
        if source_layer is None:
            layers = [node for node in self.svg if isinstance(node, inkex.Layer)]
            source_layer = layers[0]
        #source_layer.style['opacity'] = '0.4'
        source_layer.style['display'] = 'none'

        if layer_mode == "same":
            base_layer = "cross_stitch_base"
            base_layer = self.get_or_create_layer(target_layer_name)

        stroke_width_str = '1px'
        w = self.svg.unittouu(stroke_width_str)
        half_w = w / 2.0

        for node in self.svg.selection:
            if isinstance(node, inkex.Rectangle):
                
                # --- 色の取得 ---
                fill_color = node.style.get('fill')
                is_alpha_gradient = (fill_color is not None) and ('url(#radialGradient_white_alpha' in fill_color)
                if not fill_color or fill_color == 'none' or is_alpha_gradient :
                    #fill_color = '#000000'
                    continue

                # --- ターゲットレイヤーの決定 ---
                target_layer = None
                
                if layer_mode == "separate":
                    # 色ごとのレイヤーを作成/取得
                    layer_name = f"stitch_{fill_color}"
                    target_layer = self.get_or_create_layer(layer_name)
                else:
                    # 固定レイヤーを使用
                    target_layer = base_layer

                # --- グループの作成 ---
                group = Group()
                target_layer.add(group)
                
                # --- 形状計算 (共通ロジック) ---
                bbox = node.bounding_box()
                x_min, x_max = bbox.left, bbox.right
                y_min, y_max = bbox.top, bbox.bottom 
                
                rect_w = x_max - x_min
                rect_h = y_max - y_min
                diag_len = math.hypot(rect_w, rect_h)
                
                if diag_len == 0: continue

                # 切片計算 (はみ出し防止)
                if rect_h == 0: x_offset = 0
                else:           x_offset = half_w * diag_len / rect_h
                
                if rect_w == 0: y_offset = 0
                else:           y_offset = half_w * diag_len / rect_w

                p_bl = (x_min, y_max)
                p_tr = (x_max, y_min)

                # レール生成
                rail1 = [p_bl, (x_min, y_max - y_offset), (x_max - x_offset, y_min), p_tr]
                rail2 = [p_tr, (x_max, y_min + y_offset), (x_min + x_offset, y_max), p_bl]

                # 短いボーダー (長さ15%)
                cx = (x_min + x_max) / 2.0
                cy = (y_min + y_max) / 2.0
                vx, vy = x_max - x_min, y_max - y_min
                border_len = diag_len * 0.15
                half_border = border_len / 2.0
                ux, uy = vx / diag_len, vy / diag_len
                
                p_border_start = (cx - ux * half_border, cy - uy * half_border)
                p_border_end   = (cx + ux * half_border, cy + uy * half_border)
                border_route = [p_border_start, p_border_end]

                routes_original = [rail1, rail2, border_route]

                # 反転データ
                routes_flipped = []
                for route in routes_original:
                    flipped_route = [(2 * cx - p[0], p[1]) for p in route]
                    routes_flipped.append(flipped_route)

                # --- 描画実行 ---
                self.draw_combined_path(INKSTITCH_NS, group, routes_original, fill_color)
                self.draw_combined_path(INKSTITCH_NS, group, routes_flipped, fill_color)

    def get_or_create_layer(self, layer_name):
        #male layer
        for layer in self.svg.findall('svg:g'):
            if layer.get('inkscape:groupmode') == 'layer' and layer.get('inkscape:label') == layer_name:
                return layer
        
        new_layer = self.svg.add(Group())
        new_layer.set('inkscape:groupmode', 'layer')
        new_layer.set('inkscape:label', layer_name)
        # IDを一意にするため名前を利用
        safe_name = layer_name.replace('#', '').replace(' ', '_')
        new_layer.set('id', f"layer_{safe_name}") 
        return new_layer

    def draw_combined_path(self,INKSTITCH_NS , parent_group, routes, color):
        def fmt(p):
            return f"{p[0]:.6g},{p[1]:.6g}"

        d_parts = []
        total_nodes = 0
        
        for route in routes:
            d_parts.append(f"M {fmt(route[0])}")
            for p in route[1:]:
                d_parts.append(f"L {fmt(p)}")
            total_nodes += len(route)

        d_str = " ".join(d_parts)

        path_elem = PathElement()
        path_elem.set('d', d_str)
        path_elem.set('transform', 'scale(1.0)')
        path_elem.set('sodipodi:nodetypes', 'c' * total_nodes) 
        #path_elem.set('inkstitch:satin_column', 'true')
        path_elem.set(f'{{{INKSTITCH_NS}}}satin_column', 'true')

        path_elem.style.update({
            'fill': 'none',
            'stroke': color,
            'stroke-width': str(units.convert_unit('0.1px', 'mm')) ,
            'stroke-linecap': 'butt',
            'stroke-linejoin': 'miter'
        })
        
        parent_group.add(path_elem)


if __name__ == '__main__':
    CrossStitchMain().run()