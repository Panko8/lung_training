from collections import OrderedDict
import matplotlib.pyplot as plt
import pandas as pd
import re
from tqdm import tqdm
import os
import pydicom
import numpy as np
import torch

from dataset import Tumor, LungDataset
from global_variable import CURRENT_DATASET_PKL_PATH, VOI_EXCEL_PATH, EXTRA_FP_EXCEL_PATH
import utils_ccy
import utils_hsz

def get_transform(dataset):
    repeated=set()
    all_spacings = []
    all_thickness = []
    all_zs = []
    all_hws = []
    norm_spacing = (1.25, 0.75, 0.75)
    for pid in dataset.pids:
        if pid in repeated:
            continue
        repeated.add(pid)
        tumor = dataset.tumors[ dataset.pid_to_excel_r_relation[pid][0] ]
        spacing = tumor.dcm_reader.PixelSpacing
        assert spacing[0]==spacing[1], "x,y has different spacing: {} != {}".format(spacing[0], spacing[1])
        all_spacings.append(spacing[0])
        thickness = tumor.dcm_reader.SliceThickness
        all_thickness.append(thickness)
        shape = tumor.original_shape
        norm_shape = shape[0]*thickness/norm_spacing[0],  shape[1]*spacing[1]/norm_spacing[1], shape[2]*spacing[0]/norm_spacing[2]
        assert norm_shape[1]==norm_shape[2]
        all_zs.append(norm_shape[0])
        all_hws.append(norm_shape[1])
    return all_spacings, all_thickness, all_zs, all_hws

class Stats():
    def __init__(self, lst:list):
        statistics = OrderedDict()
        for i in lst:
            if i not in statistics:
                statistics[i]=1
            else:
                statistics[i]+=1
        #plt.bar(statistics.keys(), statistics.values())
        self.statistics = statistics
    def filter_show(self, count=0):
        view=self.statistics.copy()
        for key in self.statistics:
            if self.statistics[key]<count:
                view.pop(key)
        return view
    def __repr__(self):
        return str(self.filter_show(count=10))


def main(dataset_path):
    dataset = LungDataset.load(dataset_path)
    pids = list(set(dataset.pids))
    dataset.get_data(pids)
    all_spacings, all_thickness, all_zs, all_hws = get_transform(dataset)
    spacing_stat = Stats(all_spacings)
    thickness_stat = Stats(all_thickness)
    z_stat = Stats(all_zs)
    hw_stat = Stats(all_hws)
    print(spacing_stat)
    plt.hist(all_spacings, bins=100)
    plt.show()
    print(thickness_stat)
    plt.hist(all_thickness, bins=100)
    plt.xlabel("Slice Thickness (mm)")
    plt.ylabel("Count")
    plt.title("Slice Thickness Distribution")
    plt.show()
    print(z_stat)
    plt.hist(all_zs, bins=100)
    plt.show()
    print(hw_stat)
    plt.hist(all_hws, bins=100)
    plt.show()
    print("average spacing", sum(all_spacings)/len(all_spacings))
    print("average thickness", sum(all_thickness)/len(all_thickness))
    print("average z", sum(all_zs)/len(all_zs))
    print("average hw", sum(all_hws)/len(all_hws))
    ## averagely and techniquely speacking, target_transform (z,y,x) = (1.25, 0.75, 0.75)


def get_benign_malignant(dataset_path, excel_path):
    dataset = LungDataset.load(dataset_path)
    pids = list(set(dataset.pids))
    dataset.get_data(pids)
    #df_voi = pd.read_excel(excel_path, sheet_name="VOI")
    df = pd.read_excel(excel_path, sheet_name=0)
    df = df[1:].astype({"病歷號":int, "Cell type":str}).astype({"病歷號":str, "Cell type":str})
    counts = {}
    for pid in tqdm(pids, total=len(pids)):
        if "_" in pid:
            pid = pid[:pid.find("_")]
        cell_types = df[df["病歷號"]==pid]["Cell type"].tolist()
        if len(cell_types) == 0:
            #print("pid={}, cell_types={}".format(pid, cell_types))
            #if 1 not in counts:
            #    counts[1] = 1
            #else:
            #    counts[1] += 1
            continue
        #print("pid = ", pid, "   cell_types =", cell_types)
        for cell_type in cell_types:
            ind = cell_type.find("(")
            if ind != -1: # contains "("
                cell_type = cell_type[:ind]
            #print("cell type =", cell_type)
            types = re.split(",|;|:|\s", cell_type)
            #print("types =", types)
            for typ in types:
                if not typ.isnumeric():
                    continue
                #assert typ.isnumeric(), "typ={} from types='{}' not numeric".format(typ, types)
                typ = int(typ)
                if typ not in counts:
                    counts[typ] = 1
                else:
                    counts[typ] += 1
    print(counts)
    b = counts[16]
    m = sum(counts.values()) - b
    print("B:M = {}:{}".format(b, m))


