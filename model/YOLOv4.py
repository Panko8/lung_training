import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np

import config.yolov4_config as cfg
from .backbones.CSPDarknet53 import _BuildCSPDarknet53
from .backbones.mobilenetv2 import _BuildMobilenetV2
from .backbones.mobilenetv3 import _BuildMobilenetV3

class Conv(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size, stride=1, dims=2):
        super(Conv, self).__init__()
        if (0): #ccy
            padding = 0
        else:
            padding = kernel_size//2
        if dims==3:
            self.conv = nn.Sequential(
                nn.Conv3d(in_channels, out_channels, kernel_size, stride, padding, bias=False),
                nn.BatchNorm3d(out_channels),
                nn.LeakyReLU()
            )
        else:
            self.conv = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, kernel_size, stride, padding, bias=False),
                nn.BatchNorm2d(out_channels),
                nn.LeakyReLU()
            )

    def forward(self, x):
        return self.conv(x)

class SpatialPyramidPooling(nn.Module):
    def __init__(self, feature_channels, pool_sizes=[5, 9, 13], dims=2):
        super(SpatialPyramidPooling, self).__init__()

        # head conv
        self.head_conv = nn.Sequential(
            Conv(feature_channels[-1], feature_channels[-1]//2, 1, dims=dims),
            Conv(feature_channels[-1]//2, feature_channels[-1], 3, dims=dims),
            Conv(feature_channels[-1], feature_channels[-1]//2, 1, dims=dims),
        )
        if dims==3:
            self.maxpools = nn.ModuleList([nn.MaxPool3d(pool_size, 1, pool_size//2) for pool_size in pool_sizes])
        else:
            self.maxpools = nn.ModuleList([nn.MaxPool2d(pool_size, 1, pool_size//2) for pool_size in pool_sizes])
        self.__initialize_weights()

    def forward(self, x):
        x = self.head_conv(x)
        features = [maxpool(x) for maxpool in self.maxpools]
        features = torch.cat([x]+features, dim=1)

        return features

    def __initialize_weights(self):
        print("**" * 10, "Initing head_conv weights", "**" * 10)

        for m in self.modules():
            if isinstance(m, nn.Conv2d) or isinstance(m, nn.Conv3d):
                m.weight.data.normal_(0, 0.01)
                if m.bias is not None:
                    m.bias.data.zero_()

                print("initing {}".format(m))
            elif isinstance(m, nn.BatchNorm2d) or isinstance(m, nn.BatchNorm3d):
                m.weight.data.fill_(1)
                m.bias.data.zero_()

                print("initing {}".format(m))


class Upsample(nn.Module):
    def __init__(self, in_channels, out_channels, scale=2, dims=2):
        super(Upsample, self).__init__()
        self.conv1x1 = nn.Sequential(
            Conv(in_channels, out_channels, 1, dims=dims),
            #nn.Upsample(scale_factor=scale)
        )

    def forward(self, x, odds=(0,0,0)): # ccy: odds is to handle odd number shape
        x = self.conv1x1(x)
        _, _, Z, Y, X = x.shape
        Z, Y, X = Z*2-odds[0], Y*2-odds[1], X*2-odds[2]
        x = torch.nn.functional.interpolate(x, size=(Z,Y,X))
        return x


class Downsample(nn.Module):
    def __init__(self, in_channels, out_channels, scale=2, dims=2):
        super(Downsample, self).__init__()
        self.downsample = Conv(in_channels, out_channels, 3, 2, dims=dims)

    def forward(self, x):
        return self.downsample(x)

class PANet(nn.Module):
    def __init__(self, feature_channels, dims=2):
        super(PANet, self).__init__()

        self.feature_transform3 = Conv(feature_channels[0], feature_channels[0]//2, 1, dims=dims)
        self.feature_transform4 = Conv(feature_channels[1], feature_channels[1]//2, 1, dims=dims)

        self.resample5_4 = Upsample(feature_channels[2]//2, feature_channels[1]//2, dims=dims)
        self.resample4_3 = Upsample(feature_channels[1]//2, feature_channels[0]//2, dims=dims)
        self.resample3_4 = Downsample(feature_channels[0]//2, feature_channels[1]//2, dims=dims)
        self.resample4_5 = Downsample(feature_channels[1]//2, feature_channels[2]//2, dims=dims)

        self.downstream_conv5 = nn.Sequential(
            Conv(feature_channels[2]*2, feature_channels[2]//2, 1, dims=dims),
            Conv(feature_channels[2]//2, feature_channels[2], 3, dims=dims),
            Conv(feature_channels[2], feature_channels[2]//2, 1, dims=dims)
        )
        self.downstream_conv4 = nn.Sequential(
            Conv(feature_channels[1], feature_channels[1]//2, 1, dims=dims),
            Conv(feature_channels[1]//2, feature_channels[1], 3, dims=dims),
            Conv(feature_channels[1], feature_channels[1]//2, 1, dims=dims),
            Conv(feature_channels[1]//2, feature_channels[1], 3, dims=dims),
            Conv(feature_channels[1], feature_channels[1]//2, 1, dims=dims),
        )
        self.downstream_conv3 = nn.Sequential(
            Conv(feature_channels[0], feature_channels[0]//2, 1, dims=dims),
            Conv(feature_channels[0]//2, feature_channels[0], 3, dims=dims),
            Conv(feature_channels[0], feature_channels[0]//2, 1, dims=dims),
            Conv(feature_channels[0]//2, feature_channels[0], 3, dims=dims),
            Conv(feature_channels[0], feature_channels[0]//2, 1, dims=dims),
        )

        self.upstream_conv4 = nn.Sequential(
            Conv(feature_channels[1], feature_channels[1]//2, 1, dims=dims),
            Conv(feature_channels[1]//2, feature_channels[1], 3, dims=dims),
            Conv(feature_channels[1], feature_channels[1]//2, 1, dims=dims),
            Conv(feature_channels[1]//2, feature_channels[1], 3, dims=dims),
            Conv(feature_channels[1], feature_channels[1]//2, 1, dims=dims),
        )
        self.upstream_conv5 = nn.Sequential(
            Conv(feature_channels[2], feature_channels[2]//2, 1, dims=dims),
            Conv(feature_channels[2]//2, feature_channels[2], 3, dims=dims),
            Conv(feature_channels[2], feature_channels[2]//2, 1, dims=dims),
            Conv(feature_channels[2]//2, feature_channels[2], 3, dims=dims),
            Conv(feature_channels[2], feature_channels[2]//2, 1, dims=dims)
        )
        self.__initialize_weights()

    def forward(self, features):
        odds = [tuple(np.array(f.shape[-3:])%2) for f in features]

        features = [self.feature_transform3(features[0]), self.feature_transform4(features[1]), features[2]]
        downstream_feature5 = self.downstream_conv5(features[2])
        #downstream_feature4 = self.downstream_conv4(torch.cat([features[1], self.resample5_4(downstream_feature5, odds[1])], dim=1))
        #downstream_feature3 = self.downstream_conv3(torch.cat([features[0], self.resample4_3(downstream_feature4, odds[0])], dim=1))
        downstream_feature4 = self.downstream_conv4(torch.cat([features[1], self.resample5_4(downstream_feature5)], dim=1))
        downstream_feature3 = self.downstream_conv3(torch.cat([features[0], self.resample4_3(downstream_feature4)], dim=1))

        upstream_feature4 = self.upstream_conv4(torch.cat([self.resample3_4(downstream_feature3), downstream_feature4], dim=1))
        upstream_feature5 = self.upstream_conv5(torch.cat([self.resample4_5(upstream_feature4), downstream_feature5], dim=1))

        return [downstream_feature3, upstream_feature4, upstream_feature5]

    def __initialize_weights(self):
        print("**" * 10, "Initing PANet weights", "**" * 10)

        for m in self.modules():
            if isinstance(m, nn.Conv2d) or isinstance(m, nn.Conv3d):
                m.weight.data.normal_(0, 0.01)
                if m.bias is not None:
                    m.bias.data.zero_()

                print("initing {}".format(m))
            elif isinstance(m, nn.BatchNorm2d) or isinstance(m, nn.BatchNorm3d):
                m.weight.data.fill_(1)
                m.bias.data.zero_()

                print("initing {}".format(m))

class PredictNet(nn.Module):
    def __init__(self, feature_channels, target_channels, dims=2):
        super(PredictNet, self).__init__()
        nn_conv = nn.Conv3d if dims==3 else nn.Conv2d
        self.predict_conv = nn.ModuleList([
            nn.Sequential(
                Conv(feature_channels[i]//2, feature_channels[i], 3, dims=dims),
                nn_conv(feature_channels[i], target_channels, 1)
            ) for i in range(len(feature_channels))
        ])
        self.__initialize_weights()

    def forward(self, features):
        predicts = [predict_conv(feature) for predict_conv, feature in zip(self.predict_conv, features)]

        return predicts

    def __initialize_weights(self):
        print("**" * 10, "Initing PredictNet weights", "**" * 10)

        for m in self.modules():
            if isinstance(m, nn.Conv2d) or isinstance(m, nn.Conv3d):
                m.weight.data.normal_(0, 0.01)
                if m.bias is not None:
                    m.bias.data.zero_()

                print("initing {}".format(m))
            elif isinstance(m, nn.BatchNorm2d) or isinstance(m, nn.BatchNorm3d):
                m.weight.data.fill_(1)
                m.bias.data.zero_()

                print("initing {}".format(m))

class YOLOv4(nn.Module):
    def __init__(self, weight_path=None, out_channels=255, resume=False, dims=2):
        super(YOLOv4, self).__init__()

        a = cfg.MODEL_TYPE['TYPE']
        if cfg.MODEL_TYPE['TYPE'] == 'YOLOv4':
            # CSPDarknet53 backbone
            self.backbone, feature_channels = _BuildCSPDarknet53(in_channel=cfg.MODEL_INPUT_CHANNEL, weight_path=weight_path, resume=resume, dims=dims)
        elif cfg.MODEL_TYPE["TYPE"] == 'Mobilenet-YOLOv4':
            # MobilenetV2 backbone
            self.backbone, feature_channels = _BuildMobilenetV2(in_channel=cfg.MODEL_INPUT_CHANNEL, weight_path=weight_path, resume=resume)
        elif cfg.MODEL_TYPE["TYPE"] == 'Mobilenetv3-YOLOv4':
            # MobilenetV2 backbone
            self.backbone, feature_channels = _BuildMobilenetV3(in_channel=cfg.MODEL_INPUT_CHANNEL, weight_path=weight_path, resume=resume)
        else:
            assert print('model type must be YOLOv4 or Mobilenet-YOLOv4')

        # Spatial Pyramid Pooling
        self.spp = SpatialPyramidPooling(feature_channels, dims=dims)

        # Path Aggregation Net
        self.panet = PANet(feature_channels, dims=dims)

        # predict
        self.predict_net = PredictNet(feature_channels, out_channels, dims=dims)

    def forward(self, x):
        features = self.backbone(x)
        #print("After backbone:", end="")
        #print(*[m.shape for m in features], sep="\n", end="\n"+"="*20+"\n")
        features[-1] = self.spp(features[-1])
        #print("After SPP:", end=" ")
        #print(*[m.shape for m in features], sep="\n", end="\n"+"="*20+"\n")
        features = self.panet(features)
        #print("After PAN:", end=" ")
        #print(*[m.shape for m in features], sep="\n", end="\n"+"="*20+"\n")
        predicts = self.predict_net(features)
        #print("After predict_net:", end=" ")
        #print(*[m.shape for m in features], sep="\n", end="\n"+"="*20+"\n")
        #raise EOFError
        return predicts

if __name__ == '__main__':
    cuda = torch.cuda.is_available()
    device = torch.device('cuda:{}'.format(0) if cuda else 'cpu')
    model = YOLOv4().to(device)
    x = torch.randn(1, 3, 160, 160).to(device)
    torch.cuda.empty_cache()
    while(1):
        predicts = model(x)
        print(predicts[0].shape)
        print(predicts[1].shape)
        print(predicts[2].shape)
