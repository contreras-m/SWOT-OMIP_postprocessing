#import plot_ration_psdglobal as ppR

from datetime import datetime
import s3fs
import xarray as xr
import pyinterp
from widetrax import DataPreprocessing as dp
from widetrax import Spectra as sp
import numpy as np
import json
from watermark import watermark
import time
import platform
from shapely.geometry import shape, box
from scipy.signal import savgol_filter
from collections import defaultdict

def read_json_s3(endpoint_url,file,mode='online'):
        if mode=='online':
            fs = s3fs.S3FileSystem(key="xxx",secret="xxx", endpoint_url=endpoint_url)
            with fs.open(file, mode='rb') as fileObj:
                data = json.load(fileObj)
        elif mode=='offline':
            with open(file, mode='rb') as fileObj:
                data = json.load(fileObj)
        return data

def read_season(season1,box,endpoint_url,models,mode = 'online',folder = "project-meom-ige/OMIP/Global/"):
    season=season1
    spectrumJFM=[]
    freqJFM=[]
    # Plot spectrum JFM
    for imod in models:
        if mode=="online":
            s3_folder= folder # "project-meom-ige/OMIP/"
            filename = f"s3://"+s3_folder+ imod +"/Global_box_" + str(box) + "_" + season + "_" + imod + ".json"
            data=read_json_s3(endpoint_url,filename)
            spectrumJFM.append(data["Spectra"])
            freqJFM.append(data["Frequency"])
        elif mode=="offline":
            local_folder= folder #"GLOBALv2/"
            filename = local_folder+ imod +"/Global_box_" + str(box) + "_" + season1 + "_" + imod + ".json"
            data=read_json_s3(endpoint_url,filename,mode='offline')
            spectrumJFM.append(data["Spectra"])
            freqJFM.append(data["Frequency"])
    return spectrumJFM, freqJFM
    

def season_cum_fall(models,selected,wlmin,wlmax,north_boxes,south_boxes,endpoint_url,rseason,
                    season1='JFM',season2='JAS',season3='AMJ',season4='OND',modeload="offline",folder = "GLOBALv2/" ):
    """
    Computes seasonal (for any season) cumulative spectra. Be careful with the season definition
    """
    box=0
    psdsW=np.zeros((len(selected),len(models)))
    psdsSe=np.zeros((len(selected),len(models)))
    for i, poly in enumerate(selected):

        # frequency do not change with the season
        spectrumJFM,freqJFM=read_season(season1,box,endpoint_url,models,mode=modeload,folder=folder)
        spectrumJAS,freqJAS=read_season(season2,box,endpoint_url,models,mode=modeload,folder=folder)
        spectrumAMJ,freqJFM=read_season(season3,box,endpoint_url,models,mode=modeload,folder=folder)
        spectrumOND,freqJFM=read_season(season4,box,endpoint_url,models,mode=modeload,folder=folder)
        wavelength=1/np.array(freqJFM)

        for imodel in range(len(models)): 
            poswl=np.where((wavelength[imodel]>wlmin) & (wavelength[imodel]<wlmax))
            spectrumJFMM=np.array(spectrumJFM[imodel])
            spectrumJASM=np.array(spectrumJAS[imodel])
            spectrumAMJM=np.array(spectrumAMJ[imodel])
            spectrumONDM=np.array(spectrumOND[imodel])
            freqJASM = np.array(freqJAS[imodel])   # now it's a 2D array
            dk = np.gradient(freqJASM[poswl[0]])
            if box in north_boxes:
                psdsW[box,imodel]  = np.cumsum(spectrumJFMM[poswl[0]] * dk)[-1]
                if rseason=='spring':
                    psdsSe[box,imodel]  = np.cumsum(spectrumAMJM[poswl[0]] * dk)[-1]
                elif rseason=='fall':
                    psdsSe[box,imodel]  = np.cumsum(spectrumONDM[poswl[0]] * dk)[-1]
            elif box in south_boxes:
                psdsW[box,imodel]  = np.cumsum(spectrumJASM[poswl[0]] * dk)[-1]
                if rseason=='spring':
                    psdsSe[box,imodel]  = np.cumsum(spectrumONDM[poswl[0]] * dk)[-1]
                elif rseason=='fall':
                    psdsSe[box,imodel]  = np.cumsum(spectrumAMJM[poswl[0]] * dk)[-1]
        box=box+1
    return psdsW, psdsSe,freqJAS
    