def get_study_range_and_age(dataset_path, excel_path):
    dataset = LungDataset.load(dataset_path)
    pids = list(set(dataset.pids))
    dataset.get_data(pids)
    #df_voi = pd.read_excel(excel_path, sheet_name="VOI")
    df = pd.read_excel(excel_path, sheet_name=0)
    df = df[1:].astype({"病歷號":int}).astype({"病歷號":str})
    counts = {}
    counts2 = {}
    for pid in tqdm(pids, total=len(pids)):
        dcm = dataset.tumors[dataset.pid_to_excel_r_relation[pid][0]].dcm_reader
        for f in os.listdir(dcm.path):
            if "." not in f:
                s0 = pydicom.read_file(os.path.join(dcm.path, f))
                break
        ct_date = s0.SeriesDate
        ct_yr = int(ct_date[:4])
        ct_date = int(ct_date)
        if ct_date not in counts2:
            counts2[ct_date] = 1
        else:
            counts2[ct_date] += 1

        if "_" in pid:
            pid = pid[:pid.find("_")]
        born_df = df[df["病歷號"]==pid]["生日"]
        if len(born_df)==0:
            print("pid={} not found".format(pid))
            continue
        born = born_df.tolist()[0]
        #assert all(age_df==age), "{}".format(age_df.tolist())
        try:
            born_yr = born.year
        except:
            print("pid={}, born_df={}, {}".format(pid, born_df.tolist(), type(born)))
            continue
        age = ct_yr - born_yr
        if age not in counts:
            counts[age] = 1
        else:
            counts[age] +=1
        if age<=20:
            print("pid={} has age={}".format(pid, age))
    print("min age", min(counts))
    print("max age", max(counts))
    print("min ct date", min(counts2))
    print("max ct date", max(counts2))

def get_sex(dataset_path, excel_path): # 1M 2F
    dataset = LungDataset.load(dataset_path)
    pids = list(set(dataset.pids))
    dataset.get_data(pids)
    #df_voi = pd.read_excel(excel_path, sheet_name="VOI")
    df = pd.read_excel(excel_path, sheet_name=0)
    df = df[1:].astype({"病歷號":int}).astype({"病歷號":str})
    counts = {}
    for pid in tqdm(pids, total=len(pids)):
        if "_" in pid:
            pid = pid[:pid.find("_")]
        sex_df = df[df["病歷號"]==pid]["性別"]
        if len(sex_df)==0:
            print("pid={} not found".format(pid))
            continue
        sex = sex_df.tolist()[0]
        #assert all(sex_df==sex), "pid={} with {}".format(pid, sex_df.tolist())
        if not all(sex_df==sex):
            sex_list = sex_df.tolist()
            sex = max(sex_list, key=lambda k: sex_list.count(k))
        try:
            sex = int(sex)
        except:
            print("pid={}, sex_df={}".format(pid, sex_df.tolist()))
        if sex not in counts:
            counts[sex] = 1
        else:
            counts[sex] +=1
    print(counts)
    #print("min", min(counts, key=lambda k: counts[k]))
    #print("max", max(counts, key=lambda k: counts[k]))

