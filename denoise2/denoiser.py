#! /usr/bin/python

import sys
import os
import Image
import numpy as np
import matplotlib.pyplot as plt
from skimage import io
from osgeo import gdal, ogr, osr

class Denoiser2:
    T = (464,432,480,308,306,
         240,216,184,180,178,153,154,
         90,89,  58,54,51, 30,27, 23, 496,488,440,436,434,410,409,
         400,304,208,176,152,88,52,50,26,25,22,19, 272,144,80,48,24,20,18,17, 16
         ,21,336)

    def denoise(self, raster_file):
        full_path = os.path.abspath(raster_file)
        img = io.imread(full_path)
        self.slim(img)
        self.erase(img)
        tmp_tif = self.createTargetDir(full_path) + "tmp1.tif"
        io.imsave(tmp_tif, img)
        print "Dnoised result by raster method : " + tmp_tif

        shape_file = self.vectorize(tmp_tif)
        self.removeNoise(shape_file)
        print "Dnoised result by vector method : " + shape_file

        result_tif = self.rasterize(shape_file)
        self.flipImage(result_tif)
        print "Export result to : " + result_tif

    def createTargetDir(self, raster_file):
        target_dir = os.path.dirname(raster_file) + "/target/"
        print "Target folder : " + target_dir
        if not os.path.exists(target_dir):
             os.makedirs(target_dir)
        return target_dir

    def trace(self, img, x, y):
        stat = []
        for k1 in range(-1,2):
            for k2 in range(-1,2):
                if k1 != 0 or k2 != 0:
                    if img[x+k1,y+k2] == 255:
                        stat.append([x+k1,y+k2])

        if len(stat) == 0:
            img[x,y] = 0
        elif len(stat) == 1:
            img[x,y] = 0
            self.trace(img, stat[0][0], stat[0][1])

    def slim(self, img):
        rs,cs = img.shape
        for r in range(1, rs-1):
            for c in range(1, cs-1):
                if img[r,c] == 0:
                    continue

                m = 0<<8
                n = 1<<8
                for k1 in range(-1,2):
                    for k2 in range(-1,2):
                        if img[r+k1, c+k2] == 255:
                            m = m | n
                        n >>= 1
                for i in range(len(self.T)):
                    if m == self.T[i]:
                        img[r,c] = 0
                        break
        return img

    def erase(self, img):
        rs,cs = img.shape
        for r in range(1, rs-1):
            for c in range(1, cs-1):
                if r == rs-2 and c == cs-2:
                    return False
                else:
                    if img[r][c] == 255:
                        self.trace(img, r, c)

    def vectorize(self, raster_file):
        tmp_shp = os.path.dirname(raster_file) + "/tmp2.shp"
        driver = ogr.GetDriverByName("ESRI Shapefile")
        if os.path.exists(tmp_shp):
            driver.DeleteDataSource(tmp_shp)

        raster = gdal.Open(raster_file)
        band = raster.GetRasterBand(1)
        #band_array = band.ReadAsArray()
        out_data_source = driver.CreateDataSource(tmp_shp)
        out_layer = out_data_source.CreateLayer("f1", None)
        new_field = ogr.FieldDefn("FLD1", ogr.OFTInteger)
        out_layer.CreateField(new_field)
        gdal.Polygonize(band, None, out_layer, 0, [], callback=None )
        out_data_source.Destroy()
        raster = None

        return tmp_shp

    def removeNoise(self, shapefile):
        driver = ogr.GetDriverByName("ESRI Shapefile")
        dataSource = driver.Open(shapefile, 1)

        if dataSource is None:
            print "Could not open %s " % (shapefile)
            return

        #print "ShapeFile: %s" % (shapefile)
        layer = dataSource.GetLayer()
        featureCount = layer.GetFeatureCount()
        #print "Features: %d" % (featureCount)

        extent = layer.GetExtent()
        box = None
        fid = None
        for feature in layer:
            geom = feature.GetGeometryRef()
            if geom is None:
                continue
            if self.boxFilter(geom, extent):
                layer.DeleteFeature(feature.GetFID())
            else:
                print "keep : " + str(feature.GetFID())

        dataSource.Destroy()

    def boxFilter(self, geom, env):
        threshold_x = (env[1] - env[0]) * 0.2
        threshold_y = (env[3] - env[2]) * 0.2
        box = geom.GetEnvelope()
        if box == env:
            return True
        if box[1] - box[0] <= threshold_x or box[3] - box[2] <= threshold_y:
            return True
        else:
            return False

    def rasterize(self, shapefile):
        tif_file = os.path.dirname(shapefile) + "/result.tiff"

        driver = ogr.GetDriverByName("ESRI Shapefile")
        data_source = driver.Open(shapefile, 1)
        if data_source is None:
            print "Could not open %s " % (shapefile)
            return
        layer = data_source.GetLayer()
        extent = layer.GetExtent()

        pixel_size = 1
        x_res = int((extent[1] - extent[0]) / pixel_size)
        y_res = int((extent[3] - extent[2]) / pixel_size)

        cols = int(extent[1] - extent[0])
        rows = int(extent[3] - extent[2])
        raster = gdal.GetDriverByName("GTiff").Create(tif_file, x_res, y_res, 1, gdal.GDT_Byte)
        raster.SetGeoTransform((extent[0], pixel_size, 0, extent[3], 0, -pixel_size))
        raster.GetRasterBand(1).SetNoDataValue(-9999)
        gdal.RasterizeLayer(raster, [1], layer, burn_values=[255])

        data_source.Destroy()
        return tif_file

    def flipImage(self, raster_file):
        img = Image.open(raster_file)
        out = img.transpose(Image.FLIP_TOP_BOTTOM)
        out.save(raster_file, "TIFF")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print "Usage : denoiser.py sample.tif"
    denoiser = Denoiser2()
    denoiser.denoise(sys.argv[1])