def season_cum(models,selected,wlmin,wlmax,north_boxes,south_boxes,endpoint_url,season1,season2,
               modeload="online",folder="project-meom-ige/OMIP/Global/"):
    """
    Computes seasonal (winter (psdsW) and summer (psdsS) cumulative spectra 
    """
    box=0
    psdsW=np.zeros((len(selected),len(models)))
    psdsS=np.zeros((len(selected),len(models)))

    for i, poly in enumerate(selected):
        spectrumJFM,freqJFM=read_season(season1,box,endpoint_url,models,mode=modeload,folder=folder)
        spectrumJAS,freqJAS=read_season(season2,box,endpoint_url,models,mode=modeload,folder=folder)

        wavelength=1/np.array(freqJFM)
            
        for imodel in range(len(models)): 
            poswl=np.where((wavelength[imodel]>wlmin) & (wavelength[imodel]<wlmax))
            spectrumJFMM=np.array(spectrumJFM[imodel])
            spectrumJASM=np.array(spectrumJAS[imodel])
            freqJASM = np.array(freqJAS[imodel])   # now it's a 2D array
            dk = np.gradient(freqJASM[poswl[0]])
            if box in north_boxes:
                psdsW[box,imodel]  = np.cumsum(spectrumJFMM[poswl[0]] * dk)[-1]
                psdsS[box,imodel]  = np.cumsum(spectrumJASM[poswl[0]] * dk)[-1]
            elif box in south_boxes:
                psdsW[box,imodel]  = np.cumsum(spectrumJASM[poswl[0]] * dk)[-1]
                psdsS[box,imodel]  = np.cumsum(spectrumJFMM[poswl[0]] * dk)[-1]
        box=box+1

    return psdsW, psdsS,freqJAS

def season_slope(models,selected,wlmin,wlmax,north_boxes,south_boxes,endpoint_url,season1,season2,
                 modeload="online",folder="project-meom-ige/OMIP/Global/"):
    """
    Computes seasonal slope (m_slopeW, m_slopeS). 
    """
    box=0
    m_slopeW=np.zeros((len(selected),len(models)))
    m_slopeS=np.zeros((len(selected),len(models)))
    s_slopeW=np.zeros((len(selected),len(models)))
    s_slopeS=np.zeros((len(selected),len(models)))
    for i, poly in enumerate(selected):

        spectrumJFM,freqJFM=read_season(season1,box,endpoint_url,models,mode=modeload,folder=folder)
        spectrumJAS,freqJAS=read_season(season2,box,endpoint_url,models,mode=modeload,folder=folder)

        wavelength=1/np.array(freqJFM)
        #poswl=np.where((wavelength>50) & (wavelength<500))
        #freqJASM = np.array(freqJAS[0])   # now it's a 2D array
        for imodel in range(len(models)): 
            poswl=np.where((wavelength[imodel]>wlmin) & (wavelength[imodel]<wlmax))
            spectrumJFMM=np.array(spectrumJFM[imodel])
            spectrumJASM=np.array(spectrumJAS[imodel])
            freqJASM = np.array(freqJAS[imodel])   # now it's a 2D array
            dk = np.gradient(freqJASM[poswl[0]])
            if box in north_boxes:
            #psdsW=(np.cumsum(spectrumJFMM[poswl[0]] * dk))
            #psdsS=(np.cumsum(spectrumJASM[poswl[0]] * dk))
                psdsW=((spectrumJFMM[poswl[0]] ))
                psdsS=((spectrumJASM[poswl[0]] ))
                x_slope = np.log10(freqJASM[poswl[0]])
                y_slope = np.log10(psdsW)
                slopeW  = -np.gradient(y_slope, x_slope)
                y_slope = np.log10(psdsS)
                slopeS  = -np.gradient(y_slope, x_slope)
                m_slopeW[box,imodel]=np.nanmean(slopeW)
                s_slopeW[box,imodel]=np.nanstd(slopeW)
                m_slopeS[box,imodel]=np.nanmean(slopeS)
                s_slopeS[box,imodel]=np.nanstd(slopeS)
            elif box in south_boxes:
                psdsW=((spectrumJASM[poswl[0]]))
                psdsS=((spectrumJFMM[poswl[0]] ))
                x_slope = np.log10(freqJASM[poswl[0]])
                y_slope = np.log10(psdsW)
                slopeW  = -np.gradient(y_slope, x_slope)
                y_slope = np.log10(psdsS)
                slopeS  = -np.gradient(y_slope, x_slope)
                m_slopeW[box,imodel]=np.nanmean(slopeW)
                s_slopeW[box,imodel]=np.nanstd(slopeW)
                m_slopeS[box,imodel]=np.nanmean(slopeS)
                s_slopeS[box,imodel]=np.nanstd(slopeS)

        box=box+1



    return m_slopeW, m_slopeS, s_slopeW, s_slopeS