def get_nodule_stats(dataset_path):
    dataset = LungDataset.load(dataset_path)
    pids = list(set(dataset.pids))
    dataset.get_data(pids)
    dataset.set_lung_voi()
    dataset.set_batch_1_eval(True, (1.25,0.75,0.75))
    sizes = []
    # part 1
    for npy_name, bboxs_ori, pid in dataset.data:
        tumor = dataset.tumors[dataset.pid_to_excel_r_relation[pid][0]]
        original_shape = tumor.original_shape
        ori_spacing = tumor.dcm_reader.transform
        bboxes = bboxs_ori
        assert npy_name==None #using raw data
        img = dataset.get_series_by_pid(pid)  #已於dicom_reader.py處理過hu
        img = utils_hsz.normalize(img)
        if dataset.use_lung_voi: # crop VOI
            lung_voi = dataset.lung_voi_lut[pid]
            z1,y1,x1,z2,y2,x2 = lung_voi
            img = img[z1:z2+1, y1:y2+1, x1:x2+1]
            original_shape = (z2+1-z1, y2+1-y1, x2+1-x1) ## voi shape
            new_bboxes = []
            for bbox in bboxes:
                oz1,oy1,ox1,oz2,oy2,ox2 = bbox[:6]
                bbox= [oz1-z1, oy1-y1, ox1-x1, oz2-z1, oy2-y1, ox2-x1, 1, 1] # shifting O from (0,0,0) to (z1,y1,x1)
                new_bboxes.append(bbox)
            bboxes = new_bboxes
                                       
        if dataset.batch_1_eval: # adjust pixel spacing to self.equal_spacing
            transform = ori_spacing
            target_transform = dataset.equal_spacing
            d, h, w = original_shape
            d_new, h_new, w_new = round(d*transform[0]/target_transform[0]), round(h*transform[1]/target_transform[1]), round(w*transform[2]/target_transform[2])
            img = utils_ccy.resize_without_pad(img, (d_new,h_new,w_new), "nearest")

        target_shape = d_new, h_new, w_new
        #print("dataset.py getitem:", target_shape)
        img = torch.FloatTensor(img).unsqueeze_(-1) # auto convert to float32
        
        bboxs_scaled = utils_ccy.scale_bbox(original_shape, target_shape, bboxes)
        bboxs_scaled = np.array(bboxs_scaled, dtype=np.int64)

        if (1): #debug
            print("pid={}, original_shape='{}', target_shape='{}', bboxs_ori='{}', bboxs_scaled='{}'".format(pid, original_shape, target_shape, bboxs_ori, bboxs_scaled))
            view_img = img.squeeze(-1).numpy()
            view_box = [bbox[:6] for bbox in bboxs_scaled.tolist()]
            utils_hsz.AnimationViewer(view_img, bbox=view_box, verbose=False, note=f"{pid}", draw_face=False)
        bbox = [bbox[:6] for bbox in bboxs_scaled.tolist()][0]
        z1, y1, x1, z2, y2, x2 = bbox
        size = ((z2-z1)*1.25 + (y2-y1)*0.75 + (x2-x1)*0.75)/3
        sizes.append(size)
    # part 2
    sizes2 = []
    df = pd.read_excel(EXTRA_FP_EXCEL_PATH, sheet_name="Sheet1", converters={'pid':str,'bbox':str, 'isFP':int})
    bboxes = [eval(lst) for lst in df[df["isFP"]==0]["bbox"]]
    for bbox in bboxes:
        z1, y1, x1, z2, y2, x2 = bbox
        size = ((z2-z1)*1.25 + (y2-y1)*0.75 + (x2-x1)*0.75)/3
        sizes2.append(size)
    
    size_total = sizes + sizes2
    plt.hist(size_total, bins=100)
    print(sum(sizes)/len(sizes))
    print(sum(sizes2)/len(sizes2))
    print(sum(size_total)/len(size_total))
    plt.xlabel("Nodule Diameter (mm)")
    plt.ylabel("Count")
    plt.title("Nodule Size Distribution")
    plt.show()



        

if __name__ == "__main__":
    ...
    #print("Using:", CURRENT_DATASET_PKL_PATH)
    #main(CURRENT_DATASET_PKL_PATH)
    complete_excel_path = "D:\CH\LungDetection\AI-肺部手術病人資料.xlsx"
    #get_benign_malignant(CURRENT_DATASET_PKL_PATH, complete_excel_path)
    #get_study_range_and_age(CURRENT_DATASET_PKL_PATH, complete_excel_path)
    #get_sex(CURRENT_DATASET_PKL_PATH, complete_excel_path)
    get_nodule_stats(CURRENT_DATASET_PKL_PATH)
