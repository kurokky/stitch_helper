#!/usr/bin/env python3
import inkex
from inkex import PathElement, Group, units, Rectangle
from lxml import etree
import math

class CrossStitchMain(inkex.EffectExtension):
    INKSTITCH_NS = "http://inkstitch.org/namespace"
    SVG_NS = inkex.NSS['svg']
    def add_arguments(self, pars):
        pars.add_argument("--layer_mode", type=str, default="same")

    def effect(self):
        self._setup_inkstitch_metadata()

        source_layer, rects = self._get_source_rectangles()
        if not rects:
            inkex.errormsg("Please select some object.")
            return

        # 元レイヤーを非表示
        source_layer.style['display'] = 'none'

        # 3. レイヤーモードの準備
        layer_mode = self.options.layer_mode
        base_layer = None
        if layer_mode == "same":
            base_layer = self.get_or_create_layer("cross_stitch_base")

        # ストローク幅の計算
        half_w = self.svg.unittouu('1px') / 2.0

        # 4. 各矩形を処理
        for node in rects:
            self._process_single_rectangle(node, layer_mode, base_layer, half_w)

        self.select_top_layer()

    def _setup_inkstitch_metadata(self):
        inkex.NSS['inkstitch'] = self.INKSTITCH_NS
        
        if "inkstitch" not in self.svg.nsmap:
            self.svg.set('xmlns:inkstitch', self.INKSTITCH_NS)

        metadata = self.svg.find(f'{{{self.SVG_NS}}}metadata')
        if metadata is None:
            metadata = etree.Element(f'{{{self.SVG_NS}}}metadata')
            self.svg.insert(0, metadata)

        target_tag_name = f'{{{self.INKSTITCH_NS}}}inkstitch_svg_version'
        
        # 既存のタグを削除して再作成
        for child in metadata.findall(target_tag_name):
            metadata.remove(child)
        
        new_elem = etree.SubElement(metadata, target_tag_name)
        new_elem.text = "3"

    def _get_source_rectangles(self):
        source_layer = self.svg.get_current_layer()
        
        if source_layer is None:
            layers = [node for node in self.svg if isinstance(node, inkex.Layer)]
            if layers:
                source_layer = layers[0]

        if source_layer is None:
            return None, []

        rects = [node for node in source_layer if isinstance(node, Rectangle)]
        return source_layer, rects

    def _get_valid_fill_color(self, node):
        fill = node.style.get('fill')
        
        # グラデーションチェック
        is_gradient = (fill is not None) and (
            'url(#radialGradient_white_alpha' in fill or 
            'url(#linearGradient' in fill or 
            'url(#mesh' in fill
        )

        if not fill or fill == 'none' or is_gradient:
            return None
        return fill

    def _process_single_rectangle(self, node, layer_mode, base_layer, half_w):
        """1つの矩形ノードに対する処理"""
        fill_color = self._get_valid_fill_color(node)
        if not fill_color:
            return

        # ターゲットレイヤーの決定
        if layer_mode == "separate":
            target_layer = self.get_or_create_layer(f"stitch_{fill_color}")
        else:
            target_layer = base_layer

        # グループ作成
        group = Group()
        target_layer.add(group)

        # パス計算と描画
        self._create_stitch_paths(group, node, fill_color, half_w)

    def _create_stitch_paths(self, group, node, fill_color, half_w):
        bbox = node.bounding_box()
        x_min, x_max = bbox.left, bbox.right
        y_min, y_max = bbox.top, bbox.bottom 
        
        rect_w = x_max - x_min
        rect_h = y_max - y_min
        diag_len = math.hypot(rect_w, rect_h)
        
        if diag_len == 0:
            return

        # オフセット計算
        x_offset = (half_w * diag_len / rect_h) if rect_h != 0 else 0
        y_offset = (half_w * diag_len / rect_w) if rect_w != 0 else 0

        p_bl = (x_min, y_max)
        p_tr = (x_max, y_min)

        # 基本パスの生成
        rail1 = [p_bl, (x_min, y_max - y_offset), (x_max - x_offset, y_min), p_tr]
        rail2 = [p_tr, (x_max, y_min + y_offset), (x_min + x_offset, y_max), p_bl]

        # 短いボーダー (中心線)
        cx = (x_min + x_max) / 2.0
        cy = (y_min + y_max) / 2.0
        
        # 15%の長さを計算
        half_border = (diag_len * 0.15) / 2.0
        ux = (x_max - x_min) / diag_len
        uy = (y_max - y_min) / diag_len
        
        border_route = [
            (cx - ux * half_border, cy - uy * half_border),
            (cx + ux * half_border, cy + uy * half_border)
        ]

        routes_original = [rail1, rail2, border_route]

        # 反転データ生成 (X軸反転)
        routes_flipped = []
        for route in routes_original:
            routes_flipped.append([(2 * cx - p[0], p[1]) for p in route])

        # 描画実行
        self.draw_combined_path(self.INKSTITCH_NS, group, routes_original, fill_color)
        self.draw_combined_path(self.INKSTITCH_NS, group, routes_flipped, fill_color)


    def get_rects(self):
        """カレントレイヤーのRectを取得するヘルパー"""
        layer = self.svg.get_current_layer()
        return [node for node in layer if isinstance(node, Rectangle)]

    def select_top_layer(self):
        svg = self.svg
        layers = []
        for layer in self.svg.findall('svg:g'):
            if layer.get('inkscape:groupmode') == 'layer':
                layers.append(layer)

        if not layers:
            inkex.errormsg("レイヤーが見つかりませんでした。")
            return
        top_layer = layers[-1]
        self.svg.selection.set(top_layer)


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