def season_slope_fall(models, selected, wlmin, wlmax, north_boxes, south_boxes,endpoint_url,rseason,
                      season1='JFM',season2='JAS',season3='AMJ',season4='OND',
                      modeload="online",folder="project-meom-ige/OMIP/Global/"):
    """
    Computes seasonal slope for dynamic lists of models.
    """
    
    m_slopeW=np.zeros((len(selected),len(models)))
    m_slopeS=np.zeros((len(selected),len(models)))
    s_slopeW=np.zeros((len(selected),len(models)))
    s_slopeS=np.zeros((len(selected),len(models)))

    for i, poly in enumerate(selected):

            
        box = i  # Synchronize box index with loop index
        
        spectrum_s1, freq_s1 = [], []
        spectrum_s2, freq_s2 = [], []
        spectrum_s3, freq_s3 = [], []
        spectrum_s4, freq_s4 = [], []

        # Fetch data for all models for Season 1 & Season 2
        spectrum_s1, freq_s1=read_season(season1,box,endpoint_url,models,mode=modeload,folder=folder)
        spectrum_s2, freq_s2=read_season(season2,box,endpoint_url,models,mode=modeload,folder=folder)
        spectrum_s3, freq_s3=read_season(season3,box,endpoint_url,models,mode=modeload,folder=folder)
        spectrum_s4, freq_s4=read_season(season4,box,endpoint_url,models,mode=modeload,folder=folder)


        # Calculate ratios dynamically per model
        for imodel, imod in enumerate(models):
            freq = np.array(freq_s1[imodel])
            wavelength = 1.0 / freq
            
            # Use dynamic wavelength limits passed to the function
            poswl = np.where((wavelength > wlmin) & (wavelength < wlmax))[0]
            
            spec_s1 = np.array(spectrum_s1[imodel])[poswl]
            spec_s2 = np.array(spectrum_s2[imodel])[poswl]
            spec_s3 = np.array(spectrum_s3[imodel])[poswl]
            spec_s4 = np.array(spectrum_s4[imodel])[poswl]
            freq_filtered = freq[poswl]
            dk = np.gradient(freq_filtered)
            if box in north_boxes:
                x_slope = np.log10(freq_filtered)
                y_slope = np.log10(spec_s1)
                slopeW  = -np.gradient(y_slope, x_slope)
                if rseason == "spring":
                    y_slope = np.log10(spec_s3)
                elif rseason == "summer":
                    y_slope = np.log10(spec_s2)
                slopeS  = -np.gradient(y_slope, x_slope)
                m_slopeW[box,imodel]=np.nanmean(slopeW)
                s_slopeW[box,imodel]=np.nanstd(slopeW)
                m_slopeS[box,imodel]=np.nanmean(slopeS)
                s_slopeS[box,imodel]=np.nanstd(slopeS)
            elif box in south_boxes:
                x_slope = np.log10(freq_filtered)
                y_slope = np.log10(spec_s2)
                slopeW  = -np.gradient(y_slope, x_slope)
                if rseason == "spring":
                    y_slope = np.log10(spec_s4)
                elif rseason == "summer":
                    y_slope = np.log10(spec_s1)
                slopeS  = -np.gradient(y_slope, x_slope)
                m_slopeW[box,imodel]=np.nanmean(slopeW)
                s_slopeW[box,imodel]=np.nanstd(slopeW)
                m_slopeS[box,imodel]=np.nanmean(slopeS)
                s_slopeS[box,imodel]=np.nanstd(slopeS)
            else:
                continue


    return m_slopeW, m_slopeS



