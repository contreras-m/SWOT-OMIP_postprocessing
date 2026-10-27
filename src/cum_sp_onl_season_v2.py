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
            fs = s3fs.S3FileSystem(key="r3WtYCGWba3FDbT2eKeQ",secret="8OCnb4LX3sPaKkp1aUCzJmfQljmaYsqg2KmQTups", endpoint_url=endpoint_url)
            with fs.open(file, mode='rb') as fileObj:
                data = json.load(fileObj)
        elif mode=='offline':
            with open(file, mode='rb') as fileObj:
                data = json.load(fileObj)
        return data

def read_season(season1,box,endpoint_url,models,mode='online'):
    season=season1
    spectrumJFM=[]
    freqJFM=[]
    # Plot spectrum JFM
    for imod in models:
        if mode=="online":
            s3_folder="project-meom-ige/OMIP/"
            filename = f"s3://"+s3_folder+"Global/"+ imod +"/Global_box_" + str(box) + "_" + season + "_" + imod + ".json"
            data=read_json_s3(endpoint_url,filename)
            spectrumJFM.append(data["Spectra"])
            freqJFM.append(data["Frequency"])
        elif mode=="offline":
            folder="GLOBALv2/"
            filename = folder+ imod +"/Global_box_" + str(box) + "_" + season1 + "_" + imod + ".json"
            data=read_json_s3(endpoint_url,filename,mode='offline')
            spectrumJFM.append(data["Spectra"])
            freqJFM.append(data["Frequency"])
    return spectrumJFM, freqJFM
    

def season_cum_fall(models,selected,wlmin,wlmax,north_boxes,south_boxes,endpoint_url,rseason,
                    season1='JFM',season2='JAS',season3='AMJ',season4='OND'):

    box=0
    psdsW=np.zeros((len(selected),len(models)))
    psdsSe=np.zeros((len(selected),len(models)))
    for i, poly in enumerate(selected):

        if (i!=14) and (i!=15):
            spectrumJFM,freqJFM=read_season(season1,box,endpoint_url,models,mode='offline')
            spectrumJAS,freqJAS=read_season(season2,box,endpoint_url,models,mode='offline')
            spectrumAMJ,freqJFM=read_season(season3,box,endpoint_url,models,mode='offline')
            spectrumOND,freqJFM=read_season(season4,box,endpoint_url,models,mode='offline')
            wavelength=1/np.array(freqJFM)
            #poswl=np.where((wavelength>50) & (wavelength<500))
            #freqJASM = np.array(freqJAS[0])   # now it's a 2D array
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
        else:
            box=box+1
    return psdsW, psdsSe,freqJAS
    
def season_cum(models,selected,wlmin,wlmax,north_boxes,south_boxes,endpoint_url,season1,season2):

    box=0
    psdsW=np.zeros((len(selected),len(models)))
    psdsS=np.zeros((len(selected),len(models)))

    for i, poly in enumerate(selected):

        if (i!=1400) and (i!=1500):
            season="JFM"
            spectrumJFM=[]
            freqJFM=[]
            # Plot spectrum JFM
            for imod in models:
                s3_folder="project-meom-ige/OMIP/"
                filename = f"s3://"+s3_folder+"Global/"+ imod +"/Global_box_" + str(box) + "_" + season + "_" + imod + ".json"
                data=read_json_s3(endpoint_url,filename)
                spectrumJFM.append(data["Spectra"])
                freqJFM.append(data["Frequency"])

            season="JAS"
            spectrumJAS=[]
            freqJAS=[]
            # Plot spectrum JAS
            for imod in models:
                s3_folder="project-meom-ige/OMIP/"
                filename = f"s3://"+s3_folder+"Global/"+ imod +"/Global_box_" + str(box) + "_" + season + "_" + imod + ".json"
                data=read_json_s3(endpoint_url,filename)
                spectrumJAS.append(data["Spectra"])
                freqJAS.append(data["Frequency"])


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
        else:
            box=box+1
    return psdsW, psdsS,freqJAS

