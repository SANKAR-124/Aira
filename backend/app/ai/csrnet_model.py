import torch
import torch.nn as nn
from torchvision import models
# from utils import save_net, load_net  # original import — utils belongs to the CSRNet repo, not needed here


class CSRNet(nn.Module):
    def __init__(self, load_weights=False):
        """
        Args:
            load_weights: If True, skip VGG16 pre-init (weights will be loaded
                          from a .pth checkpoint externally via load_state_dict).
                          If False, initialise frontend from VGG16 ImageNet weights.
        """
        super(CSRNet, self).__init__()
        self.seen = 0
        self.frontend_feat = [64, 64, 'M', 128, 128, 'M', 256, 256, 256, 'M', 512, 512, 512]
        self.backend_feat = [512, 512, 512, 256, 128, 64]
        self.frontend = make_layers(self.frontend_feat)
        self.backend = make_layers(self.backend_feat, in_channels=512, dilation=True)
        self.output_layer = nn.Conv2d(64, 1, kernel_size=1)

        if not load_weights:
            # Initialise frontend conv layers from VGG16 ImageNet weights.
            # torchvision >= 0.13 uses `weights=` instead of deprecated `pretrained=True`.
            vgg16 = models.vgg16(weights=models.VGG16_Weights.DEFAULT)
            # mod = models.vgg16(pretrained=True)  # original — pretrained kwarg removed in torchvision >= 0.13
            self._initialize_weights()
            # Copy only the matching frontend layers from VGG16 features.
            vgg_items = list(vgg16.state_dict().items())
            frontend_items = list(self.frontend.state_dict().items())
            for i, (key, _) in enumerate(frontend_items):
                self.frontend.state_dict()[key].data[:] = vgg_items[i][1].data[:]
            # original Python 2 loop (broken in Python 3 — xrange and dict.items()[i] don't exist):
            # for i in xrange(len(self.frontend.state_dict().items())):
            #     self.frontend.state_dict().items()[i][1].data[:] = mod.state_dict().items()[i][1].data[:]

    def forward(self, x):
        x = self.frontend(x)
        x = self.backend(x)
        x = self.output_layer(x)
        return x

    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.normal_(m.weight, std=0.01)
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)


def make_layers(cfg, in_channels=3, batch_norm=False, dilation=False):
    d_rate = 2 if dilation else 1
    layers = []
    for v in cfg:
        if v == 'M':
            layers += [nn.MaxPool2d(kernel_size=2, stride=2)]
        else:
            conv2d = nn.Conv2d(in_channels, v, kernel_size=3, padding=d_rate, dilation=d_rate)
            if batch_norm:
                layers += [conv2d, nn.BatchNorm2d(v), nn.ReLU(inplace=True)]
            else:
                layers += [conv2d, nn.ReLU(inplace=True)]
            in_channels = v
    return nn.Sequential(*layers)