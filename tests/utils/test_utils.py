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

import unittest
import torch

from utils.utils import to_onehot


class ToOneHotTest(unittest.TestCase):

    def setUp(self):
        pass

    @staticmethod
    def test_to_onehot():
        indices = torch.LongTensor([0, 1, 2, 3])
        actual = to_onehot(indices, 4)
        expected = torch.eye(4)
        assert actual.equal(expected)

        y = torch.randint(0, 21, size=(1000,))
        y_ohe = to_onehot(y, num_classes=21)
        y2 = torch.argmax(y_ohe, dim=1)
        assert y.equal(y2)

        y = torch.randint(0, 21, size=(4, 250, 255))
        y_ohe = to_onehot(y, num_classes=21)
        y2 = torch.argmax(y_ohe, dim=1)
        assert y.equal(y2)

        y = torch.randint(0, 21, size=(4, 150, 155, 4, 6))
        y_ohe = to_onehot(y, num_classes=21)
        y2 = torch.argmax(y_ohe, dim=1)
        assert y.equal(y2)