# -*- coding: utf-8 -*-
"""
@author: mcreng
"""

import itertools
import functools
import cartopy
import cartopy.io.shapereader as shpreader
from matplotlib.figure import Figure
from shapely.geometry import Point, Polygon
from matplotlib.backends.qt_compat import QtWidgets, is_pyqt5
from util import timeit
import file_reader as fr

if is_pyqt5():
    from matplotlib.backends.backend_qt5agg import (
        FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
else:
    from matplotlib.backends.backend_qt4agg import (
        FigureCanvas, NavigationToolbar2QT as NavigationToolbar)


class WorldMapCanvas(FigureCanvas):
    def __init__(self, parent=None, width=8, height=6, dpi=150):
        """
        Initialization
        """
        # Initialize figure and axis
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.ax = fig.add_subplot(
            1, 1, 1, projection=cartopy.crs.PlateCarree())
        self.ax.stock_img()
        self.ax.add_feature(cartopy.feature.LAND, zorder=1)
        self.ax.add_feature(cartopy.feature.BORDERS, zorder=2)
        self.ax.add_feature(cartopy.feature.COASTLINE, zorder=2)
        fig.tight_layout()

        # Initialize FigureCanvas
        FigureCanvas.__init__(self, fig)
        self.setParent(parent)
        FigureCanvas.setSizePolicy(self,
                                   QtWidgets.QSizePolicy.Expanding,
                                   QtWidgets.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

        # Initialize some variables we use
        self.countries = shpreader.Reader(shpreader.natural_earth(resolution='110m',
                                                                  category='cultural',
                                                                  name='admin_0_countries')).records()
        tmp, self.countries = itertools.tee(self.countries)
        self.land = cartopy.feature.ShapelyFeature(
            (c.geometry for c in tmp), cartopy.crs.PlateCarree(), facecolor=cartopy.feature.COLORS['land'])

        # Initialize filereader
        self.fr = fr.FileReader('data.txt')
        # Read file
        self.sel_countries = self.fr.read_countries()
        # Fill in those in file
        self.fill_country(self.find_country_a3(self.sel_countries), 1)

    def on_click(self, event):
        """
        On mouse click handler
        """
        # Locate country from x/y
        country = self.find_country_xy(event.xdata, event.ydata)
        # Fill in the country
        self.fill_country(country, event.button)

    def on_move(self, event):
        """
        On mouse move handler
        """
        # Updates the value info of screen from top right corner
        # Currently this is a workaround since the '[]' is hardcoded
        # Will wait until new version of matplotlib and change this
        country = self.find_country_xy(event.xdata, event.ydata)
        if country:
            self.ax.images[0].format_cursor_data = lambda data: country.attributes['NAME_LONG']

    def get_new_land(self, country):
        for l in self.land.geometries():
            tmp, country = itertools.tee(country)
            for c in tmp:
                l = l.difference(c.geometry)
            yield l

    def fill_country(self, country, button):
        """
        Function to fill in countries
        """
        # Need an iterable
        if not isinstance(country, itertools.filterfalse):
            if not country:
                return
            country = [country]
        if button == 1:
            # check if country is empty
            tmp, country = itertools.tee(country)
            try:
                next(tmp)
            except StopIteration:
                return
            # Get current extent so we can apply again after clearing axis
            ext = self.ax.get_extent()
            # Duplicate country since it is needed twice
            country, country2 = itertools.tee(country)
            # Redraw all
            self.ax.clear()
            self.ax.stock_img()
            self.land = cartopy.feature.ShapelyFeature(self.get_new_land(
                country), cartopy.crs.PlateCarree(), facecolor=cartopy.feature.COLORS['land'])
            self.ax.add_feature(self.land, zorder=1)
            self.ax.add_feature(cartopy.feature.BORDERS, zorder=2)
            self.ax.add_feature(cartopy.feature.COASTLINE, zorder=2)
            self.ax.set_xlim([ext[0], ext[1]])
            self.ax.set_ylim([ext[2], ext[3]])
            self.draw()
            self.flush_events()
            # Append unique country elements to list
            for c in country2:
                self.sel_countries.append(c.attributes['BRK_A3'])
            self.sel_countries = list(set(self.sel_countries))

        elif button == 3:
            # Get current extent so we can apply again after clearing axis
            ext = self.ax.get_extent(crs=cartopy.crs.PlateCarree())
            # Duplicate country since it is needed twice
            country, country2 = itertools.tee(country)
            # Redraw all
            self.ax.clear()
            self.ax.stock_img()
            # Find new self.land to print
            self.land = self.land.geometries()
            # Add back the geometric objects by chaining it to iter
            self.land = itertools.chain(
                self.land, (c.geometry for c in country))
            self.land = cartopy.feature.ShapelyFeature(
                self.land, cartopy.crs.PlateCarree(), facecolor=cartopy.feature.COLORS['land'])
            self.ax.add_feature(self.land, zorder=1)
            self.ax.add_feature(cartopy.feature.BORDERS, zorder=2)
            self.ax.add_feature(cartopy.feature.COASTLINE, zorder=2)
            self.ax.set_xlim([ext[0], ext[1]])
            self.ax.set_ylim([ext[2], ext[3]])
            self.draw()
            self.flush_events()
            # Delete entries from list
            for c in country2:
                try:
                    self.sel_countries.remove(c.attributes['BRK_A3'])
                except:
                    continue

        self.fr.write_countries(self.sel_countries)

    def find_country_xy(self, x, y):
        """
        Return country object based on location
        """
        local_countries, self.countries = itertools.tee(self.countries)
        try:
            point = Point(x, y)
            country = next(itertools.filterfalse(
                lambda country: not country.geometry.intersects(point), local_countries))
            return country
        except:
            return None

    def find_country_a3(self, a3):
        """
        Return country object based on BRK_A3 code, support a3 as list
        """
        local_countries, self.countries = itertools.tee(self.countries)
        country = itertools.filterfalse(
            lambda country: country.attributes['BRK_A3'] not in a3, local_countries)
        return country