def season_slope(models,selected,wlmin,wlmax,north_boxes,south_boxes,endpoint_url,season1,season2):


    box=0
    m_slopeW=np.zeros((len(selected),len(models)))
    m_slopeS=np.zeros((len(selected),len(models)))
    s_slopeW=np.zeros((len(selected),len(models)))
    s_slopeS=np.zeros((len(selected),len(models)))
    for i, poly in enumerate(selected):

        if (i!=14) and (i!=15):
            season=season1
            spectrumJFM=[]
            freqJFM=[]
            # Plot spectrum JFM
            for imod in models:
                s3_folder="project-meom-ige/OMIP/"
                filename = f"s3://"+s3_folder+"Global/"+ imod +"/Global_box_" + str(box) + "_" + season + "_" + imod + ".json"
                data=read_json_s3(endpoint_url,filename)
                spectrumJFM.append(data["Spectra"])
                freqJFM.append(data["Frequency"])

            season=season2
            spectrumJAS=[]
            freqJAS=[]
            # Plot spectrum JAS
            for imod in models:
                s3_folder="project-meom-ige/OMIP/"
                filename = f"s3://"+s3_folder+"Global/"+ imod +"/Global_box_" + str(box) + "_" + season + "_" + imod + ".json"
                data=read_json_s3(endpoint_url,filename)
                spectrumJAS.append(data["Spectra"])
                freqJAS.append(data["Frequency"])

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
            #psds1[box,imodel] = np.squeeze(np.cumsum(ratio[poswl[0]] * freqJASM[poswl[0]])/np.sum( 1/freqJASM[poswl[0]]))

            box=box+1
        else:
            box=box+1


    return m_slopeW, m_slopeS, s_slopeW, s_slopeS

def season_slope_fall(models, selected, wlmin, wlmax, north_boxes, south_boxes,endpoint_url,rseason,season1='JFM',season2='JAS',season3='AMJ',season4='OND'):
    """
    Computes seasonal spectrum ratio for dynamic lists of models.
    """
    s3_folder = "project-meom-ige/OMIP/Global/"
    
    m_slopeW=np.zeros((len(selected),len(models)))
    m_slopeS=np.zeros((len(selected),len(models)))
    s_slopeW=np.zeros((len(selected),len(models)))
    s_slopeS=np.zeros((len(selected),len(models)))

    for i, poly in enumerate(selected):
        # Skip specific indices if required
        if i in (14, 15):
            continue
            
        box = i  # Synchronize box index with loop index
        
        spectrum_s1, freq_s1 = [], []
        spectrum_s2, freq_s2 = [], []
        spectrum_s3, freq_s3 = [], []
        spectrum_s4, freq_s4 = [], []

        # Fetch data for all models for Season 1 & Season 2
        for imod in models:
            # Season 1
            folder="GLOBALv2/"
            filename_s1 = folder+ imod +"/Global_box_" + str(box) + "_" + season1 + "_" + imod + ".json"
            #filename_s1 = f"s3://{s3_folder}{imod}/Global_box_{box}_{season1}_{imod}.json"
            data_s1 = read_json_s3(endpoint_url, filename_s1,mode='offline')
            spectrum_s1.append(data_s1["Spectra"])
            freq_s1.append(data_s1["Frequency"])

            # Season 2
            filename_s2 = folder+ imod +"/Global_box_" + str(box) + "_" + season2 + "_" + imod + ".json"
            #filename_s2 = f"s3://{s3_folder}{imod}/Global_box_{box}_{season2}_{imod}.json"
            data_s2 = read_json_s3(endpoint_url, filename_s2,mode='offline')
            spectrum_s2.append(data_s2["Spectra"])
            freq_s2.append(data_s2["Frequency"])

            # Season 3
            filename_s3 = folder+ imod +"/Global_box_" + str(box) + "_" + season3 + "_" + imod + ".json"
            #filename_s3 = f"s3://{s3_folder}{imod}/Global_box_{box}_{season3}_{imod}.json"
            data_s3 = read_json_s3(endpoint_url, filename_s3,mode='offline')
            spectrum_s3.append(data_s3["Spectra"])
            freq_s3.append(data_s3["Frequency"])

            # Season 4
            filename_s4 = folder+ imod +"/Global_box_" + str(box) + "_" + season4 + "_" + imod + ".json"
            #filename_s4 = f"s3://{s3_folder}{imod}/Global_box_{box}_{season4}_{imod}.json"
            data_s4 = read_json_s3(endpoint_url, filename_s4,mode='offline')
            spectrum_s4.append(data_s4["Spectra"])
            freq_s4.append(data_s4["Frequency"])

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



