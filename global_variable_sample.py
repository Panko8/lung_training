

LUNG_DATA_PATH = r"E:/LungData/1500_DICOM" #r"D:/CH/LungDetection/DATA/1500_DICOM" 
VOI_EXCEL_PATH = r"D:/CH/LungDetection/AI-肺部手術病人資料_trimmed_5mm.xlsx" #記錄VOI的那個Excel
EXCLUDE_KEYWORDS = () #("5mm有點淡", "5mm看不到") #若VOI_EXCEL的備註欄裡面有任何這些keyword, 將略過該筆資料
NPY_SAVED_PATH = r"E:/LungData/Preprocessed"
MASK_SAVED_PATH = r"E:/LungData/AutoMask"
LUNG_DATASET_PKL_PATH = r"D:/CH/LungDetection/training/lung_dataset_20210118.pkl"  # mostly lung_dataset_20210118.pkl
NEGATIVE_NPY_SAVED_PATH = r"E:/LungData/NegativeSamples"
GT_LUT_PKL_PATH = r"D:/CH/LungDetection/gt_lut_1.25x0.75x0.75.pkl"

EXTRA_FP_EXCEL_PATH = r"D:/CH/LungDetection/not_fp_1.25mm.xlsx"
ITERATIVE_FP_CROP_PATH = r"E:/LungData/iterative_fp_crops_tmp"

#REPEATABLE_SERIES = () #MRI資料中，可允許重複出現的series種類

USE_LUNA = False  ##記得要同時改Anchorbox3D
LUNA_DIR = r"E:/Luna16/RAW"
LUNA_DATASET_PKL_PATH = r"D:/CH/LungDetection/training/luna_test_dataset.pkl"


CURRENT_DATASET_PKL_PATH = LUNA_DATASET_PKL_PATH if USE_LUNA else LUNG_DATASET_PKL_PATH

