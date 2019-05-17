# -*- coding: utf-8 -*-
# Copyright 2019 SAMITorch Authors. All Rights Reserved.
#
# Licensed under the MIT License;
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================

import torch

from samitorch.configs.model import ModelConfiguration
from samitorch.factories.factories import ActivationFunctionsFactory, PaddingFactory, PoolingFactory, \
    NormalizationLayerFactory


class UNet3D(torch.nn.Module):
    """
     3DUnet model from `"3D U-Net: Learning Dense Volumetric Segmentation from Sparse Annotation"
        <https://arxiv.org/pdf/1606.06650.pdf>`.

    Args:
        config (dict): Dictionary containing the various model's configuration.
    """

    def __init__(self, config: ModelConfiguration):
        super(UNet3D, self).__init__()

        feature_maps = self._get_feature_maps(config.feature_maps, config.num_levels)

        self.encoders = torch.nn.ModuleList(self._build_encoder(feature_maps, config))

        self.decoders = torch.nn.ModuleList(self._build_decoder(feature_maps, config))

        self.final_conv = torch.nn.Conv3d(feature_maps[0], config.out_channels, 1)

        self.final_activation = torch.nn.Softmax(dim=1)

    @staticmethod
    def _get_feature_maps(starting_feature_maps, num_levels):
        return [starting_feature_maps * 2 ** k for k in range(num_levels)]

    @staticmethod
    def _build_encoder(feature_maps: list, config: ModelConfiguration):
        encoders = []
        for i, num_out_features in enumerate(feature_maps):
            if i == 0:
                encoder = Encoder(config.in_channels, num_out_features, DoubleConv, config,
                                  apply_pooling=False)
            else:
                encoder = Encoder(feature_maps[i - 1], num_out_features, DoubleConv, config,
                                  apply_pooling=True)
            encoders.append(encoder)
        return encoders

    @staticmethod
    def _build_decoder(feature_maps, config_decoder):
        decoders = []
        reversed_feature_maps = list(reversed(feature_maps))
        for i in range(len(reversed_feature_maps) - 1):
            in_feature_num = reversed_feature_maps[i] + reversed_feature_maps[i + 1]
            out_feature_num = reversed_feature_maps[i + 1]
            decoder = Decoder(in_feature_num, out_feature_num, DoubleConv, config_decoder)
            decoders.append(decoder)
        return decoders

    def forward(self, x):
        encoders_features = []
        for encoder in self.encoders:
            x = encoder(x)
            # reverse the encoder outputs to be aligned with the decoder
            encoders_features.insert(0, x)

        # remove the last encoder's output from the list
        encoders_features = encoders_features[1:]

        for decoder, encoder_features in zip(self.decoders, encoders_features):
            x = decoder(encoder_features, x)

        x = self.final_conv(x)

        x = self.final_activation(x)

        return x


class SingleConv(torch.nn.Module):
    """
    A module consisting of a single convolution layer, which is composed of a Replication Padding + Convolution +
    Normalization.

    Args:
        in_channels (int): Number of input channels.
        out_channels (int): Number of output channels.
        kernel_size (int): The size of the convolving kernel.
        num_groups (int): The number of groups for the GroupNorm.
        padding (tuple): The size of padding to add around the image.
        activation (str): The desired activation function in each block.
    """

    def __init__(self, in_channels: int, out_channels: int, kernel_size: int = 3, num_groups: int = None,
                 padding: tuple = None, activation: str = None):
        super(SingleConv, self).__init__()
        self._padding_factory = PaddingFactory()
        self._activation_factory = ActivationFunctionsFactory()
        self._normalization_factory = NormalizationLayerFactory()

        if padding is not None:
            self.padding = self._padding_factory.get_layer("ReplicationPad3d", padding)
            self.conv = torch.nn.Conv3d(in_channels, out_channels, kernel_size)
        else:
            self.padding = None
            self.conv = torch.nn.Conv3d(in_channels, out_channels, kernel_size, padding=1)

        if num_groups is not None:
            assert isinstance(num_groups, int)
            self.norm = self._normalization_factory.get_layer("GroupNorm", num_groups, out_channels)
        else:
            self.norm = self._normalization_factory.get_layer("BatchNorm3d", out_channels)

        if activation is not None:
            self.activation = self._activation_factory.get_layer(activation, True)
        else:
            self.activation = None

    def forward(self, x):
        """
         Forward pass on a SingleConv module.
         Args:
             x (:obj:`torch.Tensor`): An input tensor.

         Returns:
             :obj:`torch.Tensor`: The transformed tensor.
         """
        if self.padding is not None:
            x = self.padding(x)

        x = self.conv(x)

        x = self.norm(x)

        if self.activation is not None:
            x = self.activation(x)
        return x


