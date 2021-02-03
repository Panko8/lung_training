import sys
sys.path.append("..")

import torch.nn as nn
import torch
from model.head.yolo_head import Yolo_head
from model.YOLOv4 import YOLOv4
import config.yolov4_config as cfg
import numpy as np

class Build_Model(nn.Module):
    """
    Note ： int the __init__(), to define the modules should be in order, because of the weight file is order
    """
    def __init__(self, weight_path=None, resume=False, dims=2):
        super(Build_Model, self).__init__()
        anchors = cfg.MODEL["ANCHORS3D"]
        if (0):
            anchors = [
                [[77., 62., 54.], [62., 77., 54.], [62., 54., 77.]],
                [[77., 62., 54.], [62., 77., 54.], [62., 54., 77.]],
                [[77., 62., 54.], [62., 77., 54.], [62., 54., 77.]],
                #[[24., 30., 32.], [46., 28., 30.], [46., 31., 18.]],
                #[[29., 19., 14.], [19., 29., 14.], [14., 19., 29.]],
                ]
            anchors = np.array(anchors)
            anchors[0] = anchors[0] / 8.
            anchors[1] = anchors[1] / 16.
            anchors[2] = anchors[2] / 32.

        self.__anchors = torch.FloatTensor(anchors)
        self.__strides = torch.FloatTensor(cfg.MODEL["STRIDES"])
        if cfg.TRAIN["DATA_TYPE"] == 'VOC':
            self.__nC = cfg.VOC_DATA["NUM"]
        elif cfg.TRAIN["DATA_TYPE"] == 'COCO':
            self.__nC = cfg.COCO_DATA["NUM"]
        elif cfg.TRAIN["DATA_TYPE"] == 'ABUS':
            self.__nC = cfg.ABUS_DATA["NUM"]
        elif cfg.TRAIN["DATA_TYPE"] == 'LUNG':
            self.__nC = cfg.LUNG_DATA["NUM"]
        else:
            self.__nC = cfg.Customer_DATA["NUM"]
        if dims==3:
            self.__out_channel = cfg.MODEL["ANCHORS_PER_SCLAE"] * (self.__nC + 7)
        else:
            self.__out_channel = cfg.MODEL["ANCHORS_PER_SCLAE"] * (self.__nC + 5)

        self.__yolov4 = YOLOv4(weight_path=weight_path, out_channels=self.__out_channel, resume=resume, dims=dims)
        #self.__yolov4 = YOLOv4() # zian
        # small
        self.__head_s = Yolo_head(nC=self.__nC, anchors=self.__anchors[0], stride=self.__strides[0], dims=dims)
        # medium
        self.__head_m = Yolo_head(nC=self.__nC, anchors=self.__anchors[1], stride=self.__strides[1], dims=dims)
        # large
        self.__head_l = Yolo_head(nC=self.__nC, anchors=self.__anchors[2], stride=self.__strides[2], dims=dims)

        self.verbose = cfg.MODEL["VERBOSE_SHAPE"]


    def forward(self, x):
        out = []
        verbose = self.verbose

        x_s, x_m, x_l = self.__yolov4(x)
        if verbose:
            print("After YOLOv4:\nx_s: {}\nx_m: {}\nx_l: {}".format(x_s.shape, x_m.shape, x_l.shape))

        out_s = self.__head_s(x_s)
        out_m = self.__head_m(x_m)
        out_l = self.__head_l(x_l)
        if verbose:
            print("After Yolo_heads:")
            print(*[m[1].shape for m in [out_s, out_m, out_l]], sep="\n", end="\n"+"="*20+"\n")
        out.append(out_s)
        out.append(out_m)
        out.append(out_l)

        if self.training:
            p, p_d = list(zip(*out))
            return p, p_d  # smalll, medium, large
        else:
            p, p_d = list(zip(*out))
            return p, torch.cat(p_d, 0)

    def getNC(self):
        return self.__nC


if __name__ == '__main__':
    from utils.flops_counter import get_model_complexity_info
    net = Build_Model()
    print(net)

    in_img = torch.randn(1, 3, 416, 416)
    p, p_d = net(in_img)
    flops, params = get_model_complexity_info(net, (224, 224), as_strings=False, print_per_layer_stat=False)
    print('GFlops: %.3fG' % (flops / 1e9))
    print('Params: %.2fM' % (params / 1e6))
    for i in range(3):
        print(p[i].shape)
        print(p_d[i].shape)