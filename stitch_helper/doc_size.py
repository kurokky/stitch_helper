#!/usr/bin/env python3
import inkex
#from inkex import PathElement, Group, units
#from lxml import etree
import math

class DocSize(inkex.EffectExtension):
    def add_arguments(self, pars):
        pars.add_argument("--size_wh", type=str, default="10,10")

    def effect(self):
        size_wh_str = self.options.size_wh
        size_w_str, size_h_str = size_wh_str.split(',')
        size_w = float(size_w_str)
        size_h = float(size_h_str)
        self.svg.set('width', f'{size_w}mm')
        self.svg.set('height', f'{size_h}mm')
        self.svg.set('viewBox', f'0 0 {size_w} {size_h}')

if __name__ == '__main__':
    DocSize().run()