class DoubleConv(torch.nn.Module):
    """
    A module consisting of two consecutive convolution layers (e.g. Convolution Layer + Normalization layer +
    Activation layer).
    Use padded convolutions to make sure that the output (H_out, W_out) is the same
    as (H_in, W_in), so that you don't have to crop in the decoder path.

    Args:
        in_channels (int): Number of input channels.
        out_channels (int): Number of output channels.
        is_in_encoder (bool): If True we're in the encoder path, otherwise we're in the decoder.
        kernel_size (int): The size of the convolving kernel.
        num_groups (int): The number of groups for the GroupNorm.
        padding (tuple): The size of padding to add around the image.
        activation (str): The desired activation function in each block.
    """

    def __init__(self, in_channels: int, out_channels: int, is_in_encoder: bool, kernel_size: int = 3,
                 num_groups: int = 8, padding: tuple = None, activation: str = None):
        super(DoubleConv, self).__init__()

        if is_in_encoder:
            conv1_in_channels = in_channels
            conv1_out_channels = out_channels // 2

            if conv1_out_channels < in_channels:
                conv1_out_channels = in_channels

            conv2_in_channels, conv2_out_channels = conv1_out_channels, out_channels

        else:
            conv1_in_channels, conv1_out_channels = in_channels, out_channels
            conv2_in_channels, conv2_out_channels = out_channels, out_channels

        self.conv1 = SingleConv(conv1_in_channels, conv1_out_channels, kernel_size, num_groups, padding, activation)
        self.conv2 = SingleConv(conv2_in_channels, conv2_out_channels, kernel_size, num_groups, padding, activation)

    def forward(self, x):
        """
        Forward pass on a DoubleConv module.
        Args:
            x (:obj:`torch.Tensor`): An input tensor.

        Returns:
            :obj:`torch.Tensor`: The transformed tensor.
        """
        x = self.conv1(x)
        x = self.conv2(x)
        return x


class Encoder(torch.nn.Module):
    """
    A single module for the UNet encoder path.

    Args:
        in_channels (int): Number of input channels
        out_channels (int): Number of output channels
        basic_module (:obj:`torch.nn.Module`): Either ResNetBlock or DoubleConv
        config (dict): Dictionary containing standard Encoder configuration.
        apply_pooling (bool): If True use MaxPool3d before DoubleConv
    """

    def __init__(self, in_channels: int, out_channels: int, basic_module: torch.nn.Module,
                 config: ModelConfiguration, apply_pooling: bool = True):
        super(Encoder, self).__init__()
        self._pooling_factory = PoolingFactory()

        if apply_pooling:
            self.pooling = self._pooling_factory.get_layer(config.pooling_type, config.pool_kernel_size)
        else:
            self.pooling = None

        self.basic_module = basic_module(in_channels, out_channels,
                                         is_in_encoder=True,
                                         kernel_size=config.conv_kernel_size,
                                         num_groups=config.num_groups,
                                         padding=config.padding,
                                         activation=config.activation)

    def forward(self, x):
        """
         Forward pass on the Encoder module.
         Args:
             x (:obj:`torch.Tensor`): An input tensor.

         Returns:
             :obj:`torch.Tensor`: The transformed tensor.
         """
        if self.pooling is not None:
            x = self.pooling(x)
        x = self.basic_module(x)
        return x


class Decoder(torch.nn.Module):
    """
    A single module for decoder path consisting of the upsample layer
    (either learned ConvTranspose3d or interpolation) followed by a DoubleConv
    module.
    Args:
        in_channels (int): number of input channels.
        out_channels (int): number of output channels.
        basic_module(:obj:`torch.nn.Module`): either ResNetBlock or DoubleConv.
        config (dict): The rest of the configuration for the decoder part of the network.
    """

    def __init__(self, in_channels: int, out_channels: int, basic_module: torch.nn.Module,
                 config: ModelConfiguration):
        super(Decoder, self).__init__()

        if config.interpolation:
            self.upsample = None
        else:
            # Otherwise use ConvTranspose3d (bear in mind your GPU memory)
            # make sure that the output size reverses the MaxPool3d from the corresponding encoder
            # (D_out = (D_in − 1) ×  stride[0] − 2 ×  padding[0] +  kernel_size[0] +  output_padding[0])
            # also scale the number of channels from in_channels to out_channels so that summation joining
            # works correctly
            self.upsample = torch.nn.ConvTranspose3d(in_channels,
                                                     out_channels,
                                                     kernel_size=config.conv_kernel_size,
                                                     stride=config.scale_factor,
                                                     padding=torch.nn.ReplicationPad3d(config.padding),
                                                     output_padding=1)
            # adapt the number of in_channels for the ExtResNetBlock
            in_channels = out_channels
        self.basic_module = basic_module(in_channels, out_channels,
                                         is_in_encoder=False,
                                         kernel_size=config.conv_kernel_size,
                                         num_groups=config.num_groups,
                                         padding=config.padding,
                                         activation=config.activation)

    def forward(self, encoder_features, x):
        """
         Forward pass on a Decoder module.
         Args:
             encoder_features (:obj:`torch.Tensor`): The encoder's features to concatenate into the decoding path.
             x (:obj:`torch.Tensor`): An input tensor.

         Returns:
             :obj:`torch.Tensor`: The transformed tensor.
         """
        if self.upsample is None:
            # use nearest neighbor interpolation and concatenation joining
            output_size = encoder_features.size()[2:]
            x = torch.nn.functional.interpolate(x, size=output_size, mode='nearest')
            # concatenate encoder_features (encoder path) with the upsampled input across channel dimension
            x = torch.cat((encoder_features, x), dim=1)
        else:
            # use ConvTranspose3d and summation joining
            x = self.upsample(x)
            x += encoder_features

        x = self.basic_module(x)
        return x