def season_spec(models, selected, wlmin, wlmax, north_boxes, south_boxes, endpoint_url, season1, season2,
                modeload="online",folder="project-meom-ige/OMIP/Global/"):
    """
    Computes seasonal spectrum ratio for dynamic lists of models.
    """
    
    # Store dynamic results mapped by model name
    R = {imod: [] for imod in models}
    F = {imod: [] for imod in models}

    for i, poly in enumerate(selected):
        box = i  # Synchronize box index with loop index
        
        spectrum_s1, freq_s1=read_season(season1,box,endpoint_url,models,mode=modeload,folder=folder)
        spectrum_s2, freq_s2=read_season(season2,box,endpoint_url,models,mode=modeload,folder=folder)
        
        # Calculate ratios dynamically per model
        for imodel, imod in enumerate(models):
            freq = np.array(freq_s1[imodel])
            wavelength = 1.0 / freq
            
            # Use dynamic wavelength limits passed to the function
            poswl = np.where((wavelength > wlmin) & (wavelength < wlmax))[0]
            
            spec_s1 = np.array(spectrum_s1[imodel])[poswl]
            spec_s2 = np.array(spectrum_s2[imodel])[poswl]
            freq_filtered = freq[poswl]

            # Assign winter/summer based on hemisphere
            if box in north_boxes:
                psdsW = spec_s1
                psdsS = spec_s2
            elif box in south_boxes:
                psdsW = spec_s2
                psdsS = spec_s1
            else:
                continue  # Skip if box isn't categorized

            # Ratio calculation
            Z = psdsW / psdsS

            # Save per model
            R[imod].append(Z)
            F[imod].append(freq_filtered)

    return R, F



def season_spec_fall(models, selected, wlmin, wlmax, north_boxes, south_boxes,endpoint_url,rseason,season1='JFM',season2='JAS',season3='AMJ',season4='OND',
                     modeload="online",folder="project-meom-ige/OMIP/Global/"):
    """
    Computes seasonal spectrum ratio for dynamic lists of models.
    """
    
    # Store dynamic results mapped by model name
    R = {imod: [] for imod in models}
    F = {imod: [] for imod in models}

    for i, poly in enumerate(selected):
            
        box = i  # Synchronize box index with loop index
        
        spectrum_s1, freq_s1 = [], []
        spectrum_s2, freq_s2 = [], []
        spectrum_s3, freq_s3 = [], []
        spectrum_s4, freq_s4 = [], []

        # Fetch data for all models for Season 1 & Season 2
        spectrum_s1, freq_s1=read_season(season1,box,endpoint_url,models,mode=modeload,folder=folder)
        spectrum_s2, freq_s2=read_season(season2,box,endpoint_url,models,mode=modeload,folder=folder)
        spectrum_s3, freq_s3=read_season(season3,box,endpoint_url,models,mode=modeload,folder=folder)
        spectrum_s4, freq_s4=read_season(season4,box,endpoint_url,models,mode=modeload,folder=folder)

        # Calculate ratios dynamically per model
        for imodel, imod in enumerate(models):
            freq = np.array(freq_s1[imodel])
            wavelength = 1.0 / freq
            
            # Use dynamic wavelength limits passed to the function
            poswl = np.where((wavelength > wlmin) & (wavelength < wlmax))[0]
            
            spec_s1 = np.array(spectrum_s1[imodel])[poswl]
            spec_s2 = np.array(spectrum_s2[imodel])[poswl]
            spec_s3 = np.array(spectrum_s3[imodel])[poswl]
            spec_s4 = np.array(spectrum_s4[imodel])[poswl]
            freq_filtered = freq[poswl]

            if box in north_boxes:
                psdsW=spec_s1
                if rseason=="spring":
                    psdsSe=spec_s3
                elif rseason=="fall":
                    psdsSe=spec_s4
            elif box in south_boxes:
                psdsW=spec_s2
                if rseason=="spring":
                    psdsSe=spec_s4
                elif rseason=="fall":
                    psdsSe=spec_s3
            else:
                continue  # Skip if box isn't categorized

            # Ratio calculation
            Z = psdsW / psdsSe

            # Save per model
            R[imod].append(Z)
            F[imod].append(freq_filtered)

    return R, F



