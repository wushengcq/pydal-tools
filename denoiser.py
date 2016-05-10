#! /usr/bin/python

import os
import sys
from osgeo import gdal, ogr

class Denoiser:
    _target_dir = None
    _shapefile = "polygonized"
    _raster_file = "rasterized"
    _extent = None
    _threshold_x = 0
    _threshold_y = 0
    
    def denoise(self, raster_file):
        self.createTargetDir(raster_file) 
        self.vectorize(raster_file)
        self.removeNoise(self._target_dir + self._shapefile + ".shp")
        self.rasterize(self._target_dir + self._shapefile + ".shp")

    def createTargetDir(self, raster_file):
        self._target_dir = os.path.dirname(raster_file) + "/target/"
        print self._target_dir
        if not os.path.exists(self._target_dir):
             os.makedirs(self._target_dir) 

    def removeNoise(self, shapefile):
        driver = ogr.GetDriverByName("ESRI Shapefile")
        dataSource = driver.Open(shapefile, 1)

        if dataSource is None:
            print "Could not open %s " % (shapefile)
            return

        print "ShapeFile: %s" % (shapefile)
        layer = dataSource.GetLayer()
        featureCount = layer.GetFeatureCount()
        print "Features: %d" % (featureCount)

        extent = layer.GetExtent()
        self._extent = extent
        self._threshold_x = (extent[1] - extent[0]) * 0.2
        self._threshold_y = (extent[3] - extent[2]) * 0.2
        print "Extent: %s" % str(extent) 
        print "Threshold X: %s" % str(self._threshold_x) 
        print "Threshold Y: %s" % str(self._threshold_y) 
       
        print "Keep features:"
        for feature in layer:
            geom = feature.GetGeometryRef()
            if self.boxFilter(geom):
                print "\t" +  str(geom.GetEnvelope())
            else:
                layer.DeleteFeature(feature.GetFID())
        dataSource.Destroy()

    def vectorize(self, raster_file):
        driver = ogr.GetDriverByName("ESRI Shapefile")
        if os.path.exists(self._target_dir + self._shapefile + ".shp"):
            driver.DeleteDataSource(self._target_dir + self._shapefile + ".shp")
        
        raster = gdal.Open(raster_file)
        band = raster.GetRasterBand(1)
        band_array = band.ReadAsArray()
        
        out_data_source = driver.CreateDataSource(self._target_dir + self._shapefile + ".shp")
        out_layer = out_data_source.CreateLayer(self._shapefile, srs=None)
        new_field = ogr.FieldDefn("FLD1", ogr.OFTInteger)
        out_layer.CreateField(new_field)
        
        gdal.Polygonize(band, None, out_layer, 0, [], callback=None )
        out_data_source.Destroy()
        raster = None

    def boxFilter(self, geom):
        box = geom.GetEnvelope()
        if box == self._extent:
            return False
        if box[1] - box[0] <= self._threshold_x or box[3] - box[2] <= self._threshold_y:
            return False
        else:
            return True           
 
    def rasterize(self, shapefile):
        driver = ogr.GetDriverByName("ESRI Shapefile")
        data_source = driver.Open(shapefile, 1)
        if data_source is None:
            print "Could not open %s " % (shapefile)
            return
        layer = data_source.GetLayer()
        
        pixel_size = 1
        x_res = int((self._extent[1] - self._extent[0]) / pixel_size)
        y_res = int((self._extent[3] - self._extent[2]) / pixel_size)

        cols = int(self._extent[1] - self._extent[0]) 
        rows = int(self._extent[3] - self._extent[2])
        raster = gdal.GetDriverByName("GTiff").Create(self._target_dir + self._raster_file + ".tif", x_res, y_res, 1, gdal.GDT_Byte)
        raster.SetGeoTransform((self._extent[0], pixel_size, 0, self._extent[3], 0, -pixel_size))
        raster.GetRasterBand(1).SetNoDataValue(-9999) 
        gdal.RasterizeLayer(raster, [1], layer, burn_values=[255])
        
        data_source.Destroy()
    
if __name__ == "__main__":
    raster_file = "/home/ws/Workspace/python/gdal/source.tif" 
    denoiser = Denoiser()
    denoiser.denoise(raster_file)
    
