import logging
import utils.gpu as gpu
from model.build_model import Build_Model
from model.loss.yolo_loss import YoloV4Loss
import torch
import torch.optim as optim
from torch.utils.data import DataLoader
import utils.datasets as data
import time
import random
import argparse
from eval.evaluator import *
from eval.froc import calculate_FROC
from utils.tools import *
#from tensorboardX import SummaryWriter
from torch.utils.tensorboard import SummaryWriter
import config.yolov4_config as cfg
from utils import cosine_lr_scheduler
from utils.log import Logger
import warnings

#from eval_coco import *
#from eval.cocoapi_evaluator import COCOAPIEvaluator

from databuilder.abus import ABUSDetectionDataset
from databuilder.yolo4dataset import YOLO4_3DDataset
from tqdm import tqdm
from trainer import Trainer
from dataset import Tumor, LungDataset
from global_variable import CURRENT_DATASET_PKL_PATH


if __name__ == "__main__":
    global logger, writer
    parser = argparse.ArgumentParser()
    parser.add_argument('--weight_path', type=str, default=None, help='weight file path')#weight/darknet53_448.weights
    parser.add_argument('--resume', action='store_true',default=False,  help='resume training flag')
    parser.add_argument('--gpu_id', type=int, default=0, help='whether use GPU(eg:0,1,2,3,4,5,6,7,8) or CPU(-1)')
    parser.add_argument('--log_path', type=str, default='log/', help='log path')
    parser.add_argument('--accumulate', type=int, default=1, help='batches to accumulate before optimizing')
    parser.add_argument('--fp_16', type=bool, default=False, help='whither to use fp16 precision')
    parser.add_argument('--exp_name', type=str, default='debug', help='log experiment name')
    parser.add_argument('--crx_valid', type=int, default=0)
    parser.add_argument('--dataset_name', type=str, default=CURRENT_DATASET_PKL_PATH)
    parser.add_argument('--eval_interval', type=int, default=-1)
    parser.add_argument('--npy_name', type=str, default="hu+norm_256x256x256_fp16.npy")
    parser.add_argument('--testing_mode', type=int, default=0)
    opt = parser.parse_args()
    writer = SummaryWriter(log_dir=opt.log_path + '/' + opt.exp_name)
    logger = Logger(log_file_name=opt.log_path + '/' + opt.exp_name + '/log.txt', log_level=logging.DEBUG, logger_name='YOLOv4').get_log()
    checkpoint_save_dir = 'checkpoint/' + opt.exp_name
    if not os.path.exists(checkpoint_save_dir):
        os.mkdir(checkpoint_save_dir)

    weight_path = opt.weight_path
    resume = opt.resume

    if (0):
        warnings.warn("Override opt settings in train3D.py!!!")
        weight_path = r"checkpoint/train_5mm_max_no_fp_reduction_dry_run_f0/backup_epoch0.pt"
        resume = True
        opt.crx_valid = 0
        opt.eval_interval = 100
        #opt.exp_name = "train_rc_config_2_f0_fp_reduction_0,1"
        writer = SummaryWriter(log_dir=opt.log_path + '/' + opt.exp_name)
        logger = Logger(log_file_name=opt.log_path + '/' + opt.exp_name + '/log.txt', log_level=logging.DEBUG, logger_name='YOLOv4').get_log()
        checkpoint_save_dir = 'checkpoint/' + opt.exp_name
        if not os.path.exists(checkpoint_save_dir):
            os.mkdir(checkpoint_save_dir)


    #resume = True
    #weight_path = 'checkpoint/YOLO_ABUS_d30_Stem16_lr25/backup_epoch140.pt'
    trainer = Trainer(testing_mode=opt.testing_mode, # 0:validation, 1:testing, -1:training_debug
            weight_path=weight_path,
            checkpoint_save_dir=checkpoint_save_dir,
            resume=resume,
            gpu_id=opt.gpu_id,
            accumulate=opt.accumulate,
            fp_16=opt.fp_16,
            writer=writer,
            logger=logger,
            crx_fold_num=opt.crx_valid,
            dataset_name=opt.dataset_name,
            eval_interval=opt.eval_interval,
            npy_name=opt.npy_name,
            )

    trainer.train()