def season_spec(models, selected, wlmin, wlmax, north_boxes, south_boxes, endpoint_url, season1, season2):
    """
    Computes seasonal spectrum ratio for dynamic lists of models.
    """
    s3_folder = "project-meom-ige/OMIP/Global/"
    
    # Store dynamic results mapped by model name
    R = {imod: [] for imod in models}
    F = {imod: [] for imod in models}

    for i, poly in enumerate(selected):
        # Skip specific indices if required
        if i in (14, 15):
            continue
            
        box = i  # Synchronize box index with loop index
        
        spectrum_s1, freq_s1 = [], []
        spectrum_s2, freq_s2 = [], []

        # Fetch data for all models for Season 1 & Season 2
        for imod in models:
            # Season 1
            filename_s1 = f"s3://{s3_folder}{imod}/Global_box_{box}_{season1}_{imod}.json"
            data_s1 = read_json_s3(endpoint_url, filename_s1)
            spectrum_s1.append(data_s1["Spectra"])
            freq_s1.append(data_s1["Frequency"])

            # Season 2
            filename_s2 = f"s3://{s3_folder}{imod}/Global_box_{box}_{season2}_{imod}.json"
            data_s2 = read_json_s3(endpoint_url, filename_s2)
            spectrum_s2.append(data_s2["Spectra"])
            freq_s2.append(data_s2["Frequency"])

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



def season_spec_fall(models, selected, wlmin, wlmax, north_boxes, south_boxes,endpoint_url,rseason,season1='JFM',season2='JAS',season3='AMJ',season4='OND'):
    """
    Computes seasonal spectrum ratio for dynamic lists of models.
    """
    s3_folder = "project-meom-ige/OMIP/Global/"
    
    # Store dynamic results mapped by model name
    R = {imod: [] for imod in models}
    F = {imod: [] for imod in models}

    for i, poly in enumerate(selected):
        # Skip specific indices if required
        if i in (14, 15):
            continue
            
        box = i  # Synchronize box index with loop index
        
        spectrum_s1, freq_s1 = [], []
        spectrum_s2, freq_s2 = [], []
        spectrum_s3, freq_s3 = [], []
        spectrum_s4, freq_s4 = [], []

        # Fetch data for all models for Season 1 & Season 2
        for imod in models:
            # Season 1
            folder="GLOBALv2/"
            filename_s1 = folder+ imod +"/Global_box_" + str(box) + "_" + season1 + "_" + imod + ".json"
            #filename_s1 = f"s3://{s3_folder}{imod}/Global_box_{box}_{season1}_{imod}.json"
            data_s1 = read_json_s3(endpoint_url, filename_s1,mode='offline')
            spectrum_s1.append(data_s1["Spectra"])
            freq_s1.append(data_s1["Frequency"])

            # Season 2
            filename_s2 = folder+ imod +"/Global_box_" + str(box) + "_" + season2 + "_" + imod + ".json"
            #filename_s2 = f"s3://{s3_folder}{imod}/Global_box_{box}_{season2}_{imod}.json"
            data_s2 = read_json_s3(endpoint_url, filename_s2,mode='offline')
            spectrum_s2.append(data_s2["Spectra"])
            freq_s2.append(data_s2["Frequency"])

            # Season 3
            filename_s3 = folder+ imod +"/Global_box_" + str(box) + "_" + season3 + "_" + imod + ".json"
            #filename_s3 = f"s3://{s3_folder}{imod}/Global_box_{box}_{season3}_{imod}.json"
            data_s3 = read_json_s3(endpoint_url, filename_s3,mode='offline')
            spectrum_s3.append(data_s3["Spectra"])
            freq_s3.append(data_s3["Frequency"])

            # Season 4
            filename_s4 = folder+ imod +"/Global_box_" + str(box) + "_" + season4 + "_" + imod + ".json"
            #filename_s4 = f"s3://{s3_folder}{imod}/Global_box_{box}_{season4}_{imod}.json"
            data_s4 = read_json_s3(endpoint_url, filename_s4,mode='offline')
            spectrum_s4.append(data_s4["Spectra"])
            freq_s4.append(data_s4["Frequency"])

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

    

    
def cum_sum(psdsW,psdsS,models):
    with open("mostly_ocean_boxes_filtered.geojson") as f:
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