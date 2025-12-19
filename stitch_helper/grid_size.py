#!/usr/bin/env python3
import inkex
from lxml import etree
import math

class GridSize(inkex.EffectExtension):
    def add_arguments(self, pars):
        pars.add_argument("--dot_size", type=str, default="", help="Dot Grid Size in mm")

    def effect(self):
        grid_size = float(self.options.dot_size)
        namedview = self.svg.namedview
        size = grid_size
        svg = self.svg
    
        for grid in namedview.findall(inkex.addNS('grid', 'inkscape')):
            namedview.remove(grid)
        
        grid = etree.SubElement(namedview, inkex.addNS('grid', 'inkscape'))
        grid.set('type', 'xygrid')
        grid.set('units', 'mm')
        grid.set('spacingx', str(grid_size))
        grid.set('spacingy', str(grid_size))
        grid.set('originx', '0')
        grid.set('originy', '0')
        namedview.set('showgrid', 'true')

if __name__ == '__main__':
    GridSize().run()