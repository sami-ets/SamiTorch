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
import unittest
import numpy as np

from samitorch.utils.parsers import UNetYamlConfigurationParser
from samitorch.models.unet3d import UNet3D, SingleConv, DoubleConv, Encoder, Decoder


def load_test_config():
    return UNetYamlConfigurationParser.parse("samitorch/configs/unet3d.yaml")


class Unet3DTest(unittest.TestCase):

    def setUp(self):
        self.config = load_test_config()
        self.input = torch.rand((2, 1, 32, 32, 32))

    def test_model_should_be_created_with_config(self):
        model = UNet3D(self.config)
        assert isinstance(model, UNet3D)

    def test_model_should_complete_one_forward_pass(self):
        model = UNet3D(self.config)
        output = model(self.input)
        assert isinstance(output, torch.Tensor)

    def test_model_output_should_have_same_dimensions_than_input(self):
        input_dim = np.array(list(self.input.size()))
        model = UNet3D(self.config)
        output = model(self.input)
        output_dim = np.array(list(output.size()))
        np.testing.assert_array_equal(input_dim, output_dim)


class UNet3DModulesTest(unittest.TestCase):

    def setUp(self):
        self.config = load_test_config()
        self.input = torch.rand((2, 1, 32, 32, 32))
        self.input_high_channels = torch.rand(2, 128, 16, 16, 16)
        self.in_channels = 1
        self.out_channels = 64
        self.kernel_size = 3
        self.num_groups = 8
        self.padding = (1, 1, 1, 1, 1, 1)
        self.relu_activation = "ReLU"
        self.leaky_relu_activation = "LeakyReLU"

    def test_single_conv_with_padding_should_give_correct_dimensions(self):
        block = SingleConv(self.in_channels, self.out_channels, self.kernel_size, self.num_groups, self.padding,
                           self.relu_activation)
        output = block(self.input)
        assert output.size() == torch.Size([2, 64, 32, 32, 32])

    def test_single_conv_without_padding_should_give_correct_dimensions(self):
        block = SingleConv(self.in_channels, self.out_channels, self.kernel_size, self.num_groups, None,
                           self.relu_activation)
        output = block(self.input)
        assert output.size() == torch.Size([2, 64, 32, 32, 32])

    def test_single_conv_with_leaky_relu_should_give_correct_instance(self):
        block = SingleConv(self.in_channels, self.out_channels, self.kernel_size, self.num_groups, None,
                           self.leaky_relu_activation)
        assert isinstance(block.activation, torch.nn.LeakyReLU)

    def test_single_conv_with_relu_should_give_correct_instance(self):
        block = SingleConv(self.in_channels, self.out_channels, self.kernel_size, self.num_groups, None,
                           self.relu_activation)
        assert isinstance(block.activation, torch.nn.ReLU)

    def test_single_conv_without_activation_should_instantiate_correctly(self):
        block = SingleConv(self.in_channels, self.out_channels, self.kernel_size, self.num_groups, self.padding,
                           None)
        assert block is not None
        assert block.activation is None

    def test_single_conv_without_group_norm_should_give_correct_instance(self):
        block = SingleConv(self.in_channels, self.out_channels, self.kernel_size, None, None,
                           self.relu_activation)
        assert isinstance(block.norm, torch.nn.BatchNorm3d)

    def test_double_conv_should_give_correct_dimensions(self):
        block = DoubleConv(self.in_channels, self.out_channels, True, self.kernel_size, self.num_groups, self.padding,
                           self.relu_activation)
        output = block(self.input)
        assert output.size() == torch.Size([2, 64, 32, 32, 32])

    def test_encoder_should_give_correct_pooling(self):
        encoder = Encoder(self.in_channels, self.out_channels, DoubleConv, self.config)
        assert hasattr(encoder, "pooling")
        assert isinstance(encoder.pooling, torch.nn.MaxPool3d)

    def test_encoder_should_give_correct_dimension(self):
        encoder = Encoder(self.in_channels, self.out_channels, DoubleConv, self.config)
        output = encoder(self.input)
        assert output.size() == torch.Size([2, 64, 16, 16, 16])

    def test_decoder_should_use_upsampling(self):
        decoder = Decoder(self.out_channels, self.in_channels, DoubleConv, self.config)
        assert hasattr(decoder, "upsample")
        assert decoder.upsample is None