def ratio_model(models, selected, wlmin, wlmax, north_boxes, south_boxes, endpoint_url, month1,month2, season,modelref,
                modeload="online",folder="project-meom-ige/OMIP/Global/"):
    """
    Computes the ratio with respect to one particular model (normally SWOT) for dynamic lists of models .
    """
     
    # Store dynamic results mapped by model name
    R = {imod: [] for imod in models if imod != modelref}
    F = {imod: [] for imod in models if imod != modelref}
    for i, poly in enumerate(selected):
            
        box = i  # Synchronize box index with loop index
        
        spectrum_s1, freq_s1 = [], []
        spectrum_s2, freq_s2 = [], []

        # Fetch data for all models for Season 1 & Season 2
        spectrum_s1, freq_s1=read_season(month1,box,endpoint_url,models,mode=modeload,folder=folder)
        spectrum_s2, freq_s2=read_season(month2,box,endpoint_url,models,mode=modeload,folder=folder)


        #--------------------------------
        # define spectra of referneces model
        #--------------------------------
        imodelref = models.index("SWOT")   
        freq = np.array(freq_s1[imodelref])
        wavelength = 1.0 / freq
            
        # Use dynamic wavelength limits passed to the function
        poswl = np.where((wavelength > wlmin) & (wavelength < wlmax))[0]
            
        spec_s1 = np.array(spectrum_s1[imodelref])[poswl]
        spec_s2 = np.array(spectrum_s2[imodelref])[poswl]
        freq_filtered = freq[poswl]

        # Assign winter/summer based on hemisphere
        if season == "winter":
            if box in north_boxes:
                psdsS = spec_s1
            elif box in south_boxes:
                psdsS = spec_s2
            else:
                continue  # Skip if box isn't categorized
        elif season == "summer":
            if box in north_boxes:
                psdsS = spec_s1
            elif box in south_boxes:
                psdsS = spec_s2
            else:
                continue  # Skip if box isn't categorized
        #--------------------------------
        # Calculate ratios dynamically per model
        #--------------------------------
                    
        # 
        for imodel, imod in enumerate(models):
            if imod == modelref:
                continue
            freq = np.array(freq_s1[imodel])
            wavelength = 1.0 / freq
            
            # Use dynamic wavelength limits passed to the function
            poswl = np.where((wavelength > wlmin) & (wavelength < wlmax))[0]
            
            spec_s1 = np.array(spectrum_s1[imodel])[poswl]
            spec_s2 = np.array(spectrum_s2[imodel])[poswl]
            freq_filtered = freq[poswl]

            # Assign winter/summer based on hemisphere
            if season == "winter":
                if box in north_boxes:
                    psds = spec_s1
                elif box in south_boxes:
                    psds = spec_s2
                else:
                    continue  # Skip if box isn't categorized
            elif season == "summer":
                if box in north_boxes:
                    psds = spec_s2
                elif box in south_boxes:
                    psds = spec_s1
                else:
                    continue  # Skip if box isn't categorized

            # Ratio calculation
            Z = psds / psdsS

            # Save per model
            R[imod].append(Z)
            F[imod].append(freq_filtered)

    return R, F

    
def remap(psdsW,psdsS,models,boxesjson="mostly_ocean_boxes_filtered.geojson"):
    """
    Re-organize two array (psdsW, psdsS) into a two global map (ZW,ZS)
    """
    with open(boxesjson) as f:
        data = json.load(f)

    nboxes = len(data["features"])
    
    lon_min_list = []
    lat_min_list = []

    for feature in data["features"]:
        coords = feature["geometry"]["coordinates"][0]
        lons = [pt[0] for pt in coords]
        lats = [pt[1] for pt in coords]

        lon_min_list.append(min(lons))
        lat_min_list.append(min(lats))

    lon_min_list = np.array(lon_min_list)
    lat_min_list = np.array(lat_min_list)

    lon_edges = np.arange(-180, 181, 10)
    lat_edges = np.arange(-90, 91, 10)

    nlon = len(lon_edges) - 1
    nlat = len(lat_edges) - 1

    ZW = np.full((len(models),nlat, nlon), np.nan)
    values = np.array(psdsW)   # shape (280,)
    for i in range(nboxes):
        lon_idx = np.where(lon_edges[:-1] == lon_min_list[i])[0][0]
        lat_idx = np.where(lat_edges[:-1] == lat_min_list[i])[0][0]
        for imodel in range(len(models)):
            ZW[imodel,lat_idx, lon_idx] = np.array(values[i,imodel])

    ZS = np.full((len(models),nlat, nlon), np.nan)
    values = np.array(psdsS)   # shape (280,)
    for i in range(nboxes):
        lon_idx = np.where(lon_edges[:-1] == lon_min_list[i])[0][0]
        lat_idx = np.where(lat_edges[:-1] == lat_min_list[i])[0][0]
        for imodel in range(len(models)):
            ZS[imodel,lat_idx, lon_idx] = np.array(values[i,imodel])

    return ZW, ZS